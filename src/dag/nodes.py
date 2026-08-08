"""
nodes.py — NEXUS DAG node functions.

Each node is an async function:  async def node(state: NEXUSState) -> None
Nodes mutate state in-place (not return a new state) for efficiency.
All exceptions are caught internally; errors are appended to state.errors
so the pipeline continues (resilient to individual node failures).

Node execution order (see nexus_graph.py for wiring):
  1. scrape_node         — fetch new jobs from all platforms
  2. analyze_jd_node     — JD analysis for each job (batch, concurrent)
  3. tailor_resume_node  — generate tailored PDF per job  ─┐ parallel
     contact_intel_node  — graph-rank contacts per company ─┘
  4. personalize_node    — generate personalized email+cover per contact
  5. outreach_node       — send (or dry-run) outreach emails
  6. feedback_node       — run nightly feedback cycle (patterns + weights)

Each node is designed to be idempotent:
  - Skips jobs already processed in this run (checks state dicts)
  - Caps at max_jobs_to_tailor / max_companies to keep runtime bounded
  - Falls back gracefully if a sub-module is unavailable
"""

from __future__ import annotations

import asyncio
import logging
from typing import List

from .state import NEXUSState

log = logging.getLogger(__name__)


# ── 1. Job Scraping ────────────────────────────────────────────────────────────

async def scrape_node(state: NEXUSState) -> None:
    """
    Fetch new jobs from all configured platforms.
    Writes to: state.scraped_jobs, state.jobs_new_count

    Skip if scraped_jobs is already populated (e.g. injected by cron runner).
    """
    t0 = state.mark_node_start("scrape")
    if state.scraped_jobs:
        log.info("scrape_node: %d jobs pre-loaded — skipping scrape", len(state.scraped_jobs))
        state.mark_node_done("scrape", t0)
        return
    try:
        from src.job_processor import JobProcessor
        from src.database import SessionLocal
        from src.models import Job

        processor = JobProcessor()
        total_new = 0

        # Scrape concurrently (max 3 queries at once to avoid rate limits)
        sem = asyncio.Semaphore(3)

        async def _fetch(query: str) -> int:
            async with sem:
                try:
                    n = await processor.fetch_and_store_jobs(query=query)
                    return n or 0
                except Exception as exc:
                    log.debug("Scrape query '%s': %s", query, exc)
                    return 0

        counts = await asyncio.gather(
            *[_fetch(q) for q in state.search_queries[:6]]
        )
        total_new = sum(counts)
        state.jobs_new_count = total_new

        # Load all pending jobs from DB
        db = SessionLocal()
        try:
            jobs = (
                db.query(Job)
                .filter(Job.description.isnot(None))
                .order_by(Job.fetched_at.desc())
                .limit(state.max_jobs_per_query * len(state.search_queries))
                .all()
            )
            state.scraped_jobs = jobs
        finally:
            db.close()

        await processor.close()
        log.info("scrape_node: %d jobs loaded (%d new)", len(state.scraped_jobs), total_new)
        state.mark_node_done("scrape", t0)

    except Exception as exc:
        state.mark_node_failed("scrape", str(exc), t0)
        log.exception("scrape_node failed: %s", exc)


# ── 2. JD Analysis ────────────────────────────────────────────────────────────

async def analyze_jd_node(state: NEXUSState) -> None:
    """
    Analyze each job's description with JDAnalyzer.
    Writes to: state.jd_analyses  {job_id → JDAnalysis}
    """
    t0 = state.mark_node_start("analyze_jd")
    if not state.scraped_jobs:
        state.mark_node_skipped("analyze_jd")
        return

    try:
        from src.resume_engine.jd_analyzer import JDAnalyzer

        analyzer = JDAnalyzer()
        sem      = asyncio.Semaphore(5)   # max 5 concurrent LLM calls

        async def _analyze(job) -> None:
            async with sem:
                try:
                    jd = await analyzer.analyze(job.description or "")
                    state.jd_analyses[job.id] = jd
                except Exception as exc:
                    log.debug("JD analyze job %d: %s", job.id, exc)

        jobs_to_analyze = state.scraped_jobs[:state.max_jobs_to_tailor * 2]
        await asyncio.gather(*[_analyze(j) for j in jobs_to_analyze])

        log.info("analyze_jd_node: %d JDs analyzed", len(state.jd_analyses))
        state.mark_node_done("analyze_jd", t0)

    except Exception as exc:
        state.mark_node_failed("analyze_jd", str(exc), t0)
        log.exception("analyze_jd_node failed: %s", exc)


