from fastapi import APIRouter
import app.services.fhir_client as fhir_client

router = APIRouter()

@router.get("/snomed/search-findings")
async def search_snomed(term: str):
    return await fhir_client.search_snomed("<404684003", term)

@router.get("/snomed/search-procedures")
async def search_snomed(term: str):
    return await fhir_client.search_snomed("<71388002", term)

@router.get("/snomed/search")
async def search_snomed(ecl: str, term: str):
    return await fhir_client.search_snomed(ecl, term)
