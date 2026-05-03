# EduPredict AI — Production Hardened Dockerfile (v5.0 Final)
# Multi-stage build for minimal runtime footprint and security.

# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM python:3.12-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ libgomp1 curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install Python dependencies
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# Build Frontend
COPY app/ui/package*.json app/ui/
RUN cd app/ui && npm ci
COPY . .
RUN cd app/ui && npm run build

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="EduPredict AI Engineering <engineering@edupredict.ai>"
LABEL version="5.0-hardened"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    WORKERS=2 \
    LOG_LEVEL=info

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /install /usr/local

# Copy application code and built frontend
COPY --chown=1000:1000 . .

# Security: Non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p data/pipeline/history data/pipeline/circuits model/artifacts logs && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# Entrypoint with shell expansion for env vars
ENTRYPOINT ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT} --workers ${WORKERS} --log-level ${LOG_LEVEL}"]
