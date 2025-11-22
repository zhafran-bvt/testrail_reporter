# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

# System deps (optional: build tools if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libjemalloc2 && rm -rf /var/lib/apt/lists/*

ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 \
    MALLOC_CONF="background_thread:true,dirty_decay_ms:600,muzzy_decay_ms:600"

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD uvicorn app.main:app \
  --host 0.0.0.0 \
  --port ${PORT:-8080} \
  --workers 1 \
  --timeout-keep-alive 120
