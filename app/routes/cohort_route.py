from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Union, Optional
import pandas as pd
import pyodbc

from app.config import settings
from collections import Counter
import app.services.fhir_client as fhir_client

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

class FindingItem(BaseModel):
    code: List[CodeEntry]

class TimeRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None

class CohortDefinition(BaseModel):
    title: str
    gender: Union[str, List[str]]  # "ALL" or a list of strings
    ethnicity: Union[str, List[str]]
    ageRange: AgeRange
    timeRange: Optional[TimeRange] = None
    mustHaveFindings: List[FindingItem]
    mustNotHaveFindings: List[FindingItem]

@router.post("/cohort/select")
async def run_select(cohort_definition: CohortDefinition):
    minAge = cohort_definition.ageRange.min
    maxAge = cohort_definition.ageRange.max
    start = cohort_definition.timeRange.start if cohort_definition.timeRange else None
    end = cohort_definition.timeRange.end if cohort_definition.timeRange else None

    # Expand MUST-HAVE codes
    must_have_codes = []
    for item in cohort_definition.mustHaveFindings:
        if item.code and item.code[0].code:
            main_code = item.code[0].code
            print("Main must-have SNOMED code:", main_code)
            try:
                snomed_expansion = client.search_snomed("<<" + main_code, "", 1000)
                expanded_codes = snomed_expansion.get('expansion', {}).get('contains', [])
                must_have_codes.extend([entry['code'] for entry in expanded_codes])
            except Exception as e:
                print(f"Error expanding must-have code {main_code}: {e}")

    # Expand MUST-NOT-HAVE codes
    must_not_have_codes = []
    for item in cohort_definition.mustNotHaveFindings:
        if item.code and item.code[0].code:
            main_code = item.code[0].code
            print("Main must-not-have SNOMED code:", main_code)
            try:
                snomed_expansion = client.search_snomed("<<" + main_code, "", 1000)
                expanded_codes = snomed_expansion.get('expansion', {}).get('contains', [])
                must_not_have_codes.extend([entry['code'] for entry in expanded_codes])
            except Exception as e:
                print(f"Error expanding must-not-have code {main_code}: {e}")

    # Logging all parameters for now
    print("\n--- Cohort Summary ---")
    print("Title:", cohort_definition.title)
    print("Gender:", cohort_definition.gender)
    print("Ethnicity:", cohort_definition.ethnicity)
    print("Age Range:", minAge, "-", maxAge)
    print("Start date:", start)
    print("End date:", end)
    print("Must-have SNOMED codes:", must_have_codes)
    print("Must-not-have SNOMED codes:", must_not_have_codes)

    # Placeholder for SQL query logic
    # Connect to DB and run queries using these filters if needed

    return {
        "title": cohort_definition.title,
        "gender": cohort_definition.gender,
        "ethnicity": cohort_definition.ethnicity,
        "ageRange": [minAge, maxAge],
        "timeRange": [start, end],
        "must_have_codes": must_have_codes,
        "must_not_have_codes": must_not_have_codes,
    }
