# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# - no .pyc files, unbuffered stdout so logs stream to CloudWatch
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps: build tools for psycopg2 + libpq runtime, then trimmed
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# App code
COPY . .

# Run as non-root
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Entrypoint runs migrations then starts gunicorn/uvicorn workers
ENTRYPOINT ["./entrypoint.sh"]
