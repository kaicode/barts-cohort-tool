# -*- coding: utf-8 -*-
"""
Created on Wed May 13 12:43:31 2026

@author: c_piazzese
"""


from fastapi import APIRouter 
from pydantic import BaseModel
from typing import List, Union, Optional
import pyodbc
from app.config import settings
import app.services.fhir_client as fhir_client
from fastapi.concurrency import run_in_threadpool
from datetime import datetime
import pandas as pd
import os
import json
import math

router = APIRouter()
client = fhir_client.FHIRClient()


def get_db_connection():
    try:
        conn = pyodbc.connect(settings.dw_connection)
        print("Connected to SQL Server successfully!")
    except Exception as e:
        print("Connection failed:", e)
        conn = None
    return conn


class AgeRange(BaseModel):
    min: int
    max: int


class CodeEntry(BaseModel):
    code: str
    display: Optional[str]


class TimeRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None

    
class CodeDetail(BaseModel):
    code: str
    display: Optional[str]
    count: Optional[int]
    codeType: Optional[str] = None
    timeFrame: Optional[TimeRange] = None
    

class FindingItem(BaseModel):
    code: List[CodeEntry]
    display: Optional[str]
    count: Optional[int]
    codesWithDetails: Optional[List[CodeDetail]]
    timeFrame: Optional[TimeRange] = None


class CohortDefinition(BaseModel):
    title: str
    gender: Union[str, List[CodeEntry]]
    ageRange: AgeRange
    ethnicity: Union[str, List[CodeEntry]]
    timeRange: Optional[TimeRange]
    mustHaveFindings: Optional[List[FindingItem]]
    mustNotHaveFindings: Optional[List[FindingItem]]


def fetch_from_db(query, params):
    df = pd.DataFrame()
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            df = pd.DataFrame.from_records(rows, columns=columns)
        finally:
            cursor.close()
            conn.close()
    return df


def anonymise_count(value, threshold=10):
    if value < threshold:
        return 0
    return round(value / 10) * 10


