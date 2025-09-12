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
    # Assuming you have a way to fetch the display name for a SNOMED code
    # This could be a call to an API or a database query
    try:
        snomed_display = client.search_snomed(code, "", 1)
        return snomed_display.get('entry', [{}])[0].get('resource', {}).get('display', 'Unknown')
    except Exception as e:
        print(f"Error fetching SNOMED display for {code}: {e}")
        return 'Unknown'

@router.post("/cohort/select")

async def run_select(cohort_definition: CohortDefinition):
    
    # print(CohortDefinition)
    
    # Define the folder and filename
    output_folder = settings.saved_searches  # change to your desired folder
    print(output_folder)
    # os.makedirs(output_folder, exist_ok=True)  # create folder if it doesn't exist
    filename = os.path.join(output_folder, f"{cohort_definition.title.replace(' ', '_')}.json")
    
    # Convert Pydantic model to dict and save as JSON
    with open(filename, "w") as f:
        json.dump(cohort_definition.dict(), f, indent=4)

    print(f"CohortDefinition saved to {filename}")

    displays_gender = []
    # Extract display values
    if cohort_definition.gender != 'ALL':
        displays_gender = [entry.display for entry in cohort_definition.gender]
        
    displays_ethnicity = []
    if cohort_definition.ethnicity != 'ALL':
        displays_ethnicity = [entry.display for entry in cohort_definition.ethnicity]

    # Extract age and date range
    minAge = cohort_definition.ageRange.min
    maxAge = cohort_definition.ageRange.max
    start_date = cohort_definition.timeRange.start if cohort_definition.timeRange else None
    end_date = cohort_definition.timeRange.end if cohort_definition.timeRange else None
    
    # print('mustHaveFindings#####################################################')
    # print(cohort_definition.mustHaveFindings)
    
    # Retrieve Gender
    gender = cohort_definition.gender  # This could be a string or a list of CodeEntry
    if isinstance(gender, str):
        gender_list = [{"code": gender, "display": gender}]
    elif isinstance(gender, list):
        gender_list = [{"code": item.code, "display": item.display} for item in gender]

    # Retrieve Ethnicity
    ethnicity = cohort_definition.ethnicity  # This could be a string or a list of CodeEntry
    if isinstance(ethnicity, str):
        ethnicity_list = [{"code": ethnicity, "display": ethnicity}]
    elif isinstance(ethnicity, list):
        ethnicity_list = [{"code": item.code, "display": item.display} for item in ethnicity]

    # Expand MUST-HAVE codes from codesWithDetails
    musthaveSnomedCodes = []
    if cohort_definition.mustHaveFindings:
        for item in cohort_definition.mustHaveFindings:
            if item.codesWithDetails:
                for detail in item.codesWithDetails:
                    if detail.code:
                        musthaveSnomedCodes.append(
                            detail.code
                        )
    
    # Expand MUST-NOT-HAVE codes from codesWithDetails
    mustNOThaveSnomedCodes = []
    if cohort_definition.mustNotHaveFindings:
        for item in cohort_definition.mustNotHaveFindings:
            if item.codesWithDetails:
                for detail in item.codesWithDetails:
                    if detail.code:
                        mustNOThaveSnomedCodes.append(
                            detail.code
                        )
    
    """
    # Logging all parameters for now
    print("\n--- Cohort Summary ---")
    print("Title:", cohort_definition.title)
    print("Gender:", gender_list)
    print("Ethnicity:", ethnicity_list)
    print("Age Range:", minAge, "-", maxAge)
    print("Start date:", start_date)
    print("End date:", end_date)
    
    # Format SNOMED codes for logging with display
    print("Must-have SNOMED codes:", musthaveSnomedCodes)
    print("Must-not-have SNOMED codes:", mustNOThaveSnomedCodes)
    """
    
    """
    # Final response
    return {
        "title": cohort_definition.title,
        "gender": gender_list,
        "ethnicity": ethnicity_list,
        "ageRange": [minAge, maxAge],
        "timeRange": [start, end],
        "must_have_codes": must_have_codes,  # Already in the desired format
        "must_not_have_codes": must_not_have_codes,  # Already in the desired format

    }
    """
    
    
    # Base SELECT and JOIN statements
    base_query = """
        SELECT a.Adm_Dt, b.Gender, c.DiagCode, c.Diagnosis, COUNT(*) AS patient_count
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
    
    # Age range condition (always included)
    where_conditions.append("(YEAR(GETDATE()) - b.Year_of_Birth) BETWEEN ? AND ?")
    params.extend([minAge, maxAge])
    
    # Admission date (only add if provided)
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
    
    # Combine everything into the final query
    where_clause = " AND ".join(where_conditions)
    final_query = f"""
        {base_query}
        WHERE {where_clause}
        GROUP BY b.Gender, c.DiagCode, a.Adm_Dt, c.Diagnosis
    """
    
    # Print final query and parameters (for debugging)
    # print(final_query)
    # print(params)
        
    # Initialise df_results so it's available outside the `if`
    df_results = pd.DataFrame()

    # Run the query
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(final_query, params)
        
        # Get column names from cursor.description
        column_names = [column[0] for column in cursor.description]
        
        # Fetch all rows
        rows = cursor.fetchall()

        # Save results into a DataFrame
        df_results = pd.DataFrame.from_records(rows, columns=column_names)

        # Optional: print the DataFrame
        print(df_results)

        # Close connections
        cursor.close()
        conn.close()
        
        
    # Convert DataFrame to JSON
    results_json = df_results.to_dict(orient="records")
    
    # Return as JSON
    return {
        "title": cohort_definition.title,
        "results": results_json
        }