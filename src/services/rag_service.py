import weaviate
from sentence_transformers import CrossEncoder
from openai import OpenAI
from src.core.config import settings
from src.models.api import Citation
from typing import List
from weaviate.connect import ConnectionParams


class RAGService:
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
        self.reranker = CrossEncoder(settings.RERANKER_MODEL)
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.collection_name = "ComplianceDocument"

    def query(self, query: str) -> tuple[str, List[Citation]]:
        # 1. Hybrid Search
        collection = self.weaviate_client.collections.get(self.collection_name)
        response = collection.query.hybrid(
            query=query,
            alpha=0.5,
            limit=10,
            return_properties=["content", "source", "page_number"],
        )

        search_results = [o.properties for o in response.objects]

        # 2. Reranking
        cross_inp = [[query, result["content"]] for result in search_results]
        cross_scores = self.reranker.predict(cross_inp)

        for result, score in zip(search_results, cross_scores):
            result["rerank_score"] = score

        reranked_results = sorted(
            search_results, key=lambda x: x["rerank_score"], reverse=True
        )

        # 3. Prompt Construction
        top_k = 3
        context = "\n".join(
            [result["content"] for result in reranked_results[:top_k]]
        )
        prompt = f"""
        You are the Compliance Copilot. Answer the user's query based on the following context.
        Provide citations for every piece of information you use, in the format [source:page_number].

        Context:
        {context}

        Query: {query}

        Answer:
        """

        # 4. LLM Call
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        answer = response.choices[0].message.content or "No answer found."

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