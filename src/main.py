from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api.v1 import endpoints
from src.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# CORS for local Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})

app.include_router(endpoints.router, prefix=settings.API_V1_STR)
