from pydantic import BaseModel


class IngestRequest(BaseModel):
    file_path: str


class IngestResponse(BaseModel):
    message: str
    document_id: str


class QueryRequest(BaseModel):
    query: str


class Citation(BaseModel):
    source: str
    page_number: int
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]