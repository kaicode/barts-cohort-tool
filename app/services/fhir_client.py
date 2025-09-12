import requests
import time
from app.config import settings

class FHIRClient:
    def __init__(self):
        # ✅ Initialize session first
        self.session = requests.Session()  

        # Token management
        self.access_token = ""
        self.token_expiry = 0

        # Create initial access token
        self.create_access_token()

    def get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def create_access_token(self):
        # Only request a new token if expired
        if self.access_token and self.token_expiry > time.time():
            return

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": settings.fhir_api_client_id,
            "client_secret": settings.fhir_api_client_secret,
        }
        response = self.session.post(settings.fhir_api_auth_server, headers=headers, data=data, timeout=40)
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.token_expiry = time.time() + token_data.get("expires_in", 3600) - 60  # buffer of 1 min

    def search_snomed(self, ecl: str, term: str, count: int = 20):
        url = f"{settings.fhir_api_url}/ValueSet/$expand?url=http://snomed.info/sct?fhir_vs=ecl/{ecl}&filter={term}"
        response = self.session.get(url, headers=self.get_headers(), timeout=10)
        return response.json()

    def map_snomed_to_icd10(self, snomed_code):
        source_system = "http://snomed.info/sct"
        target_system = "http://hl7.org/fhir/sid/icd-10"
        url = f"{settings.fhir_api_url}/ConceptMap/$translate?code={snomed_code}&system={source_system}&targetsystem={target_system}"
        response = self.session.get(url, headers=self.get_headers(), timeout=10)
        return response.json()
