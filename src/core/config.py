from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Compliance Copilot"
    API_V1_STR: str = "/api/v1"
    WEAVIATE_URL: str = "http://weaviate:8080"
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"
    RERANKER_MODEL: str = "BAAI/bge-reranker-large"
    OPENAI_API_KEY: str
    USE_OPENAI_EMBEDDINGS: bool = True
    USE_OPENAI_RERANKER: bool = True
    ENABLE_PRESIDIO: bool = False

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()