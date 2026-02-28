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
import json
import logging
import logging.handlers
import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session

from src.job_processor import JobProcessor
from src.database import init_db, SessionLocal
from src.models import Application, Job, OutreachRecord
from src.config import settings

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
    from src.contact_finder import ContactFinder, Contact
    _CONTACT_OK = True
except Exception as _e:
    _CONTACT_OK = False
    logging.warning("contact_finder not available: %s", _e)


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
#
# Problem: our code calls process_all_jobs(resume_text, min_score=50)
#          but the on-disk file may only accept (resume_text).
# Solution: inspect the actual live signature and silently drop any kwargs
#           the function doesn't accept. Works with any version on disk.
# =============================================================================

def _call_with_accepted(fn: Any, *args, **kwargs) -> Any:
    """
    Call fn(*args, **kwargs) but drop any kwargs the function won't accept.

    How it works (like explaining to a kid):
      Imagine asking someone "can you do X, Y, and Z?"
      Before asking, we look at their job description.
      If they can't do Z, we just ask for X and Y — no argument, no crash.

    This makes our code work with both old and new versions of any module.
    """
    try:
        sig = inspect.signature(fn)
        params = sig.parameters

        # If the function accepts **kwargs, pass everything through
        has_var_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in params.values()
        )
        if has_var_kw:
            return fn(*args, **kwargs)

        # Otherwise, only pass kwargs that are in the signature
        accepted = set(params.keys())
        safe_kw  = {k: v for k, v in kwargs.items() if k in accepted}

        dropped = set(kwargs) - accepted
        if dropped:
            log.debug(
                "Dropped unsupported kwargs for %s.%s: %s",
                getattr(fn, "__module__", "?"),
                getattr(fn, "__name__", "?"),
                dropped,
            )

        return fn(*args, **safe_kw)

    except (ValueError, TypeError) as exc:
        # Can't introspect — call without extra kwargs as safest fallback
        log.warning("Could not introspect %s, calling without kwargs: %s", fn, exc)
        return fn(*args)


async def _safe_close(obj: Any, name: str = "resource") -> None:
    """
    Close an object whether its .close() is sync or async.
    No crash if the object has no close() method.

    Fixes: 'coroutine was never awaited' RuntimeWarning.
    """
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

class _TN:  # TrieNode, minimal
    __slots__ = ("ch", "path")
    def __init__(self): self.ch: Dict[str, "_TN"] = {}; self.path: Optional[str] = None


class ResumeTrie:
    """
    Maps query keywords → resume file paths.
    O(keyword_length) lookup. Add new variants by editing ROUTES below.
    """
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
    global _state
    log.info("🚀 Booting…")
    init_db()
    log.info("✅ DB ready")

    state = AppState()
    state.load_callbacks()

    # JobProcessor — always needed
    try:
        state.job_processor = JobProcessor()
        sig_params = set(inspect.signature(state.job_processor.process_all_jobs).parameters)
        log.info("✅ JobProcessor ready | process_all_jobs params: %s", sig_params)
    except Exception as exc:
        log.error("❌ JobProcessor failed: %s", exc)

    # EmailOutreach — optional
    if _EMAIL_OK:
        try:
            state.email_outreach = await EmailOutreach.create()
            log.info("✅ EmailOutreach (SMTP pool) ready")
        except Exception as exc:
            log.warning("⚠️  EmailOutreach unavailable: %s", exc)

    # OutreachProcessor — optional
    if _OUTREACH_OK:
        try:
            state.outreach_proc = OutreachProcessor(email_outreach=state.email_outreach)
            await state.outreach_proc.initialise()
            log.info("✅ OutreachProcessor ready")
        except Exception as exc:
            log.warning("⚠️  OutreachProcessor unavailable: %s", exc)

    _state = state
    log.info("🟢 Server ready")

    yield  # ← server runs here

    log.info("🔴 Shutting down…")
    for obj, name in [
        (state.outreach_proc,  "outreach_proc"),
        (state.email_outreach, "email_outreach"),
        (state.job_processor,  "job_processor"),
    ]:
        if obj: await _safe_close(obj, name)
    log.info("👋 Done")


