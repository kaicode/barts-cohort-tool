from fastapi import APIRouter
import app.services.fhir_client as fhir_client

router = APIRouter()
client = fhir_client.FHIRClient()

def include_inactive(code):
    # Add ECL History Supplement to include inactive SNOMED codes, by leveraging historical associations.
    # See History Supplements section in the ECL Guide - https://snomed.org/ecl
    return code + ' {{ %2B HISTORY-MAX }}'

@router.get("/snomed/search-findings")
async def search_snomed_findings(term: str):
    return client.search_snomed("<404684003", term)

@router.get("/snomed/search-procedures")
async def search_snomed_procedures(term: str):
    return client.search_snomed("<71388002", term)

@router.get("/snomed/search")
async def search_snomed(ecl: str, term: str):
    ecl = include_inactive('(' + ecl + ')')
    return client.search_snomed(ecl, term)

@router.get("/snomed/count-descendants-and-self")
async def snomed_count_descendants(code: str):
    code = include_inactive(code)
    return client.search_snomed("<<" + code, "", 1)

@router.get("/snomed/lookup")
async def lookup_snomed(code: str):
    """
    Returns SNOMED concept details including descriptionId (if supported)
    """
    return client.search_snomed_description_id(code)
