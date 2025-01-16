import httpx
from app.config import settings

async def search_snomed(ecl: str, term: str):
    # Search SNOMED CT using an Implicit ValueSet with a SNOMED Query (ECL) see: https://snomed.org/ecl
    url = f"{settings.fhir_api_url}/ValueSet/$expand?url=http://snomed.info/sct?fhir_vs=ecl/{ecl}&filter={term}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
