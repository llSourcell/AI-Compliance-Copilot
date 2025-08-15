from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
from src.models.api import (
    QueryRequest,
    QueryResponse,
    IngestRequest,
    IngestResponse,
)
from src.services.rag_service import RAGService
from src.services.ingestion_service import IngestionService

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    request: IngestRequest | None = None,
    file: UploadFile | None = File(default=None),
    service: IngestionService = Depends(),
) -> IngestResponse:
    """Ingest a document into the vector store. Supports either file_path JSON or direct file upload."""
    if file is None and request is None:
        raise HTTPException(status_code=400, detail="Provide either 'file' upload or 'file_path' in body")

    file_path: str
    if file is not None:
        # Save uploaded file to a temp path under /app/data/uploads
        uploads_dir = "/app/data/uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, file.filename)
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    else:
        file_path = request.file_path  # type: ignore[assignment]

    result = service.ingest_document(file_path)
    return IngestResponse(message="Success", document_id=result)


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, service: RAGService = Depends()) -> QueryResponse:
    """Query the compliance documents."""
    answer, citations = service.query(request.query)
    return QueryResponse(answer=answer, citations=citations)