# ── 3a. Resume Tailoring ──────────────────────────────────────────────────────

async def tailor_resume_node(state: NEXUSState) -> None:
    """
    Generate a tailored PDF resume for each top job.
    Uses ATS scorer to pick which jobs to tailor (highest coverage gap first).
    Writes to: state.resume_variants  {job_id → ResumeVariant}
    """
    t0 = state.mark_node_start("tailor_resume")
    if not state.jd_analyses:
        state.mark_node_skipped("tailor_resume")
        return

    try:
        from src.resume_engine.resume_engine import get_engine

        engine = get_engine(resume_path=state.resume_path)
        sem    = asyncio.Semaphore(2)   # PDF gen is CPU-ish, keep concurrency low

        # Pick top jobs by number of missing keywords (most room to improve)
        ranked_jobs = sorted(
            [(jid, jd) for jid, jd in state.jd_analyses.items()],
            key=lambda x: len(x[1].critical_keywords),
            reverse=True,
        )[:state.max_jobs_to_tailor]

        async def _tailor(job_id: int, jd) -> None:
            async with sem:
                # Find the job object
                job = next((j for j in state.scraped_jobs if j.id == job_id), None)
                if not job:
                    return
                try:
                    variant = await engine.tailor(
                        jd_text   = job.description or "",
                        job_id    = job_id,
                        job_title = job.title or "",
                        company   = job.company or "",
                    )
                    state.resume_variants[job_id] = variant
                except Exception as exc:
                    log.debug("tailor_resume job %d: %s", job_id, exc)

        await asyncio.gather(*[_tailor(jid, jd) for jid, jd in ranked_jobs])

        if state.resume_variants:
            scores = [v.ats_score for v in state.resume_variants.values()]
            state.avg_ats_score = sum(scores) / len(scores)

        log.info(
            "tailor_resume_node: %d variants (avg ATS %.0f)",
            len(state.resume_variants), state.avg_ats_score
        )
        state.mark_node_done("tailor_resume", t0)

    except Exception as exc:
        state.mark_node_failed("tailor_resume", str(exc), t0)
        log.exception("tailor_resume_node failed: %s", exc)


# ── 3b. Contact Intelligence ──────────────────────────────────────────────────

async def contact_intel_node(state: NEXUSState) -> None:
    """
    For each unique company in scraped jobs, run the contact graph ranker.
    Writes to: state.contact_results, state.top_contacts
    """
    t0 = state.mark_node_start("contact_intel")
    if not state.scraped_jobs:
        state.mark_node_skipped("contact_intel")
        return

    try:
        from src.contact_intelligence.intelligence_engine import get_engine as get_intel

        engine = get_intel()

        # Unique companies from scraped jobs + JD context
        company_specs = {}
        for job in state.scraped_jobs:
            company = (job.company or "").strip()
            if not company or company in company_specs:
                continue
            # Only use domain from URL if it's the company's own site (not a job board)
            url_domain = _domain_from_url(job.url or "")
            JOB_BOARDS = {"adzuna.in", "indeed.com", "linkedin.com", "glassdoor.com",
                          "naukri.com", "monster.com", "ziprecruiter.com", "lever.co",
                          "greenhouse.io", "workable.com", "smartrecruiters.com"}
            domain = "" if url_domain in JOB_BOARDS else url_domain
            jd     = state.jd_analyses.get(job.id)
            company_specs[company] = {
                "company_name":  company,
                "domain":        domain,
                "job_title":     job.title or "",
                "company_size":  state.company_size_hint,
            }

        # Cap to max_companies
        specs = list(company_specs.values())[:state.max_companies]

        # Analyze all companies concurrently
        results = await engine.analyze_batch(specs, concurrency=5)

        for result in results:
            state.contact_results[result.company] = result
            # Collect top 2 contacts per company
            state.top_contacts.extend(result.outreach_order[:2])

        log.info(
            "contact_intel_node: %d companies, %d top contacts",
            len(state.contact_results), len(state.top_contacts)
        )
        state.mark_node_done("contact_intel", t0)

    except Exception as exc:
        state.mark_node_failed("contact_intel", str(exc), t0)
        log.exception("contact_intel_node failed: %s", exc)


