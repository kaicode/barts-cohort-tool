from fastapi import APIRouter 
from pydantic import BaseModel
from typing import List, Union, Optional
import pyodbc
from app.config import settings
import app.services.fhir_client as fhir_client
from fastapi.concurrency import run_in_threadpool
import pandas as pd
import os
import json
import math

router = APIRouter()
client = fhir_client.FHIRClient()

# Database connection function
def get_db_connection():
    try:
        conn = pyodbc.connect(settings.dw_connection)
        print("Connected to SQL Server successfully!")
    except Exception as e:
        print("Connection failed:", e)
        conn = None
    return conn

# Pydantic models
class AgeRange(BaseModel):
    min: int
    max: int

class CodeEntry(BaseModel):
    code: str
    display: Optional[str]

class CodeDetail(BaseModel):
    code: str
    display: Optional[str]
    count: Optional[int]

class FindingItem(BaseModel):
    code: List[CodeEntry]
    display: Optional[str]
    count: Optional[int]
    codesWithDetails: Optional[List[CodeDetail]]

class TimeRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None

class CohortDefinition(BaseModel):
    title: str
    gender: Union[str, List[CodeEntry]]
    ageRange: AgeRange
    ethnicity: Union[str, List[CodeEntry]]
    timeRange: Optional[TimeRange]
    mustHaveFindings: Optional[List[FindingItem]]
    mustNotHaveFindings: Optional[List[FindingItem]]

# Helper function to fetch SNOMED display name
def get_snomed_display(code: str) -> str:
    try:
        snomed_display = client.search_snomed(code, "", 1)
        return snomed_display.get('entry', [{}])[0].get('resource', {}).get('display', 'Unknown')
    except Exception as e:
        print(f"Error fetching SNOMED display for {code}: {e}")
        return 'Unknown'
    
    
def fetch_from_db(query, params):
    """
    Synchronous function to run a SQL query and return a DataFrame.
    """
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

