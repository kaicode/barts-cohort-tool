from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    fhir_api_auth_server: str
    fhir_api_url: str
    fhir_api_client_id: str
    fhir_api_client_secret: str
    dw_connection: str
    saved_searches: str


    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'  # specify encoding if necessary

settings = Settings()

