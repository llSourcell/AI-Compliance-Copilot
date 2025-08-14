from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Compliance Copilot"
    API_V1_STR: str = "/api/v1"
    WEAVIATE_URL: str = "http://weaviate:8080"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