@router.post("/cohort/select")
async def run_select(cohort_definition: CohortDefinition):
    output_folder = settings.saved_searches
    filename = os.path.join(output_folder, f"{cohort_definition.title.replace(' ', '_')}.json")

    # Save definition as JSON
    with open(filename, "w") as f:
        json.dump(cohort_definition.dict(), f, indent=4)

    # Extract demographics
    displays_gender = []
    if cohort_definition.gender != 'ALL':
        displays_gender = [entry.display for entry in cohort_definition.gender]
        
    displays_ethnicity = []
    if cohort_definition.ethnicity != 'ALL':
        displays_ethnicity = [entry.display for entry in cohort_definition.ethnicity]

    minAge = cohort_definition.ageRange.min
    maxAge = cohort_definition.ageRange.max
    start_date = cohort_definition.timeRange.start if cohort_definition.timeRange else None
    end_date = cohort_definition.timeRange.end if cohort_definition.timeRange else None

    # Build gender/ethnicity lists
    gender = cohort_definition.gender
    if isinstance(gender, str):
        gender_list = [{"code": gender, "display": gender}]
    else:
        gender_list = [{"code": item.code, "display": item.display} for item in gender]

    ethnicity = cohort_definition.ethnicity
    if isinstance(ethnicity, str):
        ethnicity_list = [{"code": ethnicity, "display": ethnicity}]
    else:
        ethnicity_list = [{"code": item.code, "display": item.display} for item in ethnicity]

    # Must-have & must-not-have codes
    musthaveSnomedCodes = set()  # ensure uniqueness

    if cohort_definition.mustHaveFindings:
        for item in cohort_definition.mustHaveFindings:
            if item.codesWithDetails:
                for detail in item.codesWithDetails:
                    if detail.code:
                        musthaveSnomedCodes.add(detail.code)
                            
    mustNOThaveDiagnosisNames = []
    
    mustNOThaveSnomedCodes = []
    if cohort_definition.mustNotHaveFindings:
        for item in cohort_definition.mustNotHaveFindings:
            if item.codesWithDetails:
                for detail in item.codesWithDetails:
                    if detail.code:
                        mustNOThaveSnomedCodes.append(detail.code)
                    
                    if detail.display:
                        mustNOThaveDiagnosisNames.append(detail.display)     
    
    # Base SELECT and JOIN statements
    base_query = settings.sql_query
    
    # Build WHERE conditions and parameters
    where_conditions = []
    params = []
    
    if displays_gender:
        placeholders_gender = ', '.join(['?'] * len(displays_gender))
        where_conditions.append(f"b.Gender IN ({placeholders_gender})")
        params.extend(displays_gender)
    
    if displays_ethnicity:
        placeholders_ethnicity = ', '.join(['?'] * len(displays_ethnicity))
        where_conditions.append(f"b.Ethnicity IN ({placeholders_ethnicity})")
        params.extend(displays_ethnicity)
    
    # Age range condition
    where_conditions.append("(YEAR(GETDATE()) - b.Year_of_Birth) BETWEEN ? AND ?")
    params.extend([minAge, maxAge])
    
    if start_date and end_date:
        where_conditions.append("a.Adm_Dt >= ? AND a.Adm_Dt <= ?")
        params.extend([start_date, end_date])
    
    if musthaveSnomedCodes:
        placeholders_have = ', '.join(['?'] * len(musthaveSnomedCodes))
        where_conditions.append(f"c.DiagCode IN ({placeholders_have})")
        params.extend(musthaveSnomedCodes)
    
    if mustNOThaveSnomedCodes:
        placeholders_nothave = ', '.join(['?'] * len(mustNOThaveSnomedCodes))
        where_conditions.append(f"c.DiagCode NOT IN ({placeholders_nothave})")
        params.extend(mustNOThaveSnomedCodes)
    
    # Final query
    where_clause = " AND ".join(where_conditions)
    final_query = f"""
        {base_query}
        WHERE {where_clause}
        GROUP BY b.Gender, b.Ethnicity, c.DiagCode, a.Adm_Dt, c.Diagnosis, b.Year_of_Birth
    """

    # print('final query')
    # print(final_query)
    
    # print('params')
    # print(params)
    
    # Run the query
    df_results = pd.DataFrame()
    df_results = await run_in_threadpool(fetch_from_db, final_query, params)
        
    # Total patients
    total_patients = df_results["patient_count"].sum()

    # print("Total patients")
    # print(total_patients)

    # Adding any included diagnoses with the count of zero
    # Group by Diagnosis from df_results
    if not df_results.empty:
        # Ensure DiagCode is string
        df_results["DiagCode"] = df_results["DiagCode"].astype(str)
        
        # Aggregate counts
        diag_counts = df_results.groupby("DiagCode")["patient_count"].sum().to_dict()
    else:
        diag_counts = {}


    diagnoses_included = []

    # Apply disclosure control: if <10, return 0
    if total_patients < 10:
        total_patients = 0
        
        gender_counts, age_groups, ethnicity_counts, results_json, admissions_by_month, admissions_by_diagnosis = [], [], [], [], [], []
        
        age_min = "NA"
        age_max = "NA"
        
    else:
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
                .to_dict(orient="records")
            )

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
                .to_dict(orient="records")
            )

            # Ethnicity counts
            ethnicity_counts = (
                df_results.groupby("Ethnicity")["patient_count"]
                .sum()
                .reset_index()
                .rename(columns={"Ethnicity": "ethnicity", "patient_count": "count"})
                .to_dict(orient="records")
            )
            
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
                .to_dict(orient="records")
            )
            
            # --- Diagnoses included ---
            # Ensure DiagCode is string
            df_results["DiagCode"] = df_results["DiagCode"].astype(str)
            
            # Aggregate counts by code
            diagnoses_included = (
                df_results.groupby(["DiagCode", "Diagnosis"], as_index=False)["patient_count"]
                .sum()
                .reset_index()
                .rename(columns={"DiagCode": "code", "Diagnosis": "diagnosis", "patient_count": "count"})
                .to_dict(orient="records")
            )
            
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
    musthave_code_display = {}
    if cohort_definition.mustHaveFindings:
        for item in cohort_definition.mustHaveFindings:
            if item.codesWithDetails:
                for detail in item.codesWithDetails:
                    if detail.code:
                        code = str(detail.code)                  # key = code
                        display = detail.display or code         # value = display
                        musthave_code_display[code] = display
                        
    # print(musthave_code_display)

    # Build a new list in the correct order
    ordered_diagnoses = []

    for code, display in musthave_code_display.items():
        # Find the existing entry, if any
        existing_entry = next((e for e in diagnoses_included if str(e["code"]) == code), None)
        if existing_entry:
            # Update diagnosis display
            existing_entry["diagnosis"] = display
            ordered_diagnoses.append(existing_entry)
        else:
            # Add missing entry with count=0
            ordered_diagnoses.append({"code": code, "diagnosis": display, "count": 0})

    diagnoses_included = ordered_diagnoses    

            
    # print(admissions_by_month)

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
        }

    if musthaveSnomedCodes:
        results_payload["diagnoses_included"] = diagnoses_included
       

    if mustNOThaveSnomedCodes:
        results_payload["diagnoses_excluded"] = mustNOThaveDiagnosisNames


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