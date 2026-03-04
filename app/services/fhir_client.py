import requests
import time
import threading
from app.config import settings
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


class FHIRClient:
    TOKEN_REFRESH_INTERVAL = 300       # Check token every 5 minutes
    EARLY_REFRESH_MARGIN = 1800        # Refresh 30 min early
    MAX_RETRIES = 3                    # Retry failed calls
    TIMEOUT = 15                       # Shorter timeout prevents 1-min hangs

    def __init__(self):
        self.session = self._new_session()
        self.access_token = ""
        self.token_expiry = 0

        # Create initial token
        self.create_access_token()

        # Background auto-refresh
        self.start_token_refresher()

    # -------------------------------------
    #   SESSION MANAGEMENT (Fixes stale conn)
    # -------------------------------------
    def _new_session(self):
        session = requests.Session()
        session.keep_alive = True

        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    # -------------------------------------
    #   BACKGROUND TOKEN REFRESH
    # -------------------------------------
    def start_token_refresher(self):
        def refresh_daemon():
            while True:
                time.sleep(self.TOKEN_REFRESH_INTERVAL)
                try:
                    self.create_access_token()
                except Exception as e:
                    print(f"[WARNING] Token refresh failed: {e}")

        thread = threading.Thread(target=refresh_daemon, daemon=True)
        thread.start()

    # -------------------------------------
    #   TOKEN HANDLING
    # -------------------------------------
    def get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def create_access_token(self):
        """Refresh token if missing or expiring within 30 minutes."""
        if self.access_token and (self.token_expiry - time.time() > self.EARLY_REFRESH_MARGIN):
            return  # Token still safe

        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.fhir_api_client_id,
            "client_secret": settings.fhir_api_client_secret,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        resp = self.session.post(
            settings.fhir_api_auth_server,
            headers=headers,
            data=payload,
            timeout=20
        )
        resp.raise_for_status()

        token_data = resp.json()
        expires_in = token_data.get("expires_in", 3600)

        # Refresh 30 minutes early
        self.access_token = token_data["access_token"]
        self.token_expiry = time.time() + expires_in - self.EARLY_REFRESH_MARGIN

    # -------------------------------------
    #   SAFE REQUEST WRAPPER (RETRY + RESET)
    # -------------------------------------
    def _request(self, method, url, **kwargs):
        """Unified request handler with retry, token refresh, and session reset."""

        for attempt in range(self.MAX_RETRIES):

            try:
                self.create_access_token()  # Ensure token fresh

                response = self.session.request(
                    method,
                    url,
                    headers=self.get_headers(),
                    timeout=self.TIMEOUT,
                    **kwargs,
                )

                # Token invalid → refresh and retry
                if response.status_code == 401:
                    print("[INFO] Token expired mid-request -> refreshing")
                    self.create_access_token()
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.ReadTimeout:
                print(f"[TIMEOUT] Attempt {attempt+1}/{self.MAX_RETRIES}")

                # 🔥 Reset session – fixes 24h stale connection bug
                self.session.close()
                self.session = self._new_session()

                if attempt == self.MAX_RETRIES - 1:
                    raise
                time.sleep(1)

            except Exception as e:
                print(f"[FHIR ERROR] Attempt {attempt+1}/{self.MAX_RETRIES}: {e}")

                if attempt == self.MAX_RETRIES - 1:
                    raise
                time.sleep(1)

        raise RuntimeError("Unhandled FHIR request failure")

    # ------------------------
    # SNOMED QUERIES
    # ------------------------
    def search_snomed(self, ecl: str, term: str, count: int = 20):
        url = f"{settings.fhir_api_url}/ValueSet/$expand?url=http://snomed.info/sct?fhir_vs=ecl/{ecl}&filter={term}"
        response = self.session.get(url, headers=self.get_headers(), timeout=60)
        return response.json()

    def map_snomed_to_icd10(self, snomed_code):
        source_system = "http://snomed.info/sct"
        target_system = "http://hl7.org/fhir/sid/icd-10"

        url = (
            f"{settings.fhir_api_url}/ConceptMap/$translate?"
            f"code={snomed_code}&system={source_system}&targetsystem={target_system}"
        )
        return self._request("GET", url)