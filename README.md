# Compliance Copilot

Enterprise-grade RAG application for compliance.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI
- **Frontend:** React, Chakra UI
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

The frontend application will be available at `http://localhost:3000`.

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
│       └── rag_service.py
└── tests
    └── test_main.py
```