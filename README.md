# Compliance Copilot

An enterprise, “glass‑box” RAG system engineered for truth, privacy, and production. It ingests PDFs, retrieves with hybrid search + reranking, generates answers with strict citations, and enforces configurable PII redaction — all with observability hooks to prove what the model saw and why.

### Why this project matters
- Transparency by design: verifiable, deduplicated citations and a per‑answer groundedness signal.
- Privacy first: configurable PERSON/EMAIL/IP redaction in contexts, answers, and citations.
- Production readiness: typed FastAPI, clean services, tests/linting, containerized, and deployable to common PaaS.

## Highlights
- Retrieval: Weaviate hybrid search (vector+BM25) with robust fallbacks; optional in‑memory store for constrained PaaS.
- Reranking: Cross‑encoder or hosted embeddings cosine proxy (batched) for low‑latency deployments.
- PII: Microsoft Presidio integration with a safe regex fallback; strict‑privacy toggle end‑to‑end.
- Observability: response includes `trace_id` and a groundedness proxy derived from rerank scores.

## Quickstart

1) Clone and enter
```bash
git clone https://github.com/llSourcell/AI-Compliance-Copilot.git
cd AI-Compliance-Copilot
```

2) Backend (FastAPI)
```bash
poetry install
OPENAI_API_KEY=... poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000
```
API docs: `http://localhost:8000/docs`

3) Frontend (optional local UI)
```bash
cd frontend && npm install && npm run dev
# Open http://localhost:3000  (set NEXT_PUBLIC_API_BASE if needed)
```

4) Ingest + Query (CLI)
```bash
# Ingest a PDF
curl -sS -X POST http://localhost:8000/api/v1/ingest -H 'Expect:' \
  -F 'file=@/absolute/path/to/your.pdf;type=application/pdf'

# Query with strict privacy ON
curl -sS -X POST http://localhost:8000/api/v1/query -H 'Content-Type: application/json' \
  -d '{"query":"who is the author?","source":"your.pdf","strict_privacy":true}'
```

## Architecture (at a glance)
```
src/
  main.py                 # FastAPI app, CORS, health, minimal HTML UI
  api/v1/endpoints.py     # /ingest, /query
  services/
    ingestion_service.py  # PDF parse (pypdf), split, embed, write to store
    rag_service.py        # hybrid search, rerank, prompt, citations, groundedness
    pii_service.py        # Presidio/regex redaction with audit logs
  models/api.py           # Pydantic request/response models
  core/config.py          # env-driven settings
```

Data flow
- Ingest: PDF → text extraction → recursive splitter → embeddings → store (Weaviate or in‑memory).
- Query: user question → hybrid search → rerank → redact context (policy) → answer with citations → redact answer (policy) → return `answer`, `citations[]`, `trace_id`, `groundedness`.

## Privacy, Tracing, and Observability
- **Strict privacy** (default ON): redact PERSON/EMAIL/IP in contexts, citations, and the final answer.
- **Redacted citations**: prevents accidental PII leakage through the UI.
- **Trace ID**: each response carries a UUID for correlation in logs and dashboards.
- **Groundedness**: softmax‑normalized proxy built from reranker scores of cited contexts (0–1).

## Quality & Tooling
- Tests: `pytest` • Types: `mypy` • Lint/Format: `ruff` • Hooks: `pre‑commit`.
- Containerized via Docker; CI pipeline ready to lint and test.

## RAG Evaluation (Ragas)
Evaluate faithfulness, answer relevancy, and context precision on a golden set.
```bash
poetry run python -m src.scripts.evaluate \
  --csv /absolute/path/to/golden_dataset.csv \
  --api-base http://localhost:8000 \
  --source your.pdf \
  --model gpt-4o-mini \
  --threshold 0.85
```
Outputs aggregate scores and a PASS/FAIL quality gate.

## Security/Compliance context
This repository showcases how I build “trustworthy AI” systems:
- I make retrieval auditable (citations), answers grounded, and privacy non‑negotiable.
- I design for production: clear modules, typed APIs, resilience, and graceful fallbacks.
- I optimize for realities of deployment (PaaS limits, latency) without sacrificing correctness.

If you’re hiring for AI/LLM engineering: let’s build systems your compliance and security teams love as much as your users do.
