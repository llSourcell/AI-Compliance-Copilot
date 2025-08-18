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


def get_rag_service() -> RAGService:
    # Isolate DI to avoid FastAPI trying to parse class __init__ annotations
    return RAGService()


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
    chunks = getattr(service, "_last_chunks_count", 0)
    ocr_pages = getattr(service, "_last_ocr_pages", 0)
    msg = "Success" if chunks > 0 else "No text extracted"
    # Return basename as the document_id so subsequent queries filter correctly
    doc_id = os.path.basename(result)
    # Back-compat: return both new and old keys so the frontend never sees undefined
    return JSONResponse(
        content={
            "message": msg,
            "document_id": doc_id,
            "chunks_count": chunks,
            "ocr_pages_count": ocr_pages,
            "chunks": chunks,
            "ocr_pages": ocr_pages,
        }
    )


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, service: RAGService = Depends(get_rag_service)) -> QueryResponse:
    """Query the compliance documents."""
    answer, citations = service.query(request.query, source=request.source)
    return QueryResponse(answer=answer, citations=citations)