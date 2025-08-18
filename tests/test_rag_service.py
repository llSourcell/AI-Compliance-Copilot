import os
from src.services.rag_service import RAGService
from src.services.ingestion_service import IngestionService, LOCAL_STORE


def test_in_memory_query_roundtrip(monkeypatch, tmp_path):
    # Ensure in-memory mode by clearing WEAVIATE_URL
    if "WEAVIATE_URL" in os.environ:
        del os.environ["WEAVIATE_URL"]

    # Create a tiny fake PDF via plain text and ingest using pypdf-friendly bytes
    # We simulate by writing a minimal text PDF (pypdf reads plain text pages only if valid)
    pdf_path = tmp_path / "tiny.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")

    ingester = IngestionService()
    # LOCAL_STORE should remain empty if pypdf can't extract text; inject a synthetic chunk instead
    LOCAL_STORE.clear()
    LOCAL_STORE.append({
        "content": "Author: Test Person\nTitle: Minimal Doc\nRetention policy: keep data only as long as necessary.",
        "source": "tiny.pdf",
        "page_number": 0,
        "vector": [0.1] * 10,  # dummy; won't be used by embed if OpenAI is on, but in-memory path compares vectors
    })

    # Query in-memory
    rag = RAGService()

    # Avoid calling remote OpenAI in unit test: monkeypatch embed & rerank
    def fake_embed(text: str):
        return [0.1] * 10

    def fake_rerank(q: str, docs: list[str]):
        return [1.0 for _ in docs]

    monkeypatch.setattr(rag, "_embed", fake_embed)
    monkeypatch.setattr(rag, "_rerank", fake_rerank)

    answer, citations, trace_id, groundedness = rag.query(
        "what is the retention policy?", source="tiny.pdf", strict_privacy=True
    )

    assert "retention" in answer.lower()
    assert citations and citations[0].source == "tiny.pdf"
    assert 0.0 <= groundedness <= 1.0
    assert len(trace_id) > 0

