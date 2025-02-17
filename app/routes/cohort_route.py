from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

import app.services.fhir_client as fhir_client

router = APIRouter()
client = fhir_client.FHIRClient()


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

    print(f'Received cohort definition: {cohort_definition}')
    minAge = cohort_definition.ageRange.min
    maxAge = cohort_definition.ageRange.min

    # Grab all relevant SNOMED codes
    findingSelection = cohort_definition.findingSelection
    findingSnomedCode = findingSelection.code[0]['code']
    findingMustHave = findingSelection.mustHave

    findingSnomedCodes = client.search_snomed("<<" + findingSnomedCode, "", 10)['expansion']['contains']
    print(f'Found {len(findingSnomedCodes)} SNOMED codes')
