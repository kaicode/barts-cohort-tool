import requests
from app.config import settings

class FHIRClient:
    def __init__(self):
        self.access_token = ""
        self.create_access_token()
        print(self.search_snomed("195967001", ""))
        # print(self.map_snomed_to_icd10("195967001"))

    def search_snomed(self, ecl: str, term: str, count: int = 20):
        # Search SNOMED CT using an Implicit ValueSet with a SNOMED Query (ECL) see: https://snomed.org/ecl
        url = f"{settings.fhir_api_url}/ValueSet/$expand?url=http://snomed.info/sct?fhir_vs=ecl/{ecl}&filter={term}"
        print(f'Expand: {url}')
        response = requests.get(url, headers={"Authorization": f"Bearer {self.access_token}"})
        return response.json()

    def create_access_token(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": settings.fhir_api_client_id,
            "client_secret": settings.fhir_api_client_secret,
        }
        response = requests.post(settings.fhir_api_auth_server, headers=headers, data=data)
        self.access_token = response.json()["access_token"]

    def map_snomed_to_icd10(self, snomed_code):
        source_system = "http://snomed.info/sct"
        target_system = "http://hl7.org/fhir/sid/icd-10"
        url = f"{settings.fhir_api_url}/ConceptMap/$translate?code={snomed_code}&system={source_system}&targetsystem={target_system}"
        response = requests.get(url, headers={"Authorization": f"Bearer {self.access_token}"})
        return response.json()
