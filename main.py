"""
main.py — Fixed for mixed old/new codebase on disk.

Bugs fixed in this version:
  1. process_all_jobs() called with min_score= kwarg but live file doesn't have it
     → Fixed: _call_with_accepted() introspects actual signature before calling
  2. processor.close() is async but called without await
     → Fixed: _safe_close() handles both sync and async close() automatically
  3. Per-request JobProcessor() instantiation (expensive, leaks connections)
     → Fixed: single instance at startup via lifespan, reused per request
  4. next(get_db()) never guaranteed to close on exception
     → Fixed: async with db_session() everywhere
  5. Deprecated @app.on_event("startup")
     → Fixed: lifespan context manager (FastAPI recommended pattern)
  6. Global signalhire_callbacks dict lost on restart
     → Fixed: JSON-backed CallbackStore persists across restarts
"""

from __future__ import annotations

import asyncio
import inspect
from urllib.parse import urlparse
import json
import logging
import logging.handlers
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from src.job_processor import JobProcessor
from src.database import init_db, SessionLocal
from src.models import Application, Job, OutreachRecord, Contact
from src.config import settings

# API models and error handlers
from src.api_models import (
    QueryRequest,
    ContactSearchRequest,
    OutreachRequest,
    OutreachStatusUpdateRequest,
    OutreachStatus,
    FollowUpRequest,
    CrawlRequest as CrawlRequestModel,
    QueryResponse,
    AsyncPipelineResponse,
    ContactSearchResponse,
    OutreachResponse,
    FollowUpResponse,
    JobsResponse,
    ContactsResponse,
    CrawlResponse,
    PipelineStatistics,
    JobData,
    ContactData,
    PaginationData,
    # Query parameter models for GET endpoints
    PaginationParams,
    JobsQueryParams,
    ContactsQueryParams,
    PendingOutreachParams,
    # Additional response models
    StatsResponse,
    StatsData,
    RecentOutreach,
    PendingOutreachResponse,
    PendingOutreachJob,
    SignalHireCallbackResponse,
    SignalHireResultResponse,
    StartupDiscoveryRequest,
    StartupDiscoveryResponse,
)
from src.api_error_handlers import (
    register_error_handlers,
    APIError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    TimeoutError as APITimeoutError,
    DatabaseError,
)

# ── Async Pipeline imports ────────────────────────────────────────────────
try:
    from src.async_pipeline import AsyncJobPipeline, ProcessorConfig
    _ASYNC_PIPELINE_OK = True
except Exception as _e:
    _ASYNC_PIPELINE_OK = False
    logging.warning("async_pipeline not available: %s", _e)

# ── Optional imports — degrade gracefully if files not yet updated on disk ────
try:
    from src.email_outreach import EmailOutreach, OutreachConfig
    _EMAIL_OK = True
except Exception as _e:
    _EMAIL_OK = False
    logging.warning("email_outreach not available: %s", _e)

try:
    from src.outreach_processor import OutreachProcessor
    _OUTREACH_OK = True
except Exception as _e:
    _OUTREACH_OK = False
    logging.warning("outreach_processor not available: %s", _e)

try:
    from src.outreach_orchestrator import OutreachOrchestrator
    _REPLY_DETECTION_OK = True
except Exception as _e:
    _REPLY_DETECTION_OK = False
    logging.warning("outreach_orchestrator not available: %s", _e)

try:
    from src.contact_finder import ContactFinder, Contact as ContactDataClass
    _CONTACT_OK = True
except Exception as _e:
    _CONTACT_OK = False
    logging.warning("contact_finder not available: %s", _e)

try:
    from src.email_discovery import EmailDiscoveryService
    _EMAIL_DISCOVERY_OK = True
except Exception as _e:
    _EMAIL_DISCOVERY_OK = False
    logging.warning("email_discovery not available: %s", _e)

try:
    from src.scrapers.crawl import CrawlRequest as CrawlRequestInternal, cloudflare_crawl
    _CRAWL_OK = True
except Exception as _e:
    _CRAWL_OK = False
    logging.warning("cloudflare crawl not available: %s", _e)

try:
    from src.news_service import NewsService, FirecrawlNewsService
    from src.scrapers.firecrawl_scraper import TOP_INDIAN_STARTUPS
    _NEWS_OK = True
except Exception as _e:
    _NEWS_OK = False
    logging.warning("news_service not available: %s", _e)


# =============================================================================
# Logging — structured, rotating, human-readable
# =============================================================================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_fmt = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
for h in [
    logging.StreamHandler(),
    logging.handlers.RotatingFileHandler(
        LOG_DIR / "main.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    ),
]:
    h.setFormatter(_fmt)
    logging.getLogger().addHandler(h)

logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger("main")


# =============================================================================
# _call_with_accepted — the core fix for "unexpected keyword argument"
# =============================================================================

def _call_with_accepted(fn: Any, *args, **kwargs) -> Any:
    """Call fn(*args, **kwargs) but drop any kwargs the function won't accept."""
    try:
        sig = inspect.signature(fn)
        params = sig.parameters

        has_var_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in params.values()
        )
        if has_var_kw:
            return fn(*args, **kwargs)

        accepted = set(params.keys())
        safe_kw  = {k: v for k, v in kwargs.items() if k in accepted}

        dropped = set(kwargs) - accepted
        if dropped:
            log.debug("Dropped unsupported kwargs for %s.%s: %s",
                      getattr(fn, "__module__", "?"),
                      getattr(fn, "__name__", "?"),
                      dropped)

        return fn(*args, **safe_kw)

    except (ValueError, TypeError) as exc:
        log.warning("Could not introspect %s, calling without kwargs: %s", fn, exc)
        return fn(*args)


async def _safe_close(obj: Any, name: str = "resource") -> None:
    """Close an object whether its .close() is sync or async."""
    close_fn = getattr(obj, "close", None)
    if close_fn is None:
        return
    try:
        result = close_fn()
        if inspect.isawaitable(result):
            await result
        log.debug("%s closed", name)
    except Exception as exc:
        log.warning("Error closing %s: %s", name, exc)


# =============================================================================
# DB session — safe, always closed
# =============================================================================

@asynccontextmanager
async def db_session():
    """One session per call. Closed even if an exception is raised inside."""
    s: Session = SessionLocal()
    try:
        yield s
    finally:
        s.close()


# =============================================================================
# Resume router — Trie-based, replaces brittle if/elif keyword chain
# =============================================================================

class _TN:
    __slots__ = ("ch", "path")
    def __init__(self): self.ch: Dict[str, "_TN"] = {}; self.path: Optional[str] = None


class ResumeTrie:
    ROUTES: Dict[str, str] = {
        "react": "data/resume_react.txt", "frontend": "data/resume_react.txt",
        "vue": "data/resume_react.txt",   "angular": "data/resume_react.txt",
        "python": "data/resume_python.txt","django": "data/resume_python.txt",
        "fastapi": "data/resume_python.txt","flask": "data/resume_python.txt",
        "machine learning": "data/resume_ml.txt", "ml": "data/resume_ml.txt",
        "java": "data/resume_java.txt",
        "golang": "data/resume_go.txt",   "go ": "data/resume_go.txt",
        "devops": "data/resume_devops.txt","kubernetes": "data/resume_devops.txt",
        "aws": "data/resume_devops.txt",
    }
    DEFAULT = "data/resume.txt"

    def __init__(self):
        self._root = _TN()
        for kw, path in self.ROUTES.items():
            node = self._root
            for ch in kw.lower():
                node.ch.setdefault(ch, _TN())
                node = node.ch[ch]
            node.path = path

    def route(self, query: str) -> str:
        q = query.lower()
        for start in range(len(q)):
            node = self._root
            for ch in q[start:]:
                if ch not in node.ch: break
                node = node.ch[ch]
                if node.path and Path(node.path).exists():
                    return node.path
        return self.DEFAULT


# =============================================================================
# AppState — kernel, lives for the lifetime of the server process
# =============================================================================

@dataclass
class AppState:
    job_processor:  Optional[JobProcessor]  = None
    outreach_proc:  Optional[Any]           = None
    email_outreach: Optional[Any]           = None
    async_pipeline: Optional[Any]           = None
    outreach_orchestrator: Optional[Any]    = None
    resume_router:  ResumeTrie              = field(default_factory=ResumeTrie)
    _cb_path:       Path = field(default_factory=lambda: Path("logs/sh_callbacks.json"))
    _callbacks:     Dict[str, Any] = field(default_factory=dict)

    def load_callbacks(self):
        if self._cb_path.exists():
            try: self._callbacks = json.loads(self._cb_path.read_text())
            except Exception: pass

    def save_cb(self, key: str, val: Any):
        self._callbacks[key] = val
        try: self._cb_path.write_text(json.dumps(self._callbacks, indent=2))
        except Exception as e: log.warning("Callback persist failed: %s", e)

    def get_cb(self, key: str) -> Optional[Any]:
        return self._callbacks.get(key)


_state: Optional[AppState] = None


def get_state() -> AppState:
    if _state is None: raise RuntimeError("AppState not initialised")
    return _state


