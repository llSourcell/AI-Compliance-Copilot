import weaviate
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from src.core.config import settings
from typing import List
from uuid import uuid4
from weaviate.connect import ConnectionParams
import weaviate.classes as wvc
from weaviate.exceptions import WeaviateBatchError
from tenacity import retry, stop_after_attempt, wait_fixed


class IngestionService:
    def __init__(self):
        self.weaviate_client = self._connect_with_retry()
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, device="cpu")
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=200)
        self.collection_name = "ComplianceDocument"
        self._create_schema()

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(2))
    def _connect_with_retry(self):
        client = weaviate.WeaviateClient(ConnectionParams.from_params(
            http_host="weaviate",
            http_port=8080,
            http_secure=False,
            grpc_host="weaviate",
            grpc_port=50051,
            grpc_secure=False,
        ))
        client.connect()
        return client

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
        try:
            doc = fitz.open(file_path)
            texts = [page.get_text() for page in doc]
            doc.close()
        except Exception as e:
            return f"Error reading file {file_path}: {e}"

        chunks_with_metadata = []
        for i, text in enumerate(texts):
            chunks = self.text_splitter.split_text(text)
            for chunk in chunks:
                chunks_with_metadata.append(
                    {"content": chunk, "source": file_path, "page_number": i + 1}
                )

        if not chunks_with_metadata:
            return f"No text could be extracted from {file_path}."

        embeddings = self.embedding_model.encode(
            [item["content"] for item in chunks_with_metadata], 
            show_progress_bar=True,
            normalize_embeddings=True
        )

        collection = self.weaviate_client.collections.get(self.collection_name)
        try:
            with collection.batch.dynamic() as batch:
                for i, chunk_data in enumerate(chunks_with_metadata):
                    batch.add_object(
                        properties=chunk_data,
                        vector=embeddings[i],
                    )
        except WeaviateBatchError as e:
            return f"Ingestion failed with error: {e}"

        return f"Successfully ingested {len(chunks_with_metadata)} chunks from {file_path}"
