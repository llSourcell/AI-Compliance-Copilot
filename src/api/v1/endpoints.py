from fastapi import APIRouter, Depends
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
def ingest(request: IngestRequest, service: IngestionService = Depends()) -> IngestResponse:
    """Ingest a document into the vector store."""
    result = service.ingest_document(request.file_path)
    return IngestResponse(message="Success", document_id=result)


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, service: RAGService = Depends()) -> QueryResponse:
    """Query the compliance documents."""
    answer, citations = service.query(request.query)
    return QueryResponse(answer=answer, citations=citations)