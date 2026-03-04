from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    fhir_api_auth_server: str
    fhir_api_url: str
    fhir_api_client_id: str
    fhir_api_client_secret: str
    dw_connection: str
    saved_searches: str
    sql_query: str


    model_config = SettingsConfigDict(
        env_file="demo.env",
        env_file_encoding="utf-8"
    )  

settings = Settings()

