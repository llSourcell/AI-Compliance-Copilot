from pydantic import BaseModel


class IngestRequest(BaseModel):
    file_path: str


class IngestResponse(BaseModel):
    message: str
    document_id: str
    chunks_count: int
    ocr_pages_count: int


class QueryRequest(BaseModel):
    query: str
    source: str | None = None
    strict_privacy: bool = True


class Citation(BaseModel):
    source: str
    page_number: int
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    trace_id: str
    groundedness: float