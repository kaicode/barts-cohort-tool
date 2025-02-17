from fastapi import APIRouter
import app.services.fhir_client as fhir_client

router = APIRouter()
client = fhir_client.FHIRClient()

@router.get("/snomed/search-findings")
async def search_snomed_findings(term: str):
    return client.search_snomed("<404684003", term)

@router.get("/snomed/search-procedures")
async def search_snomed_procedures(term: str):
    return client.search_snomed("<71388002", term)

@router.get("/snomed/search")
async def search_snomed(ecl: str, term: str):
    return client.search_snomed(ecl, term)

@router.get("/snomed/count-descendants-and-self")
async def snomed_count_descendants(code: str):
    # TODO: Use the ECL history supplement to include inactive SNOMEDCT codes
    # This is not working with the NHS Terminology Server
    # https://confluence.ihtsdotools.org/display/DOCECL/6.11+History+Supplements
    # return client.search_snomed("<<" + code + ' {{ %2B HISTORY }}', "", 1)
    return client.search_snomed("<<" + code, "", 1)
