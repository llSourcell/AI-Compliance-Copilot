import weaviate
from sentence_transformers import CrossEncoder, SentenceTransformer
from openai import OpenAI
from src.core.config import settings
from src.models.api import Citation
from typing import List
from weaviate.connect import ConnectionParams
from tenacity import retry, stop_after_attempt, wait_fixed
import weaviate.classes as wvc

class RAGService:
    def __init__(self):
        self.weaviate_client = self._connect_with_retry()
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, device="cpu")
        self.reranker = CrossEncoder(settings.RERANKER_MODEL)
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.collection_name = "ComplianceDocument"

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

    def query(self, query: str) -> tuple[str, List[Citation]]:
        # 1. Get query embedding
        query_embedding = self.embedding_model.encode(query, normalize_embeddings=True).tolist()

        # 2. Hybrid Search
        collection = self.weaviate_client.collections.get(self.collection_name)
        
        response = collection.query.hybrid(
            query=query,
            vector=query_embedding,
            alpha=0.5,
            limit=10,
            return_metadata=wvc.query.MetadataQuery(score=True)
        )

        search_results = []
        if response.objects:
            for o in response.objects:
                result = o.properties
                result['score'] = o.metadata.score
                search_results.append(result)

        # 3. Reranking
        if not search_results:
            return "No results found.", []
            
        cross_inp = [[query, result["content"]] for result in search_results]
        cross_scores = self.reranker.predict(cross_inp).tolist()

        for result, score in zip(search_results, cross_scores):
            result["rerank_score"] = score

        reranked_results = sorted(
            search_results, key=lambda x: x["rerank_score"], reverse=True
        )

        # 4. Prompt Construction
        top_k = 3
        context = "\n".join(
            [f"Source: {result['source']}, Page: {result['page_number']}\nContent: {result['content']}" for result in reranked_results[:top_k]]
        )
        prompt = f"""
        You are the Compliance Copilot. Answer the user's query based on the following context.
        Provide citations for every piece of information you use, in the format [Source: <source>, Page: <page_number>].

        Context:
        {context}

        Query: {query}

        Answer:
        """

        # 5. LLM Call
        llm_response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides answers with citations."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        answer = llm_response.choices[0].message.content or "No answer found."

        citations = [
            Citation(
                source=result["source"],
                page_number=result["page_number"],
                text=result["content"],
                score=result["rerank_score"],
            )
            for result in reranked_results[:top_k]
        ]

        return answer, citations