# ── 4. Personalization ────────────────────────────────────────────────────────

async def personalize_node(state: NEXUSState) -> None:
    """
    Generate a hyper-personalized email + cover letter for each top contact.
    Writes to: state.personalized_outreaches, state.avg_personalization_score
    """
    t0 = state.mark_node_start("personalize")
    if not state.top_contacts:
        log.info("personalize_node: no contacts — skipping")
        state.mark_node_skipped("personalize")
        return

    try:
        from src.personalization.personalization_engine import get_engine as get_pe

        engine = get_pe()

        # Build contact specs from RankedContact objects
        contact_specs = []
        for rc in state.top_contacts[:20]:   # cap at 20
            # Find a matching job for this company
            company = rc.node.company
            job     = next(
                (j for j in state.scraped_jobs if (j.company or "") == company), None
            )
            jd_text = job.description if job else ""
            jd_analysis = state.jd_analyses.get(job.id) if job else None

            url_domain  = _domain_from_url(getattr(job, "url", "") or "")
            JOB_BOARDS  = {"adzuna.in", "indeed.com", "linkedin.com", "glassdoor.com",
                           "naukri.com", "monster.com", "ziprecruiter.com", "lever.co",
                           "greenhouse.io", "workable.com", "smartrecruiters.com"}
            job_domain  = "" if url_domain in JOB_BOARDS else url_domain
            # Prefer the email domain (already discovered by contact_intel) over URL guess
            email_domain = rc.email.split("@")[1] if rc.email and "@" in rc.email else ""
            domain = email_domain or job_domain

            contact_specs.append({
                "name":    rc.name,
                "email":   rc.email,
                "company": company,
                "domain":  domain,
                "jd_text": jd_text,
                "job_title": rc.title or (job.title if job else ""),
            })

        outreaches = await engine.batch_personalize(
            contacts   = contact_specs,
            jd_text    = "",   # per-contact jd_text passed in spec
            concurrency = 5,
        )

        state.personalized_outreaches = outreaches
        if outreaches:
            scores = [o.personalization_score for o in outreaches]
            state.avg_personalization_score = sum(scores) / len(scores)

        log.info(
            "personalize_node: %d outreaches (avg score %.0f)",
            len(outreaches), state.avg_personalization_score
        )
        state.mark_node_done("personalize", t0)

    except Exception as exc:
        state.mark_node_failed("personalize", str(exc), t0)
        log.exception("personalize_node failed: %s", exc)


# ── 5. Outreach ───────────────────────────────────────────────────────────────

