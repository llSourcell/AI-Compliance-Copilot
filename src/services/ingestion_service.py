import weaviate
from langchain_text_splitters import RecursiveCharacterTextSplitter
try:
    from sentence_transformers import SentenceTransformer  # optional for Heroku
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore
from src.core.config import settings
from typing import List
from uuid import uuid4
from weaviate.connect import ConnectionParams
import weaviate.classes as wvc
from weaviate.exceptions import WeaviateBatchError
from tenacity import retry, stop_after_attempt, wait_fixed
import os
from urllib.parse import urlparse
from openai import OpenAI

# Process-wide lightweight fallback store when Weaviate is unavailable (Heroku)
LOCAL_STORE: list[dict] = []


class IngestionService:
    def __init__(self):
        # Try to connect to Weaviate; if unavailable (e.g., Heroku without external URL), fallback to in-memory store
        try:
            self.weaviate_client = self._connect_with_retry()
        except Exception:
            self.weaviate_client = None
        self.use_openai_embeddings = bool(settings.USE_OPENAI_EMBEDDINGS)
        if self.use_openai_embeddings:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            if SentenceTransformer is None:
                raise RuntimeError(
                    "SentenceTransformer is not installed. Set USE_OPENAI_EMBEDDINGS=true on Heroku."
                )
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, device="cpu")
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        self.collection_name = "ComplianceDocument"
        if self.weaviate_client is not None:
            self._create_schema()

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(2))
    def _connect_with_retry(self):
        weaviate_url = os.environ.get("WEAVIATE_URL", "").strip()
        if weaviate_url:
            client = weaviate.WeaviateClient(ConnectionParams.from_url(weaviate_url))
            client.connect()
            return client
        # On Heroku, do not attempt docker host; signal caller to fallback immediately
        raise RuntimeError("WEAVIATE_URL not set; using in-memory store")

    def _embed_many(self, texts: list[str]) -> list[list[float]]:
        if self.use_openai_embeddings:
            out = self.openai_client.embeddings.create(model="text-embedding-3-large", input=texts)
            return [d.embedding for d in out.data]
        return self.embedding_model.encode(texts, show_progress_bar=True, normalize_embeddings=True).tolist()

    def _create_schema(self) -> None:
        if not self.weaviate_client.collections.exists(self.collection_name):
            self.weaviate_client.collections.create(
                name=self.collection_name,
                properties=[
                    wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT, tokenization=wvc.config.Tokenization.WORD),
                    wvc.config.Property(name="source", data_type=wvc.config.DataType.TEXT),
                    wvc.config.Property(name="page_number", data_type=wvc.config.DataType.INT),
                ],
                vectorizer_config=wvc.config.Configure.Vectorizer.none(),
            )

    def ingest_document(self, file_path: str) -> str:
        # Lightweight PDF text extraction using pypdf (Heroku-friendly)
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            page_texts: List[str] = []
            ocr_pages = 0
            for page in reader.pages:
                text = page.extract_text() or ""
                page_texts.append(text)
            metadata = reader.metadata or {}
            author = getattr(metadata, "author", None) or metadata.get("/Author") if isinstance(metadata, dict) else None
            title = getattr(metadata, "title", None) or metadata.get("/Title") if isinstance(metadata, dict) else None
            subject = getattr(metadata, "subject", None) or metadata.get("/Subject") if isinstance(metadata, dict) else None
            keywords = getattr(metadata, "keywords", None) or metadata.get("/Keywords") if isinstance(metadata, dict) else None
        except Exception as e:
            return f"Error reading file {file_path}: {e}"

        chunks_with_metadata: List[dict] = []
        for i, text in enumerate(page_texts):
            chunks = self.text_splitter.split_text(text)
            for chunk in chunks:
                chunks_with_metadata.append(
                    {"content": chunk, "source": os.path.basename(file_path), "page_number": i + 1}
                )

        # Add a small synthetic chunk with document-level metadata for better Q&A (e.g., author/title)
        metadata_lines: List[str] = []
        if title:
            metadata_lines.append(f"Title: {title}")
        if author:
            metadata_lines.append(f"Author: {author}")
        if subject:
            metadata_lines.append(f"Subject: {subject}")
        if keywords:
            metadata_lines.append(f"Keywords: {keywords}")
        if metadata_lines:
            chunks_with_metadata.append(
                {
                    "content": "\n".join(metadata_lines),
                    "source": os.path.basename(file_path),
                    "page_number": 0,
                }
            )

        if not chunks_with_metadata:
            return f"No text could be extracted from {file_path}."

        texts = [item["content"] for item in chunks_with_metadata]
        embeddings = self._embed_many(texts)

        if self.weaviate_client is None:
            # In-memory fallback for Heroku
            for i, chunk_data in enumerate(chunks_with_metadata):
                LOCAL_STORE.append({**chunk_data, "vector": embeddings[i]})
        else:
            collection = self.weaviate_client.collections.get(self.collection_name)

            def _send_batch() -> None:
                with collection.batch.dynamic() as batch:
                    for i, chunk_data in enumerate(chunks_with_metadata):
                        batch.add_object(properties=chunk_data, vector=embeddings[i])

            # Primary attempt: batch insert
            try:
                _send_batch()
            except WeaviateBatchError as e:
                if "read-only" in str(e).lower():
                    import time
                    time.sleep(2)
                    _send_batch()
                else:
                    return f"Ingestion failed with error: {e}"

            # Fallback: re-insert individually
            try:
                import time
                with collection.batch.fixed_size(1) as single:
                    for i, chunk_data in enumerate(chunks_with_metadata):
                        for _ in range(3):
                            try:
                                single.add_object(properties=chunk_data, vector=embeddings[i])
                                break
                            except Exception:
                                time.sleep(0.5)
                                continue
            except Exception:
                pass

        self._last_chunks_count = len(chunks_with_metadata)  # type: ignore[attr-defined]
        self._last_ocr_pages = ocr_pages  # type: ignore[attr-defined]
        return file_path
