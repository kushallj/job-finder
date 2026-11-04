# ==============================================================================
# Multi-Stage Production Dockerfile: React SPA + FastAPI Cloud Runtime
# ==============================================================================

# ── Stage 1: Compile React / TypeScript Frontend ──────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Production Python Backend & Playwright Runtime ───────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

WORKDIR /app

# Install system dependencies including PostgreSQL client libs, curl, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir flower

# Install Playwright Chromium headless for autonomous Workday & NextRaise auto-apply
RUN python -m playwright install --with-deps chromium || true

# Copy application source code
COPY . .

# Copy compiled frontend SPA bundle from Stage 1 into FastAPI static distribution
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Ensure data and config directories exist
RUN mkdir -p /app/data /app/config

# Expose API port & Flower celery dashboard port
EXPOSE 8000 5555

# Container healthcheck targeting /health liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Default entrypoint runs FastAPI server
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