async def outreach_node(state: NEXUSState) -> None:
    """
    Send (or dry-run) personalized emails via OutreachOrchestrator.
    Writes to: state.outreach_results, state.emails_sent, state.emails_skipped
    """
    t0 = state.mark_node_start("outreach")
    if not state.personalized_outreaches:
        log.info("outreach_node: no personalized outreaches — skipping")
        state.mark_node_skipped("outreach")
        state.route_decision = "skip_feedback"
        return

    try:
        if state.dry_run:
            _save_drafts(state.personalized_outreaches)
            skipped = len(state.personalized_outreaches)
            log.info("outreach_node: %d drafts saved to data/outreach_queue.json", skipped)
            state.emails_skipped = skipped
            state.route_decision = "skip_feedback"
            state.mark_node_done("outreach", t0)
            return

        # NOTE: real (non-dry-run) sending through OutreachOrchestrator is not
        # wired up yet. OutreachOrchestrator.orchestrate()/_send_one() build
        # their own subject line via A/B testing and don't accept the
        # already-personalized outreach.email.subject/body/cover_letter this
        # node has — routing through them as-is would silently discard the
        # personalization that personalize_node just produced. This used to
        # call a nonexistent `orchestrator.send_one(...)` method, which threw
        # AttributeError on every contact and was swallowed by the broad
        # except block below (logged at .debug, so effectively invisible).
        # Failing loudly here instead of pretending to work until
        # OutreachOrchestrator supports sending pre-built content directly.
        raise NotImplementedError(
            "outreach_node non-dry-run sending is not implemented — "
            "OutreachOrchestrator needs a send method that accepts pre-built "
            "subject/body/cover_letter instead of generating its own via A/B "
            "testing. See comment above. Real outreach sending currently "
            "happens via job_processor.py through the Celery beat schedule."
        )

    except Exception as exc:
        state.mark_node_failed("outreach", str(exc), t0)
        log.exception("outreach_node failed: %s", exc)
        state.route_decision = "skip_feedback"


# ── 6. Feedback ───────────────────────────────────────────────────────────────

async def feedback_node(state: NEXUSState) -> None:
    """
    Run the feedback analysis cycle to update pipeline weights.
    Writes to: state.feedback_snapshot, state.recommendations
    """
    t0 = state.mark_node_start("feedback")
    try:
        from src.feedback.feedback_loop import get_loop

        loop     = get_loop()
        snapshot = await loop.run_once(metrics_window=7, pattern_window=30)

        state.feedback_snapshot  = snapshot
        state.recommendations    = snapshot.recommendations

        log.info(
            "feedback_node: %d patterns, %d recommendations",
            len(snapshot.patterns), len(snapshot.recommendations)
        )
        state.mark_node_done("feedback", t0)

    except Exception as exc:
        state.mark_node_failed("feedback", str(exc), t0)
        log.exception("feedback_node failed: %s", exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _domain_from_url(url: str) -> str:
    """Extract domain from a job posting URL."""
    import re
    m = re.search(r"https?://(?:www\.)?([^/]+)", url or "")
    if m:
        host  = m.group(1)
        parts = host.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
    return ""


def _save_drafts(outreaches: list) -> None:
    """
    Append dry-run outreach drafts to data/outreach_queue.json.
    Each draft gets a unique ID and 'pending' status for manual review.
    """
    import json, uuid
    from datetime import datetime
    from pathlib import Path

    queue_path = Path("data/outreach_queue.json")
    queue_path.parent.mkdir(exist_ok=True)

    # Load existing queue
    existing: list = []
    if queue_path.exists():
        try:
            existing = json.loads(queue_path.read_text())
        except Exception:
            existing = []

    now = datetime.utcnow().isoformat()
    new_drafts = []
    for o in outreaches:
        draft = {
            "id":                   str(uuid.uuid4())[:8],
            "status":               "pending",          # pending | approved | sent | skipped
            "created_at":           now,
            "contact_name":         o.contact_name,
            "contact_email":        getattr(o, "contact_email", ""),
            "company":              o.company,
            "personalization_score": o.personalization_score,
            "subject":              o.email.subject,
            "body":                 o.email.body,
            "subject_variants":     getattr(o.email, "subject_variants", []),
            "cover_letter":         getattr(o, "cover_letter", ""),
        }
        new_drafts.append(draft)

    queue_path.write_text(json.dumps(existing + new_drafts, indent=2))
    log.info("_save_drafts: saved %d drafts → %s", len(new_drafts), queue_path)
