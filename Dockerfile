# Stage 1: Build the application
FROM python:3.11-slim as builder

WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

COPY pyproject.toml poetry.lock* ./

RUN apt-get update && apt-get install -y tesseract-ocr build-essential g++ && rm -rf /var/lib/apt/lists/* && \
    pip install poetry && \
    poetry lock && \
    poetry install --only main --no-root && \
    ./.venv/bin/python -m spacy download en_core_web_sm && \
    rm -rf $POETRY_CACHE_DIR

# Stage 2: Create the final production image
FROM python:3.11-slim

WORKDIR /app

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y curl tesseract-ocr && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv ./.venv
COPY src/ ./src

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "--timeout", "300", "-b", "0.0.0.0:8000", "src.main:app"]
