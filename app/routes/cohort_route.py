from fastapi import APIRouter 
from pydantic import BaseModel
from typing import List, Union, Optional
import pyodbc
from app.config import settings
import app.services.fhir_client as fhir_client
import pandas as pd
import os
import json

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
    musthaveSnomedCodes = []
    if cohort_definition.mustHaveFindings:
        for item in cohort_definition.mustHaveFindings:
            if item.codesWithDetails:
                for detail in item.codesWithDetails:
                    if detail.code:
                        musthaveSnomedCodes.append(detail.code)
    
    mustNOThaveSnomedCodes = []
    if cohort_definition.mustNotHaveFindings:
        for item in cohort_definition.mustNotHaveFindings:
            if item.codesWithDetails:
                for detail in item.codesWithDetails:
                    if detail.code:
                        mustNOThaveSnomedCodes.append(detail.code)
    
    # Base SELECT and JOIN statements
    base_query = """
        SELECT 
            a.Adm_Dt, 
            b.Gender, 
            b.Ethnicity,
            CAST(c.DiagCode AS VARCHAR(50)) AS DiagCode,
            c.Diagnosis, 
            b.Year_of_Birth,
            COUNT(*) AS patient_count
        FROM [synth].[rde_cds_apc_PCT] a WITH(NOLOCK) 
        INNER JOIN [synth].[rde_patient_demographics_PCT] b WITH(NOLOCK) 
        ON a.PERSON_ID = b.PERSON_ID
        INNER JOIN [synth].[rde_pc_diagnosis_PCT] c WITH(NOLOCK)
        ON b.PERSON_ID = c.PERSON_ID
    """
    
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

    
    # Run the query
    df_results = pd.DataFrame()
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(final_query, params)
        column_names = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        df_results = pd.DataFrame.from_records(rows, columns=column_names)
        cursor.close()
        conn.close()
        
    # Total patients
    total_patients = df_results["patient_count"].sum()
    
    
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
        df_results["AgeGroup"] = (df_results["Age"] // 10 * 10).astype(str) + "-" + (
            (df_results["Age"] // 10 * 10 + 9).astype(str)
        )
        age_groups = (
            df_results.groupby("AgeGroup")["patient_count"]
            .sum()
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
        age_min = df_results["Age"].min()
        age_max = df_results["Age"].max()

        # Raw results
        results_json = df_results.to_dict(orient="records")
    else:
        gender_counts, age_groups, ethnicity_counts, results_json = [], [], [], []

    
    return {
        "title": cohort_definition.title,
        "total_patients": int(total_patients),
        "minAge": int(age_min),
        "maxAge": int(age_max),        
        "genderCounts": gender_counts,
        "ageGroups": age_groups,
        "ethnicityCounts": ethnicity_counts,
        "results": results_json
    }
