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
from fastapi import Depends, FastAPI, HTTPException, Request, status, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from src.job_processor import JobProcessor
from src.database import init_db, SessionLocal
from src.models import Application, Job, OutreachRecord, Contact
from src.lifecycle import next_action, require_transition, normalize_status, sort_actions, KNOWN_STATUSES
from src.job_data_providers import JobDataAPIClient, AIDevBoardClient, FantasticJobsClient, ArbeitnowClient, CareerjetClient, USAJobsClient, search_all
from src.resume_parser import SharpAPIResumeParser
from src.tier1_companies import TIER1_REGISTRY, get_tier1_company
from src.scrapers.tier1_career_scraper import Tier1CareerScraper
from src.referral_engine import generate_referral_xray_queries, search_company_referral_contacts, compose_referral_request
from src.indian_app_startups import INDIAN_APP_STARTUPS, get_indian_app_startup, filter_indian_startups
from src.scrapers.indian_app_startups_scraper import IndianAppStartupsScraper
from src.fintech_festival_companies import FINTECH_FESTIVAL_REGISTRY, get_fintech_festival_company, filter_fintech_festival_companies
from src.scrapers.fintech_festival_scraper import FinTechFestivalScraper
from src.autonomous_job_crawler import autonomous_crawler, extract_tech_tags_and_seniority
from src.config import settings





try:
    from src.api.routers.agents_router import router as agents_router
    _AGENTS_ROUTER_OK = True
except Exception as _agents_router_err:  # noqa: BLE001
    _AGENTS_ROUTER_OK = False
    logging.warning("src.api.routers.agents_router not importable: %s", _agents_router_err)

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
    OpportunitySignal,
    OpportunityPerson,
    OpportunityResume,
    OpportunityOutreach,
    OpportunityNextAction,
    OpportunityBriefResponse,
    ActionQueueResponse,
    ActionQueueItem,
    LifecycleActionData,
    LifecycleTransitionRequest,
    SubmissionProofRequest,
    ProviderSyncRequest,
    ProviderSyncResponse,
    ProviderSyncSource,
    MarketIntelligenceResponse,
    ApplicationUpdateRequest,
    JobCaptureRequest,
    JobCaptureResponse,
    ReferralTargetsResponse,
    ReferralSearchRequest,
    ReferralSearchResponse,
    ReferralProfileSyncRequest,
    ReferralProfileSyncResponse,
    ReferralNoteGenerateRequest,
    ReferralNoteGenerateResponse,
    ReferralActionLogRequest,
    ReferralActionLogResponse,
    XAuthUrlResponse,
    XAuthCallbackRequest,
    XAuthCallbackResponse,
    XAuthStatusResponse,
    XTargetsResponse,
    XSearchRequest,
    XSearchResponse,
    XTweetSearchRequest,
    XTweetSearchResponse,
    XMessageGenerateRequest,
    XMessageGenerateResponse,
    XEngageRequest,
    XEngageResponse,
    XProfileSyncRequest,
    XProfileSyncResponse,
    EmailDiscoveryRequest,
    EmailDiscoveryResponse,
    EmailVerifyRequest,
    EmailVerifyResponse,
    EmailDorksRequest,
    EmailDorksResponse,
    EmailPermutationsRequest,
    EmailPermutationsResponse,
    AttentionMatchRequest,
    AttentionMatchResponse,
    AttentionTailorRequest,
    AttentionTailorResponse,
    AttentionOutreachRequest,
    AttentionOutreachResponse,
    GhostAnalysisRequest,
    GhostAnalysisResponse,
    DeliverabilityDraftRequest,
    DeliverabilityDraftResponse,
    VoiceFeedbackRequest,
    VoiceFeedbackResponse,
    NotificationConfigSchema,
    NotificationAlertSchema,
    NotificationTestRequest,
    NotificationDispatchResponseSchema,
    OfferPackageSchema,
    CompSimulationResponse,
    CompComparisonRequest,
    ResumeGenerateRequestSchema,
    CoverLetterGenerateRequestSchema,
    ResumeDocumentResponseSchema,
    CommunityHarvestRequest,
    CommunityIntelResponse,
    CopilotChatRequest,
    CopilotChatResponse,
    CopilotDorksRequest,
    CopilotDorksResponse,
    HiregramStartSessionRequest,
    HiregramStartSessionResponse,
    HiregramSubmitTurnRequest,
    HiregramSubmitTurnResponse,
    HiregramFinalizeResponse,
    AgentFleetConfigSchema,
    FleetCycleResponseSchema,
    InstagramSearchRequestSchema,
    InstagramSearchResponseSchema,
    InstagramMessageRequestSchema,
    InstagramMessageResponseSchema,
    SkillBridgeProjectRequestSchema,
    SkillBridgeProjectResponseSchema,
    MarketRadarResponseSchema,
)
from src.referral import referral_service
from src.x_referral import x_referral_service, x_oauth
from src.email_intelligence import email_intelligence_service
from src.attention import attention_service
from src.ghost_hunter import ghost_hunter_service
from src.deliverability import deliverability_service
from src.voice_interviewer import voice_interview_service
from src.notifications import notification_service, NotificationConfig, AlertPayload
from src.comp_simulator import comp_simulator_service, OfferPackage
from src.resume_generator import (
    resume_generator_service,
    ResumeGenerateRequest,
    CoverLetterGenerateRequest,
)
from src.community_intel import community_intel_service
from src.copilot import copilot_service, ChatTurnRequest, DorkGenerateRequest
from src.hiregram import hiregram_service, InterviewerPersona
from src.agent_fleet import agent_fleet_service, AgentFleetConfig
from src.instagram_referral import (
    instagram_referral_service,
    InstagramSearchRequest,
    InstagramMessageRequest,
)
from src.skill_bridge import skill_bridge_service, ProjectGenerateRequest
from src.market_radar import market_radar_service
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
    global _state
    if _state is None:
        _state = AppState()
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
if _AGENTS_ROUTER_OK:
    app.include_router(agents_router)

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
            from sqlalchemy import text
            db.execute(text("SELECT 1")).fetchone()
            
            # Check table existence and row counts
            from src.models import Job, Application, Contact, OutreachRecord
            
            # Verify tables exist and get counts
            job_count = db.query(Job).count()
            app_count = db.query(Application).count()
            contact_count = db.query(Contact).count()
            outreach_count = db.query(OutreachRecord).count()
            
            # Check if processing_results table exists (for async pipeline)
            try:
                result = db.execute(text("SELECT COUNT(*) FROM processing_results")).fetchone()
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


def _to_job_data(j: Job, match_score: Optional[float] = None, application_status: Optional[str] = None) -> JobData:
    tags = []
    if j.tags:
        try:
            tags = json.loads(j.tags) if isinstance(j.tags, str) else j.tags
        except Exception:
            tags = []
    provider_sources = []
    if j.provider_sources:
        try:
            provider_sources = json.loads(j.provider_sources) if isinstance(j.provider_sources, str) else j.provider_sources
        except Exception:
            provider_sources = [j.source] if j.source else []
    elif j.source:
        provider_sources = [j.source]

    return JobData(
        id=j.id,
        job_id=j.job_id,
        title=j.title,
        company=j.company,
        location=j.location,
        description=j.description,
        url=j.url,
        source=j.source or "other",
        posted_date=j.posted_date,
        fetched_at=j.fetched_at,
        match_score=match_score,
        application_status=application_status,
        provider_id=j.provider_id,
        company_website=j.company_website,
        salary_min=j.salary_min,
        salary_max=j.salary_max,
        salary_currency=j.salary_currency,
        has_remote=j.has_remote,
        work_mode=j.work_mode,
        experience_level=j.experience_level,
        tags=tags,
        provider_sources=provider_sources,
    )


# ── External job intelligence providers ──────────────────────────────────────

@app.post("/api/providers/sync", tags=["providers"], response_model=ProviderSyncResponse)
async def sync_external_providers(request: ProviderSyncRequest):
    """Fetch structured jobs from both providers and upsert into the local catalog."""
    results = await search_all(query=request.query, location=request.location,
                               max_age=request.max_age_days, limit=request.limit)
    source_results: List[ProviderSyncSource] = []
    inserted = updated = 0
    async with db_session() as db:
        for provider, rows in results.items():
            ins = upd = 0
            try:
                for row in rows:
                    existing = None
                    if row.get("provider_id"):
                        existing = db.query(Job).filter(Job.job_id == row["job_id"]).first()
                    if existing is None and row.get("url"):
                        existing = db.query(Job).filter(Job.url == row["url"]).first()
                    if existing is None:
                        existing = db.query(Job).filter(Job.title == row["title"], Job.company == row.get("company"), Job.url == row.get("url")).first()
                    if existing:
                        current_sources = []
                        try:
                            current_sources = json.loads(existing.provider_sources) if existing.provider_sources else []
                        except Exception:
                            current_sources = [existing.source] if existing.source else []
                        current_sources = list(dict.fromkeys([x for x in (current_sources + [provider]) if x]))
                        existing.provider_sources = json.dumps(current_sources)
                        existing.title = row["title"]
                        existing.company = row.get("company") or existing.company
                        existing.location = row.get("location") or existing.location
                        existing.description = row.get("description") or existing.description
                        existing.url = row.get("url") or existing.url
                        existing.source = provider
                        existing.posted_date = row.get("posted_date") or existing.posted_date
                        existing.provider_id = row.get("provider_id") or existing.provider_id
                        existing.company_website = row.get("company_website") or existing.company_website
                        existing.salary_min = row.get("salary_min")
                        existing.salary_max = row.get("salary_max")
                        existing.salary_currency = row.get("salary_currency")
                        existing.has_remote = row.get("has_remote")
                        existing.work_mode = row.get("work_mode")
                        existing.experience_level = row.get("experience_level")
                        existing.tags = json.dumps(row.get("tags", []))
                        existing.expired_at = row.get("expired_at")
                        existing.provider_payload = json.dumps(row.get("provider_payload", {}), default=str)
                        upd += 1
                    else:
                        db.add(Job(job_id=row["job_id"], title=row["title"], company=row.get("company"),
                                   location=row.get("location"), description=row.get("description"), url=row.get("url"),
                                   source=provider, posted_date=row.get("posted_date"), provider_id=row.get("provider_id"),
                                   company_website=row.get("company_website"), salary_min=row.get("salary_min"), salary_max=row.get("salary_max"),
                                   salary_currency=row.get("salary_currency"), has_remote=row.get("has_remote"), work_mode=row.get("work_mode"),
                                   experience_level=row.get("experience_level"), tags=json.dumps(row.get("tags", [])), expired_at=row.get("expired_at"),
                                   provider_payload=json.dumps(row.get("provider_payload", {}), default=str),
                                   provider_sources=json.dumps([provider])))
                        ins += 1
                db.commit()
            except Exception as exc:
                db.rollback()
                source_results.append(ProviderSyncSource(provider=provider, fetched=len(rows), inserted=0, updated=0, failed=True, error=str(exc)))
                continue
            inserted += ins; updated += upd
            source_results.append(ProviderSyncSource(provider=provider, fetched=len(rows), inserted=ins, updated=upd))
    return ProviderSyncResponse(status="success", total_fetched=sum(len(v) for v in results.values()),
                                total_inserted=inserted, total_updated=updated, sources=source_results)


@app.get("/api/market-intelligence", tags=["providers"], response_model=MarketIntelligenceResponse)
async def market_intelligence():
    """Expose current AI-dev market statistics through our backend without leaking provider credentials."""
    try:
        data = await AIDevBoardClient().stats()
        return MarketIntelligenceResponse(status="success", provider="aidevboard", data=data)
    except Exception as exc:
        return MarketIntelligenceResponse(status="degraded", provider="aidevboard", stale=True, error=str(exc))


# ── Jobs ──────────────────────────────────────────────────────────────────────