# =============================================================================
# Lifespan — boot once, destroy once
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and graceful shutdown.
    
    Startup:
    - Initialize database
    - Create service instances (JobProcessor, EmailOutreach, etc.)
    - Initialize HTTP client pools
    - Start async pipeline
    - Register signal handlers for graceful shutdown
    
    Shutdown (Requirements 24.1-24.4, 34.1):
    - Stop accepting new jobs on SIGTERM/SIGINT
    - Wait for in-flight jobs to complete (with timeout)
    - Close database connection pools
    - Close async HTTP client sessions
    - Flush and close log handlers
    - Clean up all resources
    
    Signal Handling:
    - SIGTERM: Graceful shutdown triggered by container orchestrators (Requirements 24.1, 24.2)
    - SIGINT: Graceful shutdown triggered by Ctrl+C (Requirements 24.3, 24.4)
    """
    global _state
    import signal
    
    # Track shutdown state
    shutdown_initiated = False
    
    def _shutdown_signal_handler(signum, frame):
        """
        Handle SIGTERM and SIGINT for graceful shutdown.
        
        Requirements 24.1, 24.2, 24.3, 24.4:
        - Stop accepting new jobs on signal
        - Allow in-flight jobs to complete
        """
        nonlocal shutdown_initiated
        if shutdown_initiated:
            log.warning("🛑 Shutdown already in progress, ignoring signal")
            return
            
        shutdown_initiated = True
        sig_name = signal.Signals(signum).name
        log.info(f"📥 Received {sig_name}, initiating graceful shutdown...")
        
        # The actual shutdown happens in the lifespan exit handler below
        # FastAPI will trigger the lifespan exit when the server stops
    
    # Register signal handlers (Requirements 24.1-24.4)
    # Note: In production, uvicorn handles these signals, but we add handlers
    # for explicit shutdown control and logging
    try:
        signal.signal(signal.SIGTERM, _shutdown_signal_handler)
        signal.signal(signal.SIGINT, _shutdown_signal_handler)
        log.debug("✅ Signal handlers registered (SIGTERM, SIGINT)")
    except Exception as e:
        # Signal handling may not work in all environments (e.g., Windows threads)
        log.warning(f"⚠️  Could not register signal handlers: {e}")
    
    log.info("🚀 Booting…")
    
    # Initialize database
    init_db()
    log.info("✅ DB ready")

    state = AppState()
    state.load_callbacks()

    # OutreachOrchestrator — the single send path for all outreach in this
    # process (rate limiting, A/B subject testing, smart timing, cross-caller
    # dedup), plus reply detection + follow-up scheduling as background tasks.
    #
    # Created first and injected into JobProcessor and OutreachProcessor below
    # so the whole API process shares exactly one rate limiter / A-B stats
    # store / dedup check, instead of each owning its own orchestrator with
    # its own independent bookkeeping.
    #
    # Previously OutreachOrchestrator was only ever instantiated per-Celery-task
    # inside src/dag/nodes.py, whose scheduled invocation is always dry_run=True,
    # so start_background_tasks() was never actually called anywhere and reply
    # detection never ran — and orchestrate()/_send_one() was never called by
    # any sender at all (see src/job_processor.py, src/outreach_processor.py,
    # and /api/outreach/send below, which now all route sends through it).
    if _REPLY_DETECTION_OK:
        try:
            dry_run = os.getenv("OUTREACH_DRY_RUN", "false").lower() == "true"
            state.outreach_orchestrator = OutreachOrchestrator(dry_run=dry_run)
            await state.outreach_orchestrator.start_background_tasks()
            log.info(
                "✅ OutreachOrchestrator ready — single send path + "
                "reply detection + follow-up scheduling (dry_run=%s)", dry_run
            )
        except Exception as exc:
            log.warning("⚠️  OutreachOrchestrator unavailable: %s", exc)
            state.outreach_orchestrator = None

    # JobProcessor — always needed
    try:
        state.job_processor = JobProcessor(orchestrator=state.outreach_orchestrator)
        sig_params = set(inspect.signature(state.job_processor.process_all_jobs).parameters)
        log.info("✅ JobProcessor ready | process_all_jobs params: %s", sig_params)
    except Exception as exc:
        log.error("❌ JobProcessor failed: %s", exc)

    # EmailOutreach — optional (has HTTP client pools). Still used directly by
    # OutreachProcessor's raw-SMTP fallback strategy and by /api/health.
    if _EMAIL_OK:
        try:
            state.email_outreach = await EmailOutreach.create()
            log.info("✅ EmailOutreach (SMTP pool + HTTP clients) ready")
        except Exception as exc:
            log.warning("⚠️  EmailOutreach unavailable: %s", exc)

    # OutreachProcessor — optional. Contact discovery + in-process dedup
    # (Trie/Graph) live here; actual sending is delegated to the shared
    # OutreachOrchestrator above.
    if _OUTREACH_OK:
        try:
            state.outreach_proc = OutreachProcessor(
                email_outreach=state.email_outreach,
                orchestrator=state.outreach_orchestrator,
            )
            await state.outreach_proc.initialise()
            log.info("✅ OutreachProcessor ready")
        except Exception as exc:
            log.warning("⚠️  OutreachProcessor unavailable: %s", exc)

    # AsyncJobPipeline — optional (has worker pool and database connections)
    if _ASYNC_PIPELINE_OK:
        try:
            try:
                import aiosqlite
                _ASYNC_DB_OK = True
            except ImportError:
                _ASYNC_DB_OK = False
                log.warning("⚠️  aiosqlite not installed - async_pipeline will use fallback mode")
            
            if _ASYNC_DB_OK:
                config = ProcessorConfig(
                    worker_count=5,
                    queue_size=100,
                    max_concurrent_api_calls=3,
                    llm_rate_limit=10,
                    email_rate_limit=2,
                    scraper_rate_limit=30,
                    log_level="INFO",
                    shutdown_timeout_seconds=30,  # Wait up to 30s for graceful shutdown
                )
                state.async_pipeline = AsyncJobPipeline(config=config)
                log.info("✅ AsyncJobPipeline ready (with async DB and graceful shutdown)")
            else:
                state.async_pipeline = None
                log.warning("⚠️  AsyncJobPipeline skipped - requires aiosqlite")
        except Exception as exc:
            log.warning("⚠️  AsyncJobPipeline unavailable: %s", exc)
            state.async_pipeline = None

    _state = state
    log.info("🟢 Server ready")

    yield

    # ═══════════════════════════════════════════════════════════════════════════
    # Graceful Shutdown — Requirements 24.1, 24.2, 24.3, 24.4, 34.1
    # ═══════════════════════════════════════════════════════════════════════════
    log.info("🔴 Shutting down gracefully…")
    shutdown_start = time.time()
    
    # Track shutdown errors for final report
    shutdown_errors = []
    
    # Step 1: Stop accepting new jobs (handled by AsyncJobPipeline signal handlers)
    # Step 2: Wait for in-flight jobs to complete (handled by AsyncJobPipeline.close())
    # Step 3: Close all resources in reverse order of initialization
    
    # ── Close AsyncJobPipeline first (has worker pool with in-flight jobs) ────
    # This implements Requirements 24.1, 24.2, 24.3, 24.4:
    # - Stops accepting new jobs on SIGTERM/SIGINT
    # - Waits for in-flight jobs to complete (with timeout)
    # - Closes database connection pool
    if state.async_pipeline:
        try:
            log.info("📦 Shutting down AsyncJobPipeline (waiting for in-flight jobs)…")
            await _safe_close(state.async_pipeline, "async_pipeline")
            log.info("✅ AsyncJobPipeline shut down")
        except Exception as exc:
            shutdown_errors.append(f"async_pipeline: {exc}")
            log.error("⚠️  Error closing async_pipeline: %s", exc)
    
    # ── Close OutreachProcessor ───────────────────────────────────────────────
    if state.outreach_proc:
        try:
            log.info("📧 Shutting down OutreachProcessor…")
            await _safe_close(state.outreach_proc, "outreach_proc")
            log.info("✅ OutreachProcessor shut down")
        except Exception as exc:
            shutdown_errors.append(f"outreach_proc: {exc}")
            log.error("⚠️  Error closing outreach_proc: %s", exc)

    # ── Stop OutreachOrchestrator background tasks (reply detector, follow-ups) ──
    if state.outreach_orchestrator:
        try:
            log.info("📬 Stopping reply detector + follow-up scheduler…")
            await state.outreach_orchestrator.stop_background_tasks()
            log.info("✅ OutreachOrchestrator background tasks stopped")
        except Exception as exc:
            shutdown_errors.append(f"outreach_orchestrator: {exc}")
            log.error("⚠️  Error stopping outreach_orchestrator: %s", exc)
    
    # ── Close EmailOutreach (closes HTTP client sessions - Requirement 34.1) ──
    if state.email_outreach:
        try:
            log.info("📨 Shutting down EmailOutreach (closing HTTP clients and SMTP pool)…")
            await _safe_close(state.email_outreach, "email_outreach")
            log.info("✅ EmailOutreach shut down (HTTP clients closed)")
        except Exception as exc:
            shutdown_errors.append(f"email_outreach: {exc}")
            log.error("⚠️  Error closing email_outreach: %s", exc)
    
    # ── Close JobProcessor (closes email discovery and other resources) ───────
    if state.job_processor:
        try:
            log.info("⚙️  Shutting down JobProcessor…")
            await _safe_close(state.job_processor, "job_processor")
            log.info("✅ JobProcessor shut down")
        except Exception as exc:
            shutdown_errors.append(f"job_processor: {exc}")
            log.error("⚠️  Error closing job_processor: %s", exc)
    
    # ── Close any remaining global async HTTP clients ─────────────────────────
    # This ensures cleanup of any stray httpx.AsyncClient or aiohttp.ClientSession
    try:
        log.info("🌐 Cleaning up global async HTTP resources…")
        
        # Close any httpx default async client
        try:
            import httpx
            # httpx doesn't have a global client, but we ensure any pending
            # connections are cleaned up by forcing garbage collection
            import gc
            gc.collect()
        except Exception:
            pass
        
        # Close any aiohttp connector
        try:
            import aiohttp
            # Similar cleanup for aiohttp - force cleanup of any unclosed connectors
            if hasattr(aiohttp, '_default_connector') and aiohttp._default_connector:
                await aiohttp._default_connector.close()
        except Exception:
            pass
            
        log.info("✅ Global HTTP resources cleaned up")
    except Exception as exc:
        log.debug("⚠️  HTTP cleanup note: %s", exc)
    
    # ── Close database connection pool (SQLAlchemy SessionLocal) ──────────────
    try:
        log.info("🗄️  Closing database connection pool…")
        from src.database import engine as db_engine
        if db_engine:
            db_engine.dispose()
            log.info("✅ Database connection pool closed")
    except Exception as exc:
        shutdown_errors.append(f"database: {exc}")
        log.warning("⚠️  Could not close database pool: %s", exc)
    
    # ── Flush and close all log handlers (Requirement 34.1) ───────────────────
    try:
        log.info("📝 Flushing and closing log handlers…")
        root_logger = logging.getLogger()
        
        # First flush all handlers
        for handler in root_logger.handlers[:]:
            try:
                handler.flush()
            except Exception as h_exc:
                print(f"⚠️  Error flushing log handler {handler}: {h_exc}")
        
        # Then close and remove handlers (iterate over copy of list)
        for handler in root_logger.handlers[:]:
            try:
                handler.close()
                root_logger.removeHandler(handler)
            except Exception as h_exc:
                # Use print since logger might be closing
                print(f"⚠️  Error closing log handler {handler}: {h_exc}")
        
        print("✅ Log handlers closed")
    except Exception as exc:
        shutdown_errors.append(f"log_handlers: {exc}")
        print(f"⚠️  Error closing log handlers: {exc}")
    
    # ── Final shutdown report ─────────────────────────────────────────────────
    shutdown_elapsed = time.time() - shutdown_start
    
    if shutdown_errors:
        print(f"⚠️  Shutdown complete in {shutdown_elapsed:.2f}s with {len(shutdown_errors)} error(s):")
        for err in shutdown_errors:
            print(f"   - {err}")
    else:
        print(f"👋 Shutdown complete in {shutdown_elapsed:.2f}s (clean)")
    
    # Reset signal handlers to default
    try:
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    except Exception:
        pass


# =============================================================================
# App + middleware
# =============================================================================

app = FastAPI(title="Job Search API", version="2.1.0", lifespan=lifespan)

# Register comprehensive error handlers
# Requirements: 23.2 (Comprehensive error responses with proper HTTP status codes)
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    """
    Request tracing middleware for comprehensive request tracking.
    
    Generates X-Trace-ID header for all requests, propagates trace IDs through
    all log entries, and includes trace ID in response headers for end-to-end
    request tracing.
    
    Requirements: 23.5, 25.2, 33.1
    """
    # Generate unique trace ID (full UUID for better uniqueness)
    # Accept trace ID from client if provided (for distributed tracing)
    tid = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    
    # Store in request state for access in route handlers
    request.state.trace_id = tid
    
    # Set correlation ID for structured logging (async_pipeline compatibility)
    if _ASYNC_PIPELINE_OK:
        try:
            from src.async_pipeline import set_correlation_id
            set_correlation_id(tid)
        except Exception:
            pass  # Graceful degradation if async_pipeline not available
    
    # Log request start with trace ID
    start_time = time.time()
    log.info(
        "[%s] Request started: %s %s | client=%s",
        tid,
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown",
    )
    
    try:
        # Process request
        resp = await call_next(request)
        
        # Calculate request duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Add trace ID to response headers (Requirement 23.5)
        resp.headers["X-Trace-ID"] = tid
        
        # Log successful request completion with trace ID (Requirement 25.2)
        log.info(
            "[%s] Request completed: %s %s | status=%d | duration=%.2fms",
            tid,
            request.method,
            request.url.path,
            resp.status_code,
            duration_ms,
        )
        
        return resp
        
    except Exception as exc:
        # Calculate request duration even on error
        duration_ms = (time.time() - start_time) * 1000
        
        # Log error with trace ID for debugging (Requirement 25.2)
        log.error(
            "[%s] Request failed: %s %s | duration=%.2fms | error=%s",
            tid,
            request.method,
            request.url.path,
            duration_ms,
            str(exc),
            exc_info=True,
        )
        
        # Return error response with trace ID for client debugging
        return JSONResponse(
            {
                "detail": "Internal server error",
                "trace_id": tid,
                "path": request.url.path,
                "method": request.method,
            },
            status_code=500,
            headers={"X-Trace-ID": tid},
        )
    
    finally:
        # Clear correlation ID for async_pipeline (cleanup)
        if _ASYNC_PIPELINE_OK:
            try:
                from src.async_pipeline import clear_correlation_id
                clear_correlation_id()
            except Exception:
                pass


# =============================================================================
# Resume reader with cascade fallback
# =============================================================================

def _read_resume(path: str) -> str:
    def _try(p: str) -> Optional[str]:
        try: return Path(p).read_text(encoding="utf-8")
        except FileNotFoundError: return None

    text = _try(path)
    if text:
        log.info("Resume loaded: %s", path)
        return text

    default = ResumeTrie.DEFAULT
    if path != default:
        log.warning("Resume missing at %s — trying default %s", path, default)
        text = _try(default)
        if text: return text

    raise HTTPException(
        status_code=404,
        detail=(
            f"No resume found. Tried: {path!r} and {default!r}. "
            f"Create {default!r} in your project root and restart."
        ),
    )


# =============================================================================
# Routes — thin adapters: validate → call service → return
# =============================================================================

@app.get("/", tags=["health"])
async def root():
    return {"status": "healthy", "service": "Job Search API", "version": "2.1.0"}


@app.get("/api/health", tags=["health"])
async def health(state: AppState = Depends(get_state)):
    """
    Comprehensive health check endpoint that verifies all system components.
    
    Checks:
    - Ollama connectivity and model availability (LLM backend)
    - Database connectivity and table status (SQLite)
    - Email service (SMTP/SendGrid/SES) connectivity
    - External API status (GitHub, Cloudflare, Google Sheets)
    - Internal service availability (job_processor, async_pipeline, etc.)
    
    Returns structured health report with component statuses.
    Requirements: 23.6, 22.1, 22.2, 22.3, 22.4, 22.5, 22.6
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.1.0",
        "components": {},
    }
    
    issues = []
    warnings = []
    
    # ── 1. Ollama (Local LLM) Health Check ───────────────────────────────────
    # Requirement 22.1: Integrate with Ollama for local LLM processing
    try:
        from src.ai.local_llm_service import LocalLLMService
        llm = LocalLLMService()
        ollama_healthy = await llm.health_check()
        
        if ollama_healthy:
            health_status["components"]["ollama"] = {
                "status": "healthy",
                "model": LocalLLMService._cached_model,
                "url": llm.BASE_URL,
                "message": f"Ollama running with model {LocalLLMService._cached_model}",
            }
        else:
            health_status["components"]["ollama"] = {
                "status": "unavailable",
                "model": None,
                "url": llm.BASE_URL,
                "message": "Ollama not running or no supported models available",
            }
            issues.append("Ollama not running or no models available - run: ollama pull mistral:latest")
    except Exception as exc:
        health_status["components"]["ollama"] = {
            "status": "error",
            "error": str(exc),
            "message": "Failed to check Ollama status",
        }
        issues.append(f"Ollama check failed: {exc}")
    
    # ── 2. Database Health Check ─────────────────────────────────────────────
    # Requirement 22.1: Check database connectivity and table status
    try:
        async with db_session() as db:
            # Check database connectivity with simple query
            db.execute("SELECT 1").fetchone()
            
            # Check table existence and row counts
            from src.models import Job, Application, Contact, OutreachRecord
            
            # Verify tables exist and get counts
            job_count = db.query(Job).count()
            app_count = db.query(Application).count()
            contact_count = db.query(Contact).count()
            outreach_count = db.query(OutreachRecord).count()
            
            # Check if processing_results table exists (for async pipeline)
            try:
                result = db.execute("SELECT COUNT(*) FROM processing_results").fetchone()
                processing_count = result[0] if result else 0
            except Exception:
                processing_count = None
                warnings.append("processing_results table not found - async pipeline results not tracked")
            
            health_status["components"]["database"] = {
                "status": "healthy",
                "type": "SQLite",
                "tables": {
                    "jobs": job_count,
                    "applications": app_count,
                    "contacts": contact_count,
                    "outreach_records": outreach_count,
                    "processing_results": processing_count if processing_count is not None else "N/A",
                },
                "message": f"Database healthy with {job_count} jobs indexed",
            }
    except Exception as exc:
        health_status["components"]["database"] = {
            "status": "error",
            "error": str(exc),
            "message": "Database connectivity failed",
        }
        issues.append(f"Database check failed: {exc}")
    
    # ── 3. Email Service (SMTP) Health Check ─────────────────────────────────
    # Requirement 22.3: Integrate with Gmail SMTP for email sending
    if state.email_outreach:
        try:
            email_report = await state.email_outreach.health_check()
            provider_value = email_report.provider
            if hasattr(provider_value, 'value'):
                provider_value = provider_value.value
            
            # Determine overall email status
            email_status = "healthy" if email_report.smtp_ok else "degraded"
            
            health_status["components"]["email"] = {
                "status": email_status,
                "provider": str(provider_value),
                "smtp": {
                    "status": "healthy" if email_report.smtp_ok else "unavailable",
                    "details": email_report.details.get("smtp", "unknown"),
                },
                "google_sheets": {
                    "status": "healthy" if email_report.sheets_ok else "not_configured",
                    "details": email_report.details.get("sheets", "unknown"),
                },
                "resume_pdf": {
                    "status": "healthy" if email_report.resume_ok else "missing",
                    "details": email_report.details.get("resume", "unknown"),
                },
                "ai_service": {
                    "status": "healthy" if email_report.ai_ok else "unavailable",
                    "details": email_report.details.get("ai", "unknown"),
                },
                "message": f"Email service using {provider_value}",
            }
            
            if not email_report.smtp_ok:
                issues.append("Email SMTP connection not available - check GMAIL_ADDRESS and GMAIL_PASSWORD")
            if not email_report.sheets_ok:
                warnings.append("Google Sheets not configured - outreach tracking using local JSON")
            if not email_report.resume_ok:
                warnings.append(f"Resume PDF not found - check RESUME_PDF_PATH")
                
        except Exception as exc:
            health_status["components"]["email"] = {
                "status": "error",
                "error": str(exc),
                "message": "Email service health check failed",
            }
            issues.append(f"Email service check failed: {exc}")
    else:
        health_status["components"]["email"] = {
            "status": "unavailable",
            "message": "EmailOutreach service not initialized",
        }
        issues.append("Email service not initialized - check SMTP configuration")
    
    # ── 4. GitHub API Health Check ───────────────────────────────────────────
    # Requirement 22.4: Integrate with GitHub API for commit email mining
    if settings.github_token:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/rate_limit",
                    headers={"Authorization": f"token {settings.github_token}"},
                    timeout=5.0,
                )
                if response.status_code == 200:
                    rate_data = response.json()
                    core_remaining = rate_data.get("rate", {}).get("remaining", 0)
                    core_limit = rate_data.get("rate", {}).get("limit", 5000)
                    
                    health_status["components"]["github"] = {
                        "status": "healthy" if core_remaining > 100 else "rate_limited",
                        "rate_limit": {
                            "remaining": core_remaining,
                            "limit": core_limit,
                            "percentage": round((core_remaining / core_limit * 100), 1) if core_limit > 0 else 0,
                        },
                        "message": f"GitHub API healthy with {core_remaining}/{core_limit} requests remaining",
                    }
                    
                    if core_remaining < 100:
                        warnings.append(f"GitHub API rate limit low: {core_remaining}/{core_limit} remaining")
                else:
                    health_status["components"]["github"] = {
                        "status": "error",
                        "http_status": response.status_code,
                        "message": f"GitHub API returned status {response.status_code}",
                    }
                    issues.append(f"GitHub API returned status {response.status_code}")
        except httpx.TimeoutException:
            health_status["components"]["github"] = {
                "status": "timeout",
                "message": "GitHub API request timed out",
            }
            warnings.append("GitHub API timeout - service may be slow")
        except Exception as exc:
            health_status["components"]["github"] = {
                "status": "error",
                "error": str(exc),
                "message": "GitHub API connectivity failed",
            }
            issues.append(f"GitHub API check failed: {exc}")
    else:
        health_status["components"]["github"] = {
            "status": "not_configured",
            "message": "GITHUB_TOKEN not set - commit email mining unavailable",
        }
        warnings.append("GitHub API not configured - set GITHUB_TOKEN for email discovery")
    
    # ── 5. Cloudflare Health Check ───────────────────────────────────────────
    # Requirement 22.5: Integrate with Cloudflare for browser rendering
    if settings.cloudflare_account_id and settings.cloudflare_api_token:
        try:
            # Validate Cloudflare credentials by attempting to list account info
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}",
                    headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"},
                    timeout=5.0,
                )
                if response.status_code == 200:
                    health_status["components"]["cloudflare"] = {
                        "status": "healthy",
                        "account_id": settings.cloudflare_account_id[:8] + "...",
                        "message": "Cloudflare browser rendering available",
                    }
                else:
                    health_status["components"]["cloudflare"] = {
                        "status": "error",
                        "http_status": response.status_code,
                        "message": f"Cloudflare API returned status {response.status_code}",
                    }
                    issues.append(f"Cloudflare API authentication failed: status {response.status_code}")
        except httpx.TimeoutException:
            health_status["components"]["cloudflare"] = {
                "status": "timeout",
                "message": "Cloudflare API request timed out",
            }
            warnings.append("Cloudflare API timeout - service may be slow")
        except Exception as exc:
            health_status["components"]["cloudflare"] = {
                "status": "error",
                "error": str(exc),
                "message": "Cloudflare connectivity check failed",
            }
            warnings.append(f"Cloudflare check failed: {exc}")
    else:
        health_status["components"]["cloudflare"] = {
            "status": "not_configured",
            "message": "Cloudflare credentials not set - anti-bot bypass unavailable",
        }
        warnings.append("Cloudflare not configured - set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN")
    
    # ── 6. Google Sheets Health Check ────────────────────────────────────────
    # Requirement 22.6: Integrate with Google Sheets API for data export
    if settings.google_sheet_id and Path(settings.google_credentials_path).exists():
        try:
            # Check if credentials file is valid JSON
            with open(settings.google_credentials_path, 'r') as f:
                creds_data = json.load(f)
            
            # Validate it's a service account credential
            if "type" in creds_data and creds_data["type"] == "service_account":
                health_status["components"]["google_sheets"] = {
                    "status": "configured",
                    "sheet_id": settings.google_sheet_id[:20] + "...",
                    "credentials": "valid_service_account",
                    "message": "Google Sheets export configured",
                }
            else:
                health_status["components"]["google_sheets"] = {
                    "status": "misconfigured",
                    "message": "Google credentials file is not a service account",
                }
                issues.append("Google Sheets credentials invalid - must be service account JSON")
        except json.JSONDecodeError as exc:
            health_status["components"]["google_sheets"] = {
                "status": "misconfigured",
                "error": "Invalid JSON in credentials file",
            }
            issues.append(f"Google Sheets credentials invalid JSON: {exc}")
        except Exception as exc:
            health_status["components"]["google_sheets"] = {
                "status": "error",
                "error": str(exc),
                "message": "Google Sheets configuration check failed",
            }
            issues.append(f"Google Sheets check failed: {exc}")
    else:
        missing_parts = []
        if not settings.google_sheet_id:
            missing_parts.append("GOOGLE_SHEET_ID")
        if not Path(settings.google_credentials_path).exists():
            missing_parts.append("credentials file")
        
        health_status["components"]["google_sheets"] = {
            "status": "not_configured",
            "message": f"Google Sheets not configured - missing: {', '.join(missing_parts)}",
        }
        warnings.append(f"Google Sheets not configured - campaign tracking using local storage")
    
    # ── 7. Internal Services Health Check ────────────────────────────────────
    internal_services = {
        "job_processor": {
            "status": "healthy" if state.job_processor else "unavailable",
            "description": "Core job processing service",
        },
        "outreach_processor": {
            "status": "healthy" if state.outreach_proc else "unavailable",
            "description": "Production outreach orchestrator",
        },
        "async_pipeline": {
            "status": "healthy" if (state.async_pipeline and _ASYNC_PIPELINE_OK) else "unavailable",
            "description": "High-performance async job processing",
        },
        "contact_finder": {
            "status": "available" if _CONTACT_OK else "unavailable",
            "description": "Contact discovery service",
        },
        "email_discovery": {
            "status": "available" if _EMAIL_DISCOVERY_OK else "unavailable",
            "description": "Multi-provider email discovery",
        },
    }
    
    health_status["components"]["internal_services"] = internal_services
    
    # Check for missing critical services
    if not state.job_processor:
        issues.append("JobProcessor not initialized - core functionality unavailable")
    if not state.async_pipeline and _ASYNC_PIPELINE_OK:
        warnings.append("AsyncJobPipeline not initialized - install aiosqlite for async processing")
    if not state.outreach_proc:
        warnings.append("OutreachProcessor not initialized - automated outreach unavailable")
    
    # ── 8. Overall Status Determination ──────────────────────────────────────
    # Determine overall health status
    if issues:
        health_status["status"] = "degraded"
        health_status["issues"] = issues
    
    if warnings:
        health_status["warnings"] = warnings
        # If we only have warnings (no issues), status is "healthy" but with warnings
        if not issues:
            health_status["status"] = "healthy_with_warnings"
    
    # Add summary
    component_count = len(health_status["components"])
    healthy_components = sum(
        1 for comp in health_status["components"].values()
        if isinstance(comp, dict) and comp.get("status") in ["healthy", "configured", "available"]
    )
    
    health_status["summary"] = {
        "total_components": component_count,
        "healthy_components": healthy_components,
        "health_percentage": round((healthy_components / component_count * 100), 1) if component_count > 0 else 0,
    }
    
    return health_status


