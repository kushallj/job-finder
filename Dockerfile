# syntax=docker/dockerfile:1.7
# ==============================================================================
# Production image: FastAPI API + Celery worker/beat (same image, different CMD).
#
# - Jobify (the UI) deploys separately to Vercel; no frontend is built here.
# - No Playwright/Chromium: scrape-tier job sources are opt-in and run from a separate
#   scraper image (requirements-scrapers.txt), per CLAUDE.md "slim API image".
# - Build tools live only in the builder stage; the runtime has no compiler.
# - Runs as an unprivileged user. Migrations run as a release step, not per container
#   (render.yaml preDeployCommand, fly.toml release_command).
# ==============================================================================

FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt


FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    WEB_CONCURRENCY=2

# libpq5: runtime client lib for psycopg2. curl: container healthcheck only.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system app && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links /wheels -r requirements.txt && rm -rf /wheels

# .dockerignore keeps .env, data/, config/profile.yml, tests and UIs out of the image.
COPY --chown=app:app . .
RUN mkdir -p /app/data /app/logs && chown -R app:app /app/data /app/logs

USER app
EXPOSE 8000

# Liveness only (no DB/LLM calls): restarts must not cascade when a dependency blips.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

# --proxy-headers: trust X-Forwarded-* from the platform's load balancer for client IPs/scheme.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
