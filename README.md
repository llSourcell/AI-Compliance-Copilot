# Compliance Copilot

Enterprise-grade RAG application for compliance.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI
- **Frontend:** Next.js 14 (React), Tailwind CSS
- **Dependency Management:** Poetry
- **Vector DB:** Weaviate
- **QA:** `pytest`, `mypy`, `ruff`, `pre-commit`
- **Deployment:** Docker, Docker Compose
- **CI/CD:** GitHub Actions

## Setup and Installation

### Prerequisites

- Python 3.11+
- Poetry
- Docker and Docker Compose
- Node.js and npm (for frontend)

### 1. Clone the repository

```bash
git clone <repository-url>
cd compliance-copilot
```

### 2. Install backend dependencies

Install the project dependencies using Poetry.

```bash
poetry install
```

### 3. Install frontend dependencies

Navigate to the `frontend` directory and install Node.js dependencies.

```bash
cd frontend
npm install
cd ..
```

### 4. Set up pre-commit hooks

Install the pre-commit hooks to ensure code quality.

```bash
poetry run pre-commit install
```

## Running the Application

### Using Docker Compose (Backend)

This is the recommended way to run the backend application for development.

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000/docs`.

### Running the Frontend Application

After starting the backend, navigate to the `frontend` directory and start the Next.js development server.

```bash
cd frontend
npm install
npm run dev
```

The frontend application will be available at `http://localhost:3000` (or `3001`).

Set `NEXT_PUBLIC_API_BASE` in `frontend/.env.local` to point to your API if different from the default `http://localhost:8000`.

### Running tests

To run the test suite:

```bash
poetry run pytest
```

To run tests with coverage:

```bash
poetry run pytest --cov=src
```

## Project Structure

```
. 
├── .github/workflows/ci.yml
├── .gitignore
├── .pre-commit-config.yaml
├── docker-compose.yml
├── Dockerfile
├── mypy.ini
├── poetry.lock
├── pyproject.toml
├── README.md
├── frontend
│   ├── app
│   ├── package.json
│   └── tailwind.config.ts
├── src
│   ├── api
│   │   └── v1
│   │       └── endpoints.py
│   ├── core
│   │   └── config.py
│   ├── main.py
│   ├── models
│   │   └── api.py
│   └── services
│       ├── ingestion_service.py
│       ├── pii_service.py
│       └── rag_service.py
└── tests
    └── test_main.py
```

## Privacy, Tracing, and Observability

- Strict Privacy (default ON):
  - Request body supports `strict_privacy: true | false` (default: true)
  - With strict privacy ON, PERSON/EMAIL/IP are redacted in: retrieved context, final answer, and citations.
  - With strict privacy OFF, identity questions (e.g., "who is the author?") may reveal names.

- Redacted Citations:
  - Citation `text` is redacted under strict privacy to prevent PII leakage in the UI.

- Trace and Groundedness:
  - Each `/query` response returns `trace_id` (UUID) to correlate logs/observability.
  - `groundedness` is a simple softmax-normalized proxy score based on reranker scores of the cited contexts (0.0–1.0).

## API Reference (Selected)

- POST `/api/v1/ingest`: multipart form upload (`file`) → returns `{ message, document_id, chunks_count, ocr_pages_count }`.

- POST `/api/v1/query`:
  - Request: `{ "query": str, "source": str|null, "strict_privacy": bool }`
  - Response: `{ "answer": str, "citations": Citation[], "trace_id": str, "groundedness": float }`
  - `Citation`: `{ source: str, page_number: int, text: str, score: float }`

## Local cURL Examples

```bash
# Ingest a PDF
curl -sS -X POST http://localhost:8000/api/v1/ingest -H 'Expect:' \
  -F 'file=@/absolute/path/to/your.pdf;type=application/pdf'

# Query with strict privacy ON (redacts names/emails/IPs everywhere)
curl -sS -X POST http://localhost:8000/api/v1/query -H 'Content-Type: application/json' \
  -d '{"query":"who is the author?","source":"your.pdf","strict_privacy":true}'

# Query with strict privacy OFF (allows revealing names for identity questions)
curl -sS -X POST http://localhost:8000/api/v1/query -H 'Content-Type: application/json' \
  -d '{"query":"who is the author?","source":"your.pdf","strict_privacy":false}'
```