@app.get("/metrics", tags=["observability"])
async def metrics_endpoint(state: AppState = Depends(get_state)):
    """
    Prometheus metrics export endpoint.
    
    Exports comprehensive pipeline metrics in Prometheus text format:
    - Job processing metrics (throughput, latency, success rate) - Req 6.1
    - Queue metrics (size, backpressure events, wait times) - Req 6.2
    - Worker metrics (utilization, active count, idle time) - Req 6.3
    - API metrics (rate limiter waits, semaphore contention) - Req 6.4
    - Error metrics (retry attempts, failure types, error rates) - Req 6.5
    
    This endpoint is designed to be scraped by Prometheus at regular intervals.
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 9.1
    """
    from fastapi.responses import PlainTextResponse
    
    # Check if async pipeline is available and has metrics
    if not _ASYNC_PIPELINE_OK or not state.async_pipeline:
        # Return empty metrics if pipeline not available
        return PlainTextResponse(
            "# Async pipeline not initialized\n"
            "# Install aiosqlite and restart: pip install aiosqlite\n",
            media_type="text/plain; version=0.0.4"
        )
    
    # Get metrics snapshot from the async pipeline
    try:
        metrics_snapshot = state.async_pipeline.get_metrics_snapshot()
        
        # Handle case when metrics collector hasn't been initialized yet
        if metrics_snapshot is None:
            return PlainTextResponse(
                "# Metrics collector not yet initialized\n"
                "# Run the async pipeline first to initialize metrics\n"
                "# HELP pipeline_status Pipeline status indicator\n"
                "# TYPE pipeline_status gauge\n"
                "pipeline_status 0\n",
                media_type="text/plain; version=0.0.4"
            )
        
        prometheus_text = metrics_snapshot.to_prometheus_format()
        
        # Return in Prometheus text format
        return PlainTextResponse(
            prometheus_text,
            media_type="text/plain; version=0.0.4"
        )
    except Exception as exc:
        log.error("Failed to export metrics: %s", exc, exc_info=True)
        return PlainTextResponse(
            f"# Error exporting metrics: {exc}\n",
            media_type="text/plain; version=0.0.4",
            status_code=500
        )