# =============================================================================
# App + middleware
# =============================================================================

app = FastAPI(title="Job Search API", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    """Inject trace_id into every request for log correlation."""
    tid = str(uuid.uuid4())[:8]
    request.state.trace_id = tid
    try:
        resp = await call_next(request)
        resp.headers["X-Trace-ID"] = tid
        return resp
    except Exception as exc:
        log.error("[%s] Unhandled: %s %s — %s", tid, request.method, request.url.path, exc)
        return JSONResponse({"detail": "Internal server error", "trace_id": tid}, status_code=500)


# =============================================================================
# Request models
# =============================================================================

class QueryRequest(BaseModel):
    query: str
    min_score: int = 50

    @validator("query")
    def not_empty(cls, v):
        if not v.strip(): raise ValueError("query cannot be empty")
        return v.strip()

    @validator("min_score")
    def valid_score(cls, v):
        if not 0 <= v <= 100: raise ValueError("min_score must be 0–100")
        return v


class ContactSearchRequest(BaseModel):
    company_name: str
    job_title: Optional[str] = None


class OutreachRequest(BaseModel):
    job_id: int
    contact_email: str
    contact_name: str
    send_immediately: bool = True


class FollowUpRequest(BaseModel):
    outreach_id: int
    follow_up_number: int = 1


# =============================================================================
# Resume reader with cascade fallback
# =============================================================================

def _read_resume(path: str) -> str:
    """
    Read resume. Cascade: routed path → default path → clear error.
    A "helper within a helper" — each level has exactly one job.
    """
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
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "subsystems": {
            "job_processor":   state.job_processor is not None,
            "outreach_proc":   state.outreach_proc is not None,
            "email_outreach":  state.email_outreach is not None,
            "contact_finder":  _CONTACT_OK,
        },
    }


# ── Core pipeline ─────────────────────────────────────────────────────────────

@app.post("/run-query", tags=["jobs"])
async def run_query(
    request: QueryRequest,
    req: Request,
    state: AppState = Depends(get_state),
):
    """
    Full pipeline: fetch → store → pick resume → AI process.

    THE KEY FIX IS HERE:
      _call_with_accepted() checks what kwargs process_all_jobs actually
      accepts on disk right now, and only passes those.
      If the on-disk file has min_score → it's passed.
      If it doesn't → it's silently dropped. No crash either way.
    """
    trace = req.state.trace_id

    if not state.job_processor:
        raise HTTPException(503, "JobProcessor not available — check startup logs")

    # Node 1: fetch + store
    log.info("[%s] Fetching jobs: %s", trace, request.query)
    jobs_count = await state.job_processor.fetch_and_store_jobs(query=request.query)
    log.info("[%s] Stored %d new jobs", trace, jobs_count)

    # Node 2: resume routing via Trie O(k)
    resume_path = state.resume_router.route(request.query)
    log.info("[%s] Resume → %s", trace, resume_path)
    resume_text = _read_resume(resume_path)

    # Node 3: AI processing — signature-safe call
    log.info("[%s] Processing jobs (min_score=%d)", trace, request.min_score)
    result = await _call_with_accepted(
        state.job_processor.process_all_jobs,
        resume_text,
        min_score=request.min_score,  # silently dropped if not in signature
    )
    # Await if process_all_jobs returned a coroutine (it should, but be safe)
    if inspect.isawaitable(result):
        await result

    log.info("[%s] Pipeline complete", trace)
    return {
        "status": "success",
        "trace_id": trace,
        "query": request.query,
        "jobs_fetched": jobs_count,
        "resume_used": resume_path,
        "min_score_requested": request.min_score,
        "min_score_applied": "min_score" in inspect.signature(
            state.job_processor.process_all_jobs
        ).parameters,
    }


