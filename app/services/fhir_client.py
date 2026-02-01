import requests
import time
import threading
from app.config import settings


class FHIRClient:
    TOKEN_REFRESH_INTERVAL = 600       # 10 minutes
    MAX_RETRIES = 3                    # Retry failed calls
    TIMEOUT = 60                       # Request timeout

    def __init__(self):
        self.session = requests.Session()
        self.session.keep_alive = True

        self.access_token = ""
        self.token_expiry = 0

        # Create first token
        self.create_access_token()

        # 🔥 Background auto-refresh every 10 minutes
        self.start_token_refresher()

    # ------------------------
    # TOKEN MANAGEMENT
    # ------------------------
    def start_token_refresher(self):
        """Background thread that refreshes the token every 10 minutes."""
        def refresh_daemon():
            while True:
                time.sleep(self.TOKEN_REFRESH_INTERVAL)
                try:
                    self.create_access_token()
                except Exception as e:
                    print(f"[WARNING] Token refresh failed: {e}")

        thread = threading.Thread(target=refresh_daemon, daemon=True)
        thread.start()

    def get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def create_access_token(self):
        """Refresh token if missing or expired."""
        if self.access_token and self.token_expiry > time.time():
            return  # Token still valid

        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.fhir_api_client_id,
            "client_secret": settings.fhir_api_client_secret,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = self.session.post(
            settings.fhir_api_auth_server,
            headers=headers,
            data=payload,
            timeout=40
        )
        response.raise_for_status()

        token_data = response.json()

        self.access_token = token_data["access_token"]
        # Renew 10 minutes before expiry
        self.token_expiry = time.time() + token_data.get("expires_in", 3600) - 600

    # ------------------------
    # API CALL WRAPPER (RETRY)
    # ------------------------
    def _request(self, method, url, **kwargs):
        """Unified request handler with retry and auto token refresh."""
        for attempt in range(self.MAX_RETRIES):
            try:
                # Ensure token valid
                self.create_access_token()

                response = self.session.request(
                    method,
                    url,
                    headers=self.get_headers(),
                    timeout=self.TIMEOUT,
                    **kwargs,
                )

                # If unauthorized, refresh token once and retry
                if response.status_code == 401:
                    self.create_access_token()
                    continue

                response.raise_for_status()
                return response.json()

            except Exception as e:
                print(f"[FHIR ERROR] Attempt {attempt+1}/{self.MAX_RETRIES}: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise
                time.sleep(1)

    # ------------------------
    # SNOMED QUERIES
    # ------------------------
    def search_snomed(self, ecl: str, term: str, count: int = 20):
        url = (
            f"{settings.fhir_api_url}/ValueSet/$expand?"
            f"url=http://snomed.info/sct?fhir_vs=ecl/{ecl}&filter={term}&count={count}"
        )
        return self._request("GET", url)

    def search_snomed_description_id(self, term: str):
        url = (
            f"{settings.fhir_api_url}/CodeSystem/$lookup?"
            f"system=http://snomed.info/sct&code={term}&includeDesignations=true"
        )
        return self._request("GET", url)

    def map_snomed_to_icd10(self, snomed_code):
        source_system = "http://snomed.info/sct"
        target_system = "http://hl7.org/fhir/sid/icd-10"

        url = (
            f"{settings.fhir_api_url}/ConceptMap/$translate?"
            f"code={snomed_code}&system={source_system}&targetsystem={target_system}"
        )
        return self._request("GET", url)