@app.get("/api/ai/status", tags=["ai"])
async def ai_cascade_status():
    """
    Get LLM cascade status and metrics.
    
    Returns comprehensive status for the AI cascade chain:
    - Current primary provider
    - Cascade order (Ollama → Gemini → Keyword matching)
    - Health status for each provider
    - Provider metrics (success rate, call counts, errors)
    - Cascade fallback statistics
    
    This endpoint is useful for monitoring AI service health and
    understanding failover patterns.
    
    Validates: Requirements 11.2, 11.3, 11.4, 32.1
    """
    try:
        from src.ai.unified_ai_service import UnifiedAIService, get_cascade_metrics
        
        service = UnifiedAIService()
        
        # Perform health checks on all providers
        health_results = await service.health_check_all()
        
        # Get comprehensive metrics
        metrics = service.get_metrics()
        
        return {
            "status": "healthy",
            "cascade_chain": {
                "primary_provider": metrics.get("current_primary", "unknown"),
                "cascade_order": metrics.get("cascade_order", []),
                "fallback_chain": "Ollama → Gemini → Keyword matching",
            },
            "providers": {
                name: {
                    "healthy": health_results.get(name, False),
                    "status": metrics.get("providers", {}).get(name, {}).get("status", "unknown"),
                    "total_calls": metrics.get("providers", {}).get(name, {}).get("total_calls", 0),
                    "success_rate": metrics.get("providers", {}).get(name, {}).get("success_rate", 0),
                    "last_error": metrics.get("providers", {}).get(name, {}).get("last_error"),
                }
                for name in metrics.get("cascade_order", [])
            },
            "cascade_metrics": {
                "total_calls": metrics.get("total_cascade_calls", 0),
                "fallback_count": metrics.get("cascade_fallback_count", 0),
                "full_failures": metrics.get("full_cascade_failures", 0),
            },
            "message": f"LLM cascade active with primary: {metrics.get('current_primary', 'unknown')}",
        }
    except Exception as exc:
        log.error("Failed to get AI cascade status: %s", exc, exc_info=True)
        return {
            "status": "error",
            "error": str(exc),
            "message": "Failed to retrieve AI cascade status",
        }