@app.get("/api/jobs", tags=["jobs"], response_model=JobsResponse)
async def get_jobs(
    page: int = Query(default=1, ge=1, le=10000, description="Page number (1-indexed)"),
    limit: int = Query(default=50, ge=1, le=500, description="Items per page (1-500)"),
    search: Optional[str] = Query(default=None, description="Fuzzy search title, company, description, or tags"),
    region: Optional[str] = Query(default=None, description="Region filter: 'india', 'us', 'remote', 'europe', 'apac' or city name"),
    experience_level: Optional[str] = Query(default=None, description="Level: 'Junior / Entry', 'Mid-Level', 'Senior', 'Lead / Staff / Principal'"),
    years_of_experience: Optional[int] = Query(default=None, ge=0, le=30, description="Numeric years of experience (e.g. 1, 4, 7, 10)"),
    date_posted: Optional[str] = Query(default=None, description="Posting time: '24h', '7d', '30d', 'anytime'"),
    tech_stack: Optional[str] = Query(default=None, description="Comma-separated tech keywords, e.g. 'Python,FastAPI,AWS'"),
    source: Optional[str] = Query(default=None, description="Job source filter, e.g. 'greenhouse_direct', 'greenhouse_startup'"),
    has_remote: Optional[bool] = Query(default=None, description="Filter remote positions only"),
    sort_by: Optional[str] = Query(default="fetched_at", description="Sort field: 'fetched_at', 'posted_date', 'title', 'company'"),
    sort_order: Optional[str] = Query(default="desc", description="Sort direction: 'asc', 'desc'"),
):
    """
    Get all jobs with multi-facet ORM filtering across region, YOE, posting date, tech stack, and keywords.
    """
    from sqlalchemy import or_, and_, func
    from datetime import datetime, timedelta, timezone

    try:
        async with db_session() as db:
            query = db.query(Job)

            # 1. Search Query across title, company, location, tags, description
            if search and search.strip():
                term = f"%{search.strip().lower()}%"
                query = query.filter(
                    or_(
                        func.lower(Job.title).like(term),
                        func.lower(Job.company).like(term),
                        func.lower(Job.location).like(term),
                        func.lower(Job.tags).like(term),
                        func.lower(Job.description).like(term),
                    )
                )

            # 2. Region / Location Filtering
            if region and region.strip() and region.lower() != "all":
                reg = region.strip().lower()
                if reg in ("remote", "global_remote", "work_from_home"):
                    query = query.filter(
                        or_(
                            Job.has_remote == True,
                            Job.work_mode == "remote",
                            Job.work_mode == "remote_any",
                            func.lower(Job.location).like("%remote%"),
                            func.lower(Job.location).like("%anywhere%"),
                        )
                    )
                elif reg in ("india", "in", "bengaluru", "bangalore", "mumbai", "delhi", "hyderabad", "pune", "chennai", "noida", "gurgaon"):
                    query = query.filter(
                        or_(
                            func.lower(Job.location).like("%india%"),
                            func.lower(Job.location).like("%bengaluru%"),
                            func.lower(Job.location).like("%bangalore%"),
                            func.lower(Job.location).like("%mumbai%"),
                            func.lower(Job.location).like("%delhi%"),
                            func.lower(Job.location).like("%hyderabad%"),
                            func.lower(Job.location).like("%pune%"),
                            func.lower(Job.location).like("%chennai%"),
                            func.lower(Job.location).like("%noida%"),
                            func.lower(Job.location).like("%gurgaon%"),
                        )
                    )
                elif reg in ("us", "usa", "united states", "san francisco", "new york", "seattle", "austin"):
                    query = query.filter(
                        or_(
                            func.lower(Job.location).like("%u.s%"),
                            func.lower(Job.location).like("%united states%"),
                            func.lower(Job.location).like("%ca%"),
                            func.lower(Job.location).like("%ny%"),
                            func.lower(Job.location).like("%wa%"),
                            func.lower(Job.location).like("%san francisco%"),
                            func.lower(Job.location).like("%new york%"),
                            func.lower(Job.location).like("%seattle%"),
                        )
                    )
                elif reg in ("europe", "eu", "germany", "uk", "london", "singapore"):
                    query = query.filter(
                        or_(
                            func.lower(Job.location).like("%europe%"),
                            func.lower(Job.location).like("%uk%"),
                            func.lower(Job.location).like("%london%"),
                            func.lower(Job.location).like("%germany%"),
                            func.lower(Job.location).like("%singapore%"),
                        )
                    )
                else:
                    query = query.filter(func.lower(Job.location).like(f"%{reg}%"))

            # 3. Experience Level & Years of Experience (YOE) Filtering
            if years_of_experience is not None:
                if years_of_experience <= 2:
                    query = query.filter(or_(Job.experience_level.like("%Junior%"), Job.experience_level.like("%Entry%"), func.lower(Job.title).like("%intern%"), func.lower(Job.title).like("%junior%")))
                elif years_of_experience <= 5:
                    query = query.filter(or_(Job.experience_level.like("%Mid%"), Job.experience_level.like("%SWE II%"), Job.experience_level.like("%L4%"), func.lower(Job.title).like("%sde 2%"), func.lower(Job.title).like("%sde ii%")))
                elif years_of_experience <= 8:
                    query = query.filter(or_(Job.experience_level.like("%Senior%"), Job.experience_level.like("%L5%"), func.lower(Job.title).like("%senior%"), func.lower(Job.title).like("%sr%")))
                else:
                    query = query.filter(or_(Job.experience_level.like("%Lead%"), Job.experience_level.like("%Staff%"), Job.experience_level.like("%Principal%"), Job.experience_level.like("%Director%"), func.lower(Job.title).like("%lead%"), func.lower(Job.title).like("%staff%"), func.lower(Job.title).like("%principal%")))
            elif experience_level and experience_level.strip() and experience_level.lower() != "all":
                exp_lower = experience_level.strip().lower()
                if "junior" in exp_lower or "entry" in exp_lower or "0-2" in exp_lower:
                    query = query.filter(or_(Job.experience_level.like("%Junior%"), Job.experience_level.like("%Entry%"), func.lower(Job.title).like("%intern%"), func.lower(Job.title).like("%junior%")))
                elif "mid" in exp_lower or "3-5" in exp_lower:
                    query = query.filter(or_(Job.experience_level.like("%Mid%"), Job.experience_level.like("%SWE II%"), Job.experience_level.like("%L4%")))
                elif "senior" in exp_lower or "5-8" in exp_lower:
                    query = query.filter(or_(Job.experience_level.like("%Senior%"), Job.experience_level.like("%L5%"), func.lower(Job.title).like("%senior%"), func.lower(Job.title).like("%sr%")))
                elif "lead" in exp_lower or "staff" in exp_lower or "principal" in exp_lower or "8+" in exp_lower:
                    query = query.filter(or_(Job.experience_level.like("%Lead%"), Job.experience_level.like("%Staff%"), Job.experience_level.like("%Principal%"), Job.experience_level.like("%Director%"), func.lower(Job.title).like("%lead%"), func.lower(Job.title).like("%staff%"), func.lower(Job.title).like("%principal%")))
                else:
                    query = query.filter(func.lower(Job.experience_level).like(f"%{exp_lower}%"))

            # 4. Date Posted Filtering
            if date_posted and date_posted.strip() and date_posted.lower() not in ("anytime", "all"):
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                dp_lower = date_posted.strip().lower()
                cutoff = None
                if dp_lower in ("24h", "1d", "today"):
                    cutoff = now - timedelta(days=1)
                elif dp_lower in ("7d", "1w", "week"):
                    cutoff = now - timedelta(days=7)
                elif dp_lower in ("14d", "2w"):
                    cutoff = now - timedelta(days=14)
                elif dp_lower in ("30d", "1m", "month"):
                    cutoff = now - timedelta(days=30)
                
                if cutoff:
                    query = query.filter(or_(Job.posted_date >= cutoff, Job.fetched_at >= cutoff))

            # 5. Tech Stack Filter
            if tech_stack and tech_stack.strip() and tech_stack.lower() != "all":
                stacks = [s.strip() for s in tech_stack.split(",") if s.strip()]
                for s in stacks:
                    s_term = f"%{s.lower()}%"
                    query = query.filter(or_(func.lower(Job.tags).like(s_term), func.lower(Job.title).like(s_term), func.lower(Job.description).like(s_term)))

            # 6. Source Filter
            if source and source.strip() and source.lower() != "all":
                src_clean = source.strip().lower()
                if src_clean == "tier1":
                    query = query.filter(Job.source.in_(["greenhouse_direct", "lever_direct", "smartrecruiters_direct"]))
                elif src_clean == "startups":
                    query = query.filter(Job.source.in_(["greenhouse_startup", "lever_startup"]))
                elif src_clean == "fintech":
                    query = query.filter(Job.source.in_(["greenhouse_fintech", "smartrecruiters_fintech"]))
                elif src_clean == "usajobs":
                    query = query.filter(Job.source == "usajobs")
                else:
                    query = query.filter(func.lower(Job.source).like(f"%{src_clean}%"))

            if has_remote is True:
                query = query.filter(or_(Job.has_remote == True, Job.work_mode == "remote", Job.work_mode == "remote_any"))

            # 7. Sorting
            sort_col = Job.fetched_at
            if sort_by == "posted_date":
                sort_col = Job.posted_date
            elif sort_by == "title":
                sort_col = Job.title
            elif sort_by == "company":
                sort_col = Job.company

            if sort_order and sort_order.lower() == "asc":
                query = query.order_by(sort_col.asc())
            else:
                query = query.order_by(sort_col.desc())

            total = query.count()
            jobs = query.offset((page - 1) * limit).limit(limit).all()
            job_data = [_to_job_data(j) for j in jobs]

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
        log.error("Failed to retrieve filtered jobs: %s", exc, exc_info=True)
        raise DatabaseError(f"Failed to retrieve filtered jobs: {str(exc)}")



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
    """Get a single job by ID."""
    try:
        async with db_session() as db:
            j = db.query(Job).filter(Job.id == job_id).first()
            if not j:
                raise ResourceNotFoundError("Job", job_id)

            app_rec = db.query(Application).filter(Application.job_id == job_id).order_by(Application.id.desc()).first()
            match_score = app_rec.match_score if app_rec else None
            app_status = app_rec.status if app_rec else None
            return _to_job_data(j, match_score=match_score, application_status=app_status)
    except ResourceNotFoundError:
        raise
    except Exception as exc:
        log.error("Failed to retrieve job %s: %s", job_id, exc, exc_info=True)
        raise DatabaseError(f"Failed to retrieve job: {str(exc)}")


# ── Opportunities & Applications ──────────────────────────────────────────────

@app.put("/api/jobs/{job_id}/application", tags=["applications"])
async def update_job_application_status(job_id: int, request: ApplicationUpdateRequest):
    """Update or create application record for a job with lifecycle validation."""
    try:
        async with db_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ResourceNotFoundError("Job", job_id)

            application = db.query(Application).filter(Application.job_id == job_id).order_by(Application.id.desc()).first()
            if application is None:
                if request.status not in ("saved", "ready", "rejected"):
                    raise HTTPException(status_code=409, detail=f"Cannot create an application directly in state: {request.status}")
                application = Application(job_id=job_id, status=request.status)
                db.add(application)
            else:
                try:
                    require_transition(application.status, request.status)
                except ValueError as exc:
                    raise HTTPException(status_code=409, detail=str(exc))
                application.status = request.status

            if request.status == "applied" and application.applied_at is None:
                application.applied_at = datetime.utcnow()

            db.commit()
            db.refresh(application)
            return {
                "status": "success",
                "application_id": application.id,
                "job_id": job_id,
                "application_status": application.status,
            }
    except (ResourceNotFoundError, HTTPException):
        raise
    except Exception as exc:
        log.error("Failed to update application for job %s: %s", job_id, exc, exc_info=True)
        raise DatabaseError(f"Failed to update application: {str(exc)}")


@app.post("/api/applications/{application_id}/transition", tags=["applications"])
async def transition_application(application_id: int, request: LifecycleTransitionRequest):
    """Perform a validated lifecycle state transition."""
    try:
        async with db_session() as db:
            application = db.query(Application).filter(Application.id == application_id).first()
            if not application:
                raise ResourceNotFoundError("Application", application_id)
            try:
                require_transition(application.status, request.status)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc))
            application.status = request.status
            if request.status == "applied" and application.applied_at is None:
                application.applied_at = datetime.utcnow()
            db.commit()
            db.refresh(application)
            return {"status": "success", "application_id": application.id, "job_id": application.job_id, "application_status": application.status}
    except (ResourceNotFoundError, HTTPException):
        raise
    except Exception as exc:
        log.error("Failed to transition application %s: %s", application_id, exc, exc_info=True)
        raise DatabaseError(f"Failed to transition application: {str(exc)}")


@app.post("/api/applications/{application_id}/proof", tags=["applications"])
async def record_application_proof(application_id: int, request: SubmissionProofRequest):
    """Record proof of external submission and transition application to applied."""
    try:
        async with db_session() as db:
            application = db.query(Application).filter(Application.id == application_id).first()
            if not application:
                raise ResourceNotFoundError("Application", application_id)
            application.status = "applied"
            application.applied_at = datetime.utcnow()
            if request.proof_url:
                application.proof_url = request.proof_url
            if request.proof_notes:
                application.proof_notes = request.proof_notes
            db.commit()
            db.refresh(application)
            return {"status": "success", "application_id": application.id, "job_id": application.job_id, "application_status": application.status}
    except (ResourceNotFoundError, HTTPException):
        raise
    except Exception as exc:
        log.error("Failed to record proof for application %s: %s", application_id, exc, exc_info=True)
        raise DatabaseError(f"Failed to record proof: {str(exc)}")


@app.get("/api/action-queue", tags=["opportunities"], response_model=ActionQueueResponse)
async def get_action_queue(limit: int = Query(default=12, ge=1, le=1000)):
    """Return the highest-value next actions across the entire career pipeline."""
    try:
        async with db_session() as db:
            applications = db.query(Application).join(Job).order_by(Application.updated_at.desc()).all()
            current_by_job = {}
            for application in applications:
                if application.job_id not in current_by_job:
                    current_by_job[application.job_id] = application
            actions = []
            for application in current_by_job.values():
                if normalize_status(application.status) in {"accepted", "rejected"}:
                    continue
                job = application.job
                records = (db.query(OutreachRecord)
                           .filter(OutreachRecord.job_id == job.id)
                           .order_by(OutreachRecord.sent_at.desc())
                           .all())
                contacts = (db.query(Contact)
                            .filter(Contact.company.ilike(f"%{job.company or ''}%"))
                            .order_by(Contact.confidence_score.desc())
                            .limit(10).all()) if job.company else []
                replied = any(r.status == "replied" or r.replied_at for r in records)
                pending = any(r.status in ("no_response", "queued") for r in records)
                has_proof = bool(getattr(application, "proof_url", None) or getattr(application, "proof_notes", None))
                action = next_action(
                    application.status,
                    has_reply=replied,
                    has_contacts=bool(contacts),
                    has_outreach=bool(records),
                    followup_due=pending,
                    has_application_proof=has_proof,
                )
                actions.append({
                    "job_id": job.id,
                    "application_id": application.id,
                    "title": job.title,
                    "company": job.company,
                    "fit_score": application.match_score,
                    "stage": normalize_status(application.status),
                    "status": normalize_status(application.status),
                    "action": {"key": action.key, "label": action.label, "reason": action.reason, "priority": action.priority, "route": action.route, "external": action.external, "requires_confirmation": action.requires_confirmation},
                    "url": job.url,
                    "updated_at": application.updated_at,
                })
            ranked = sort_actions(actions)[:limit]
            return ActionQueueResponse(status="success", actions=ranked, total=len(actions))
    except Exception as exc:
        log.error("Failed to build action queue: %s", exc, exc_info=True)
        raise DatabaseError(f"Failed to build action queue: {str(exc)}")


