# Compliance Copilot

Enterprise-grade RAG application for compliance.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI
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

### 1. Clone the repository

```bash
git clone <repository-url>
cd compliance-copilot
```

### 2. Install dependencies

Install the project dependencies using Poetry.

```bash
poetry install
```

### 3. Set up pre-commit hooks

Install the pre-commit hooks to ensure code quality.

```bash
poetry run pre-commit install
```

## Running the Application

### Using Docker Compose

This is the recommended way to run the application for development.

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000/docs`.

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
├── pyproject.toml
├── README.md
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
