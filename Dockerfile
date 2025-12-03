# syntax=docker/dockerfile:1
# --- Build Stage (for development dependencies and running checks) ---
FROM python:3.11 AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies needed for both build and runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libjemalloc2 ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies (including dev dependencies for checks)
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt -r requirements-dev.txt

# Copy all application code and configurations
COPY . .

# Run linting, formatting checks, type checking, and unit tests
# Note: These commands will cause the build to fail if checks do not pass
RUN ruff format --check .
RUN ruff check .
RUN mypy .
RUN python -m unittest discover -s tests -p 'test*.py' -v

# --- Production Stage (lean image for deployment) ---
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

# System deps (ffmpeg for video transcoding, jemalloc for memory management)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libjemalloc2 ffmpeg && rm -rf /var/lib/apt/lists/*

ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 \
    MALLOC_CONF="background_thread:true,dirty_decay_ms:400,muzzy_decay_ms:400"

# Copy only production dependencies from the builder stage
COPY --from=builder /app/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy only necessary application files from the builder stage
COPY --from=builder /app/app ./app
COPY --from=builder /app/templates ./templates
COPY --from=builder /app/assets ./assets
COPY --from=builder /app/testrail_client.py ./testrail_client.py
COPY --from=builder /app/testrail_daily_report.py ./testrail_daily_report.py
COPY --from=builder /app/.env.example ./.env.example
COPY --from=builder /app/pyproject.toml ./pyproject.toml
COPY --from=builder /app/Procfile ./Procfile

EXPOSE 8080

# Start the Uvicorn application (pytest removed)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}", "--workers", "1", "--timeout-keep-alive", "120"]