# ── Contacts ──────────────────────────────────────────────────────────────────

@app.post("/api/contacts/search", tags=["contacts"])
async def search_contacts(
    request: ContactSearchRequest,
    req: Request,
    state: AppState = Depends(get_state),
):
    trace = req.state.trace_id
    if not _CONTACT_OK:
        raise HTTPException(503, "ContactFinder not available — replace contact_finder.py")
    try:
        finder = ContactFinder()
        contacts = await finder.find_company_contacts(
            request.company_name, request.job_title or ""
        )
        await finder.close()
    except Exception as exc:
        log.error("[%s] Contact search failed: %s", trace, exc)
        raise HTTPException(500, str(exc))

    return {
        "status": "success",
        "trace_id": trace,
        "company": request.company_name,
        "total_contacts": len(contacts),
        "contacts": [
            {"name": c.name, "email": c.email, "title": c.title,
             "company": c.company, "confidence": c.confidence_score}
            for c in contacts
        ],
    }


# ── Outreach ──────────────────────────────────────────────────────────────────

@app.post("/api/outreach/send", tags=["outreach"])
async def send_outreach(
    request: OutreachRequest,
    req: Request,
    state: AppState = Depends(get_state),
):
    trace = req.state.trace_id
    if not state.email_outreach:
        raise HTTPException(503, "Email outreach not available — check SMTP config in startup logs")

    # Load job in its own session
    async with db_session() as db:
        job = db.query(Job).filter(Job.id == request.job_id).first()
        if not job:
            raise HTTPException(404, f"Job {request.job_id} not found")
        job_snap = {
            "id": job.id, "title": job.title, "company": job.company,
            "description": getattr(job, "description", ""),
            "url": getattr(job, "url", ""),
        }

    if not request.send_immediately:
        return {"status": "queued", "trace_id": trace,
                "job_id": request.job_id, "contact_email": request.contact_email}

    # Build minimal Contact object compatible with both old and new Contact dataclass
    contact_kwargs = dict(
        name=request.contact_name, email=request.contact_email,
        title="Hiring Contact", company=job_snap["company"],
    )
    if _CONTACT_OK:
        contact = Contact(**{
            k: v for k, v in contact_kwargs.items()
            if k in inspect.signature(Contact.__init__).parameters
        })
        # Fill any required fields that Contact expects
        for attr, default in [("department", ""), ("linkedin_url", None), ("confidence_score", 80.0)]:
            if not hasattr(contact, attr):
                try: setattr(contact, attr, default)
                except Exception: pass
    else:
        # Fallback: plain object with attributes set directly
        contact = type("Contact", (), contact_kwargs)()

    class _Stub:
        def __init__(self, **kw): [setattr(self, k, v) for k, v in kw.items()]

    success = await state.email_outreach.send_outreach_email(contact, _Stub(**job_snap))

    # Record result — own session
    async with db_session() as db:
        rec = OutreachRecord(
            job_id=job_snap["id"],
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            email_sent=success,
            sent_at=datetime.utcnow() if success else None,
            status="sent" if success else "failed",
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        record_id = rec.id

    log.info("[%s] Outreach %s → %s", trace, "sent" if success else "FAILED",
             request.contact_email)
    return {
        "status": "success" if success else "failed",
        "trace_id": trace,
        "job_id": request.job_id,
        "contact_email": request.contact_email,
        "email_sent": success,
        "outreach_id": record_id,
    }


@app.post("/api/outreach/followup", tags=["outreach"])
async def send_followup(
    request: FollowUpRequest,
    req: Request,
    state: AppState = Depends(get_state),
):
    trace = req.state.trace_id
    if not state.email_outreach:
        raise HTTPException(503, "Email outreach not available")

    async with db_session() as db:
        rec = db.query(OutreachRecord).filter(OutreachRecord.id == request.outreach_id).first()
        if not rec: raise HTTPException(404, f"Outreach {request.outreach_id} not found")
        job = db.query(Job).filter(Job.id == rec.job_id).first()
        if not job: raise HTTPException(404, "Associated job not found")
        snap = {
            "contact_email": rec.contact_email, "contact_name": rec.contact_name,
            "job_id": job.id, "job_title": job.title, "company": job.company,
            "url": getattr(job, "url", ""),
        }

    contact = type("Contact", (), {
        "name": snap["contact_name"], "email": snap["contact_email"],
        "title": "Hiring Contact", "company": snap["company"],
        "department": "", "linkedin_url": None, "confidence_score": 80.0,
    })()

    class _Stub:
        id = snap["job_id"]; title = snap["job_title"]
        company = snap["company"]; url = snap["url"]

    success = await state.email_outreach.send_followup_email(
        contact, _Stub(), follow_up_number=request.follow_up_number
    )

    if success:
        async with db_session() as db:
            r = db.query(OutreachRecord).filter(OutreachRecord.id == request.outreach_id).first()
            if r:
                r.follow_up_count = (getattr(r, "follow_up_count", None) or 0) + 1
                r.last_follow_up_at = datetime.utcnow()
                r.status = "followed_up"
                db.commit()

    return {
        "status": "success" if success else "failed",
        "trace_id": trace,
        "outreach_id": request.outreach_id,
        "follow_up_number": request.follow_up_number,
        "email_sent": success,
    }


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/jobs/pending-outreach", tags=["jobs"])
async def pending_outreach(min_score: int = 50, limit: int = 50):
    from sqlalchemy import and_
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
        return {
            "status": "success", "total_jobs": len(jobs),
            "jobs": [{"id": j.id, "title": j.title, "company": j.company,
                      "location": j.location, "url": j.url, "source": j.source}
                     for j in jobs],
        }


@app.get("/api/stats", tags=["stats"])
async def stats(state: AppState = Depends(get_state)):
    # Fast path: live O(1) counters
    if state.outreach_proc and hasattr(state.outreach_proc, "get_stats"):
        return {"status": "success", "source": "live",
                "stats": state.outreach_proc.get_stats()}

    # Fallback: bounded DB queries
    async with db_session() as db:
        tj = db.query(Job).count()
        ta = db.query(Application).count()
        to = db.query(OutreachRecord).count()
        se = db.query(OutreachRecord).filter(OutreachRecord.email_sent == True).count()
        fu = db.query(OutreachRecord).filter(
            OutreachRecord.follow_up_count > 0).count() if hasattr(
            OutreachRecord, "follow_up_count") else 0
        recent = [
            {"id": r.id, "contact_email": r.contact_email, "status": r.status,
             "sent_at": r.sent_at.isoformat() if r.sent_at else None}
            for r in db.query(OutreachRecord)
                       .order_by(OutreachRecord.sent_at.desc()).limit(5).all()
        ]
    return {
        "status": "success", "source": "db_fallback",
        "stats": {
            "total_jobs": tj, "total_applications": ta,
            "total_outreach_attempts": to, "emails_sent": se,
            "follow_ups_sent": fu,
            "success_rate": round(se / to * 100, 1) if to else 0,
        },
        "recent_outreach": recent,
    }


# ── SignalHire webhook ────────────────────────────────────────────────────────

@app.post("/api/signalhire/callback", tags=["webhooks"])
async def sh_callback(request_data: Any, req: Request,
                      state: AppState = Depends(get_state)):
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
    return {"status": "received", "saved": saved, "total": len(items)}


@app.get("/api/signalhire/results/{linkedin_url:path}", tags=["webhooks"])
async def sh_result(linkedin_url: str, state: AppState = Depends(get_state)):
    r = state.get_cb(linkedin_url)
    return ({"status": "found", "contact": r} if r
            else {"status": "not_found", "message": "No callback yet"})


# =============================================================================
# Dev entry point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)