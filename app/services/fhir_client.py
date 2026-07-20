import re
import requests
import time
import threading

from app.config import settings
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


_SNOMED_CODE_RE = re.compile(r"^[1-9]\d{5,17}$")


def is_snomed_code(value: str) -> bool:
    """
    Return True when the supplied value looks like a SNOMED CT code.
    """
    return bool(_SNOMED_CODE_RE.fullmatch(value.strip()))


class FHIRClient:
    TOKEN_REFRESH_INTERVAL = 300
    EARLY_REFRESH_MARGIN = 1800
    MAX_RETRIES = 3
    TIMEOUT = 15

    SNOMED_SYSTEM = "http://snomed.info/sct"
    ICD10_SYSTEM = "http://hl7.org/fhir/sid/icd-10"

    def __init__(self):
        self.session = self._new_session()
        self.access_token = ""
        self.token_expiry = 0

        # Create initial token
        self.create_access_token()

        # Background auto-refresh
        self.start_token_refresher()

    # -------------------------------------
    # SESSION MANAGEMENT
    # -------------------------------------
    def _new_session(self):
        session = requests.Session()
        session.keep_alive = True

        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    # -------------------------------------
    # BACKGROUND TOKEN REFRESH
    # -------------------------------------
    def start_token_refresher(self):
        def refresh_daemon():
            while True:
                time.sleep(self.TOKEN_REFRESH_INTERVAL)

                try:
                    self.create_access_token()
                except Exception as exc:
                    print(f"[WARNING] Token refresh failed: {exc}")

        thread = threading.Thread(
            target=refresh_daemon,
            daemon=True,
        )

        thread.start()

    # -------------------------------------
    # TOKEN HANDLING
    # -------------------------------------
    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/fhir+json",
        }

    def create_access_token(self, force=False):
        """
        Refresh the token if it is missing or close to expiry.
        """
        if (
            not force
            and self.access_token
            and self.token_expiry - time.time() > self.EARLY_REFRESH_MARGIN
        ):
            return

        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.fhir_api_client_id,
            "client_secret": settings.fhir_api_client_secret,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = self.session.post(
            settings.fhir_api_auth_server,
            headers=headers,
            data=payload,
            timeout=20,
        )

        response.raise_for_status()

        token_data = response.json()
        expires_in = token_data.get("expires_in", 3600)

        self.access_token = token_data["access_token"]

        # Store the actual expiry time.
        self.token_expiry = time.time() + expires_in

    # -------------------------------------
    # SAFE REQUEST WRAPPER
    # -------------------------------------
    def _request(self, method, url, **kwargs):
        """
        Send one FHIR request.
    
        Retries temporary server/network failures, but does not retry
        normal client errors such as a SNOMED lookup returning 404.
        """
    
        for attempt in range(self.MAX_RETRIES):
            try:
                self.create_access_token()
    
                response = self.session.request(
                    method,
                    url,
                    headers=self.get_headers(),
                    timeout=self.TIMEOUT,
                    **kwargs,
                )
    
                # Token expired: refresh once and try again.
                if response.status_code == 401:
                    print("[INFO] Token expired. Refreshing token.")
    
                    self.access_token = ""
                    self.token_expiry = 0
                    self.create_access_token()
    
                    continue
    
                # Do not retry 404 or other ordinary client errors.
                if 400 <= response.status_code < 500:
                    response.raise_for_status()
    
                response.raise_for_status()
                return response.json()
    
            except requests.exceptions.HTTPError:
                # A 4xx response should immediately return to the caller.
                raise
    
            except (
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
            ) as exc:
                print(
                    f"[FHIR CONNECTION ERROR] "
                    f"Attempt {attempt + 1}/{self.MAX_RETRIES}: {exc}"
                )
    
                self.session.close()
                self.session = self._new_session()
    
                if attempt == self.MAX_RETRIES - 1:
                    raise
    
                time.sleep(1)
    
            except requests.exceptions.RequestException as exc:
                print(f"[FHIR REQUEST ERROR] {exc}")
                raise
    
        raise RuntimeError("FHIR request failed")

    # -------------------------------------
    # SNOMED CODE LOOKUP
    # -------------------------------------
    def lookup_snomed_term(self, snomed_code: str):
        """
        Look up a SNOMED CT code and return its preferred display term.
    
        Returns None only when the terminology server confirms that the
        current code does not exist.
        """
        code = str(snomed_code).strip()
    
        url = f"{settings.fhir_api_url}/CodeSystem/$lookup"
    
        try:
            result = self._request(
                "GET",
                url,
                params={
                    "system": "http://snomed.info/sct",
                    "code": code,
                },
            )
    
        except requests.exceptions.HTTPError as exc:
            status_code = (
                exc.response.status_code
                if exc.response is not None
                else None
            )
    
            response_text = (
                exc.response.text
                if exc.response is not None
                else ""
            )
    
            # print(
            #     f"[SNOMED LOOKUP FAILED] "
            #     f"code={code}, "
            #     f"status={status_code}, "
            #     f"response={response_text}"
            # )
    
            if status_code == 404:
                return None
    
            raise
    
        # print(f"[SNOMED LOOKUP RESPONSE] code={code}, result={result}")
    
        for parameter in result.get("parameter", []):
            if parameter.get("name") == "display":
                display = parameter.get("valueString")
    
                if display:
                    return display.strip()
    
        # print(
        #     f"[SNOMED LOOKUP] No display parameter returned for {code}"
        # )
    
        return None

    # -------------------------------------
    # SNOMED SEARCH
    # -------------------------------------
    def search_snomed(
        self,
        ecl: str,
        term: str,
        count: int = 20,
    ):
        search_value = str(term).strip()
        ecl_value = str(ecl).strip()
    
        # print(
        #     f"[SNOMED SEARCH RECEIVED] "
        #     f"value={search_value!r}, "
        #     f"length={len(search_value)}, "
        #     f"is_numeric={search_value.isdigit()}"
        # )
    
        if search_value.isdigit():
            # SNOMED concept identifiers contain at least six digits.
            # For shorter partial values, simply wait for more input.
            if len(search_value) < 6:
                pass
    
            filter_term = self.lookup_snomed_term(search_value)
    
            if not filter_term:
                # print(
                #     f"[SNOMED SEARCH] No concept currently found "
                #     f"for code {search_value}"
                # )
                pass
    
            # print(
            #     f"[SNOMED SEARCH] Code {search_value} resolved "
            #     f"to {filter_term!r}"
            # )
    
        else:
            filter_term = search_value
        
        url = f"{settings.fhir_api_url}/ValueSet/$expand?url=http://snomed.info/sct?fhir_vs=ecl/{ecl}&filter={term}"
        response = self.session.get(url, headers=self.get_headers(), timeout=60)
        return response.json()
    
    # -------------------------------------
    # SNOMED TO ICD-10
    # -------------------------------------
    def map_snomed_to_icd10(self, snomed_code):
        source_system = self.SNOMED_SYSTEM
        target_system = self.ICD10_SYSTEM

        url = (
            f"{settings.fhir_api_url}/ConceptMap/$translate"
        )

        return self._request(
            "GET",
            url,
            params={
                "code": snomed_code,
                "system": source_system,
                "targetsystem": target_system,
            },
        )