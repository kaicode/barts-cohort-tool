from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    fhir_api_url: str

    class Config:
        env_file = ".env"

settings = Settings()
