# Multi-stage Dockerfile for Backend Services (API, Celery Worker, Celery Beat, Flower, Telegram Daemon)
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr and writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

WORKDIR /app

# Install system dependencies including build tools, libpq for PostgreSQL, curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir flower

# Optional: Install Playwright browsers for scrapers
RUN python -m playwright install --with-deps chromium || true

# Copy application source code
COPY . .

# Ensure data directory exists for runtime files & sqlite fallback
RUN mkdir -p /app/data /app/config

# Expose API port & Flower port
EXPOSE 8000 5555

# Default entrypoint runs the FastAPI server
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