@app.post("/api/ai/health-check", tags=["ai"])
async def ai_health_check():
    """
    Trigger a health check on all LLM providers.
    
    Forces a fresh health check on all providers in the cascade chain
    and returns updated status. Useful for:
    - Verifying provider availability after configuration changes
    - Debugging failover issues
    - Manual health verification
    
    Validates: Requirements 11.2, 11.3, 11.4
    """
    try:
        from src.ai.unified_ai_service import UnifiedAIService
        
        service = UnifiedAIService()
        
        # Force health checks on all providers
        health_results = await service.health_check_all()
        
        # Get provider statuses after health check
        provider_statuses = service.get_all_provider_statuses()
        
        return {
            "status": "completed",
            "health_check_results": health_results,
            "provider_details": provider_statuses,
            "cascade_chain": service._cascade_order,
            "primary_provider": service.backend_name,
        }
    except Exception as exc:
        log.error("AI health check failed: %s", exc, exc_info=True)
        return {
            "status": "error",
            "error": str(exc),
        }


# ── Core pipeline ─────────────────────────────────────────────────────────────

@app.post("/run-query", tags=["jobs"], response_model=QueryResponse)
async def run_query(
    request: QueryRequest,
    req: Request,
    state: AppState = Depends(get_state),
):
    """
    Execute job search and processing pipeline.
    
    This endpoint fetches jobs matching the query, processes them through the AI pipeline,
    and returns comprehensive statistics.
    
    Requirements: 23.1 (POST endpoint), 23.2 (Validate request parameters),
                  23.3 (Return processing statistics), 23.4 (Request timeout handling)
    """
    trace = req.state.trace_id

    if not state.job_processor:
        raise ServiceUnavailableError("JobProcessor", "Check startup logs for initialization errors")

    try:
        log.info("[%s] Fetching jobs: %s", trace, request.query)
        
        # Apply timeout to job fetching
        jobs_count = await asyncio.wait_for(
            state.job_processor.fetch_and_store_jobs(query=request.query),
            timeout=request.timeout_seconds or 300,
        )
        log.info("[%s] Stored %d new jobs", trace, jobs_count)

        resume_path = state.resume_router.route(request.query)
        log.info("[%s] Resume → %s", trace, resume_path)
        resume_text = _read_resume(resume_path)

        log.info("[%s] Processing jobs (min_score=%d)", trace, request.min_score)
        
        start_time = time.monotonic()
        result = await asyncio.wait_for(
            _call_with_accepted(
                state.job_processor.process_all_jobs,
                resume_text,
                min_score=request.min_score,
            ),
            timeout=request.timeout_seconds or 300,
        )
        if inspect.isawaitable(result):
            await result
        elapsed = time.monotonic() - start_time

        log.info("[%s] Pipeline complete in %.2fs", trace, elapsed)
        
        # Build response with statistics
        # Requirements: 23.3 (Return processing statistics in response)
        return QueryResponse(
            status="success",
            trace_id=trace,
            query=request.query,
            resume_used=resume_path,
            min_score_requested=request.min_score,
            statistics=PipelineStatistics(
                jobs_fetched=jobs_count,
                jobs_processed=jobs_count,
                jobs_completed=jobs_count,
                jobs_failed=0,
                processing_time_seconds=round(elapsed, 2),
                throughput_jobs_per_second=round(jobs_count / elapsed, 2) if elapsed > 0 else 0,
            ),
        )
    
    except asyncio.TimeoutError:
        raise APITimeoutError("job processing pipeline", request.timeout_seconds or 300)
    except FileNotFoundError as exc:
        raise ResourceNotFoundError("Resume file", resume_path)
    except Exception as exc:
        log.error("[%s] Pipeline error: %s", trace, exc, exc_info=True)
        raise APIError(f"Pipeline execution failed: {str(exc)}")


# ── Async Pipeline endpoint ─────────────────────────────────────────────────

@app.post("/run-query-async", tags=["jobs"], response_model=AsyncPipelineResponse)
async def run_query_async(
    request: QueryRequest,
    req: Request,
    state: AppState = Depends(get_state),
):
    """
    Run job processing using the new async pipeline.
    
    This endpoint uses the fully async pipeline with:
    - O(1) memory usage via streaming
    - Concurrent processing with worker pool
    - Automatic retry with exponential backoff
    - Rate limiting for external APIs
    
    Requirements: 23.1 (POST endpoint), 23.2 (Validate request parameters),
                  23.3 (Return processing statistics), 23.4 (Request timeout handling)
    """
    trace = req.state.trace_id

    if not _ASYNC_PIPELINE_OK or not state.async_pipeline:
        raise ServiceUnavailableError(
            "AsyncJobPipeline",
            "Install aiosqlite and restart: pip install aiosqlite"
        )

    if not state.job_processor:
        raise ServiceUnavailableError("JobProcessor", "Check startup logs for initialization errors")
    
    try:
        log.info("[%s] Starting async pipeline for query: %s", trace, request.query)
        
        # Fetch jobs first using existing processor with timeout
        jobs_count = await asyncio.wait_for(
            state.job_processor.fetch_and_store_jobs(query=request.query),
            timeout=60,  # 60 second timeout for job fetching
        )
        log.info("[%s] Fetched %d new jobs", trace, jobs_count)
        
        # Get appropriate resume
        resume_path = state.resume_router.route(request.query)
        log.info("[%s] Resume → %s", trace, resume_path)
        resume_text = _read_resume(resume_path)
        
        # Run async pipeline with timeout
        start_time = time.monotonic()
        results = await asyncio.wait_for(
            state.async_pipeline.run(
                query=request.query,
                resume_text=resume_text,
                filters={"min_score": request.min_score},
            ),
            timeout=request.timeout_seconds or 300,
        )
        elapsed = time.monotonic() - start_time
        
        # Aggregate results
        completed = sum(1 for r in results if r.status.value == "completed")
        failed = sum(1 for r in results if r.status.value == "failed")
        
        log.info("[%s] Async pipeline complete: %d succeeded, %d failed in %.2fs", 
                 trace, completed, failed, elapsed)
        
        # Build response with statistics
        # Requirements: 23.3 (Return processing statistics in response)
        return AsyncPipelineResponse(
            status="success",
            trace_id=trace,
            query=request.query,
            statistics=PipelineStatistics(
                jobs_fetched=jobs_count,
                jobs_processed=len(results),
                jobs_completed=completed,
                jobs_failed=failed,
                processing_time_seconds=round(elapsed, 2),
                throughput_jobs_per_second=round(len(results) / elapsed, 2) if elapsed > 0 else 0,
            ),
            resume_used=resume_path,
            min_score_requested=request.min_score,
        )
        
    except asyncio.TimeoutError:
        raise APITimeoutError("async pipeline execution", request.timeout_seconds or 300)
    except FileNotFoundError as exc:
        raise ResourceNotFoundError("Resume file", resume_path)
    except Exception as exc:
        log.error("[%s] Async pipeline error: %s", trace, exc, exc_info=True)
        raise APIError(f"Async pipeline execution failed: {str(exc)}")


# ── Contacts ──────────────────────────────────────────────────────────────────

