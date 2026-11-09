"""Logging + error tracking, configured once at process start (API and Celery).

Production (ENV=production): one JSON object per line on stdout, which is what
Render/Fly/Docker log drivers ingest; no log files (containers are ephemeral).
Development: human-readable lines on stdout plus a rotating file under logs/.

Every record carries the request's trace id (set by the trace middleware via
`trace_id_var`), so one id ties together the access line, app logs and the
`error.trace_id` the frontend shows.

Sentry is optional: set SENTRY_DSN (and install sentry-sdk) to report unhandled
errors. PII is not sent (send_default_pii=False).
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")

_STD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None)).keys()) | {"message", "asctime", "trace_id"}
_state = {"configured": False}


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Single-line JSON; `extra={...}` fields are included as top-level keys."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _STD_ATTRS and not k.startswith("_")})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(env: str, level: str = "INFO", log_dir: str = "logs") -> None:
    """Idempotent: safe to call from main.py and Celery workers."""
    if _state["configured"]:
        return
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    root.setLevel(getattr(logging, (level or "INFO").upper(), logging.INFO))

    trace = TraceIdFilter()
    stream = logging.StreamHandler()
    stream.addFilter(trace)
    if env.lower() == "production":
        stream.setFormatter(JsonFormatter())
        root.addHandler(stream)
    else:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s [%(trace_id)s]: %(message)s", "%Y-%m-%d %H:%M:%S")
        stream.setFormatter(fmt)
        root.addHandler(stream)
        Path(log_dir).mkdir(exist_ok=True)
        rotating = logging.handlers.RotatingFileHandler(Path(log_dir) / "main.log", maxBytes=5_000_000,
                                                        backupCount=5, encoding="utf-8")
        rotating.addFilter(trace)
        rotating.setFormatter(fmt)
        root.addHandler(rotating)

    # Third-party chatter that drowns real signal at INFO.
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _state["configured"] = True


def init_sentry(dsn: str | None, env: str, release: str | None = None) -> bool:
    """Start Sentry if a DSN is configured and the SDK is installed. Returns True when active."""
    if not dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        logging.getLogger(__name__).warning("SENTRY_DSN is set but sentry-sdk is not installed; error tracking off")
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=env,
        release=release or os.getenv("RENDER_GIT_COMMIT") or os.getenv("FLY_IMAGE_REF"),
        send_default_pii=False,  # no emails, IPs, cookies or bodies (CLAUDE.md: personal data)
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
    )
    return True
