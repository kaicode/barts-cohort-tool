import requests
import time
from app.config import settings

class FHIRClient:
    def __init__(self):
        self.access_token = ""
        self.token_timeout_seconds = 60
        self.token_expiry = 0
        self.create_access_token()

    def search_snomed(self, ecl: str, term: str, count: int = 20):
        self.ensure_valid_token()
        url = f"{settings.fhir_api_url}/ValueSet/$expand?url=http://snomed.info/sct?fhir_vs=ecl/{ecl}&filter={term}"
        print(f'Expanding ValueSet: {url}')
        response = requests.get(url, headers={"Authorization": f"Bearer {self.access_token}"})
        return response.json()

    def map_snomed_to_icd10(self, snomed_code):
        self.ensure_valid_token()
        source_system = "http://snomed.info/sct"
        target_system = "http://hl7.org/fhir/sid/icd-10"
        url = f"{settings.fhir_api_url}/ConceptMap/$translate?code={snomed_code}&system={source_system}&targetsystem={target_system}"
        response = requests.get(url, headers={"Authorization": f"Bearer {self.access_token}"})
        return response.json()

    def ensure_valid_token(self):
        """Check if token is expired and create a new one if needed"""
        if time.time() >= self.token_expiry:
            self.create_access_token()

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
        print(f'New access token {self.access_token}')
        self.token_expiry = time.time() + self.token_timeout_seconds  # Set token to expire in x seconds
