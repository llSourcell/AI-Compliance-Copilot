import weaviate
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from src.core.config import settings
from typing import List
from uuid import uuid4
from weaviate.connect import ConnectionParams
import weaviate.classes.config


class IngestionService:
    def __init__(self):
        self.weaviate_client = weaviate.WeaviateClient(ConnectionParams.from_params(
            http_host="weaviate",
            http_port=8080,
            http_secure=False,
            grpc_host="weaviate",
            grpc_port=50051,
            grpc_secure=False,
        ))
        self.weaviate_client.connect()
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=200)
        self.collection_name = "ComplianceDocument"
        self._create_schema()

    def _create_schema(self) -> None:
        if not self.weaviate_client.collections.exists(self.collection_name):
            self.weaviate_client.collections.create(
                name=self.collection_name,
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
                vector_config=weaviate.classes.config.Configure.Vector.none(),
                properties=[
                    weaviate.classes.config.Property(name="content", data_type=weaviate.classes.config.DataType.TEXT),
                    weaviate.classes.config.Property(name="source", data_type=weaviate.classes.config.DataType.TEXT),
                    weaviate.classes.config.Property(name="page_number", data_type=weaviate.classes.config.DataType.INT),
                ],
            )

    def ingest_document(self, file_path: str) -> str:
        doc = fitz.open(file_path)
        texts = [page.get_text() for page in doc]
        doc.close()

        chunks_with_metadata = []
        for i, text in enumerate(texts):
            chunks = self.text_splitter.split_text(text)
            for chunk in chunks:
                chunks_with_metadata.append(
                    {"content": chunk, "source": file_path, "page_number": i + 1}
                )

        embeddings = self.embedding_model.encode(
            [item["content"] for item in chunks_with_metadata], show_progress_bar=True
        )

        with self.weaviate_client.batch.dynamic() as batch:
            for i, chunk_data in enumerate(chunks_with_metadata):
                batch.add_object(
                    properties=chunk_data,
                    collection=self.collection_name,
                    vector=embeddings[i],
                )
        return f"Successfully ingested {len(chunks_with_metadata)} chunks from {file_path}"