@app.post("/api/opportunities/{job_id}/do-next", tags=["opportunities"])
async def do_next_opportunity_action(job_id: int):
    """Execute the safest internal step and return the next human action."""
    try:
        async with db_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ResourceNotFoundError("Job", job_id)
            records = (db.query(OutreachRecord)
                       .filter(OutreachRecord.job_id == job_id)
                       .order_by(OutreachRecord.sent_at.desc())
                       .all())
            contacts = (db.query(Contact)
                        .filter(Contact.company.ilike(f"%{job.company or ''}%"))
                        .order_by(Contact.confidence_score.desc())
                        .limit(10).all()) if job.company else []
            application = (db.query(Application)
                           .filter(Application.job_id == job_id)
                           .order_by(Application.id.desc())
                           .first())

            if application is None:
                application = Application(job_id=job_id, status="saved")
                db.add(application); db.commit(); db.refresh(application)
                return {"status": "success", "action": "save", "application_id": application.id, "application_status": application.status, "open_url": f"/opportunities/{job_id}", "message": "Saved to your tracker. The next action is now available in Do This Next.", "requires_confirmation": False}
            replied = any(r.status == "replied" or r.replied_at for r in records)
            pending = any(r.status in ("no_response", "queued") for r in records)
            has_proof = bool(getattr(application, "proof_url", None) or getattr(application, "proof_notes", None))
            action = next_action(
                application.status,
                has_reply=replied,
                has_contacts=bool(contacts),
                has_outreach=bool(records),
                followup_due=pending,
                has_application_proof=has_proof,
            )

            if action.key == "prepare_application":
                require_transition(application.status, "ready")
                application.status = "ready"
                db.commit(); db.refresh(application)
                return {"status": "success", "action": "apply", "application_id": application.id, "application_status": application.status, "open_url": job.url, "message": "Application packet is ready. Review it, then submit on the employer site.", "requires_confirmation": False}
            if action.key == "apply":
                return {"status": "success", "action": "apply", "application_id": application.id, "application_status": application.status, "open_url": job.url, "message": "Application packet is ready. Submit on the employer site, then log proof."}
            if action.key in {"outreach", "followup", "respond"}:
                return {"status": "success", "action": action.key, "application_id": application.id, "application_status": application.status, "open_url": action.route + f"?jobId={job_id}" if action.route else f"/outreach?jobId={job_id}", "message": action.reason}
            if action.key == "interview_prep":
                return {"status": "success", "action": "interview_prep", "application_id": application.id, "application_status": application.status, "open_url": f"/opportunities/{job_id}", "message": action.reason}
            if action.key == "negotiate":
                require_transition(application.status, "negotiation")
                application.status = "negotiation"
                db.commit(); db.refresh(application)
                return {"status": "success", "action": "negotiate", "application_id": application.id, "application_status": application.status, "open_url": f"/opportunities/{job_id}", "message": "Negotiation stage started. Review the offer and record your target terms.", "requires_confirmation": False}
            if action.key == "accept_offer":
                return {"status": "success", "action": "accept_offer", "application_id": application.id, "application_status": application.status, "open_url": f"/opportunities/{job_id}", "message": "Confirm that you want to mark this offer as accepted.", "requires_confirmation": True}
            return {"status": "success", "action": "complete", "application_id": application.id, "application_status": application.status, "open_url": None, "message": "No further action is required for this opportunity."}
    except ResourceNotFoundError:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        log.error("Failed to perform next action for job %s: %s", job_id, exc, exc_info=True)
        raise DatabaseError(f"Failed to perform next action: {str(exc)}")