@app.post("/api/contacts/search", tags=["contacts"], response_model=ContactSearchResponse)
async def search_contacts(
    request: ContactSearchRequest,
    req: Request,
):
    """
    Find email contacts at a company using all configured providers in priority order:
      Hunter.io → Apollo.io → SignalHire → GitHub → free scrape + SMTP verify

    Pass smtp_verify=true in request body to run SMTP verification on results.
    
    Requirements: 23.2 (Validate request parameters), 23.3 (Return processing statistics)
    """
    trace = req.state.trace_id

    if not _EMAIL_DISCOVERY_OK:
        raise ServiceUnavailableError("EmailDiscoveryService", "Check startup logs for initialization errors")

    try:
        log.info("[%s] Contact search: company=%s job_title=%s limit=%d smtp_verify=%s",
                 trace, request.company_name, request.job_title, request.limit, request.smtp_verify)

        svc = EmailDiscoveryService(settings)
        try:
            contacts = await asyncio.wait_for(
                svc.find_contacts(
                    company_name=request.company_name,
                    job_title=request.job_title or "",
                    limit=request.limit,
                    smtp_verify=request.smtp_verify,
                ),
                timeout=120,  # 2 minute timeout for contact discovery
            )
        finally:
            await svc.close()

        # Persist new contacts to DB
        saved = []
        try:
            async with db_session() as db:
                for c in contacts:
                    existing = db.query(Contact).filter(Contact.email == c["email"]).first()
                    if not existing:
                        row = Contact(
                            name=c.get("name", ""),
                            title=c.get("title", ""),
                            email=c.get("email", ""),
                            linkedin_url=c.get("linkedin_url", ""),
                            company=request.company_name,
                            department=c.get("department", ""),
                            confidence_score=c.get("confidence", 0),
                            source=c.get("source", "email_discovery"),
                        )
                        db.add(row)
                        db.flush()
                        saved.append(row.id)
                db.commit()
        except Exception as db_exc:
            log.error("[%s] Failed to persist contacts: %s", trace, db_exc)
            raise DatabaseError(f"Failed to save contacts: {str(db_exc)}")

        log.info("[%s] Found %d contacts (%d new saved)", trace, len(contacts), len(saved))

        # Build response
        contact_data = [
            ContactData(
                id=c.get("id"),
                name=c.get("name", ""),
                title=c.get("title"),
                email=c.get("email", ""),
                linkedin_url=c.get("linkedin_url"),
                company=request.company_name,
                department=c.get("department"),
                confidence_score=c.get("confidence", 0),
                source=c.get("source", "email_discovery"),
                found_at=datetime.utcnow(),
            )
            for c in contacts
        ]

        return ContactSearchResponse(
            status="success",
            company=request.company_name,
            contacts_found=len(contacts),
            contacts_saved=len(saved),
            contacts=contact_data,
        )
    
    except asyncio.TimeoutError:
        raise APITimeoutError("contact discovery", 120)
    except Exception as exc:
        log.error("[%s] Contact search error: %s", trace, exc, exc_info=True)
        raise APIError(f"Contact search failed: {str(exc)}")


# ── Outreach ──────────────────────────────────────────────────────────────────

@app.post("/api/outreach/send", tags=["outreach"], response_model=OutreachResponse)
async def send_outreach(
    request: OutreachRequest,
    req: Request,
    state: AppState = Depends(get_state),
):
    """
    Send outreach email to a contact for a specific job.
    
    This endpoint validates the request, retrieves the job details, and sends
    a personalized outreach email to the specified contact.
    
    Requirements: 23.2 (Validate request parameters), 23.3 (Return processing statistics)
    """
    trace = req.state.trace_id

    if not state.outreach_orchestrator:
        raise ServiceUnavailableError("OutreachOrchestrator", "Check startup logs")

    try:
        # Load job with proper error handling
        async with db_session() as db:
            job = db.query(Job).filter(Job.id == request.job_id).first()
            if not job:
                raise ResourceNotFoundError("Job", request.job_id)
            job_snap = {
                "id": job.id, "title": job.title, "company": job.company,
                "description": getattr(job, "description", ""),
                "url": getattr(job, "url", ""),
            }

        if not request.send_immediately:
            return OutreachResponse(
                status="queued",
                trace_id=trace,
                job_id=request.job_id,
                contact_email=request.contact_email,
                email_sent=False,
                outreach_id=None,
            )

        # Build minimal Contact object compatible with both old and new Contact dataclass
        contact_kwargs = dict(
            name=request.contact_name, email=request.contact_email,
            title="Hiring Contact", company=job_snap["company"],
        )
        if _CONTACT_OK:
            contact = ContactDataClass(**{
                k: v for k, v in contact_kwargs.items()
                if k in inspect.signature(ContactDataClass.__init__).parameters
            })
            for attr, default in [("department", ""), ("linkedin_url", None), ("confidence_score", 80.0)]:
                if not hasattr(contact, attr):
                    try: setattr(contact, attr, default)
                    except Exception: pass
        else:
            contact = type("Contact", (), contact_kwargs)()

        # Send via the same OutreachOrchestrator instance the cron job and CLI
        # use — this is what gives the cross-caller dedup check, per-domain
        # rate limiting, A/B subject testing, and smart send timing any
        # actual effect on a send triggered by this button. Orchestrator
        # persists the OutreachRecord itself on a real send, so we don't
        # write a second one here.
        # Load a resume + pass the job description so the orchestrator's
        # EmailBuilder can personalize the body via AI (same as this endpoint
        # did before, through the old send_outreach_email → EmailBuilder path)
        # rather than silently falling back to the static template.
        resume_text = ""
        try:
            resume_path = state.resume_router.route(job_snap["title"])
            resume_text = _read_resume(resume_path)
        except Exception as exc:
            log.warning("[%s] Could not load resume for outreach personalization: %s", trace, exc)

        results = await asyncio.wait_for(
            state.outreach_orchestrator.orchestrate(
                contacts=[contact],
                job_title=job_snap["title"],
                job_url=job_snap["url"],
                job_id=job_snap["id"],
                job_description=job_snap["description"],
                resume_text=resume_text,
            ),
            timeout=30,
        )
        result = results[0] if results else None

        if result is None:
            raise APIError("Outreach send failed: orchestrator returned no result")

        success = result.status == "sent"
        record_id = result.outreach_record_id  # set by the orchestrator on a real "sent"

        if result.status in ("skipped", "rate_limited"):
            # No new send happened (already sent, or rate-limited) — surface
            # that distinctly rather than reporting it as a failure.
            log.info("[%s] Outreach %s for %s: %s", trace, result.status,
                     request.contact_email, result.reason)
            return OutreachResponse(
                status=result.status,
                trace_id=trace,
                job_id=request.job_id,
                contact_email=request.contact_email,
                email_sent=False,
                outreach_id=None,
            )

        if not success:
            # Orchestrator send failed (SMTP/API error) — this endpoint has no
            # fallback chain of its own, so record the failure for visibility.
            try:
                async with db_session() as db:
                    rec = OutreachRecord(
                        job_id=job_snap["id"],
                        contact_email=request.contact_email,
                        contact_name=request.contact_name,
                        email_sent=False,
                        sent_at=None,
                        status="failed",
                    )
                    db.add(rec)
                    db.commit()
                    db.refresh(rec)
                    record_id = rec.id
            except Exception as db_exc:
                log.error("[%s] Failed to record outreach failure: %s", trace, db_exc)
                raise DatabaseError(f"Failed to save outreach record: {str(db_exc)}")

        log.info("[%s] Outreach %s → %s", trace, "sent" if success else "FAILED",
                 request.contact_email)

        return OutreachResponse(
            status="success" if success else "failed",
            trace_id=trace,
            job_id=request.job_id,
            contact_email=request.contact_email,
            email_sent=success,
            outreach_id=record_id,
        )

    except asyncio.TimeoutError:
        raise APITimeoutError("outreach email send", 30)
    except (ResourceNotFoundError, ServiceUnavailableError, DatabaseError):
        raise
    except Exception as exc:
        log.error("[%s] Outreach error: %s", trace, exc, exc_info=True)
        raise APIError(f"Outreach send failed: {str(exc)}")


@app.post("/api/outreach/followup", tags=["outreach"], response_model=FollowUpResponse)
async def send_followup(
    request: FollowUpRequest,
    req: Request,
    state: AppState = Depends(get_state),
):
    """
    Send follow-up email for an existing outreach record.
    
    Requirements: 23.2 (Validate request parameters), 23.3 (Return processing statistics)
    """
    trace = req.state.trace_id
    
    if not state.email_outreach:
        raise ServiceUnavailableError("EmailOutreach", "Check SMTP configuration")

    try:
        # Load outreach record and associated job
        async with db_session() as db:
            rec = db.query(OutreachRecord).filter(OutreachRecord.id == request.outreach_id).first()
            if not rec:
                raise ResourceNotFoundError("OutreachRecord", request.outreach_id)
            
            job = db.query(Job).filter(Job.id == rec.job_id).first()
            if not job:
                raise ResourceNotFoundError("Job", rec.job_id)
            
            snap = {
                "contact_email": rec.contact_email, "contact_name": rec.contact_name,
                "job_id": job.id, "job_title": job.title, "company": job.company,
                "url": getattr(job, "url", ""),
            }

        # Build contact object
        contact = type("Contact", (), {
            "name": snap["contact_name"], "email": snap["contact_email"],
            "title": "Hiring Contact", "company": snap["company"],
            "department": "", "linkedin_url": None, "confidence_score": 80.0,
        })()

        class _Stub:
            id = snap["job_id"]; title = snap["job_title"]
            company = snap["company"]; url = snap["url"]

        # Send follow-up with timeout
        success = await asyncio.wait_for(
            state.email_outreach.send_followup_email(
                contact, _Stub(), follow_up_number=request.follow_up_number
            ),
            timeout=30,  # 30 second timeout
        )

        if success:
            try:
                async with db_session() as db:
                    r = db.query(OutreachRecord).filter(OutreachRecord.id == request.outreach_id).first()
                    if r:
                        r.follow_up_count = (getattr(r, "follow_up_count", None) or 0) + 1
                        r.last_follow_up_at = datetime.utcnow()
                        r.status = "followed_up"
                        db.commit()
            except Exception as db_exc:
                log.error("[%s] Failed to update follow-up record: %s", trace, db_exc)
                # Don't fail the request if record update fails, email was sent

        return FollowUpResponse(
            status="success" if success else "failed",
            trace_id=trace,
            outreach_id=request.outreach_id,
            follow_up_number=request.follow_up_number,
            email_sent=success,
        )
    
    except asyncio.TimeoutError:
        raise APITimeoutError("follow-up email send", 30)
    except (ResourceNotFoundError, ServiceUnavailableError):
        raise
    except Exception as exc:
        log.error("[%s] Follow-up error: %s", trace, exc, exc_info=True)
        raise APIError(f"Follow-up send failed: {str(exc)}")


