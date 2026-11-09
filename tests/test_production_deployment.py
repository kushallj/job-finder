"""
Unit and integration tests for Step 4 Production Deployment Architecture.
Covers:
- Database URL normalization (PostgreSQL / Supabase compatibility)
- Production health and liveness probe endpoints (/health, /api/health, /)
- Cloud deployment configuration validation (fly.toml, render.yaml, Dockerfile, docker-compose.prod.yml)
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.database import normalize_database_url
from main import app


def test_normalize_database_url():
    """Verify postgres:// is rewritten to postgresql:// for SQLAlchemy 2.0 compatibility."""
    # Supabase / Render legacy prefix
    legacy_url = "postgres://postgres:secretpassword@db.projectref.supabase.co:5432/postgres?sslmode=require"
    normalized = normalize_database_url(legacy_url)
    assert normalized.startswith("postgresql://")
    assert "secretpassword" in normalized

    # Modern prefix remains unchanged
    modern_url = "postgresql://user:pass@localhost:5432/mydb"
    assert normalize_database_url(modern_url) == modern_url

    # SQLite remains unchanged
    sqlite_url = "sqlite:///./data/jobs.db"
    assert normalize_database_url(sqlite_url) == sqlite_url

    # None / empty fallback
    assert normalize_database_url("") == "sqlite:///./jobs.db"


def test_health_and_liveness_endpoints():
    """Verify /health and /api/health endpoints respond successfully for cloud load balancers."""
    client = TestClient(app)

    # 1. Root /
    res_root = client.get("/")
    assert res_root.status_code == 200

    # 2. Cloud liveness probe /health
    res_health = client.get("/health")
    assert res_health.status_code == 200
    data = res_health.json()
    assert "status" in data
    assert "version" in data

    # 3. API health check /api/health
    res_api_health = client.get("/api/health")
    assert res_api_health.status_code == 200
    assert "components" in res_api_health.json()


def test_deployment_manifests_integrity():
    """Ensure all required production deployment manifests exist and are non-empty."""
    root_dir = Path(__file__).resolve().parent.parent

    manifests = [
        "Dockerfile",
        "fly.toml",
        "render.yaml",
        "docker-compose.prod.yml",
        ".env.production.example",
    ]

    for filename in manifests:
        filepath = root_dir / filename
        assert filepath.is_file(), f"Missing deployment manifest: {filename}"
        content = filepath.read_text(encoding="utf-8")
        assert len(content.strip()) > 50, f"Manifest {filename} is suspiciously empty"

    # Verify fly.toml contains critical directives
    fly_content = (root_dir / "fly.toml").read_text()
    assert "job-finder-ai" in fly_content
    assert "internal_port = 8000" in fly_content
    assert 'path = "/readyz"' in fly_content                       # readiness probe, not legacy /health
    assert 'release_command = "alembic upgrade head"' in fly_content  # schema before traffic

    # Verify render.yaml contains required services
    render_content = (root_dir / "render.yaml").read_text()
    assert "type: web" in render_content
    assert "job-finder-postgres" in render_content
    assert "healthCheckPath: /readyz" in render_content
    assert "preDeployCommand: alembic upgrade head" in render_content

    # Dockerfile: slim multi-stage API image, non-root, no Playwright/frontend (CLAUDE.md)
    dockerfile_content = (root_dir / "Dockerfile").read_text()
    assert "FROM python:3.12-slim AS builder" in dockerfile_content
    assert "FROM python:3.12-slim AS runtime" in dockerfile_content
    assert "USER app" in dockerfile_content.splitlines()
    assert "/healthz" in dockerfile_content
    assert "playwright install" not in dockerfile_content
    assert "COPY --from=frontend-builder" not in dockerfile_content

    # Secrets and personal data never enter the build context
    ignored = (root_dir / ".dockerignore").read_text().splitlines()
    for entry in (".env", "data/", "config/profile.yml"):
        assert entry in ignored, f".dockerignore must exclude {entry}"


def test_vercel_builds_only_the_frontend():
    """Vercel builds jobify/ from the repo root: the root vercel.json mirrors jobify/vercel.json
    (routing + security headers) and .vercelignore keeps the FastAPI backend out of the upload,
    otherwise Vercel detects main.py/requirements.txt as a Python app (build failed on psycopg2)."""
    import json

    repo = Path(__file__).resolve().parents[1]
    root = json.loads((repo / "vercel.json").read_text(encoding="utf-8"))
    app_cfg = json.loads((repo / "jobify" / "vercel.json").read_text(encoding="utf-8"))
    assert root["framework"] == "vite" and root["outputDirectory"] == "jobify/dist"
    assert "--prefix jobify" in root["installCommand"] and "--prefix jobify" in root["buildCommand"]
    assert root["rewrites"] == app_cfg["rewrites"]
    assert root["headers"] == app_cfg["headers"]   # one security-header policy, two entry points

    ignore = (repo / ".vercelignore").read_text(encoding="utf-8").splitlines()
    assert "/*" in ignore and "!/jobify" in ignore and "!/vercel.json" in ignore
    assert not any(line.lstrip("!").strip("/") in {"main.py", "requirements.txt", "src", "data"}
                   for line in ignore if line.startswith("!"))
