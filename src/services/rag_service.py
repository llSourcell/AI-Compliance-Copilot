import weaviate
try:
    from sentence_transformers import CrossEncoder, SentenceTransformer  # optional
except Exception:  # pragma: no cover
    CrossEncoder = None  # type: ignore
    SentenceTransformer = None  # type: ignore
from openai import OpenAI
from src.core.config import settings
from src.models.api import Citation
from typing import List
from weaviate.connect import ConnectionParams
from tenacity import retry, stop_after_attempt, wait_fixed
import weaviate.classes as wvc
from src.services.pii_service import PIIRedactionService
from src.services.ingestion_service import LOCAL_STORE
import os

class RAGService:
    def __init__(self, pii_service: PIIRedactionService | None = None):
        try:
            self.weaviate_client = self._connect_with_retry()
        except Exception:
            self.weaviate_client = None
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # Embeddings backend
        self.use_openai_embeddings = bool(settings.USE_OPENAI_EMBEDDINGS)
        if not self.use_openai_embeddings and SentenceTransformer is not None:
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, device="cpu")
        # Reranker backend
        self.use_openai_reranker = bool(settings.USE_OPENAI_RERANKER)
        if not self.use_openai_reranker and CrossEncoder is not None:
            self.reranker = CrossEncoder(settings.RERANKER_MODEL)
        self.collection_name = "ComplianceDocument"
        self.pii_service = pii_service or PIIRedactionService()

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(2))
    def _connect_with_retry(self):
        weaviate_url = os.environ.get("WEAVIATE_URL", "").strip()
        if weaviate_url:
            client = weaviate.WeaviateClient(ConnectionParams.from_url(weaviate_url))
            client.connect()
            return client
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

    def _embed(self, text: str) -> list[float]:
        if self.use_openai_embeddings:
            v = self.openai_client.embeddings.create(model="text-embedding-3-large", input=text).data[0].embedding
            return v
        return self.embedding_model.encode(text, normalize_embeddings=True).tolist()

    def _rerank(self, query: str, docs: list[str]) -> list[float]:
        if self.use_openai_reranker:
            # Use direct relevance scoring via embeddings cosine similarity as a light proxy
            qv = self._embed(query)
            import numpy as np
            q = np.array(qv, dtype=float)
            scores = []
            for d in docs:
                dv = self.openai_client.embeddings.create(model="text-embedding-3-large", input=d).data[0].embedding
                v = np.array(dv, dtype=float)
                sim = float(q @ v / (np.linalg.norm(q) * np.linalg.norm(v) + 1e-8))
                scores.append(sim)
            return scores
        # Fallback to CrossEncoder
        return self.reranker.predict([[query, d] for d in docs]).tolist()

    def query(self, query: str, source: str | None = None, strict_privacy: bool = True) -> tuple[str, List[Citation], str, float]:
        # 1. Get query embedding
        query_embedding = self._embed(query)

        # 2. Hybrid Search
        if self.weaviate_client is None:
            # In-memory cosine search over LOCAL_STORE
            import numpy as np
            def cos(a: list[float], b: list[float]) -> float:
                va = np.array(a, dtype=float)
                vb = np.array(b, dtype=float)
                return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-8))

            candidates = [item for item in LOCAL_STORE if (not source) or os.path.basename(item.get("source", "")) == os.path.basename(source)]
            scored = []
            for item in candidates:
                v = item.get("vector")
                if not v:
                    continue
                scored.append({**item, "score": cos(query_embedding, v)})
            scored.sort(key=lambda x: x["score"], reverse=True)
            search_results = scored[:50]
        else:
            collection = self.weaviate_client.collections.get(self.collection_name)
        
        # Prepare DB-level filters if a specific source is targeted (try basename first, then full path)
        filter_basename = None
        filter_fullpath = None
        src_name = None
        if source:
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

            # Fallback hybrid with fullpath
            if not search_results and filter_fullpath is not None:
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

            # Fallback fetch by source
            if not search_results and (filter_basename is not None or filter_fullpath is not None):
                try:
                    fetched = collection.query.fetch_objects(limit=10, filters=filter_basename or filter_fullpath)
                    if (not fetched.objects) and (filter_fullpath is not None):
                        fetched = collection.query.fetch_objects(limit=10, filters=filter_fullpath)
                    if fetched.objects:
                        for o in fetched.objects:
                            search_results.append({**o.properties})
                        search_results.sort(key=lambda x: int(x.get("page_number", 9999)))
                except Exception:
                    pass

        if not search_results and source:
            try:
                broad = collection.query.fetch_objects(limit=100)
                candidates: list[dict] = []
                if broad.objects:
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

        if source and search_results:
            src_name = os.path.basename(source)
            search_results = [
                r for r in search_results
                if os.path.basename(r.get("source", "")) == src_name or r.get("source", "") == source
            ]

        # 3. Reranking
        if not search_results:
            return "No results found.", [], self._new_trace_id(), 0.0
        docs = [r["content"] for r in search_results]
        cross_scores = self._rerank(query, docs)
        for result, score in zip(search_results, cross_scores):
            result["rerank_score"] = float(score)
        reranked_results = sorted(search_results, key=lambda x: x["rerank_score"], reverse=True)

        # Dedupe
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

        # 4. Prompt
        top_k = 3
        selected = reranked_results[:top_k]
        redacted_context_parts: List[str] = []
        lower_q = query.lower()
        skip_entities: list[str] = []
        if not strict_privacy and any(word in lower_q for word in ["author", "who is", "who's", "person", "name"]):
            skip_entities = ["PERSON"]
        for result in selected:
            content = result["content"]
            redacted_content = self.pii_service.redact_text(content, skip_entities=skip_entities)
            redacted_context_parts.append(f"Source: {result['source']}, Page: {result['page_number']}\nContent: {redacted_content}")
        context = "\n".join(redacted_context_parts)
        prompt = f"""
        You are the Compliance Copilot. Answer the user's query based on the following context.
        Provide citations for every piece of information you use, in the format [Source: <source>, Page: <page_number>].

        Context:
        {context}

        Query: {query}

        Answer:
        """

        llm_response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides answers with citations."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        raw_answer = llm_response.choices[0].message.content or "No answer found."
        answer = self.pii_service.redact_text(raw_answer, skip_entities=skip_entities)

        citations = [
            Citation(
                source=result["source"],
                page_number=result["page_number"],
                text=self.pii_service.redact_text(result["content"], skip_entities=skip_entities) if strict_privacy else result["content"],
                score=float(result["rerank_score"]),
            )
            for result in reranked_results[:top_k]
        ]

        import math
        scores = [max(-20.0, min(20.0, float(r.get("rerank_score", 0.0)))) for r in reranked_results[:top_k]]
        if scores:
            exps = [math.exp(s - max(scores)) for s in scores]
            sm = [e / (sum(exps) or 1.0) for e in exps]
            groundedness = float(sum(sm) / len(sm))
        else:
            groundedness = 0.0

        trace_id = self._new_trace_id()
        return answer, citations, trace_id, groundedness

    def _new_trace_id(self) -> str:
        from uuid import uuid4
        return str(uuid4())