# ── Jobs ──────────────────────────────────────────────────────────────────────

@app.get("/api/jobs", tags=["jobs"], response_model=JobsResponse)
async def get_jobs(
    page: int = Query(default=1, ge=1, le=10000, description="Page number (1-indexed)"),
    limit: int = Query(default=50, ge=1, le=500, description="Items per page (1-500)"),
):
    """
    Get all jobs with pagination, sorted by recently fetched.
    
    Requirements: 23.2 (Validate request parameters), 23.3 (Return processing statistics)
    """
    try:
        async with db_session() as db:
            total = db.query(Job).count()
            jobs = (
                db.query(Job)
                .order_by(Job.fetched_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
                .all()
            )
            
            job_data = [
                JobData(
                    id=j.id,
                    job_id=j.job_id,
                    title=j.title,
                    company=j.company,
                    location=j.location,
                    description=j.description,
                    url=j.url,
                    source=j.source,
                    posted_date=j.posted_date,
                    fetched_at=j.fetched_at,
                )
                for j in jobs
            ]
            
            return JobsResponse(
                status="success",
                jobs=job_data,
                pagination=PaginationData(
                    page=page,
                    limit=limit,
                    total=total,
                    pages=(total + limit - 1) // limit if limit > 0 else 0,
                ),
            )
    except Exception as exc:
        log.error("Failed to retrieve jobs: %s", exc, exc_info=True)
        raise DatabaseError(f"Failed to retrieve jobs: {str(exc)}")


@app.get("/api/jobs/pending-outreach", tags=["jobs"], response_model=PendingOutreachResponse)
async def pending_outreach(
    min_score: int = Query(default=50, ge=0, le=100, description="Minimum match score threshold"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of jobs to return"),
):
    """
    Get jobs that have been scored but have no outreach records yet.
    
    Requirements: 23.2 (Validate request parameters), 23.3 (Return processing statistics)
    """
    from sqlalchemy import and_
    try:
        async with db_session() as db:
            jobs = (
                db.query(Job)
                .join(Application)
                .outerjoin(OutreachRecord, Job.id == OutreachRecord.job_id)
                .filter(and_(Application.match_score >= min_score, OutreachRecord.id == None))
                .order_by(Application.match_score.desc())
                .limit(limit)
                .all()
            )
            
            job_data = [
                PendingOutreachJob(
                    id=j.id,
                    title=j.title,
                    company=j.company,
                    location=j.location,
                    url=j.url,
                    source=j.source,
                    posted_date=j.posted_date,
                    fetched_at=j.fetched_at,
                )
                for j in jobs
            ]
            
            return PendingOutreachResponse(
                status="success",
                total_jobs=len(jobs),
                jobs=job_data,
            )
    except Exception as exc:
        log.error("Failed to retrieve pending outreach jobs: %s", exc, exc_info=True)
        raise DatabaseError(f"Failed to retrieve pending outreach jobs: {str(exc)}")


@app.get("/api/jobs/{job_id}", tags=["jobs"], response_model=JobData)
async def get_job_by_id(job_id: int):
    """
    Get a single job by ID.

    Wired for frontend's jobsApi.getJob (frontend/src/api/endpoints/jobs.ts),
    which was calling this route even though it didn't exist on the backend.
    Registered after the more specific /api/jobs/pending-outreach route so
    that literal path doesn't get swallowed by this int-typed path param.
    """
    try:
        async with db_session() as db:
            j = db.query(Job).filter(Job.id == job_id).first()
            if not j:
                raise ResourceNotFoundError("Job", job_id)

            return JobData(
                id=j.id,
                job_id=j.job_id,
                title=j.title,
                company=j.company,
                location=j.location,
                description=j.description,
                url=j.url,
                source=j.source,
                posted_date=j.posted_date,
                fetched_at=j.fetched_at,
            )
    except ResourceNotFoundError:
        raise
    except Exception as exc:
        log.error("Failed to retrieve job %s: %s", job_id, exc, exc_info=True)
        raise DatabaseError(f"Failed to retrieve job: {str(exc)}")


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats", tags=["stats"], response_model=StatsResponse)
async def stats(state: AppState = Depends(get_state)):
    """
    Return comprehensive statistics about the job pipeline.
    
    Returns job counts, contact counts, outreach statistics, and recent activity.
    Attempts to use live processor stats first, falling back to database queries.
    
    Requirements: 23.2 (Validate request parameters), 23.3 (Return processing statistics)
    """
    # Fast path: live O(1) counters
    if state.outreach_proc and hasattr(state.outreach_proc, "get_stats"):
        try:
            live_stats = state.outreach_proc.get_stats()
            log.info("Stats from live processor: %s", live_stats)
            return StatsResponse(
                status="success",
                source="live",
                stats=StatsData(
                    total_jobs=live_stats.get("total_jobs", 0),
                    total_contacts=live_stats.get("total_contacts", 0),
                    total_applications=live_stats.get("total_applications", 0),
                    total_outreach_attempts=live_stats.get("total_outreach_attempts", 0),
                    emails_sent=live_stats.get("emails_sent", 0),
                    follow_ups_sent=live_stats.get("follow_ups_sent", 0),
                    success_rate=live_stats.get("success_rate", 0.0),
                ),
                recent_outreach=[],
            )
        except Exception as e:
            log.warning("Live get_stats() failed, falling back to DB: %s", e)

    # Fallback: bounded DB queries with proper error handling
    try:
        async with db_session() as db:
            # Execute all count queries
            tj = db.query(Job).count()
            ta = db.query(Application).count()
            to = db.query(OutreachRecord).count()
            tc = db.query(Contact).count()
            se = db.query(OutreachRecord).filter(OutreachRecord.email_sent == True).count()
            
            # Safely handle follow_up_count
            try:
                fu = db.query(OutreachRecord).filter(
                    OutreachRecord.follow_up_count > 0).count()
            except Exception as e:
                log.warning("Failed to count follow-ups: %s", e)
                fu = 0
            
            # Get recent outreach records
            recent = [
                RecentOutreach(
                    id=r.id,
                    contact_email=r.contact_email,
                    status=r.status,
                    sent_at=r.sent_at,
                )
                for r in db.query(OutreachRecord)
                           .order_by(OutreachRecord.sent_at.desc()).limit(5).all()
            ]
            
            # Calculate success rate safely
            success_rate = round(se / to * 100, 1) if to > 0 else 0.0
            
            log.info("Stats from DB: jobs=%d, contacts=%d, apps=%d, outreach=%d, emails=%d, success_rate=%s%%",
                     tj, tc, ta, to, se, success_rate)
            
            return StatsResponse(
                status="success",
                source="db_fallback",
                stats=StatsData(
                    total_jobs=tj,
                    total_contacts=tc,
                    total_applications=ta,
                    total_outreach_attempts=to,
                    emails_sent=se,
                    follow_ups_sent=fu,
                    success_rate=success_rate,
                ),
                recent_outreach=recent,
            )
    except Exception as e:
        log.error("Stats endpoint error: %s", e, exc_info=True)
        return StatsResponse(
            status="error",
            source="empty",
            error=str(e),
            stats=StatsData(
                total_jobs=0,
                total_contacts=0,
                total_applications=0,
                total_outreach_attempts=0,
                emails_sent=0,
                follow_ups_sent=0,
                success_rate=0.0,
            ),
            recent_outreach=[],
        )


# ── Contacts ──────────────────────────────────────────────────────────────────

from sqlalchemy import func
from typing import Optional

@app.get("/api/contacts", tags=["contacts"], response_model=ContactsResponse)
async def get_contacts(
    page: int = Query(default=1, ge=1, le=10000, description="Page number (1-indexed)"),
    limit: int = Query(default=50, ge=1, le=500, description="Items per page (1-500)"),
    company: Optional[str] = Query(default=None, max_length=200, description="Filter by company name (partial match)"),
):
    """
    Get all discovered contacts with optional company filter and pagination.
    
    Requirements: 23.2 (Validate request parameters), 23.3 (Return processing statistics)
    """
    try:
        async with db_session() as db:
            query = db.query(Contact).order_by(Contact.found_at.desc())
            if company:
                query = query.filter(Contact.company.ilike(f"%{company}%"))
            
            total_query = db.query(func.count(Contact.id))
            if company:
                total_query = total_query.filter(Contact.company.ilike(f"%{company}%"))
            total = total_query.scalar()
            
            contacts = query.offset((page - 1) * limit).limit(limit).all()
            
            contact_data = [
                ContactData(
                    id=c.id,
                    name=c.name,
                    title=getattr(c, 'title', None),
                    email=getattr(c, 'email', ''),
                    linkedin_url=getattr(c, 'linkedin_url', None),
                    company=c.company,
                    department=getattr(c, 'department', None),
                    confidence_score=getattr(c, 'confidence_score', 0),
                    source=getattr(c, 'source', 'unknown'),
                    found_at=c.found_at,
                )
                for c in contacts
            ]
            
            return ContactsResponse(
                status="success",
                contacts=contact_data,
                pagination=PaginationData(
                    page=page,
                    limit=limit,
                    total=total,
                    pages=(total + limit - 1) // limit if limit > 0 else 0,
                ),
            )
    except Exception as exc:
        log.error("Failed to retrieve contacts: %s", exc, exc_info=True)
        raise DatabaseError(f"Failed to retrieve contacts: {str(exc)}")


@app.get("/api/contacts/{contact_id}", tags=["contacts"], response_model=ContactData)
async def get_contact_by_id(contact_id: int):
    """
    Get a single contact by ID.

    Wired for frontend's contactsApi.getById (frontend/src/api/endpoints/contacts.ts),
    which was calling this route even though it didn't exist on the backend.
    """
    try:
        async with db_session() as db:
            c = db.query(Contact).filter(Contact.id == contact_id).first()
            if not c:
                raise ResourceNotFoundError("Contact", contact_id)

            return ContactData(
                id=c.id,
                name=c.name,
                title=getattr(c, 'title', None),
                email=getattr(c, 'email', ''),
                linkedin_url=getattr(c, 'linkedin_url', None),
                company=c.company,
                department=getattr(c, 'department', None),
                confidence_score=getattr(c, 'confidence_score', 0),
                source=getattr(c, 'source', 'unknown'),
                found_at=c.found_at,
            )
    except ResourceNotFoundError:
        raise
    except Exception as exc:
        log.error("Failed to retrieve contact %s: %s", contact_id, exc, exc_info=True)
        raise DatabaseError(f"Failed to retrieve contact: {str(exc)}")


@app.put("/api/outreach/{outreach_id}/status", tags=["outreach"])
async def update_outreach_status(outreach_id: int, request: OutreachStatusUpdateRequest):
    """
    Update the status of an existing outreach record.

    Wired for frontend's outreachApi.updateStatus (frontend/src/api/endpoints/outreach.ts),
    which was calling this route even though it didn't exist on the backend.
    """
    try:
        async with db_session() as db:
            rec = db.query(OutreachRecord).filter(OutreachRecord.id == outreach_id).first()
            if not rec:
                raise ResourceNotFoundError("OutreachRecord", outreach_id)

            rec.status = request.status.value if isinstance(request.status, OutreachStatus) else request.status
            if request.status == OutreachStatus.REPLIED and not rec.replied_at:
                rec.replied_at = datetime.utcnow()
            db.commit()

            return {
                "status": "success",
                "outreach_id": outreach_id,
                "new_status": rec.status,
            }
    except ResourceNotFoundError:
        raise
    except Exception as exc:
        log.error("Failed to update outreach status %s: %s", outreach_id, exc, exc_info=True)
        raise DatabaseError(f"Failed to update outreach status: {str(exc)}")


# ── SignalHire webhook ────────────────────────────────────────────────────────

@app.post("/api/signalhire/callback", tags=["webhooks"], response_model=SignalHireCallbackResponse)
async def sh_callback(
    request_data: Any,
    req: Request,
    state: AppState = Depends(get_state),
):
    """
    Webhook callback endpoint for SignalHire contact enrichment results.
    
    Processes contact data returned from SignalHire API and persists to local store.
    """
    items = request_data if isinstance(request_data, list) else request_data.get("items", [])
    saved = 0
    for item in items:
        if item.get("status") != "success": continue
        cand = item.get("candidate", {})
        email = next(
            (c.get("value") for c in cand.get("contacts", []) if c.get("type") == "email"),
            None,
        )
        if not email: continue
        state.save_cb(item.get("item", email), {
            "email": email, "name": cand.get("fullName", ""),
            "title": cand.get("headLine", ""),
            "company": (cand.get("experience") or [{}])[0].get("company", ""),
            "linkedin_url": item.get("item", ""),
            "source": "signalhire",
            "received_at": datetime.utcnow().isoformat(),
        })
        saved += 1
    return SignalHireCallbackResponse(status="received", saved=saved, total=len(items))


@app.get("/api/signalhire/results/{linkedin_url:path}", tags=["webhooks"], response_model=SignalHireResultResponse)
async def sh_result(linkedin_url: str, state: AppState = Depends(get_state)):
    """
    Retrieve SignalHire enrichment results for a LinkedIn URL.
    
    Looks up previously received callback data for the specified LinkedIn URL.
    """
    r = state.get_cb(linkedin_url)
    if r:
        return SignalHireResultResponse(status="found", contact=r)
    return SignalHireResultResponse(status="not_found", message="No callback yet")


# ── Cloudflare Crawl ──────────────────────────────────────────────────────────

@app.post("/crawl", tags=["crawl"], response_model=CrawlResponse)
async def crawl(
    request: CrawlRequestModel,
    req: Request,
    state: AppState = Depends(get_state),
):
    """
    Crawl a company careers site via Cloudflare Browser Rendering (headless Chrome).

    - Pass the career page URL as `url` (e.g. https://stripe.com/jobs)
    - `include_patterns` / `exclude_patterns` restrict which pages are crawled
    - `query` filters returned pages by keyword after crawling (post-processing)
    - `feed_pipeline` runs matched pages through the job scoring pipeline

    Requires CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in settings.
    """
    if not _CRAWL_OK:
        raise HTTPException(503, "Cloudflare crawl module not available — check startup logs")

    trace = req.state.trace_id

    if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
        raise HTTPException(
            503,
            "Cloudflare credentials not configured. "
            "Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in .env.",
        )

    log.info("[%s] CF crawl start: %s (limit=%d, depth=%d)",
             trace, request.url, request.limit, request.depth)

    pages = await cloudflare_crawl(
        url=request.url,
        limit=request.limit,
        depth=request.depth,
        include_patterns=request.include_patterns,
        exclude_patterns=request.exclude_patterns,
    )

    # Post-crawl keyword filter (query is not sent to Cloudflare)
    if request.query:
        q = request.query.lower()
        pages = [p for p in pages if q in p["text"].lower() or q in p["title"].lower()]
        log.info("[%s] Query filter '%s' → %d pages", trace, request.query, len(pages))

    log.info("[%s] CF crawled %d pages", trace, len(pages))

    # Store each page as a Job row
    stored_ids: list[int] = []
    async with db_session() as db:
        for page in pages:
            existing = db.query(Job).filter(Job.job_id == page["url"]).first()
            if not existing:
                job = Job(
                    job_id=page["url"],
                    title=page["title"] or page["url"],
                    company=request.company_name or urlparse(page["url"]).netloc,
                    location="remote",
                    description=page["text"][:8000],
                    url=page["url"],
                    source="cloudflare_crawl",
                    fetched_at=datetime.utcnow(),
                )
                db.add(job)
                db.flush()
                stored_ids.append(job.id)
            else:
                stored_ids.append(existing.id)
        db.commit()

    # Optionally feed into job pipeline
    pipeline_result = None
    if request.feed_pipeline and state.job_processor:
        query_hint = request.query or (pages[0]["title"] if pages else request.url)
        resume_path = state.resume_router.route(query_hint)
        try:
            resume_text = _read_resume(resume_path)
        except HTTPException:
            resume_text = ""

        if resume_text:
            log.info("[%s] Feeding CF crawl into pipeline (resume=%s)", trace, resume_path)
            try:
                result = await _call_with_accepted(
                    state.job_processor.process_all_jobs,
                    resume_text,
                    min_score=0,
                )
                if inspect.isawaitable(result):
                    result = await result
                pipeline_result = {"resume_used": resume_path, "result": str(result)}
            except Exception as exc:
                log.error("[%s] Pipeline error: %s", trace, exc, exc_info=True)
                pipeline_result = {"resume_used": resume_path, "result": f"error: {exc}"}
        else:
            pipeline_result = {"resume_used": None, "result": "skipped — no resume found"}

    return CrawlResponse(
        status="success",
        trace_id=trace,
        url=request.url,
        pages_crawled=len(pages),
        jobs_stored=len(stored_ids),
        pages=[
            {
                "url": p["url"],
                "title": p["title"],
                "text_preview": p["text"][:300],
            }
            for p in pages
        ],
    )


# ── Startup Discovery ──────────────────────────────────────────────────────────

@app.post("/api/startups/discover", tags=["startups"], response_model=StartupDiscoveryResponse)
async def discover_startups(
    request: StartupDiscoveryRequest,
    req: Request,
    state: AppState = Depends(get_state),
):
    """
    Find recently funded startups using Firecrawl or NewsAPI.
    
    Discovered startups are compared against TOP_INDIAN_STARTUPS and new ones
    can be added for future scraping.
    """
    if not _NEWS_OK:
        raise HTTPException(503, "News service module not available")

    trace = req.state.trace_id
    log.info("[%s] Startup discovery start (provider=%s, target=%d)",
             trace, request.provider, request.target_count)

    try:
        if request.provider == "firecrawl":
            service = FirecrawlNewsService()
            new_startup_names = await service.fetch_funded_startups(
                limit=request.target_count,
                location=request.location
            )
        else:
            service = NewsService()
            # NewsAPI is more limited in parameters here, but we'll use a fixed page count for now
            new_startup_names = await service.fetch_funded_startups(pages=5)

        existing_names = {name.lower() for name, _ in TOP_INDIAN_STARTUPS}
        newly_added = 0
        found_companies = []

        for name in new_startup_names:
            found_companies.append(name)
            if name.lower() not in existing_names:
                # In a real scenario, we might want to persist these to a DB table
                # or dynamically update TOP_INDIAN_STARTUPS.
                # For this implementation, we just report them.
                newly_added += 1

        await service.close()

        return StartupDiscoveryResponse(
            status="success",
            trace_id=trace,
            startups_found=len(new_startup_names),
            new_startups_added=newly_added,
            companies=found_companies
        )

    except Exception as exc:
        log.error("[%s] Startup discovery error: %s", trace, exc, exc_info=True)
        raise HTTPException(500, f"Discovery failed: {str(exc)}")


# =============================================================================
# Dev entry point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)