@app.get("/api/opportunities/{job_id}/brief", tags=["opportunities"], response_model=OpportunityBriefResponse)
async def get_opportunity_brief(job_id: int, state: AppState = Depends(get_state)):
    """Build a single, decision-ready view from the existing job-search data."""
    try:
        async with db_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ResourceNotFoundError("Job", job_id)

            application = (db.query(Application)
                           .filter(Application.job_id == job_id)
                           .order_by(Application.id.desc())
                           .first())

            contacts = (db.query(Contact)
                        .filter(Contact.company.ilike(f"%{job.company or ''}%"))
                        .filter(~Contact.do_not_contact.is_(True))
                        .order_by(Contact.confidence_score.desc(), Contact.found_at.desc())
                        .limit(6).all()) if job.company else []

            outreach_records = (db.query(OutreachRecord)
                                .filter(OutreachRecord.job_id == job_id)
                                .order_by(OutreachRecord.sent_at.desc())
                                .all())

            company_jobs = (db.query(Job)
                            .filter(Job.company.ilike(f"%{job.company or ''}%"))
                            .count()) if job.company else 1
            company_sources = (db.query(Job.source)
                               .filter(Job.company.ilike(f"%{job.company or ''}%"))
                               .filter(Job.source.isnot(None)).distinct().all()) if job.company else []

            resume_text = ""
            master_label = None
            try:
                resume_path = state.resume_router.route(job.title)
                resume_text = _read_resume(resume_path)
                master_label = Path(resume_path).name
            except Exception:
                pass

            fit_score = application.match_score if application and application.match_score is not None else None
            fit_reasons: List[str] = []
            missing_keywords: List[str] = []
            if fit_score is None:
                import re
                jd_words = {w for w in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", f"{job.title} {job.description or ''}".lower())}
                stop = {"the","and","for","with","from","this","that","you","your","are","our","will","have","has","into","about","job","role","team","years"}
                jd_words = {w for w in jd_words if w not in stop and len(w) >= 4}
                resume_words = set(re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", resume_text.lower()))
                overlap = len(jd_words & resume_words)
                fit_score = min(95.0, max(35.0, 35.0 + overlap * 2.5)) if jd_words else 50.0
                if overlap:
                    fit_reasons.append(f"Your resume overlaps with {overlap} role-relevant terms in the indexed job description.")
                missing_keywords = sorted(jd_words - resume_words, key=lambda x: (len(x), x), reverse=True)[:8]
            else:
                fit_score = float(fit_score)
                matched = []
                if application.skills_matched:
                    try:
                        matched = json.loads(application.skills_matched) if isinstance(application.skills_matched, str) else application.skills_matched
                    except Exception:
                        matched = []
                fit_reasons.append("Stored AI match score from the job-processing pipeline.")
                if matched:
                    fit_reasons.append(f"{len(matched)} skills are already marked as matched.")
                if application.skills_missing:
                    try:
                        missing_keywords = json.loads(application.skills_missing) if isinstance(application.skills_missing, str) else application.skills_missing
                    except Exception:
                        missing_keywords = [str(application.skills_missing)]
            fit_label = "Excellent fit" if fit_score >= 85 else "Strong fit" if fit_score >= 70 else "Possible fit" if fit_score >= 55 else "Weak fit"

            now = datetime.utcnow()
            age_days = None
            if job.posted_date:
                age_days = max(0, (now - job.posted_date).days)
            signal_data = []
            signal_data.append(OpportunitySignal(
                label="Hiring activity", value=f"{company_jobs} indexed role{'s' if company_jobs != 1 else ''}",
                strength="strong" if company_jobs >= 3 else "medium" if company_jobs == 2 else "info",
                detail="Based on roles already indexed for this company in your workspace."))
            if age_days is not None:
                signal_data.append(OpportunitySignal(
                    label="Role freshness", value=f"{age_days}d old", strength="strong" if age_days <= 3 else "medium" if age_days <= 10 else "weak",
                    detail="Newer postings generally deserve faster action."))
            signal_data.append(OpportunitySignal(
                label="Network access", value=f"{len(contacts)} contact{'s' if len(contacts) != 1 else ''} found", strength="strong" if contacts else "weak",
                detail="Contacts discovered in your existing contact intelligence store."))
            if company_sources:
                signal_data.append(OpportunitySignal(
                    label="Source breadth", value=f"{len(company_sources)} source{'s' if len(company_sources) != 1 else ''}", strength="medium" if len(company_sources) > 1 else "info",
                    detail="Multiple indexed sources can increase confidence that the role is worth reviewing."))

            corroborated = []
            try:
                corroborated = json.loads(job.provider_sources) if job.provider_sources else []
            except Exception:
                corroborated = [job.source] if job.source else []
            if len(corroborated) > 1:
                signal_data.append(OpportunitySignal(label="Provider corroboration", value=f"{len(corroborated)} independent feeds", strength="strong",
                    detail="This role was independently found by multiple structured job providers."))

            if getattr(job, "salary_min", None) or getattr(job, "salary_max", None):
                salary_text = f"${job.salary_min:,.0f}" if job.salary_min is not None else "Salary disclosed"
                if job.salary_max is not None:
                    salary_text += f"–${job.salary_max:,.0f}"
                signal_data.append(OpportunitySignal(label="Compensation", value=salary_text,
                    strength="strong", detail=f"Provider salary data ({job.salary_currency or 'USD/base'}) stored with this listing."))
            if getattr(job, "has_remote", None) is not None:
                signal_data.append(OpportunitySignal(label="Work model", value=("Remote-capable" if job.has_remote else "On-site / hybrid"),
                    strength="medium", detail="Normalized from external job intelligence."))
            if getattr(job, "source", None) in ("jobdataapi", "aidevboard"):
                signal_data.append(OpportunitySignal(label="Data provenance", value=job.source, strength="medium",
                    detail="Structured provider data is cached in your local catalog for repeatable ranking."))

            people = []
            for c in contacts:
                hint = "Likely hiring contact" if c.title and any(k in c.title.lower() for k in ("manager", "director", "head", "recruit", "talent", "people", "hr")) else "Potential internal contact"
                people.append(OpportunityPerson(id=c.id, name=c.name, title=c.title, email=c.email, linkedin_url=c.linkedin_url, confidence_score=c.confidence_score or 0, relationship_hint=hint))

            total = len(outreach_records)
            sent = sum(1 for r in outreach_records if r.status in ("sent", "followed_up", "replied"))
            replied = sum(1 for r in outreach_records if r.status == "replied" or r.replied_at)
            pending = sum(1 for r in outreach_records if r.status in ("no_response", "queued"))
            latest_status = outreach_records[0].status if outreach_records else None
            if replied:
                msg = "Someone replied. Stop automation and take the conversation personally."
            elif total and pending:
                msg = "A follow-up is the highest-value next move; avoid starting another cold thread."
            elif contacts:
                msg = "Lead with the strongest relevant contact and personalize around this role before applying."
            else:
                msg = "Find the hiring manager or an internal referral before spending time on a low-context application."

            resume = OpportunityResume(
                has_master_resume=bool(resume_text),
                master_resume_label=master_label,
                has_tailored_resume=bool(application and application.resume_version),
                tailored_resume_label=(application.resume_version[:120] if application and application.resume_version else None),
                cover_letter_preview=(application.cover_letter[:400] if application and application.cover_letter else None),
                missing_keywords=[str(x) for x in missing_keywords[:8]],
            )

            has_proof = bool(application and (getattr(application, "proof_url", None) or getattr(application, "proof_notes", None)))
            action = next_action(
                application.status if application else "saved",
                has_reply=bool(replied),
                has_contacts=bool(contacts),
                has_outreach=bool(outreach_records),
                followup_due=bool(pending),
                has_application_proof=has_proof,
            )

            job_data = _to_job_data(job, match_score=fit_score, application_status=(application.status if application else None))
            return OpportunityBriefResponse(
                status="success", job=job_data, fit_score=fit_score, fit_label=fit_label,
                fit_reasons=fit_reasons, company_signals=signal_data, people=people,
                resume=resume, outreach=OpportunityOutreach(total=total, sent=sent, replied=replied, pending=pending,
                                                            latest_status=latest_status, recommended_message=msg),
                next_action=OpportunityNextAction(key=action.key, label=action.label, reason=action.reason, priority=action.priority, route=action.route, external=action.external, requires_confirmation=action.requires_confirmation),
                application_status=(application.status if application else None),
            )
    except ResourceNotFoundError:
        raise
    except Exception as exc:
        log.error("Failed to build opportunity brief for job %s: %s", job_id, exc, exc_info=True)
        raise DatabaseError(f"Failed to build opportunity brief: {str(exc)}")


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats", tags=["stats"], response_model=StatsResponse)
async def stats(state: AppState = Depends(get_state)):
    """
    Return comprehensive statistics about the job pipeline.
    
    Returns job counts, contact counts, outreach statistics, and recent activity.
    Attempts to use live processor stats first, falling back to database queries.
    
    Requirements: 23.2 (Validate request parameters), 23.3 (Return processing statistics)
    """
    try:
        async with db_session() as db:
            # Execute all count queries directly from database
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


# ═══════════════════════════════════════════════════════════════════════════
# Job Capture & LinkedIn Referral Automator Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/jobs/capture", tags=["jobs"], response_model=JobCaptureResponse)
async def capture_job(
    request: JobCaptureRequest,
    req: Request,
    state: AppState = Depends(get_state),
):
    """
    Save a single job scraped from the browser extension (LinkedIn/Indeed posting),
    deduplicated by URL. Optionally scores it against the configured resume.
    """
    trace = req.state.trace_id
    import hashlib

    try:
        job_id = "ext-" + hashlib.sha256(request.url.encode("utf-8")).hexdigest()[:24]

        async with db_session() as db:
            existing = db.query(Job).filter(Job.url == request.url).first()
            already_existed = existing is not None

            if existing:
                j = existing
            else:
                j = Job(
                    job_id=job_id,
                    title=request.title,
                    company=request.company,
                    location=request.location,
                    description=request.description,
                    url=request.url,
                    source=request.source,
                    fetched_at=datetime.utcnow(),
                )
                db.add(j)
                db.commit()
                db.refresh(j)
                log.info("[%s] Captured job from extension: %s @ %s", trace, j.title, j.company)

            job_data = JobData(
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

        response = JobCaptureResponse(
            status="success",
            job=job_data,
            already_existed=already_existed,
        )

        if request.score:
            if not state.job_processor:
                response.score_error = "AI service unavailable — check server startup logs"
                return response
            try:
                resume_path = state.resume_router.route(request.title)
                resume_text = _read_resume(resume_path)
                skills = await state.job_processor.ai.extract_skills(
                    request.description or request.title
                )
                match = await state.job_processor.ai.match_resume_to_job(resume_text, skills)
                response.match_score = match.get("match_score")
                response.matched_skills = match.get("matched_skills")
                response.missing_skills = match.get("missing_skills")
            except Exception as exc:
                log.warning("[%s] Scoring failed for captured job: %s", trace, exc)
                response.score_error = str(exc)

        return response

    except Exception as exc:
        log.error("[%s] Job capture failed: %s", trace, exc, exc_info=True)
        raise APIError(f"Job capture failed: {str(exc)}")


@app.get("/api/referrals/targets", tags=["referrals"], response_model=ReferralTargetsResponse)
async def get_referral_targets(
    limit: int = 30,
    req: Request = None,
):
    """
    Retrieve active target companies and roles currently in the pipeline
    for automated LinkedIn referral discovery and targeting.
    """
    try:
        async with db_session() as db:
            targets = referral_service.get_active_targets(db, limit=limit)
            return ReferralTargetsResponse(
                status="success",
                total_targets=len(targets),
                targets=targets,
            )
    except Exception as exc:
        log.error("Failed to retrieve referral targets: %s", exc, exc_info=True)
        raise APIError(f"Failed to retrieve referral targets: {str(exc)}")


@app.post("/api/referrals/search", tags=["referrals"], response_model=ReferralSearchResponse)
async def search_company_referrals(
    request: ReferralSearchRequest,
    req: Request,
):
    """
    Search for LinkedIn employee and alumni profiles at a target company
    (uses live Proxycurl API or offline sample CSV fallback with disk caching).
    """
    trace = req.state.trace_id
    try:
        res = referral_service.search_company_referrals(request.company, limit=request.limit)
        return ReferralSearchResponse(
            status="success",
            company=res["company"],
            source=res["source"],
            count=res["count"],
            profiles=res["profiles"],
        )
    except Exception as exc:
        log.error("[%s] Referral search error: %s", trace, exc, exc_info=True)
        raise APIError(f"Referral search failed: {str(exc)}")


@app.post("/api/referrals/sync", tags=["referrals"], response_model=ReferralProfileSyncResponse)
async def sync_referral_profiles(
    request: ReferralProfileSyncRequest,
    req: Request,
):
    """
    Batch ingests discovered LinkedIn profiles into the Contacts CRM database.
    """
    trace = req.state.trace_id
    try:
        async with db_session() as db:
            result = referral_service.sync_profiles_to_contacts(db, request.profiles)
            log.info("[%s] Synced %d referral contacts (%d new)", trace, result["synced_count"], result["new_contacts_count"])
            return ReferralProfileSyncResponse(
                status="success",
                synced_count=result["synced_count"],
                new_contacts_count=result["new_contacts_count"],
            )
    except Exception as exc:
        log.error("[%s] Referral profile sync error: %s", trace, exc, exc_info=True)
        raise APIError(f"Referral profile sync failed: {str(exc)}")


@app.post("/api/referrals/generate-note", tags=["referrals"], response_model=ReferralNoteGenerateResponse)
async def generate_referral_note(
    request: ReferralNoteGenerateRequest,
    req: Request,
):
    """
    Generates a personalized LinkedIn connection note (<=200/300 chars)
    and full referral pitch letter for a specific candidate and role.
    """
    try:
        profile_data = {
            "full_name": request.full_name,
            "first_name": request.first_name,
            "company": request.company,
            "title": request.title,
            "headline": request.headline,
        }
        context_data = {
            "company": request.company,
            "job_title": request.job_title,
            "job_link": request.job_link,
            "short_bio": request.short_bio,
            "highlight": request.highlight,
            "reason": request.reason,
            "sender_name": request.sender_name,
            "max_length": request.max_length,
        }
        result = referral_service.generate_referral_note(
            profile_data, context_data, max_length=request.max_length
        )
        return ReferralNoteGenerateResponse(
            status="success",
            connection_note=result["connection_note"],
            full_letter=result["full_letter"],
            char_count=result["char_count"],
            is_under_limit=result["is_under_limit"],
        )
    except Exception as exc:
        log.error("Referral note generation error: %s", exc, exc_info=True)
        raise APIError(f"Referral note generation failed: {str(exc)}")


@app.post("/api/referrals/log-action", tags=["referrals"], response_model=ReferralActionLogResponse)
async def log_referral_action(
    request: ReferralActionLogRequest,
    req: Request,
):
    """
    Logs a LinkedIn referral action (connection request, direct message, or reply)
    into the OutreachRecord CRM table.
    """
    trace = req.state.trace_id
    try:
        async with db_session() as db:
            rec = referral_service.log_referral_action(
                db,
                contact_name=request.contact_name,
                company=request.company,
                action_type=request.action_type,
                linkedin_url=request.linkedin_url,
                contact_email=request.contact_email,
                message_body=request.message_body,
                job_id=request.job_id,
            )
            log.info("[%s] Logged referral action '%s' for %s (record #%d)", trace, request.action_type, request.contact_name, rec.id)
            return ReferralActionLogResponse(
                status="success",
                outreach_id=rec.id,
                message=f"Referral action '{request.action_type}' recorded successfully",
            )
    except Exception as exc:
        log.error("[%s] Failed to log referral action: %s", trace, exc, exc_info=True)
        raise APIError(f"Failed to log referral action: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# X (Twitter) Referral Automator & Engagement Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/x/auth/url", tags=["x-referral"], response_model=XAuthUrlResponse)
async def get_x_auth_url(req: Request):
    """Generates an OAuth 2.0 PKCE authorization link for connecting user's X account."""
    try:
        data = x_oauth.get_authorization_url()
        return XAuthUrlResponse(
            status="success",
            authorization_url=data["authorization_url"],
            state=data["state"],
        )
    except Exception as exc:
        log.error("Failed to generate X auth URL: %s", exc, exc_info=True)
        raise APIError(f"Failed to generate X auth URL: {str(exc)}")


@app.post("/api/x/auth/callback", tags=["x-referral"], response_model=XAuthCallbackResponse)
async def handle_x_auth_callback(
    request: XAuthCallbackRequest,
    req: Request,
):
    """Exchanges OAuth authorization code for tokens and persists in database."""
    trace = req.state.trace_id
    try:
        token_data = await x_oauth.exchange_code_for_tokens(
            code=request.code,
            state=request.state,
            verifier=request.code_verifier,
        )
        async with db_session() as db:
            x_oauth.save_token(db, token_data, user_identifier="default_user")
            log.info("[%s] Successfully authenticated X account for default_user", trace)
            return XAuthCallbackResponse(
                status="success",
                connected=True,
                message="X account connected successfully via OAuth 2.0 PKCE",
            )
    except Exception as exc:
        log.error("[%s] X OAuth callback error: %s", trace, exc, exc_info=True)
        raise APIError(f"X authentication failed: {str(exc)}")


@app.get("/api/x/auth/status", tags=["x-referral"], response_model=XAuthStatusResponse)
async def get_x_auth_status(req: Request):
    """Returns connection status and expiration info of user's X account."""
    try:
        async with db_session() as db:
            token = x_oauth.get_token(db, user_identifier="default_user")
            if not token:
                return XAuthStatusResponse(connected=False)
            scopes_list = token.scopes.split(" ") if token.scopes else []
            return XAuthStatusResponse(
                connected=True,
                username=token.x_username or "connected_user",
                expires_at=token.expires_at,
                scopes=scopes_list,
            )
    except Exception as exc:
        log.error("Failed to get X auth status: %s", exc, exc_info=True)
        raise APIError(f"Failed to get X auth status: {str(exc)}")


@app.get("/api/x/targets", tags=["x-referral"], response_model=XTargetsResponse)
async def get_x_targets(limit: int = 30, req: Request = None):
    """Retrieves target companies and roles currently in the pipeline for X networking."""
    try:
        async with db_session() as db:
            targets = x_referral_service.get_active_targets(db, limit=limit)
            return XTargetsResponse(
                status="success",
                total_targets=len(targets),
                targets=targets,
            )
    except Exception as exc:
        log.error("Failed to get X targets: %s", exc, exc_info=True)
        raise APIError(f"Failed to get X targets: {str(exc)}")


@app.post("/api/x/search", tags=["x-referral"], response_model=XSearchResponse)
async def search_x_profiles(request: XSearchRequest, req: Request):
    """Searches tech employees, recruiters, and engineering managers on X for a company."""
    trace = req.state.trace_id
    try:
        result = x_referral_service.search_company_referrals(
            company=request.company, role=request.role, limit=request.limit
        )
        return XSearchResponse(
            status="success",
            company=result["company"],
            role=result["role"],
            source=result["source"],
            count=result["count"],
            profiles=result["profiles"],
        )
    except Exception as exc:
        log.error("[%s] X profile search failed: %s", trace, exc, exc_info=True)
        raise APIError(f"X profile search failed: {str(exc)}")


@app.post("/api/x/search-tweets", tags=["x-referral"], response_model=XTweetSearchResponse)
async def search_x_hiring_tweets(request: XTweetSearchRequest, req: Request):
    """Searches active hiring announcements and referral tweets for a company on X."""
    trace = req.state.trace_id
    try:
        result = x_referral_service.search_hiring_tweets(
            company=request.company, role=request.role, limit=request.limit
        )
        return XTweetSearchResponse(
            status="success",
            company=result["company"],
            role=result["role"],
            count=result["count"],
            tweets=result["tweets"],
        )
    except Exception as exc:
        log.error("[%s] X tweet search failed: %s", trace, exc, exc_info=True)
        raise APIError(f"X tweet search failed: {str(exc)}")


@app.post("/api/x/generate-message", tags=["x-referral"], response_model=XMessageGenerateResponse)
async def generate_x_message(request: XMessageGenerateRequest, req: Request):
    """Generates AI-crafted contextual tweet replies, quote tweets, or DMs."""
    try:
        profile_data = {
            "x_user_id": "0",
            "username": request.username,
            "name": request.name or request.username,
            "company": request.company,
            "title": request.title,
        }
        context_data = {
            "company": request.company,
            "role_title": request.role_title or "Engineer",
            "job_link": request.job_link,
            "candidate_bio": request.candidate_bio,
            "highlight": request.highlight,
            "target_topic": request.target_topic,
            "sender_name": request.sender_name or "Candidate",
        }
        tweet_data = None
        if request.tweet_id and request.tweet_text:
            tweet_data = {
                "tweet_id": request.tweet_id,
                "text": request.tweet_text,
                "author_username": request.username,
            }

        result = x_referral_service.generate_message(
            action_type=request.action_type,
            profile_data=profile_data,
            context_data=context_data,
            tweet_data=tweet_data,
            max_length=request.max_length,
        )
        return XMessageGenerateResponse(
            status="success",
            action_type=result["action_type"],
            message=result["message"],
            char_count=result["char_count"],
            is_under_limit=result["is_under_limit"],
            intent_url=result.get("intent_url"),
        )
    except Exception as exc:
        log.error("X message generation error: %s", exc, exc_info=True)
        raise APIError(f"X message generation failed: {str(exc)}")


@app.post("/api/x/engage", tags=["x-referral"], response_model=XEngageResponse)
async def engage_x_user(request: XEngageRequest, req: Request):
    """Executes follow, like, repost, reply, or DM, and logs action to OutreachRecord."""
    trace = req.state.trace_id
    try:
        async with db_session() as db:
            result = await x_referral_service.engage_user(
                db=db,
                action_type=request.action_type,
                target_username=request.target_username,
                company=request.company,
                target_user_id=request.target_user_id,
                tweet_id=request.tweet_id,
                message_text=request.message_text,
                job_id=request.job_id,
            )
            log.info("[%s] Executed X action '%s' for @%s (outreach #%d)", trace, request.action_type, request.target_username, result["outreach_id"])
            return XEngageResponse(
                status="success",
                outreach_id=result["outreach_id"],
                action_type=result["action_type"],
                target=result["target"],
                intent_url=result.get("intent_url"),
                mode=result.get("mode", "api"),
                daily_usage=result.get("daily_usage", {}),
            )
    except Exception as exc:
        log.error("[%s] X engagement error: %s", trace, exc, exc_info=True)
        raise APIError(f"X engagement failed: {str(exc)}")


@app.post("/api/x/sync", tags=["x-referral"], response_model=XProfileSyncResponse)
async def sync_x_profiles(request: XProfileSyncRequest, req: Request):
    """Batch ingests discovered X profiles into Contacts CRM."""
    trace = req.state.trace_id
    try:
        async with db_session() as db:
            result = x_referral_service.sync_profiles_to_contacts(db, request.profiles)
            log.info("[%s] Synced %d X contacts (%d new)", trace, result["synced_count"], result["new_contacts_count"])
            return XProfileSyncResponse(
                status="success",
                synced_count=result["synced_count"],
                new_contacts_count=result["new_contacts_count"],
            )
    except Exception as exc:
        log.error("[%s] X profile sync failed: %s", trace, exc, exc_info=True)
        raise APIError(f"X profile sync failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# Email Intelligence & Google Boolean Dorking Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/email-intelligence/discover", tags=["email-intelligence"], response_model=EmailDiscoveryResponse)
async def discover_emails(request: EmailDiscoveryRequest, req: Request):
    """
    Executes the multi-provider waterfall (Google Boolean Dorks, Clearbit domain resolution,
    GitHub commit harvesting, and pattern synthesis) to discover verified decision-maker emails.
    """
    trace = req.state.trace_id
    try:
        async with db_session() as db:
            result = await email_intelligence_service.discover_company_decision_makers(
                db=db,
                company=request.company,
                job_title=request.job_title,
                website_hint=request.website_hint,
                target_name=request.target_name,
                limit=request.limit,
            )
            log.info("[%s] Discovered %d verified decision-makers for %s (%s)", trace, result["total_found"], request.company, result["domain"])
            return EmailDiscoveryResponse(
                status="success",
                company=result["company"],
                domain=result["domain"],
                has_mx=result["has_mx"],
                mail_provider=result["mail_provider"],
                total_found=result["total_found"],
                contacts=result["contacts"],
                recommended_contact=result["recommended_contact"],
            )
    except Exception as exc:
        log.error("[%s] Email discovery failed: %s", trace, exc, exc_info=True)
        raise APIError(f"Email discovery failed: {str(exc)}")


@app.post("/api/email-intelligence/verify", tags=["email-intelligence"], response_model=EmailVerifyResponse)
async def verify_email_address(request: EmailVerifyRequest, req: Request):
    """Executes live RFC 5322 syntax validation, disposable email filter, and DNS MX checks."""
    try:
        res = email_intelligence_service.verify_email(request.email)
        return EmailVerifyResponse(
            status="success",
            email=res.email,
            is_valid_syntax=res.is_valid_syntax,
            is_disposable=res.is_disposable,
            is_free_mail=res.is_free_mail,
            has_mx_records=res.has_mx_records,
            mx_records=res.mx_records,
            mail_provider=res.mail_provider,
            confidence_score=res.confidence_score,
            verification_status=res.status,
            reason=res.reason,
        )
    except Exception as exc:
        log.error("Email verification error: %s", exc, exc_info=True)
        raise APIError(f"Email verification failed: {str(exc)}")


@app.post("/api/email-intelligence/dorks", tags=["email-intelligence"], response_model=EmailDorksResponse)
async def generate_email_dorks(request: EmailDorksRequest, req: Request):
    """Generates targeted Google Boolean Search Dorks for uncovering emails and decision-makers."""
    try:
        dorks = email_intelligence_service.generate_dorks(
            company=request.company,
            domain=request.domain,
            person_name=request.person_name,
            role_title=request.role_title,
        )
        return EmailDorksResponse(
            status="success",
            company=request.company,
            domain=request.domain or f"{request.company.lower().replace(' ', '')}.com",
            total_dorks=len(dorks),
            dorks=[d.model_dump() for d in dorks],
        )
    except Exception as exc:
        log.error("Dork generation error: %s", exc, exc_info=True)
        raise APIError(f"Dork generation failed: {str(exc)}")


@app.post("/api/email-intelligence/permutations", tags=["email-intelligence"], response_model=EmailPermutationsResponse)
async def generate_email_permutations(request: EmailPermutationsRequest, req: Request):
    """Generates 12 standard corporate email permutations for a person and domain with MX checks."""
    try:
        perms = email_intelligence_service.generate_permutations(
            full_name=request.full_name,
            domain=request.domain,
        )
        return EmailPermutationsResponse(
            status="success",
            full_name=request.full_name,
            domain=request.domain,
            has_mx=perms[0].has_mx if perms else True,
            total_permutations=len(perms),
            permutations=[p.model_dump() for p in perms],
        )
    except Exception as exc:
        log.error("Permutation generation error: %s", exc, exc_info=True)
        raise APIError(f"Permutation generation failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# Transformer Q, K, V Attention Architecture Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/attention/match", tags=["attention"], response_model=AttentionMatchResponse)
async def match_job_with_attention(request: AttentionMatchRequest, req: Request):
    """
    Computes 4-Head Scaled Dot-Product Attention (Tech, Scale, Impact, Seniority)
    between Job Description requirement queries (Q) and Candidate capability keys (K),
    synthesizing the attended value vector (V) and attention weight matrix.
    """
    trace = req.state.trace_id
    try:
        result = attention_service.match_job(
            job_description=request.job_description,
            custom_bullets=request.custom_bullets,
        )
        log.info("[%s] Transformer Q,K,V match computed: score=%.1f%% (%s)", trace, result.overall_score, result.fit_label)
        return AttentionMatchResponse(
            status="success",
            overall_score=result.overall_score,
            fit_label=result.fit_label,
            heads={h_name: h.model_dump() for h_name, h in result.heads.items()},
            matrix=result.matrix.model_dump(),
            top_attended_values=[v.model_dump() for v in result.top_attended_values],
            tailored_bullets=[b.model_dump() for b in result.tailored_bullets],
            outreach_hooks=[h.model_dump() for h in result.outreach_hooks],
            summary_insight=result.summary_insight,
        )
    except Exception as exc:
        log.error("[%s] Attention match failed: %s", trace, exc, exc_info=True)
        raise APIError(f"Attention match failed: {str(exc)}")


@app.post("/api/attention/tailor", tags=["attention"], response_model=AttentionTailorResponse)
async def tailor_resume_bullets_with_attention(request: AttentionTailorRequest, req: Request):
    """Generates attention-ranked tailored bullets for a job description based on received attention weights."""
    try:
        bullets = attention_service.tailor_resume(
            job_description=request.job_description,
            custom_bullets=request.custom_bullets,
        )
        return AttentionTailorResponse(
            status="success",
            total_bullets=len(bullets),
            tailored_bullets=[b.model_dump() for b in bullets],
        )
    except Exception as exc:
        log.error("Attention tailoring error: %s", exc, exc_info=True)
        raise APIError(f"Attention tailoring failed: {str(exc)}")


@app.post("/api/attention/outreach", tags=["attention"], response_model=AttentionOutreachResponse)
async def generate_cross_attention_outreach(request: AttentionOutreachRequest, req: Request):
    """Cross-attends target contact persona against candidate portfolio wins to generate personalized hooks."""
    try:
        result = attention_service.synthesize_outreach_hooks(
            contact_name=request.contact_name,
            contact_title=request.contact_title,
            company=request.company,
            job_description=request.job_description,
        )
        return AttentionOutreachResponse(
            status="success",
            contact_name=result["contact_name"],
            contact_title=result["contact_title"],
            company=result["company"],
            role_type=result["role_type"],
            subject=result["subject"],
            hook_message=result["hook_message"],
            attended_proof_point=result["attended_proof_point"],
            impact_metric=result["impact_metric"],
            call_to_action=result["call_to_action"],
        )
    except Exception as exc:
        log.error("Cross-attention outreach error: %s", exc, exc_info=True)
        raise APIError(f"Cross-attention outreach failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# Ghost Job & Stale Listing Detector Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/ghost-hunter/analyze", tags=["ghost-hunter"], response_model=GhostAnalysisResponse)
async def analyze_ghost_job(request: GhostAnalysisRequest, req: Request):
    """Analyzes a job posting against temporal, textual, and company signals to compute its Ghost Score."""
    try:
        result = ghost_hunter_service.analyze(
            title=request.title,
            company=request.company,
            description=request.description,
            posted_date=request.posted_date,
            has_decision_maker=request.has_decision_maker,
        )
        return GhostAnalysisResponse(
            status="success",
            ghost_score=result.ghost_score,
            urgency_label=result.urgency_label,
            is_ghost_risk=result.is_ghost_risk,
            confidence_score=result.confidence_score,
            estimated_age_days=result.estimated_age_days,
            signals=[s.model_dump() for s in result.signals],
            action_recommendation=result.action_recommendation,
        )
    except Exception as exc:
        log.error("Ghost analysis failed: %s", exc, exc_info=True)
        raise APIError(f"Ghost analysis failed: {str(exc)}")


@app.get("/api/jobs/{job_id}/ghost-score", tags=["ghost-hunter"], response_model=GhostAnalysisResponse)
async def get_job_ghost_score(job_id: int, req: Request):
    """Retrieves Ghost Job legitimacy analysis for an existing database job."""
    try:
        async with db_session() as db:
            result = ghost_hunter_service.analyze_db_job(db, job_id)
            return GhostAnalysisResponse(
                status="success",
                ghost_score=result.ghost_score,
                urgency_label=result.urgency_label,
                is_ghost_risk=result.is_ghost_risk,
                confidence_score=result.confidence_score,
                estimated_age_days=result.estimated_age_days,
                signals=[s.model_dump() for s in result.signals],
                action_recommendation=result.action_recommendation,
            )
    except ValueError as exc:
        raise ResourceNotFoundError("Job", job_id)
    except Exception as exc:
        log.error("Database ghost analysis failed: %s", exc, exc_info=True)
        raise APIError(f"Database ghost analysis failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# Cold Email Deliverability Sandbox Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/deliverability/analyze-draft", tags=["deliverability"], response_model=DeliverabilityDraftResponse)
async def analyze_email_deliverability(request: DeliverabilityDraftRequest, req: Request):
    """Analyzes a cold outreach draft for spam trigger keywords, reading grade level, and deliverability risk."""
    try:
        result = deliverability_service.analyze(subject=request.subject, body=request.body)
        return DeliverabilityDraftResponse(
            status="success",
            spam_score=result.spam_score,
            deliverability_tier=result.deliverability_tier,
            is_safe=result.is_safe,
            flesch_kincaid_grade=result.flesch_kincaid_grade,
            reading_time_seconds=result.reading_time_seconds,
            word_count=result.word_count,
            char_count=result.char_count,
            link_count=result.link_count,
            uppercase_ratio=result.uppercase_ratio,
            spam_matches=[m.model_dump() for m in result.spam_matches],
            subject_score=result.subject_score,
            subject_advice=result.subject_advice,
            deliverability_recommendations=result.deliverability_recommendations,
        )
    except Exception as exc:
        log.error("Deliverability analysis failed: %s", exc, exc_info=True)
        raise APIError(f"Deliverability analysis failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# Live Voice & Audio AI Mock Interviewer Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/interview/voice-feedback", tags=["interview"], response_model=VoiceFeedbackResponse)
async def analyze_spoken_mock_interview(request: VoiceFeedbackRequest, req: Request):
    """Analyzes a candidate's spoken mock interview response for filler words, speech cadence (WPM), and STAR structure."""
    try:
        result = voice_interview_service.analyze_spoken_response(
            transcript=request.transcript,
            duration_seconds=request.duration_seconds,
            target_focus=request.target_focus or "Distributed Systems",
        )
        return VoiceFeedbackResponse(
            status="success",
            speech_delivery_score=result.speech_delivery_score,
            filler_stats=result.filler_stats.model_dump(),
            cadence_stats=result.cadence_stats.model_dump(),
            star_eval=result.star_eval.model_dump(),
            delivery_tips=result.delivery_tips,
        )
    except Exception as exc:
        log.error("Voice interview feedback failed: %s", exc, exc_info=True)
        raise APIError(f"Voice interview feedback failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# Instant Multi-Channel Webhook Alerts Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/notifications/config", tags=["notifications"], response_model=NotificationConfigSchema)
async def get_notification_config(req: Request):
    """Retrieves current Telegram, Discord, and Slack webhook alert configuration."""
    return notification_service.get_config()


@app.post("/api/notifications/config", tags=["notifications"], response_model=NotificationConfigSchema)
async def update_notification_config(config: NotificationConfigSchema, req: Request):
    """Updates Telegram, Discord, and Slack webhook alert settings."""
    try:
        saved = notification_service.save_config(NotificationConfig(**config.model_dump()))
        return saved
    except Exception as exc:
        log.error("Failed to save notification configuration: %s", exc, exc_info=True)
        raise APIError(f"Failed to save notification settings: {str(exc)}")


@app.post("/api/notifications/test", tags=["notifications"])
async def test_notification_channel(request: NotificationTestRequest, req: Request):
    """Sends a sample test alert payload to Telegram, Discord, or Slack."""
    try:
        res = await notification_service.send_test_alert(request.channel)
        return {"status": "success", "channel": res.channel, "delivery_status": res.status, "detail": res.detail}
    except Exception as exc:
        log.error("Notification channel test failed: %s", exc, exc_info=True)
        raise APIError(f"Channel test failed: {str(exc)}")


@app.post("/api/notifications/dispatch", tags=["notifications"], response_model=NotificationDispatchResponseSchema)
async def dispatch_opportunity_alert(alert: NotificationAlertSchema, req: Request):
    """Dispatches a high-priority opportunity alert to all active webhook channels."""
    try:
        res = await notification_service.dispatch_alert(AlertPayload(**alert.model_dump()))
        return NotificationDispatchResponseSchema(
            status=res.status,
            dispatched_count=res.dispatched_count,
            results=[r.model_dump() for r in res.results],
            timestamp=res.timestamp,
        )
    except Exception as exc:
        log.error("Notification dispatch failed: %s", exc, exc_info=True)
        raise APIError(f"Notification dispatch failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# 4-Year Total Compensation & Equity Simulator Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/comp/simulate", tags=["compensation"], response_model=CompSimulationResponse)
async def simulate_compensation_package(offer: OfferPackageSchema, req: Request):
    """Simulates 4-year total compensation cash flows, equity vesting curves, and counter-offer targets."""
    try:
        pkg = OfferPackage(**offer.model_dump())
        result = comp_simulator_service.simulate(pkg)
        return CompSimulationResponse(
            status="success",
            company=result.company,
            role_title=result.role_title,
            four_year_total_pre_tax=result.four_year_total_pre_tax,
            four_year_total_post_tax=result.four_year_total_post_tax,
            average_annual_comp=result.average_annual_comp,
            yearly_breakdowns=[b.model_dump() for b in result.yearly_breakdowns],
            negotiation_counter_target=result.negotiation_counter_target,
            negotiation_advice=result.negotiation_advice,
        )
    except Exception as exc:
        log.error("Comp package simulation failed: %s", exc, exc_info=True)
        raise APIError(f"Comp package simulation failed: {str(exc)}")


@app.post("/api/comp/compare", tags=["compensation"], response_model=List[CompSimulationResponse])
async def compare_compensation_packages(request: CompComparisonRequest, req: Request):
    """Simulates and ranks multiple competing job offer packages over a 4-year horizon."""
    try:
        packages = [OfferPackage(**o.model_dump()) for o in request.offers]
        results = comp_simulator_service.compare(packages)
        return [
            CompSimulationResponse(
                status="success",
                company=r.company,
                role_title=r.role_title,
                four_year_total_pre_tax=r.four_year_total_pre_tax,
                four_year_total_post_tax=r.four_year_total_post_tax,
                average_annual_comp=r.average_annual_comp,
                yearly_breakdowns=[b.model_dump() for b in r.yearly_breakdowns],
                negotiation_counter_target=r.negotiation_counter_target,
                negotiation_advice=r.negotiation_advice,
            )
            for r in results
        ]
    except Exception as exc:
        log.error("Comp comparison failed: %s", exc, exc_info=True)
        raise APIError(f"Comp comparison failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# 1-Click ATS Tailored Resume & Cover Letter Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/resume/generate-ats", tags=["resume"], response_model=ResumeDocumentResponseSchema)
async def generate_tailored_ats_resume(request: ResumeGenerateRequestSchema, req: Request):
    """Generates an attention-weighted, single-page ATS-compliant HTML/PDF resume tailored to target job requirements."""
    try:
        req_obj = ResumeGenerateRequest(**request.model_dump())
        result = resume_generator_service.generate_resume(req_obj)
        return ResumeDocumentResponseSchema(
            status="success",
            document_type=result.document_type,
            company=result.company,
            role_title=result.role_title,
            ats_match_score=result.ats_match_score,
            html_content=result.html_content,
            plain_text=result.plain_text,
            suggested_keywords=result.suggested_keywords,
            timestamp=result.timestamp,
        )
    except Exception as exc:
        log.error("ATS resume generation failed: %s", exc, exc_info=True)
        raise APIError(f"ATS resume generation failed: {str(exc)}")


@app.post("/api/resume/generate-cover-letter", tags=["resume"], response_model=ResumeDocumentResponseSchema)
async def generate_tailored_cover_letter(request: CoverLetterGenerateRequestSchema, req: Request):
    """Generates a tailored executive cover letter explicitly referencing target company challenges and candidate metrics."""
    try:
        req_obj = CoverLetterGenerateRequest(**request.model_dump())
        result = resume_generator_service.generate_cover_letter(req_obj)
        return ResumeDocumentResponseSchema(
            status="success",
            document_type=result.document_type,
            company=result.company,
            role_title=result.role_title,
            ats_match_score=result.ats_match_score,
            html_content=result.html_content,
            plain_text=result.plain_text,
            suggested_keywords=result.suggested_keywords,
            timestamp=result.timestamp,
        )
    except Exception as exc:
        log.error("Cover letter generation failed: %s", exc, exc_info=True)
        raise APIError(f"Cover letter generation failed: {str(exc)}")


@app.post("/api/resume/parse", tags=["resume"])
async def parse_resume_document(
    file: UploadFile = File(...),
):
    """Parses resume PDF/DOCX/TXT via ApyHub SharpAPI into structured candidate JSON."""
    try:
        content = await file.read()
        parser = SharpAPIResumeParser()
        result = await parser.parse_resume_bytes(content, filename=file.filename or "resume.pdf")
        return result
    except Exception as exc:
        log.error("SharpAPI resume parse failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(exc), "provider": "sharpapi_apyhub"},
        )


@app.post("/api/resume/evaluate", tags=["resume"])
async def evaluate_resume_document(
    file: Optional[UploadFile] = File(None),
    job_description: Optional[str] = Form(None),
    job_title: Optional[str] = Form(None),
):
    """Evaluates candidate resume against target JD using ApyHub SharpAPI parsing and cross-attention scoring."""
    try:
        parser = SharpAPIResumeParser()
        if file is not None:
            content = await file.read()
            filename = file.filename or "resume.pdf"
        else:
            default_path = Path("data/resume.pdf")
            if default_path.exists():
                content = default_path.read_bytes()
                filename = "resume.pdf"
            else:
                raise HTTPException(status_code=400, detail="No resume file uploaded and default data/resume.pdf not found.")

        evaluation = await parser.evaluate_resume(
            content,
            filename=filename,
            job_description=job_description,
            job_title=job_title,
        )
        return evaluation
    except Exception as exc:
        log.error("Resume evaluation failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(exc), "provider": "sharpapi_apyhub"},
        )


# ═══════════════════════════════════════════════════════════════════════════
# 60 Tier-1 Tech Companies: Career Scraping, Leveling & Referral Engine
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/tier1/companies", tags=["tier1-sourcing"])
async def list_tier1_companies(search: Optional[str] = None):
    """Returns the 60 top-tier target companies with compensation, 4-YOE leveling, and negotiation targets."""
    companies = [c.to_dict() for c in TIER1_REGISTRY]
    if search:
        s_lower = search.lower()
        companies = [c for c in companies if s_lower in c["name"].lower()]
    return {
        "status": "success",
        "total_companies": len(companies),
        "companies": companies,
    }


@app.get("/api/tier1/compensation/{company_name}", tags=["tier1-sourcing"])
async def get_company_compensation_benchmark(company_name: str):
    """Retrieves 4-YOE Base, Bonus, RSU, Typical TC, and Negotiation Target for a specific company."""
    comp = get_tier1_company(company_name)
    if not comp:
        raise HTTPException(status_code=404, detail=f"Company '{company_name}' not found in Tier-1 database.")
    return {
        "status": "success",
        "company": comp.to_dict(),
        "negotiation_advice": f"For {comp.name} at {comp.likely_level}, target {comp.negotiation_target_lakhs} total compensation (Typical TC: {comp.typical_tc_lakhs})."
    }


class Tier1SyncCareersRequest(BaseModel):
    companies: Optional[List[str]] = None
    keywords: Optional[List[str]] = ["Python", "FastAPI", "Backend", "Engineer", "Software"]
    limit: int = 50


@app.post("/api/tier1/sync-careers", tags=["tier1-sourcing"])
async def sync_tier1_career_pages(payload: Tier1SyncCareersRequest = Tier1SyncCareersRequest()):
    """Concurrently scrapes official career portals & ATS endpoints across Tier-1 companies."""
    try:
        scraper = Tier1CareerScraper()
        jobs = await scraper.scrape_all_tier1_careers(
            keywords=payload.keywords,
            companies=payload.companies,
            max_jobs=payload.limit,
        )
        return {
            "status": "success",
            "total_found": len(jobs),
            "jobs": jobs,
        }
    except Exception as exc:
        log.error("Tier-1 career sync failed: %s", exc, exc_info=True)
        raise APIError(f"Tier-1 career sync failed: {str(exc)}")


class Tier1ReferralRequest(BaseModel):
    company_name: str
    role_title: Optional[str] = "Software Engineer"
    job_id_or_url: Optional[str] = None
    max_leads: int = 5


@app.post("/api/tier1/find-referrals", tags=["tier1-sourcing"])
async def find_tier1_referral_contacts(payload: Tier1ReferralRequest):
    """Discovers Engineering Managers and Senior Engineers on LinkedIn and generates personalized referral requests."""
    try:
        queries = generate_referral_xray_queries(payload.company_name)
        leads = await search_company_referral_contacts(payload.company_name, max_leads=payload.max_leads)

        comp = get_tier1_company(payload.company_name)

        # Compose message for each lead
        enriched_leads = []
        for lead in leads:
            msg = compose_referral_request(
                contact_name=lead["name"],
                company_name=payload.company_name,
                role_title=payload.role_title or "Software Engineer",
                job_id_or_url=payload.job_id_or_url,
                candidate_name=getattr(settings, "sender_name", "Kushall Jain") or "Kushall Jain",
            )
            enriched_leads.append({
                **lead,
                "outreach_materials": msg,
            })

        return {
            "status": "success",
            "company": comp.to_dict() if comp else {"name": payload.company_name},
            "xray_queries": queries,
            "leads_found": len(enriched_leads),
            "leads": enriched_leads,
        }
    except Exception as exc:
        log.error("Tier-1 referral search failed: %s", exc, exc_info=True)
        raise APIError(f"Tier-1 referral search failed: {str(exc)}")



# ═══════════════════════════════════════════════════════════════════════════
# Top Indian App Startups (Top Downloads & Revenue) Career Ingestion Engine
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/indian-startups/directory", tags=["indian-startups"])
async def list_indian_startups(
    category: Optional[str] = None,
    tier: Optional[str] = None,
    search: Optional[str] = None,
):
    """Returns top Indian startups on App Store / Play Store with download/revenue scale & career links."""
    startups = filter_indian_startups(category=category, tier_category=tier, search=search)
    return {
        "status": "success",
        "total_startups": len(startups),
        "startups": [s.to_dict() for s in startups],
    }


@app.get("/api/indian-startups/stats", tags=["indian-startups"])
async def get_indian_startups_stats():
    """Returns statistical breakdown of the Indian startup catalog across sectors and app tiers."""
    from collections import Counter
    categories = Counter(s.category for s in INDIAN_APP_STARTUPS)
    tiers = Counter(s.tier_category for s in INDIAN_APP_STARTUPS)
    ats_breakdown = Counter(s.ats_platform for s in INDIAN_APP_STARTUPS)
    return {
        "status": "success",
        "total_tracked_startups": len(INDIAN_APP_STARTUPS),
        "category_distribution": dict(categories),
        "tier_distribution": dict(tiers),
        "ats_breakdown": dict(ats_breakdown),
    }


class IndianStartupsSyncRequest(BaseModel):
    categories: Optional[List[str]] = None
    startup_ids: Optional[List[str]] = None
    keywords: Optional[List[str]] = ["Python", "FastAPI", "Backend", "Engineer", "Software", "SDE"]
    limit: int = 100


@app.post("/api/indian-startups/sync-jobs", tags=["indian-startups"])
async def sync_indian_startups_jobs(payload: IndianStartupsSyncRequest = IndianStartupsSyncRequest()):
    """Concurrently scrapes live engineering opportunities from top Indian app startups."""
    try:
        scraper = IndianAppStartupsScraper()
        jobs = await scraper.scrape_all_startups(
            keywords=payload.keywords,
            categories=payload.categories,
            startup_ids=payload.startup_ids,
            max_jobs=payload.limit,
        )
        return {
            "status": "success",
            "total_found": len(jobs),
            "jobs": jobs,
        }
    except Exception as exc:
        log.error("Indian startups job sync failed: %s", exc, exc_info=True)
        raise APIError(f"Indian startups job sync failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# FinTech Festival (GFF & SFF) Sponsors & Career Ingestion Engine
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/fintech-festival/sponsors", tags=["fintech-festival"])
async def list_fintech_festival_sponsors(
    category: Optional[str] = None,
    festival: Optional[str] = None,
    tier_role: Optional[str] = None,
    search: Optional[str] = None,
):
    """Returns sponsors and exhibitors from Global FinTech Fest and Singapore FinTech Festival."""
    sponsors = filter_fintech_festival_companies(
        category=category,
        festival=festival,
        tier_role=tier_role,
        search=search,
    )
    return {
        "status": "success",
        "total_sponsors": len(sponsors),
        "sponsors": [s.to_dict() for s in sponsors],
    }


@app.get("/api/fintech-festival/stats", tags=["fintech-festival"])
async def get_fintech_festival_stats():
    """Returns statistical breakdown of FinTech Festival sponsors across categories, events, and ATS platforms."""
    from collections import Counter
    categories = Counter(c.category for c in FINTECH_FESTIVAL_REGISTRY)
    festivals = Counter(c.festival for c in FINTECH_FESTIVAL_REGISTRY)
    tiers = Counter(c.tier_role for c in FINTECH_FESTIVAL_REGISTRY)
    ats_breakdown = Counter(c.ats_platform for c in FINTECH_FESTIVAL_REGISTRY)
    return {
        "status": "success",
        "total_tracked_sponsors": len(FINTECH_FESTIVAL_REGISTRY),
        "category_distribution": dict(categories),
        "festival_distribution": dict(festivals),
        "tier_distribution": dict(tiers),
        "ats_breakdown": dict(ats_breakdown),
    }


class FinTechFestivalSyncRequest(BaseModel):
    categories: Optional[List[str]] = None
    festivals: Optional[List[str]] = None
    company_ids: Optional[List[str]] = None
    keywords: Optional[List[str]] = ["Python", "FastAPI", "Backend", "Engineer", "Software", "Fintech"]
    limit: int = 100


@app.post("/api/fintech-festival/sync-jobs", tags=["fintech-festival"])
async def sync_fintech_festival_jobs(payload: FinTechFestivalSyncRequest = FinTechFestivalSyncRequest()):
    """Concurrently scrapes live engineering opportunities from FinTech Festival sponsors & partners."""
    try:
        scraper = FinTechFestivalScraper()
        jobs = await scraper.scrape_all_festival_sponsors(
            keywords=payload.keywords,
            categories=payload.categories,
            festivals=payload.festivals,
            company_ids=payload.company_ids,
            max_jobs=payload.limit,
        )
        return {
            "status": "success",
            "total_found": len(jobs),
            "jobs": jobs,
        }
    except Exception as exc:
        log.error("FinTech Festival job sync failed: %s", exc, exc_info=True)
        raise APIError(f"FinTech Festival job sync failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# Autonomous Continuous Job Ingestion & Intelligence Pipeline Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/crawler/status", tags=["autonomous-crawler"])
async def get_crawler_status():
    """Returns live worker status, current scraping engine, uptime, and event timeline."""
    return autonomous_crawler.get_status()


class CrawlerStartRequest(BaseModel):
    interval_seconds: int = 180


@app.post("/api/crawler/start", tags=["autonomous-crawler"])
async def start_autonomous_crawler(payload: CrawlerStartRequest = CrawlerStartRequest()):
    """Starts the continuous background autonomous job crawler daemon."""
    started = autonomous_crawler.start_daemon(interval_seconds=max(30, payload.interval_seconds))
    if not started:
        return {"status": "already_running", "message": "Autonomous crawler is already running in the background."}
    return {"status": "started", "message": f"Autonomous crawler started with {payload.interval_seconds}s interval."}


@app.post("/api/crawler/stop", tags=["autonomous-crawler"])
async def stop_autonomous_crawler():
    """Stops/pauses the continuous background autonomous job crawler."""
    stopped = autonomous_crawler.stop_daemon()
    return {"status": "stopped" if stopped else "not_running", "message": "Autonomous crawler stopped."}


class CrawlerSinglePassRequest(BaseModel):
    max_per_source: int = 30


@app.post("/api/crawler/run-single-pass", tags=["autonomous-crawler"])
async def trigger_crawler_single_pass(payload: CrawlerSinglePassRequest = CrawlerSinglePassRequest()):
    """Triggers an immediate, comprehensive job sweep across all 5 sourcing engines."""
    results = await autonomous_crawler.run_single_pass(max_per_source=payload.max_per_source)
    return {
        "status": "success",
        "sweep_results": results,
    }


@app.get("/api/crawler/metrics", tags=["autonomous-crawler"])
async def get_enterprise_crawler_metrics():
    """Returns enterprise-grade metrics for CTO / VC pitch: tech stack distribution, remote ratio, salary benchmarks."""
    from collections import Counter
    from src.tier1_companies import TIER1_REGISTRY
    from src.indian_app_startups import INDIAN_APP_STARTUPS
    from src.fintech_festival_companies import FINTECH_FESTIVAL_REGISTRY

    db = SessionLocal()
    try:
        total_jobs = db.query(Job).count()
        all_jobs = db.query(Job.title, Job.tags, Job.experience_level, Job.work_mode, Job.has_remote, Job.company, Job.source).all()

        tech_counts = Counter()
        seniority_counts = Counter()
        work_mode_counts = Counter()
        sources_counts = Counter()

        for row in all_jobs:
            sources_counts[row.source or "unknown"] += 1
            work_mode_counts[row.work_mode or "onsite"] += 1
            seniority_counts[row.experience_level or "Mid-Level"] += 1
            if row.tags:
                try:
                    tags = json.loads(row.tags) if isinstance(row.tags, str) else row.tags
                    for t in tags:
                        tech_counts[t] += 1
                except Exception:
                    pass


        return {
            "status": "success",
            "enterprise_summary": {
                "total_verified_target_companies": len(TIER1_REGISTRY) + len(INDIAN_APP_STARTUPS) + len(FINTECH_FESTIVAL_REGISTRY),
                "tier1_global_unicorns": len(TIER1_REGISTRY),
                "top_indian_app_startups": len(INDIAN_APP_STARTUPS),
                "fintech_festival_sponsors": len(FINTECH_FESTIVAL_REGISTRY),
                "total_jobs_in_database": total_jobs,
            },
            "taxonomy_metrics": {
                "tech_stack_distribution": dict(tech_counts.most_common(20)),
                "seniority_distribution": dict(seniority_counts),
                "work_mode_distribution": dict(work_mode_counts),
                "source_distribution": dict(sources_counts),
            },
            "crawler_live_state": autonomous_crawler.get_status(),
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# Global FinTech Fest Decision Maker Mining & Autonomous Outreach Engine
# ═══════════════════════════════════════════════════════════════════════════

class FinTechMineRequest(BaseModel):
    auto_send: bool = True
    max_companies: int = 50
    interval_seconds: int = 3600


@app.post("/api/fintech/mine-decision-makers", tags=["fintech-decision-makers"])
async def trigger_fintech_decision_maker_mining(
    payload: FinTechMineRequest = FinTechMineRequest()
):
    """Triggers autonomous mining of technical & executive decision makers across 150+ FinTech Fest companies."""
    from src.fintech_decision_maker_miner import fintech_miner
    try:
        # Run asynchronous sweep in background
        asyncio.create_task(fintech_miner.run_full_gff_decision_maker_sweep(auto_send=payload.auto_send))
        return {
            "status": "started",
            "message": f"FinTech decision maker mining started in background (Auto-Send: {payload.auto_send}).",
            "recent_events": fintech_miner.recent_events[-5:],
        }
    except Exception as exc:
        log.error("Failed to start decision maker mining: %s", exc, exc_info=True)
        raise APIError(f"Decision maker mining failed: {str(exc)}")


@app.get("/api/fintech/decision-makers", tags=["fintech-decision-makers"])
async def get_mined_fintech_decision_makers(
    limit: int = Query(default=100, ge=1, le=500),
    company: Optional[str] = Query(default=None),
):
    """Returns all discovered decision makers, verified emails, phone numbers, and outreach statuses."""
    db = SessionLocal()
    try:
        q = db.query(Contact).filter(Contact.source == "gff_decision_maker_miner")
        if company:
            q = q.filter(Contact.company.ilike(f"%{company}%"))
        contacts = q.order_by(Contact.id.desc()).limit(limit).all()

        results = []
        for c in contacts:
            sent_record = db.query(OutreachRecord).filter(OutreachRecord.contact_id == c.id).first()
            results.append({
                "id": c.id,
                "name": c.name,
                "title": c.title,
                "company": c.company,
                "email": c.email,
                "category": c.department,
                "linkedin_url": c.linkedin_url,
                "confidence_score": c.confidence_score,
                "source": c.source,
                "found_at": c.found_at.isoformat() if c.found_at else None,
                "outreach_sent": sent_record is not None,
                "outreach_status": sent_record.status if sent_record else "pending",
                "outreach_sent_at": sent_record.sent_at.isoformat() if sent_record and sent_record.sent_at else None,
            })
        return {
            "status": "success",
            "total": len(results),
            "decision_makers": results,
        }
    finally:
        db.close()


@app.post("/api/fintech/auto-outreach", tags=["fintech-decision-makers"])
async def trigger_fintech_auto_outreach(limit: int = Query(default=20, ge=1, le=100)):
    """Dispatches hyper-personalized cold outreach emails to pending discovered decision makers."""
    from src.fintech_decision_maker_miner import fintech_miner, DecisionMakerContact
    db = SessionLocal()
    sent_count = 0
    errors = 0
    try:
        contacts = db.query(Contact).filter(Contact.source == "gff_decision_maker_miner").limit(limit).all()
        for c in contacts:
            already_sent = db.query(OutreachRecord).filter(OutreachRecord.contact_id == c.id).first()
            if not already_sent and c.email:
                dm = DecisionMakerContact(
                    company=c.company,
                    name=c.name,
                    title=c.title or "Engineering Leader",
                    domain=c.company.lower().replace(" ", "") + ".com",
                    email=c.email,
                    linkedin_url=c.linkedin_url,
                )
                subj, text, html = fintech_miner.compose_personalized_outreach(dm)
                loop = asyncio.get_event_loop()
                sent_ok = await loop.run_in_executor(
                    None, lambda: fintech_miner.send_smtp_email(dm.email, subj, text, html)
                )
                if sent_ok:
                    sent_count += 1
                    rec = OutreachRecord(
                        contact_id=c.id,
                        subject=subj,
                        body=text,
                        template_type="fintech_decision_maker_outreach",
                        status="sent",
                        email_sent=True,
                        sent_at=datetime.now(timezone.utc),
                    )
                    db.add(rec)
                    db.commit()
                    await asyncio.sleep(2.0)
                else:
                    errors += 1

        return {
            "status": "success",
            "sent_count": sent_count,
            "errors": errors,
            "total_evaluated": len(contacts),
        }
    finally:
        db.close()


@app.get("/api/fintech/miner-status", tags=["fintech-decision-makers"])
async def get_fintech_miner_status():
    """Returns real-time telemetry, worker state, and event logs for the GFF decision maker engine."""
    from src.fintech_decision_maker_miner import fintech_miner
    return {
        "status": "running" if fintech_miner.is_running else "idle",
        "total_mined": fintech_miner.total_mined,
        "total_emailed": fintech_miner.total_emailed,
        "recent_events": fintech_miner.recent_events[-15:],
    }


# ═══════════════════════════════════════════════════════════════════════════
# Y Combinator & Global Accelerators Sourcing & Decision Maker Outreach
# ═══════════════════════════════════════════════════════════════════════════

class AcceleratorSyncRequest(BaseModel):
    accelerator: Optional[str] = None
    max_jobs: int = 15

class AcceleratorOutreachRequest(BaseModel):
    accelerator: Optional[str] = None
    auto_send: bool = True
    limit: int = 20

@app.get("/api/accelerators/companies", tags=["accelerators"])
async def get_accelerator_companies(
    accelerator: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    stage: Optional[str] = Query(default=None),
):
    """Lists startups from Y Combinator, Surge by Peak XV, Accel Atoms, Antler, Techstars, and Blume Ventures."""
    from src.accelerators_registry import ACCELERATORS_REGISTRY, filter_by_accelerator, filter_by_category
    startups = ACCELERATORS_REGISTRY
    if accelerator:
        startups = filter_by_accelerator(accelerator)
    if category:
        startups = [s for s in startups if category.lower() in s.category.lower()]
    if stage:
        startups = [s for s in startups if stage.lower() in s.stage.lower()]
    return {
        "status": "success",
        "total": len(startups),
        "companies": [s.to_dict() for s in startups],
    }


@app.post("/api/accelerators/sync-jobs", tags=["accelerators"])
async def sync_accelerator_jobs(payload: AcceleratorSyncRequest = AcceleratorSyncRequest()):
    """Concurrently scrapes live engineering opportunities from YC and accelerator startups."""
    from src.accelerators_registry import ACCELERATORS_REGISTRY, filter_by_accelerator
    from src.accelerator_miner import accelerator_miner
    startups = ACCELERATORS_REGISTRY
    if payload.accelerator:
        startups = filter_by_accelerator(payload.accelerator)

    all_jobs = []
    for s in startups:
        jobs = await accelerator_miner.scrape_startup_jobs(s, max_jobs=payload.max_jobs)
        all_jobs.extend(jobs)

    return {
        "status": "success",
        "total_sourced": len(all_jobs),
        "companies_checked": len(startups),
        "jobs": all_jobs[:50],
    }


@app.post("/api/accelerators/mine-and-outreach", tags=["accelerators"])
async def mine_and_outreach_accelerator_startups(payload: AcceleratorOutreachRequest = AcceleratorOutreachRequest()):
    """Mines founders & CTOs across accelerator startups and dispatches cold outreach (strictly <= 2/company)."""
    from src.accelerators_registry import ACCELERATORS_REGISTRY, filter_by_accelerator
    from src.accelerator_miner import accelerator_miner
    startups = ACCELERATORS_REGISTRY
    if payload.accelerator:
        startups = filter_by_accelerator(payload.accelerator)

    total_mined = 0
    all_contacts = []
    for s in startups[:payload.limit]:
        res = await accelerator_miner.mine_and_outreach_startup(s, auto_send=payload.auto_send)
        total_mined += len(res)
        all_contacts.extend(res)

    return {
        "status": "success",
        "companies_processed": min(len(startups), payload.limit),
        "total_leaders_mined": total_mined,
        "contacts": all_contacts,
        "max_per_company_enforced": 2,
    }



@app.get("/api/community-intel/company/{company}", tags=["community-intel"], response_model=CommunityIntelResponse)
async def get_company_community_intel(company: str, role: Optional[str] = "Software Engineer", force_refresh: bool = False, req: Request = None):
    """Retrieves aggregated interview experiences, question leaks, and source citations from Reddit, HN, Medium, Substack, and YouTube."""
    try:
        result = await community_intel_service.get_company_intel(company=company, role=role or "Software Engineer", force_refresh=force_refresh)
        return CommunityIntelResponse(
            status="success",
            company=result.company,
            role_category=result.role_category or "Software Engineering",
            total_sources_scanned=result.total_sources_scanned,
            overall_sentiment=result.overall_sentiment,
            interview_debrief=result.interview_debrief.model_dump(),
            sources=[s.model_dump() for s in result.sources],
            last_updated=result.last_updated,
        )
    except Exception as exc:
        log.error("Failed to fetch community intel for %s: %s", company, exc, exc_info=True)
        raise APIError(f"Community intel fetch failed: {str(exc)}")


@app.post("/api/community-intel/harvest", tags=["community-intel"], response_model=CommunityIntelResponse)
async def harvest_company_community_intel(request: CommunityHarvestRequest, req: Request = None):
    """Triggers an on-demand multi-channel intelligence harvest for a target company."""
    try:
        result = await community_intel_service.get_company_intel(
            company=request.company,
            role=request.role_category or "Software Engineer",
            force_refresh=request.force_refresh,
        )
        return CommunityIntelResponse(
            status="success",
            company=result.company,
            role_category=result.role_category or "Software Engineering",
            total_sources_scanned=result.total_sources_scanned,
            overall_sentiment=result.overall_sentiment,
            interview_debrief=result.interview_debrief.model_dump(),
            sources=[s.model_dump() for s in result.sources],
            last_updated=result.last_updated,
        )
    except Exception as exc:
        log.error("Failed to harvest community intel: %s", exc, exc_info=True)
        raise APIError(f"Community harvest failed: {str(exc)}")


@app.get("/api/jobs/{job_id}/community-intel", tags=["community-intel"], response_model=CommunityIntelResponse)
async def get_job_community_intel(job_id: int, req: Request = None):
    """Retrieves synthesized interview loops and community intel auto-mapped to a specific Job ID."""
    try:
        job = db.get_job(job_id)
        company = (job.get("company") or "Target Company") if job else "Target Company"
        title = (job.get("title") or "Software Engineer") if job else "Software Engineer"
        result = await community_intel_service.get_company_intel(company=company, role=title)
        return CommunityIntelResponse(
            status="success",
            company=result.company,
            role_category=result.role_category or "Software Engineering",
            total_sources_scanned=result.total_sources_scanned,
            overall_sentiment=result.overall_sentiment,
            interview_debrief=result.interview_debrief.model_dump(),
            sources=[s.model_dump() for s in result.sources],
            last_updated=result.last_updated,
        )
    except Exception as exc:
        log.error("Failed to get community intel for job %s: %s", job_id, exc, exc_info=True)
        raise APIError(f"Job community intel failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# AI OSINT Boolean Query Copilot Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/copilot/starters", tags=["copilot"])
async def get_copilot_prompt_starters(req: Request = None):
    """Returns curated starter prompts for discovering unindexed JDs, hiring managers, and salary spreadsheets."""
    return {"status": "success", "starters": copilot_service.get_starters()}


@app.post("/api/copilot/chat", tags=["copilot"], response_model=CopilotChatResponse)
async def copilot_chat_turn(request: CopilotChatRequest, req: Request = None):
    """Executes a multi-turn conversational turn with automated Boolean query synthesis and repository intelligence."""
    try:
        req_obj = ChatTurnRequest(**request.model_dump())
        result = await copilot_service.chat(req_obj)
        return CopilotChatResponse(
            status="success",
            session_id=result.session_id,
            reply=result.reply,
            dorks=[d.model_dump() for d in result.dorks],
            suggested_followups=result.suggested_followups,
            timestamp=result.timestamp,
        )
    except Exception as exc:
        log.error("Copilot chat failed: %s", exc, exc_info=True)
        raise APIError(f"Copilot chat failed: {str(exc)}")


@app.post("/api/copilot/generate-dorks", tags=["copilot"], response_model=CopilotDorksResponse)
async def generate_osint_dorks(request: CopilotDorksRequest, req: Request = None):
    """Generates targeted Google Boolean Dork queries for a specific role and company."""
    try:
        req_obj = DorkGenerateRequest(**request.model_dump())
        result = copilot_service.generate_dorks(req_obj)
        return CopilotDorksResponse(
            status="success",
            total_dorks=result.total_dorks,
            dorks=[d.model_dump() for d in result.dorks],
            timestamp=result.timestamp,
        )
    except Exception as exc:
        log.error("Dork generation failed: %s", exc, exc_info=True)
        raise APIError(f"Dork generation failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# Hiregram Voice AI Mock Interview Integration Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/hiregram/start-session", tags=["hiregram"], response_model=HiregramStartSessionResponse)
async def start_hiregram_session(request: HiregramStartSessionRequest, req: Request = None):
    """Initializes a multi-persona Hiregram live voice mock interview session."""
    try:
        try:
            persona_enum = InterviewerPersona(request.persona or "recruiter_sara")
        except ValueError:
            persona_enum = InterviewerPersona.RECRUITER_SARA

        result = hiregram_service.start_session(
            company=request.company,
            role_title=request.role_title,
            persona=persona_enum,
            job_description=request.job_description,
            candidate_resume_summary=request.candidate_resume_summary,
            total_questions_target=request.total_questions_target or 4,
        )
        return HiregramStartSessionResponse(
            status="success",
            session_id=result["session_id"],
            company=result["company"],
            role_title=result["role_title"],
            persona=result["persona"].value if hasattr(result["persona"], "value") else str(result["persona"]),
            total_questions=result["total_questions"],
            current_turn=result["current_turn"],
        )
    except Exception as exc:
        log.error("Hiregram session initialization failed: %s", exc, exc_info=True)
        raise APIError(f"Hiregram session initialization failed: {str(exc)}")


@app.post("/api/hiregram/submit-turn", tags=["hiregram"], response_model=HiregramSubmitTurnResponse)
async def submit_hiregram_turn(request: HiregramSubmitTurnRequest, req: Request = None):
    """Submits candidate audio/text response, returning speech cadence, STAR critique, and next question."""
    try:
        result = hiregram_service.submit_turn(
            session_id=request.session_id,
            answer_text=request.answer_text,
            duration_seconds=request.duration_seconds or 30.0,
        )
        return HiregramSubmitTurnResponse(
            status="success",
            session_id=result["session_id"],
            evaluated_turn=result["evaluated_turn"],
            next_turn=result["next_turn"],
            is_finished=result["is_finished"],
            current_question_number=result["current_question_number"],
            total_questions=result["total_questions"],
        )
    except KeyError:
        raise ResourceNotFoundError("Hiregram session", request.session_id)
    except Exception as exc:
        log.error("Hiregram turn evaluation failed: %s", exc, exc_info=True)
        raise APIError(f"Hiregram turn evaluation failed: {str(exc)}")


@app.post("/api/hiregram/finalize-session", tags=["hiregram"], response_model=HiregramFinalizeResponse)
async def finalize_hiregram_session(session_id: str, req: Request = None):
    """Finalizes session and generates full Hiregram multi-competency diagnostic scorecard."""
    try:
        scorecard = hiregram_service.finalize_session(session_id=session_id)
        return HiregramFinalizeResponse(
            status="success",
            scorecard=scorecard.model_dump(),
        )
    except KeyError:
        raise ResourceNotFoundError("Hiregram session", session_id)
    except Exception as exc:
        log.error("Hiregram session finalization failed: %s", exc, exc_info=True)
        raise APIError(f"Hiregram session finalization failed: {str(exc)}")


@app.get("/api/hiregram/sessions/{session_id}", tags=["hiregram"], response_model=HiregramFinalizeResponse)
async def get_hiregram_session_scorecard(session_id: str, req: Request = None):
    """Retrieves completed Hiregram scorecard for a session."""
    scorecard = hiregram_service.get_scorecard(session_id=session_id)
    if not scorecard:
        raise ResourceNotFoundError("Hiregram scorecard", session_id)
    return HiregramFinalizeResponse(
        status="success",
        scorecard=scorecard.model_dump(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Personal Autonomous Google AI Fleet Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/fleet/config", tags=["fleet"], response_model=AgentFleetConfigSchema)
async def get_agent_fleet_config(req: Request = None):
    """Retrieves current user's personal Google AI fleet configuration."""
    cfg = agent_fleet_service.get_config()
    return AgentFleetConfigSchema(**cfg.model_dump())


@app.post("/api/fleet/config", tags=["fleet"], response_model=AgentFleetConfigSchema)
async def update_agent_fleet_config(config: AgentFleetConfigSchema, req: Request = None):
    """Updates personal Google AI key and 24/7 autonomous fleet parameters."""
    cfg_obj = AgentFleetConfig(**config.model_dump())
    updated = agent_fleet_service.update_config(cfg_obj)
    return AgentFleetConfigSchema(**updated.model_dump())


@app.post("/api/fleet/run-cycle", tags=["fleet"], response_model=FleetCycleResponseSchema)
async def run_personal_fleet_cycle(config: Optional[AgentFleetConfigSchema] = None, req: Request = None):
    """Triggers an on-demand personal 4-agent autonomous cycle."""
    try:
        cfg_obj = AgentFleetConfig(**config.model_dump()) if config else None
        result = await agent_fleet_service.run_cycle(cfg_obj)
        return FleetCycleResponseSchema(
            status="success",
            cycle=result.model_dump(),
        )
    except Exception as exc:
        log.error("Agent fleet cycle failed: %s", exc, exc_info=True)
        raise APIError(f"Agent fleet cycle failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# Instagram & Threads Referral Automator Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/instagram/search", tags=["instagram"], response_model=InstagramSearchResponseSchema)
async def search_instagram_profiles(request: InstagramSearchRequestSchema, req: Request = None):
    """Discovers tech founders and engineering leaders on Instagram/Threads."""
    try:
        req_obj = InstagramSearchRequest(**request.model_dump())
        result = instagram_referral_service.search_profiles(req_obj)
        return InstagramSearchResponseSchema(
            status="success",
            company=result.company,
            total_found=result.total_found,
            profiles=[p.model_dump() for p in result.profiles],
        )
    except Exception as exc:
        log.error("Instagram profile search failed: %s", exc, exc_info=True)
        raise APIError(f"Instagram profile search failed: {str(exc)}")


@app.post("/api/instagram/generate-message", tags=["instagram"], response_model=InstagramMessageResponseSchema)
async def generate_instagram_dm(request: InstagramMessageRequestSchema, req: Request = None):
    """Synthesizes high-converting casual DMs and story replies with direct intent links."""
    try:
        req_obj = InstagramMessageRequest(**request.model_dump())
        result = instagram_referral_service.generate_message(req_obj)
        return InstagramMessageResponseSchema(
            status="success",
            target_username=result.target_username,
            action_type=result.action_type,
            message=result.message,
            intent_url=result.intent_url,
            character_count=result.character_count,
            timestamp=result.timestamp,
        )
    except Exception as exc:
        log.error("Instagram DM generation failed: %s", exc, exc_info=True)
        raise APIError(f"Instagram DM generation failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# "Proof of Work" Skill-to-Job Bridge Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/skill-bridge/generate-project", tags=["skill-bridge"], response_model=SkillBridgeProjectResponseSchema)
async def generate_proof_of_work_project(request: SkillBridgeProjectRequestSchema, req: Request = None):
    """Generates a 24-hour production-grade micro-project with starter code, test suites, and pitch note."""
    try:
        req_obj = ProjectGenerateRequest(**request.model_dump())
        result = skill_bridge_service.generate_project(req_obj)
        return SkillBridgeProjectResponseSchema(
            status="success",
            company=result.company,
            role_title=result.role_title,
            gap_analysis=result.gap_analysis.model_dump(),
            project_spec=result.project_spec.model_dump(),
            timestamp=result.timestamp,
        )
    except Exception as exc:
        log.error("Skill bridge project generation failed: %s", exc, exc_info=True)
        raise APIError(f"Skill bridge project generation failed: {str(exc)}")


# ═══════════════════════════════════════════════════════════════════════════
# Global Remote USD/EUR Arbitrage & GCC Radar Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/market-radar/opportunities", tags=["market-radar"], response_model=MarketRadarResponseSchema)
async def get_market_radar_opportunities(req: Request = None):
    """Surfaces global remote USD/EUR contracts, PPP multipliers, and top Indian GCC hubs."""
    try:
        result = market_radar_service.get_market_radar()
        return MarketRadarResponseSchema(
            status="success",
            usd_to_inr_rate=result.usd_to_inr_rate,
            eur_to_inr_rate=result.eur_to_inr_rate,
            remote_global_roles=[r.model_dump() for r in result.remote_global_roles],
            top_gcc_hubs=[h.model_dump() for h in result.top_gcc_hubs],
            timestamp=result.timestamp,
        )
    except Exception as exc:
        log.error("Market radar retrieval failed: %s", exc, exc_info=True)
        raise APIError(f"Market radar retrieval failed: {str(exc)}")


# =============================================================================

# Dev entry point
# =============================================================================

if __name__ == "__main__":
    import uvicorn



    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)