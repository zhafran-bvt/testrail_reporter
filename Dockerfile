# syntax=docker/dockerfile:1
# --- Build Stage (for development dependencies and running checks) ---
FROM python:3.11 AS builder

ARG ORBIS_AUTOMATION_REPO="https://github.com/bvarta-tech/orbis-test-automation.git"
ARG ORBIS_AUTOMATION_REF="testrail-automation-management"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies needed for both build and runtime (include git for submodules)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libjemalloc2 ffmpeg git && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies (including dev dependencies for checks)
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt -r requirements-dev.txt

# Copy all application code and configurations
COPY . .
# Ensure dataset_generator submodule/content is available (clone if missing)
RUN if [ ! -f dataset_generator/file_generator.py ]; then \
      git submodule update --init --recursive || true; \
      if [ ! -f dataset_generator/file_generator.py ]; then \
        git clone --depth=1 https://github.com/zhafran-bvt/dataset_generator.git dataset_generator; \
      fi; \
    fi

# Bake orbis-test-automation into the image so automation features work in deployed environments
RUN if [ -n "$ORBIS_AUTOMATION_REPO" ]; then \
      git clone --depth=1 --branch "$ORBIS_AUTOMATION_REF" --single-branch "$ORBIS_AUTOMATION_REPO" /opt/orbis-test-automation; \
    fi

# Run linting, formatting checks, type checking, and unit tests
# Note: These commands will cause the build to fail if checks do not pass
RUN ruff format --check .
RUN ruff check .
RUN mypy .
RUN python -m unittest discover -s tests -p 'test*.py' -v

# --- Production Stage (lean image for deployment) ---
FROM python:3.11-slim

WORKDIR /app

ARG ORBIS_AUTOMATION_REPO="https://github.com/bvarta-tech/orbis-test-automation.git"
ARG ORBIS_AUTOMATION_REF="testrail-automation-management"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    AUTOMATION_REPO_ROOT=/opt/orbis-test-automation \
    AUTOMATION_FEATURES_ROOT=/opt/orbis-test-automation/apps/lokasi_intelligence/cypress \
    ORBIS_AUTOMATION_REPO=${ORBIS_AUTOMATION_REPO} \
    ORBIS_AUTOMATION_REF=${ORBIS_AUTOMATION_REF}

# System deps (ffmpeg for video transcoding, jemalloc for memory management, node/npm for automation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libjemalloc2 ffmpeg nodejs npm git && rm -rf /var/lib/apt/lists/*

ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 \
    MALLOC_CONF="background_thread:true,dirty_decay_ms:400,muzzy_decay_ms:400"

# Copy only production dependencies from the builder stage
COPY --from=builder /app/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy only necessary application files from the builder stage
COPY --from=builder /app/app ./app
COPY --from=builder /app/templates ./templates
COPY --from=builder /app/assets ./assets
COPY --from=builder /app/dataset_generator ./dataset_generator
COPY --from=builder /app/testrail_client.py ./testrail_client.py
COPY --from=builder /app/testrail_daily_report.py ./testrail_daily_report.py
COPY --from=builder /app/.env.example ./.env.example
COPY --from=builder /app/pyproject.toml ./pyproject.toml
COPY --from=builder /app/Procfile ./Procfile
COPY --from=builder /app/scripts ./scripts
COPY --from=builder /opt/orbis-test-automation /opt/orbis-test-automation

EXPOSE 8080

# Start the application (sync automation repo if configured)
CMD ["/app/scripts/start.sh"]
