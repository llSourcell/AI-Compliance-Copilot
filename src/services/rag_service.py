import weaviate
from sentence_transformers import CrossEncoder, SentenceTransformer
from openai import OpenAI
from src.core.config import settings
from src.models.api import Citation
from typing import List
from weaviate.connect import ConnectionParams
from tenacity import retry, stop_after_attempt, wait_fixed
import weaviate.classes as wvc
from src.services.pii_service import PIIRedactionService

class RAGService:
    def __init__(self, pii_service: PIIRedactionService | None = None):
        self.weaviate_client = self._connect_with_retry()
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, device="cpu")
        self.reranker = CrossEncoder(settings.RERANKER_MODEL)
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.collection_name = "ComplianceDocument"
        self.pii_service = pii_service or PIIRedactionService()

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

    def query(self, query: str, source: str | None = None) -> tuple[str, List[Citation]]:
        # 1. Get query embedding
        query_embedding = self.embedding_model.encode(query, normalize_embeddings=True).tolist()

        # 2. Hybrid Search
        collection = self.weaviate_client.collections.get(self.collection_name)
        
        # Prepare DB-level filters if a specific source is targeted (try basename first, then full path)
        filter_basename = None
        filter_fullpath = None
        src_name = None
        if source:
            import os
            src_name = os.path.basename(source)
            filter_basename = wvc.query.Filter.by_property("source").equal(src_name)
            filter_fullpath = wvc.query.Filter.by_property("source").equal(source)

        def run_hybrid(alpha: float, filters: object | None):
            return collection.query.hybrid(
                query=query,
                vector=query_embedding,
                alpha=alpha,
                limit=50,
                filters=filters,
                return_metadata=wvc.query.MetadataQuery(score=True)
            )

        # Try basename filter first, then fullpath, then no filter
        response = run_hybrid(alpha=0.5, filters=filter_basename)

        search_results = []
        if response.objects:
            for o in response.objects:
                result = o.properties
                result['score'] = o.metadata.score
                search_results.append(result)

        # Fallback BM25-only with filter
        if not search_results:
            response = run_hybrid(alpha=0.0, filters=filter_basename)
            if response.objects:
                for o in response.objects:
                    result = o.properties
                    result['score'] = o.metadata.score
                    search_results.append(result)

        # Fallback hybrid without filter
        if not search_results and filter_fullpath is not None:
            # Try fullpath filter
            response = run_hybrid(alpha=0.5, filters=filter_fullpath)
            if response.objects:
                for o in response.objects:
                    result = o.properties
                    result['score'] = o.metadata.score
                    search_results.append(result)

        # Fallback hybrid without filter
        if not search_results and (filter_basename is not None or filter_fullpath is not None):
            response = run_hybrid(alpha=0.5, filters=None)
            if response.objects:
                for o in response.objects:
                    result = o.properties
                    result['score'] = o.metadata.score
                    search_results.append(result)

        # Fallback fetch by source (page 1 first) when nothing retrieved
        if not search_results and (filter_basename is not None or filter_fullpath is not None):
            try:
                # Try basename fetch, then fullpath fetch
                fetched = collection.query.fetch_objects(limit=10, filters=filter_basename or filter_fullpath)
                if (not fetched.objects) and (filter_fullpath is not None):
                    fetched = collection.query.fetch_objects(limit=10, filters=filter_fullpath)
                if fetched.objects:
                    for o in fetched.objects:
                        search_results.append({
                            **o.properties
                        })
                    # Sort by page_number ascending to favor first page content like names/titles
                    search_results.sort(key=lambda x: int(x.get("page_number", 9999)))
            except Exception:
                pass

        # If still nothing, fetch broadly and filter client-side by matching basename/full path suffix
        if not search_results and source:
            try:
                broad = collection.query.fetch_objects(limit=100)
                candidates: list[dict] = []
                if broad.objects:
                    import os
                    src_name = os.path.basename(source)
                    for o in broad.objects:
                        props = o.properties or {}
                        src_val = str(props.get("source", ""))
                        if not src_val:
                            continue
                        if src_val == source or os.path.basename(src_val) == src_name or src_val.endswith(f"/{src_name}"):
                            if props.get("content"):
                                candidates.append(props)
                if candidates:
                    candidates.sort(key=lambda x: int(x.get("page_number", 9999)))
                    search_results = candidates[:10]
            except Exception:
                pass

        # Redundant safety filter (post-query)
        if source and search_results:
            import os
            src_name = os.path.basename(source)
            search_results = [
                r for r in search_results
                if os.path.basename(r.get("source", "")) == src_name or r.get("source", "") == source
            ]

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

        # Dedupe results by (source, page_number, content)
        def _dedupe(results: List[dict]) -> List[dict]:
            seen: set[tuple[str, int, str]] = set()
            unique: List[dict] = []
            for r in results:
                key = (str(r.get("source", "")), int(r.get("page_number", -1)), str(r.get("content", "")))
                if key in seen:
                    continue
                seen.add(key)
                unique.append(r)
            return unique

        reranked_results = _dedupe(reranked_results)

        # 4. Prompt Construction (with PII redaction on context)
        top_k = 3
        selected = reranked_results[:top_k]
        redacted_context_parts: List[str] = []
        # If the user is asking for authorship/people, do not redact PERSON entities
        lower_q = query.lower()
        skip_entities: list[str] = []
        if any(word in lower_q for word in ["author", "who is", "who's", "person", "name"]):
            skip_entities = ["PERSON"]
        for result in selected:
            content = result["content"]
            redacted_content = self.pii_service.redact_text(content, skip_entities=skip_entities)
            redacted_context_parts.append(
                f"Source: {result['source']}, Page: {result['page_number']}\nContent: {redacted_content}"
            )
        context = "\n".join(redacted_context_parts)
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
        raw_answer = llm_response.choices[0].message.content or "No answer found."

        # 6. Redact final answer for any residual PII and log
        answer = self.pii_service.redact_text(raw_answer, skip_entities=skip_entities)

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
