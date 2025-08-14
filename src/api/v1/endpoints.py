from fastapi import APIRouter, Depends
from src.models.api import QueryRequest, QueryResponse
from src.services.rag_service import RAGService, get_rag_service

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> QueryResponse:
    """Query the compliance documents."""
    answer = rag_service.query(request.query)
    return QueryResponse(answer=answer)
