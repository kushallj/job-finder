"""Liveness and readiness probes (public, minimal, no internals leaked).

/healthz   process is up. No I/O, so a database blip never makes the platform kill
           every container at once. Used by the Docker HEALTHCHECK.
/readyz    dependencies reachable: database (SELECT 1) and, when configured, Redis.
           503 when not ready so load balancers stop routing.

The legacy /health and /api/health (Ollama, pipeline internals) stay for the old UI but
are not suitable as platform probes.
"""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])
log = logging.getLogger(__name__)


@router.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


def _check_db() -> None:
    from src.database import engine

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def _check_redis(url: str) -> None:
    import redis

    redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2).ping()


async def _timed(name: str, fn, *args) -> tuple[str, bool, float]:
    started = time.perf_counter()
    try:
        await asyncio.wait_for(asyncio.to_thread(fn, *args), timeout=3)
        ok = True
    except Exception as exc:  # any failure means "not ready"; the probe body shows booleans only
        log.warning("readiness check %s failed: %s", name, exc)
        ok = False
    return name, ok, round((time.perf_counter() - started) * 1000, 1)


@router.get("/readyz", include_in_schema=False)
async def readyz() -> JSONResponse:
    from src.config import settings

    checks = [_timed("database", _check_db)]
    if settings.redis_url and not settings.redis_url.startswith("memory"):
        checks.append(_timed("redis", _check_redis, settings.redis_url))
    results = await asyncio.gather(*checks)
    ready = all(ok for _, ok, _ in results)
    body = {"status": "ready" if ready else "not_ready",
            "checks": {name: {"ok": ok, "ms": ms} for name, ok, ms in results}}
    return JSONResponse(body, status_code=200 if ready else 503)
