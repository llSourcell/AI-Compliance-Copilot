from fastapi import FastAPI
from src.api.v1 import endpoints
from src.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(endpoints.router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {"status": "ok"}
