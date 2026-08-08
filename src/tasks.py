"""
src/tasks.py — NEXUS Celery task queue

Replaces nexus_cron.sh with a parallel, fault-tolerant task system.

Architecture:
  Celery Beat  →  run_full_pipeline  (every 2 hours)
                      │
                      ├── group([scrape_query(q) for q in QUERIES])  ← parallel
                      │       each task: fetch_and_store_jobs for one query
                      │
                      ├── score_new_jobs          ← keyword-score all new jobs
                      │
                      ├── run_llm_pipeline        ← full NEXUS DAG on top 15
                      │
                      └── regenerate_tracker      ← write data/applications.md

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

from celery import Celery, chain, group
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

    # Beat schedule — every 2 hours, on the hour
    beat_schedule={
        "nexus-pipeline-every-2h": {
            "task": "src.tasks.run_full_pipeline",
            "schedule": crontab(minute="0", hour="*/2"),
        },
    },
)

# ── Queries to search across sources ─────────────────────────────────────────
SCRAPE_QUERIES = [
    "Senior Python Engineer",
    "Backend Developer FastAPI",
    "Full Stack Developer React Python",
    "Software Development Engineer",
    "Django Developer",
]

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
        from src.job_processor import JobProcessor, ProcessorConfig
        cfg = ProcessorConfig(auto_send_emails=False)
        p   = JobProcessor(config=cfg)

        async def _go():
            n = await p.fetch_and_store_jobs(query=query)
            await p.close()
            return n or 0

        stored = _run(_go())
        log.info("[scrape] query='%s' → %d new jobs stored", query, stored)
        return stored
    except Exception as exc:
        log.error("[scrape] query='%s' failed: %s", query, exc, exc_info=True)
        raise self.retry(exc=exc)


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
    Finds contacts via Hunter/Apollo/GitHub, generates AI email via Ollama,
    and sends via Gmail SMTP. Rate-limited to avoid spam flags.
    llm_result is the chained input — ignored.
    """
    log.info("[outreach] starting outreach send pass…")
    try:
        from src.job_processor import JobProcessor, ProcessorConfig

        cfg = ProcessorConfig(auto_send_emails=True, min_score=50)

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
    Orchestrator task fired by Celery Beat every 2 hours.

    Execution graph:
      group(scrape_query × N queries)   ← all run in parallel
        → score_new_jobs                ← chord callback
        → run_llm_pipeline
        → regenerate_tracker
    """
    log.info("[pipeline] NEXUS full pipeline starting — %s", datetime.utcnow().isoformat())

    workflow = chain(
        # Step 1: scrape all queries in parallel
        group(scrape_query.s(q) for q in SCRAPE_QUERIES),

        # Step 2: keyword-score all new jobs, return top-15 IDs
        score_new_jobs.s(),

        # Step 3: LLM analysis + contact intel on top matches (dry-run, no send)
        run_llm_pipeline.s(),

        # Step 4: find contacts + send emails via SMTP for all ready applications
        send_outreach.s(),

        # Step 5: regenerate tracker
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

    if cmd == "email":
        print("Triggering outreach send (ready applications)…")
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
        print("Usage: python -m src.tasks [pipeline|email|scrape <query>]")