@router.post("/cohort/select")
async def run_select(cohort_definition: CohortDefinition):
    
    datetime_mail = datetime.now().strftime("%d %B %Y, %H:%M")
    datetime_title = datetime_mail.replace(",", "").replace(":", "_").replace(" ", "_")

    output_folder = settings.saved_searches
    filename = os.path.join(output_folder, f"{cohort_definition.title.replace(' ', '_')}_selected_criteria_{datetime_title}.json")
    
    with open(filename, "w") as f:
            json.dump(cohort_definition.model_dump(), f, indent=4, allow_nan=True)

    displays_gender = []
    if cohort_definition.gender != "ALL":
        displays_gender = [entry.display for entry in cohort_definition.gender]

    displays_ethnicity = []
    if cohort_definition.ethnicity != "ALL":
        displays_ethnicity = [entry.display for entry in cohort_definition.ethnicity]

    minAge = cohort_definition.ageRange.min
    maxAge = cohort_definition.ageRange.max

    start_date = cohort_definition.timeRange.start if cohort_definition.timeRange else None
    end_date = cohort_definition.timeRange.end if cohort_definition.timeRange else None

    musthaveSnomedCodes = set()
    musthave_filters = []

    if cohort_definition.mustHaveFindings:
        for item in cohort_definition.mustHaveFindings:
            codes = []

            if item.codesWithDetails:
                for detail in item.codesWithDetails:
                    if detail.code:
                        codes.append(detail.code)
                        musthaveSnomedCodes.add(detail.code)

            if codes:
                musthave_filters.append({
                    "codes": codes,
                    "start": item.timeFrame.start if item.timeFrame else None,
                    "end": item.timeFrame.end if item.timeFrame else None,
                })

    mustNOThaveDiagnosisDetails = []
    mustNOThaveSnomedCodes = []
    mustNOT_filters = []

    if cohort_definition.mustNotHaveFindings:
        for item in cohort_definition.mustNotHaveFindings:
            codes = []

            if item.codesWithDetails:
                for detail in item.codesWithDetails:
                    if detail.code:
                        codes.append(detail.code)
                        mustNOThaveSnomedCodes.append(detail.code)

                    if detail.display:
                        mustNOThaveDiagnosisDetails.append({
                            "code": str(detail.code),
                            "diagnosis": detail.display,
                            "codeType": detail.codeType or "Child code",
                            "timeFrame": {
                                "start": detail.timeFrame.start if detail.timeFrame else (
                                    item.timeFrame.start if item.timeFrame else None
                                ),
                                "end": detail.timeFrame.end if detail.timeFrame else (
                                    item.timeFrame.end if item.timeFrame else None
                                ),
                            },
                        })

            if codes:
                mustNOT_filters.append({
                    "codes": codes,
                    "start": item.timeFrame.start if item.timeFrame else None,
                    "end": item.timeFrame.end if item.timeFrame else None,
                })

    base_query = settings.sql_query

    where_conditions = []
    params = []

    if displays_gender:
        placeholders_gender = ", ".join(["?"] * len(displays_gender))
        where_conditions.append(f"b.Gender IN ({placeholders_gender})")
        params.extend(displays_gender)

    if displays_ethnicity:
        placeholders_ethnicity = ", ".join(["?"] * len(displays_ethnicity))
        where_conditions.append(f"b.Ethnicity IN ({placeholders_ethnicity})")
        params.extend(displays_ethnicity)

    where_conditions.append("(YEAR(GETDATE()) - b.Year_of_Birth) BETWEEN ? AND ?")
    params.extend([minAge, maxAge])

    if start_date and end_date:
        where_conditions.append("a.Adm_Dt >= ? AND a.Adm_Dt <= ?")
        params.extend([start_date, end_date])

    if musthave_filters:
        snomed_blocks = []

        for f in musthave_filters:
            block_conditions = []

            placeholders_have = ", ".join(["?"] * len(f["codes"]))
            block_conditions.append(f"c.DiagCode IN ({placeholders_have})")
            params.extend(f["codes"])

            if f["start"]:
                block_conditions.append("c.DiagDt >= ?")
                params.append(f["start"])

            if f["end"]:
                block_conditions.append("c.DiagDt <= ?")
                params.append(f["end"])

            snomed_blocks.append("(" + " AND ".join(block_conditions) + ")")

        where_conditions.append("(" + " OR ".join(snomed_blocks) + ")")

    if mustNOT_filters:

        for f in mustNOT_filters:
    
            exclusion_conditions = []
    
            placeholders_not = ", ".join(["?"] * len(f["codes"]))
    
            exclusion_conditions.append(
                f"""
                COALESCE(
                    l2.SNOMED_ConceptId,
                    CAST(c2.DiagCode AS VARCHAR(200))
                ) IN ({placeholders_not})
                """
            )
    
            params.extend(f["codes"])
    
            if f["start"]:
                exclusion_conditions.append("c2.DiagDt >= ?")
                params.append(f["start"])
    
            if f["end"]:
                exclusion_conditions.append("c2.DiagDt <= ?")
                params.append(f["end"])
    
            where_conditions.append(
                f"""
                NOT EXISTS (
                    SELECT 1
                    FROM [dbo].[rde_cds_apc_PCT] a2 WITH(NOLOCK)
    
                    INNER JOIN [dbo].[rde_pc_diagnosis_PCT] c2 WITH(NOLOCK)
                        ON a2.PERSON_ID = c2.PERSON_ID
    
                    LEFT JOIN [dbo].[SNOMED_lookup_PCT] l2 WITH(NOLOCK)
                        ON c2.DiagCode = l2.SNOMED_DescriptionId
    
                    WHERE a2.PERSON_ID = b.PERSON_ID
                    AND {' AND '.join(exclusion_conditions)}
                )
                """
            )
    
    # Build final WHERE clause
    where_clause = " AND ".join(where_conditions)

    final_query = f"""
        {base_query}
        WHERE {where_clause}
        GROUP BY b.Gender, b.Ethnicity, c.DiagCode, a.Adm_Dt, c.Diagnosis, b.Year_of_Birth
    """
    
    # print(final_query)
    
    # Saving query 
    filename_query = os.path.join(output_folder, f"{cohort_definition.title.replace(' ', '_')}_final_query_{datetime_title}.json")

    with open(filename_query, "w", encoding="utf-8") as f:
        f.write(final_query)    

    df_results = await run_in_threadpool(fetch_from_db, final_query, params)

    total_patients = df_results["patient_count"].sum()

    if not df_results.empty:
        df_results["DiagCode"] = df_results["DiagCode"].astype(str)
    else:
        df_results = pd.DataFrame()

    diagnoses_included = []

    # Apply disclosure control: if <10, return 0
    if total_patients < 10:
        total_patients = 0
        
        gender_counts, age_groups, ethnicity_counts, results_json, admissions_by_month, admissions_by_diagnosis = [], [], [], [], [], []
        
        age_min = "NA"
        age_max = "NA"
        
    else:
        
        # approximating to the nearest 10 
        total_patients = round(total_patients / 10) * 10
        
        # Build aggregated results for frontend
        if not df_results.empty:
            # Ensure DiagCode is string
            df_results["DiagCode"] = df_results["DiagCode"].astype(str)

            # Gender counts
            gender_counts = (
                df_results.groupby("Gender")["patient_count"]
                .sum()
                .reset_index()
                .rename(columns={"Gender": "gender", "patient_count": "count"})
            )
            
            gender_counts["count"] = gender_counts["count"].apply(anonymise_count)
            gender_counts = gender_counts.to_dict(orient="records")

            # Age groups (bucket by decades)
            current_year = pd.to_datetime("today").year
            df_results["Age"] = current_year - df_results["Year_of_Birth"]
            
            bins = [18, 30, 40, 50, 60, 70, 80, 90, 100, float("inf")]
            labels = ["18-29","30-39","40-49","50-59","60-69","70-79","80-89","90-99","100+"]
            
            df_results["AgeGroup"] = pd.cut(df_results["Age"], bins=bins, labels=labels, right=False)
            
            # Ensure all labels appear even if count is 0
            age_groups = (
                df_results.groupby("AgeGroup", observed=True)["patient_count"]
                .sum()
                .reindex(labels, fill_value=0)  # <-- reindex ensures missing groups appear with 0
                .reset_index()
                .rename(columns={"AgeGroup": "range", "patient_count": "count"})
            )
            
            age_groups["count"] = age_groups["count"].apply(anonymise_count)
            age_groups = age_groups.to_dict(orient="records")

            # Ethnicity counts
            ethnicity_counts = (
                df_results.groupby("Ethnicity")["patient_count"]
                .sum()
                .reset_index()
                .rename(columns={"Ethnicity": "ethnicity", "patient_count": "count"})
            )
            
            ethnicity_counts["count"] = ethnicity_counts["count"].apply(anonymise_count)
            ethnicity_counts = ethnicity_counts.to_dict(orient="records")
            
            # Overall age range
            if df_results["Age"].notna().any():
                age_min = int(df_results["Age"].min(skipna=True))
                age_max = int(df_results["Age"].max(skipna=True))
            else:
                age_min = "NA"
                age_max = "NA"
                
            # --- Admissions by Month-Year ---
            df_results["Adm_Dt"] = pd.to_datetime(df_results["Adm_Dt"])
            df_results["Month_Year"] = df_results["Adm_Dt"].dt.to_period('M').astype(str)
            
            admissions_by_month = (
                df_results.groupby("Month_Year")["patient_count"]
                .sum()
                .reset_index()
                .rename(columns={"Month_Year": "monthYear", "patient_count": "count"})
            )
            
            admissions_by_month["count"] = admissions_by_month["count"].apply(anonymise_count)
            admissions_by_month = admissions_by_month.to_dict(orient="records")
            
            # --- Diagnoses included ---
            # Ensure DiagCode is string
            df_results["DiagCode"] = df_results["DiagCode"].astype(str)
            
            # Aggregate counts by code
            diagnoses_included = (
                df_results.groupby(["DiagCode", "Diagnosis"], as_index=False)["patient_count"]
                .sum()
                .reset_index()
                .rename(columns={"DiagCode": "code", "Diagnosis": "diagnosis", "patient_count": "count"})
            )
            
            diagnoses_included["count"] = diagnoses_included["count"].apply(anonymise_count)
            diagnoses_included = diagnoses_included.to_dict(orient="records")
            
            # print(diagnoses_included)
            
            # Raw results
            results_json = df_results.to_dict(orient="records")
        else:
            gender_counts, age_groups, ethnicity_counts, results_json, admissions_by_month, admissions_by_diagnosis = [], [], [], [], [], []
            
            age_min = "NA"
            age_max = "NA"

    # Build a set of diagnoses already included
    if diagnoses_included:
        existing_diagnoses = {d["diagnosis"] for d in diagnoses_included}
        

    # Build mapping: DISPLAY -> CODE for must-have findings
    # Build mapping: CODE -> DISPLAY
    musthave_code_details = {}
    
    if cohort_definition.mustHaveFindings:
        for item in cohort_definition.mustHaveFindings:
            if item.codesWithDetails:
                for detail in item.codesWithDetails:
                    if detail.code:
                        code = str(detail.code)
                        musthave_code_details[code] = {
                            "diagnosis": detail.display or code,
                            "codeType": detail.codeType or "Child code",
                            "timeFrame": {
                                "start": detail.timeFrame.start if detail.timeFrame else (
                                    item.timeFrame.start if item.timeFrame else None
                                ),
                                "end": detail.timeFrame.end if detail.timeFrame else (
                                    item.timeFrame.end if item.timeFrame else None
                                ),
                            },
                        }
                        
    # print(musthave_code_details)

    # Build a new list in the correct order
    ordered_diagnoses = []

    for code, detail_info in musthave_code_details.items():
        existing_entry = next(
            (e for e in diagnoses_included if str(e["code"]) == code),
            None
        )
    
        if existing_entry:
            existing_entry["diagnosis"] = detail_info["diagnosis"]
            existing_entry["codeType"] = detail_info["codeType"]
            existing_entry["timeFrame"] = detail_info["timeFrame"]
            ordered_diagnoses.append(existing_entry)
        else:
            ordered_diagnoses.append({
                "code": code,
                "diagnosis": detail_info["diagnosis"],
                "codeType": detail_info["codeType"],
                "count": 0,
                "timeFrame": detail_info["timeFrame"],
            })
            
    diagnoses_included = ordered_diagnoses   

            
    # print(admissions_by_month)

    def build_timeframe_label(findings):
        if not findings:
            return None
    
        labels = []
    
        for item in findings:
            start = item.timeFrame.start if item.timeFrame else None
            end = item.timeFrame.end if item.timeFrame else None
    
            if start or end:
                labels.append(f"Timeframe: {start or 'Any'} to {end or 'Any'}")
    
        return "; ".join(labels) if labels else None


    results_payload = {
        "title": cohort_definition.title,
        "total_patients": int(total_patients),
        "minAge": age_min,
        "maxAge": age_max,
        "genderCounts": gender_counts,
        "ageGroups": age_groups,
        "ethnicityCounts": ethnicity_counts,
        "admissions_by_month": admissions_by_month,
        "results": results_json,
        "diagnoses_included_timeframe": build_timeframe_label(cohort_definition.mustHaveFindings),
        "diagnoses_excluded_timeframe": build_timeframe_label(cohort_definition.mustNotHaveFindings),
    }

    if musthaveSnomedCodes:
        results_payload["diagnoses_included"] = diagnoses_included
       

    if mustNOThaveSnomedCodes:
        results_payload["diagnoses_excluded"] = mustNOThaveDiagnosisDetails


    def sanitize_for_json(obj):
        """Recursively replace NaN/inf with None in dicts/lists."""
        if isinstance(obj, dict):
            return {k: sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_for_json(v) for v in obj]
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
        return obj

    # Apply to both payloads in one line
    results_payload = sanitize_for_json(results_payload) 
    
    return results_payload