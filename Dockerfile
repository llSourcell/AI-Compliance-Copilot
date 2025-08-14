# Stage 1: Build the application
FROM python:3.11-slim as builder

WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

COPY pyproject.toml poetry.lock* ./

RUN pip install poetry && \
    poetry install --only main --no-root && \
    rm -rf $POETRY_CACHE_DIR

# Stage 2: Create the final production image
FROM python:3.11-slim

WORKDIR /app

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1

COPY --from=builder /app/.venv ./.venv
COPY src/ ./src

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

