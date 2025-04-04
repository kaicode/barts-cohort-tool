from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import pandas as pd

from app.config import settings

import pyodbc

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

class AgeRange(BaseModel):
    min: int
    max: int

class FindingSelection(BaseModel):
    code: List
    mustHave: bool

class CohortDefinition(BaseModel):
    title: str
    ageRange: AgeRange
    findingSelection: FindingSelection


@router.post("/cohort/select")
async def run_select(cohort_definition: CohortDefinition):

    minAge = cohort_definition.ageRange.min
    maxAge = cohort_definition.ageRange.max

    # Grab all relevant SNOMED codes
    findingSelection = cohort_definition.findingSelection
    findingSnomedCode = findingSelection.code[0]['code']
    findingMustHave = findingSelection.mustHave

    findingSnomedCodes = client.search_snomed("<<" + findingSnomedCode, "", 10)['expansion']['contains']
        
    # Extracting only the 'code' values
    foundSnomedCodes = [str(entry['code']) for entry in findingSnomedCodes]
    
    # print(foundSnomedCodes)
    
    # Dynamically create placeholders for the IN clause based on the number of SNOMED codes
    placeholders = ', '.join(['?'] * len(findingSnomedCodes))

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # SQL Query with parameters
    query = f"""
        SELECT b.Gender, c.DiagCode, a.Adm_Dt, COUNT(*) AS patient_count
        FROM [synth].[rde_cds_apc_PCT] a WITH(NOLOCK) 
        INNER JOIN [synth].[rde_patient_demographics_PCT] b WITH(NOLOCK) 
        ON a.PERSON_ID = b.PERSON_ID
        INNER JOIN [synth].[rde_pc_diagnosis_PCT] c WITH(NOLOCK)
        ON b.PERSON_ID = c.PERSON_ID
        WHERE (YEAR(GETDATE()) - b.Year_of_Birth) BETWEEN ? AND ?  -- Convert Year of Birth to Age
        AND c.DiagCode IN ({placeholders})
        GROUP BY b.Gender, c.DiagCode, a.Adm_Dt
    """ 
    
    # Execute query with parameters
    params = (minAge, maxAge, *foundSnomedCodes)
    cursor.execute(query, params)
    
    columns = [column[0] for column in cursor.description]  # Get column names
    df = pd.DataFrame.from_records(cursor.fetchall(), columns=columns)
    
    # print(df)

    # Close DB connection
    cursor.close()
    conn.close()    
