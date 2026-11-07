"""
src/tasks.py — NEXUS Celery task queue

Replaces nexus_cron.sh with a parallel, fault-tolerant task system.

Scheduled (Celery Beat):
  refresh_job_catalog    twice daily (CATALOG_REFRESH_HOURS_UTC, default 08:00 + 20:00 IST)
      └── chord(scrape_catalog_query(q) for q in catalog_queries()) → catalog_refresh_done
          Scrape + dedupe into the shared Job table only. Jobify computes each user's
          match % at request time, so nothing here scores, finds contacts, or emails.
  sync_gmail_mailboxes   hourly
  sweep_ghosted_applications   daily 03:15 UTC

  Hard rule (CLAUDE.md §1): no scheduled task may send email or apply anywhere.

Manual only (single-candidate NEXUS flow, scores against data/resume.txt):
  run_full_pipeline  →  `python -m src.tasks pipeline`
      ├── group([scrape_query(q) for q in SCRAPE_QUERIES])  ← parallel
      ├── score_new_jobs          ← keyword-score all new jobs
      ├── run_llm_pipeline        ← full NEXUS DAG on top 15 (dry run, drafts only)
      └── regenerate_tracker      ← write data/applications.md
  send_outreach  →  `python -m src.tasks email`; sends only if AUTO_SEND_EMAILS=true,
                    otherwise it leaves drafts for review (`python -m src.cli drafts`).

Workers: start with
    celery -A src.tasks worker --loglevel=info -c 4
Beat:    start with
    celery -A src.tasks beat   --loglevel=info
Monitor: start with
    celery -A src.tasks flower --port=5555
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from celery import Celery, chain, chord, group
from celery.schedules import crontab
from celery.utils.log import get_task_logger

# ── project root on path ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import settings

log = get_task_logger(__name__)

# ── Redis health check ────────────────────────────────────────────────────────
def _check_redis():
    """Verify Redis is reachable before starting workers."""
    import redis as _redis
    try:
        r = _redis.from_url(settings.redis_url, socket_connect_timeout=5)
        r.ping()
        log.info("✅ Redis connection healthy: %s", settings.redis_url)
    except (_redis.ConnectionError, _redis.TimeoutError) as e:
        log.warning(
            "⚠️  Redis not reachable at %s: %s — tasks will retry on startup",
            settings.redis_url, e,
        )

_check_redis()

# ── Celery app ────────────────────────────────────────────────────────────────
app = Celery(
    "nexus",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

app.conf.update(
    # Suppress Celery 5→6 deprecation warning
    broker_connection_retry_on_startup=True,

    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Reliability
    task_acks_late=True,           # ack only after task completes (safe on crash)
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # one task at a time per worker slot (fair queue)

    # Result TTL
    result_expires=86_400,         # 24 h

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Beat schedule. Never schedule anything that sends email or applies (CLAUDE.md §1);
    # tests/test_catalog_refresh.py enforces this.
    beat_schedule={
        "jobify-catalog-refresh-twice-daily": {
            "task": "src.tasks.refresh_job_catalog",
            "schedule": crontab(minute=str(settings.catalog_refresh_minute),
                                hour=settings.catalog_refresh_hours_utc),
        },
        "jobify-gmail-sync-hourly": {
            "task": "src.tasks.sync_gmail_mailboxes",
            "schedule": crontab(minute="30"),
        },
        "jobify-ghosted-sweep-daily": {
            "task": "src.tasks.sweep_ghosted_applications",
            "schedule": crontab(minute="15", hour="3"),
        },
    },
)

# ── Queries to search across sources ─────────────────────────────────────────
# Defaults for both the manual pipeline and the catalog refresh. Production overrides
# the catalog list with CATALOG_QUERIES (config/profile.yml is personal and not shipped).
SCRAPE_QUERIES = [
    "Senior Python Engineer",
    "Backend Developer FastAPI",
    "Full Stack Developer React Python",
    "Software Development Engineer",
    "Django Developer",
]


def catalog_queries() -> list[str]:
    """CATALOG_QUERIES split on commas, trimmed, de-duplicated (case-insensitive), in order.
    Falls back to SCRAPE_QUERIES when unset or empty."""
    seen: set[str] = set()
    out: list[str] = []
    for q in (settings.catalog_queries or "").split(","):
        q = q.strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out or list(SCRAPE_QUERIES)

# ── helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.run(coro)


def _resume_text() -> str:
    path = ROOT / "data" / "resume.txt"
    return path.read_text() if path.exists() else ""


# =============================================================================
# Tasks
# =============================================================================

@app.task(
    bind=True,
    name="src.tasks.scrape_query",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def scrape_query(self, query: str) -> int:
    """
    Scrape all job sources for a single query and store new results in DB.
    Returns number of new jobs stored.
    Runs in parallel with other scrape_query tasks via group().
    """
    log.info("[scrape] query='%s'", query)
    try:
        stored = _scrape(query)
        log.info("[scrape] query='%s' → %d new jobs stored", query, stored)
        return stored
    except Exception as exc:
        log.error("[scrape] query='%s' failed: %s", query, exc, exc_info=True)
        raise self.retry(exc=exc)


def _scrape(query: str) -> int:
    """Fetch every job source for one query and store new jobs (deduped) in the Job table."""
    from src.job_processor import JobProcessor, ProcessorConfig
    p = JobProcessor(config=ProcessorConfig(auto_send_emails=False))

    async def _go():
        try:
            return await p.fetch_and_store_jobs(query=query) or 0
        finally:
            await p.close()

    return _run(_go())


# ── Shared Jobify job catalog (scheduled twice daily) ─────────────────────────

@app.task(name="src.tasks.scrape_catalog_query", time_limit=900, soft_time_limit=840)
def scrape_catalog_query(query: str) -> dict:
    """One catalog search. Never raises, so one failing query or source can't stop the
    chord callback from running and the rest of the refresh is still recorded."""
    try:
        stored = _scrape(query)
        log.info("[catalog] query='%s' → %d new jobs", query, stored)
        return {"query": query, "stored": stored, "error": None}
    except Exception as exc:  # noqa: BLE001 - reported in the run summary instead
        log.error("[catalog] query='%s' failed: %s", query, exc, exc_info=True)
        return {"query": query, "stored": 0, "error": f"{type(exc).__name__}: {exc}"[:300]}


@app.task(name="src.tasks.catalog_refresh_done")
def catalog_refresh_done(results: list[dict]) -> dict:
    """Chord callback: log one summary line per refresh so a silent failure is visible."""
    results = [r for r in (results or []) if isinstance(r, dict)]
    failed = [r for r in results if r.get("error")]
    summary = {
        "queries": len(results),
        "new_jobs": sum(int(r.get("stored") or 0) for r in results),
        "failed": [{"query": r["query"], "error": r["error"]} for r in failed],
    }
    if results and len(failed) == len(results):
        log.error("[catalog] refresh FAILED for every query: %s", summary)
    else:
        log.info("[catalog] refresh done: %s", summary)
    return summary


@app.task(name="src.tasks.refresh_job_catalog")
def refresh_job_catalog() -> str:
    """Beat entry point (twice daily): scrape every catalog query in parallel into the
    shared Job table. Scrape and store only: no scoring, contact lookup, or email."""
    queries = catalog_queries()
    log.info("[catalog] refresh starting: %d queries", len(queries))
    result = chord(scrape_catalog_query.s(q) for q in queries)(catalog_refresh_done.s())
    return result.id


@app.task(
    bind=True,
    name="src.tasks.score_new_jobs",
    max_retries=2,
    default_retry_delay=30,
)
def score_new_jobs(self, scrape_results=None) -> list[int]:
    """
    Keyword-score all unprocessed jobs instantly.
    Returns list of top-15 job IDs by score (sent to LLM pass next).
    `scrape_results` is the chord result from the scrape group — ignored,
    present only so this can be chained after a group().
    """
    log.info("[score] scoring unprocessed jobs…")
    try:
        from sqlalchemy.exc import IntegrityError
        from src.database import SessionLocal, init_db
        from src.models import Job, Application
        from src.ai.fallback_service import FallbackAIService

        init_db()
        resume = _resume_text()

        async def _go():
            db    = SessionLocal()
            ai    = FallbackAIService()
            unprocessed = (
                db.query(Job)
                .outerjoin(Application, Application.job_id == Job.id)
                .filter(Application.id == None)
                .order_by(Job.id.desc())
                .all()
            )

            if not unprocessed:
                log.info("[score] no new jobs to score")
                db.close()
                return []

            scored: list[tuple[int, float]] = []
            for job in unprocessed:
                skills = await ai.extract_skills(job.description or "")
                match  = await ai.match_resume_to_job(resume, skills)
                score  = match["match_score"]
                try:
                    app = Application(
                        job_id         = job.id,
                        match_score    = score,
                        skills_matched = json.dumps(match["matched_skills"]),
                        skills_missing = json.dumps(match["missing_skills"]),
                        status         = "ready",
                        created_at     = datetime.utcnow(),
                        updated_at     = datetime.utcnow(),
                    )
                    db.add(app)
                    db.commit()
                    scored.append((job.id, score))
                except IntegrityError:
                    db.rollback()

            db.close()
            top = sorted(scored, key=lambda x: x[1], reverse=True)[:15]
            top_ids = [jid for jid, _ in top]
            log.info("[score] scored %d jobs, top %d: %s", len(scored), len(top_ids), top_ids)
            return top_ids

        return _run(_go())
    except Exception as exc:
        log.error("[score] failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    name="src.tasks.run_llm_pipeline",
    max_retries=2,
    default_retry_delay=60,
    # LLM calls can be slow — allow up to 10 min
    time_limit=600,
    soft_time_limit=540,
)
def run_llm_pipeline(self, top_ids: list[int]) -> dict:
    """
    Run the full NEXUS DAG (LLM analysis → contact intel → personalized outreach)
    on the top-scoring jobs. Dry-run mode — drafts outreach, does not send.
    """
    if not top_ids:
        log.info("[llm] no high-scoring jobs — skipping")
        return {"jds": 0, "outreaches": 0}

    log.info("[llm] running NEXUS DAG on %d jobs: %s", len(top_ids), top_ids)
    try:
        from src.database import SessionLocal, init_db
        from src.models import Job
        from src.dag.state import NEXUSState
        from src.dag.nexus_graph import build_nexus_graph

        init_db()

        async def _go():
            db   = SessionLocal()
            jobs = db.query(Job).filter(Job.id.in_(top_ids)).all()
            db.close()

            if not jobs:
                log.warning("[llm] no jobs found for IDs %s", top_ids)
                return {"jds": 0, "outreaches": 0}

            graph = build_nexus_graph()
            state = NEXUSState(
                search_queries     = [],
                resume_path        = str(ROOT / "data" / "resume.txt"),
                dry_run            = True,
                max_jobs_per_query = len(jobs),
                max_jobs_to_tailor = len(jobs),
                max_companies      = 10,
                company_size_hint  = 150,
            )
            state.scraped_jobs = jobs
            result = await graph.run(state)

            summary = {
                "jds":            len(result.jd_analyses),
                "resumes":        len(result.resume_variants),
                "avg_ats":        round(result.avg_ats_score, 1),
                "contacts":       len(result.top_contacts),
                "outreaches":     len(result.personalized_outreaches),
                "avg_outreach":   round(result.avg_personalization_score, 1),
                "runtime_s":      round(sum(result.node_timings_ms.values()) / 1000, 1),
                "errors":         result.errors[:3] if result.errors else [],
            }
            log.info("[llm] done: %s", summary)
            return summary

        return _run(_go())
    except Exception as exc:
        log.error("[llm] failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    name="src.tasks.send_outreach",
    max_retries=2,
    default_retry_delay=60,
    # Sending emails with delays can take a while
    time_limit=1800,
    soft_time_limit=1740,
)
def send_outreach(self, llm_result=None) -> dict:
    """
    Run JobProcessor.process_all_jobs on all status='ready' applications.
    Finds contacts via Hunter/Apollo/GitHub and generates an AI email draft. It sends
    via SMTP only when AUTO_SEND_EMAILS=true (default false = drafts for review).
    Manual only: never add this to the beat schedule or a scheduled chain.
    llm_result is the chained input — ignored.
    """
    log.info("[outreach] starting outreach pass (auto_send=%s)…", settings.auto_send_emails)
    try:
        from src.job_processor import JobProcessor, ProcessorConfig

        cfg = ProcessorConfig(auto_send_emails=settings.auto_send_emails, min_score=50)

        async def _go():
            p = JobProcessor(config=cfg)
            resume = _resume_text()
            await p.process_all_jobs(resume_text=resume, min_score=50)
            await p.close()
            return {
                "emails_sent":   p.metrics.emails_sent,
                "emails_failed": p.metrics.emails_failed,
                "processed":     p.metrics.jobs_processed,
            }

        result = _run(_go())
        log.info("[outreach] done: %s", result)
        return result
    except Exception as exc:
        log.error("[outreach] failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@app.task(
    name="src.tasks.regenerate_tracker",
    max_retries=2,
    default_retry_delay=15,
)
def regenerate_tracker(llm_result=None) -> str:
    """Write data/applications.md. llm_result is the chained input — ignored."""
    log.info("[tracker] regenerating…")
    try:
        from src.database import SessionLocal, init_db
        from src import tracker

        init_db()
        db  = SessionLocal()
        md  = tracker.generate(db=db)
        db.close()

        out = ROOT / "data" / "applications.md"
        out.write_text(md)
        msg = f"Tracker written → {out} ({md.count(chr(10))} lines)"
        log.info("[tracker] %s", msg)
        return msg
    except Exception as exc:
        log.error("[tracker] failed: %s", exc, exc_info=True)
        raise


@app.task(name="src.tasks.run_full_pipeline")
def run_full_pipeline() -> str:
    """
    Single-candidate NEXUS pipeline. Manual only (`python -m src.tasks pipeline`); it
    is not on the beat schedule (production uses refresh_job_catalog).

    Execution graph:
      group(scrape_query × N queries)   ← all run in parallel
        → score_new_jobs                ← chord callback
        → run_llm_pipeline              ← dry run: drafts, never sends
        → regenerate_tracker

    Outreach is deliberately not in this chain: send_outreach is a separate,
    explicit command (CLAUDE.md §1).
    """
    log.info("[pipeline] NEXUS full pipeline starting — %s", datetime.utcnow().isoformat())

    workflow = chain(
        # Step 1: scrape all queries in parallel
        group(scrape_query.s(q) for q in SCRAPE_QUERIES),

        # Step 2: keyword-score all new jobs, return top-15 IDs
        score_new_jobs.s(),

        # Step 3: LLM analysis + contact intel on top matches (dry-run, no send)
        run_llm_pipeline.s(),

        # Step 4: regenerate tracker
        regenerate_tracker.s(),
    )
    result = workflow.apply_async()
    log.info("[pipeline] dispatched, root task id=%s", result.id)
    return result.id


# =============================================================================
# CLI convenience
# =============================================================================

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pipeline"

    if cmd == "catalog":
        print(f"Triggering job catalog refresh ({len(catalog_queries())} queries)…")
        print(f"Dispatched. Task ID: {refresh_job_catalog.delay().id}")

    elif cmd == "email":
        mode = "SEND (AUTO_SEND_EMAILS=true)" if settings.auto_send_emails else "drafts only"
        print(f"Triggering outreach pass for ready applications: {mode}…")
        result = send_outreach.delay()
        print(f"Dispatched. Task ID: {result.id}")
        val = result.get(timeout=1800)
        print(f"Done: {val}")

    elif cmd == "scrape":
        query = sys.argv[2] if len(sys.argv) > 2 else "Senior Python Engineer"
        print(f"Scraping: {query!r}…")
        result = scrape_query.delay(query)
        val = result.get(timeout=120)
        print(f"Stored {val} new jobs")

    else:
        print("Triggering full NEXUS pipeline…")
        task_id = run_full_pipeline.delay()
        print(f"Dispatched. Task ID: {task_id}")
        print("Usage: python -m src.tasks [pipeline|catalog|email|scrape <query>]")


@app.task(name="src.tasks.sweep_ghosted_applications")
def sweep_ghosted_applications() -> int:
    """Jobify board: move cards with no inbound email for 30 days from applied to ghosted."""
    from src.database import SessionLocal
    from src.services.jobify_applications import sweep_ghosted

    with SessionLocal() as db:
        moved = sweep_ghosted(db)
    log.info("[ghosted] moved %d application(s) to ghosted", moved)
    return moved


@app.task(name="src.tasks.sync_gmail_mailboxes")
def sync_gmail_mailboxes() -> dict:
    """Jobify: sync connected Gmail mailboxes whose next_scan_at is due (read-only)."""
    from datetime import datetime
    from src.database import SessionLocal
    from src.models import MailboxAccount
    from src.services import gmail_sync as gs

    if not gs.configured():
        return {"skipped": "gmail not configured"}
    done, failed = 0, 0
    with SessionLocal() as db:
        due = (db.query(MailboxAccount)
               .filter(MailboxAccount.provider == "gmail", MailboxAccount.oauth_refresh_token_enc.isnot(None),
                       MailboxAccount.sync_status.in_(["connected", "failed"]),
                       MailboxAccount.next_scan_at <= datetime.utcnow())
               .all())
        client = gs.get_client()
        for mb in due:
            try:
                gs.sync_mailbox(db, mb, client)
                done += 1
            except gs.GmailError as exc:
                failed += 1
                log.warning("[gmail] mailbox %s sync failed: %s", mb.id, exc.code)
    return {"synced": done, "failed": failed}
