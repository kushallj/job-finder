"""
outreach_orchestrator.py — Multi-Channel Outreach Orchestration Engine.

This is the single entry point for all outreach operations.
It wires together the six sub-components in the src/outreach/ package:

  SmartSendTimer       — timezone-aware optimal send windows
  DomainRateLimiter    — global daily + per-domain weekly caps
  ABTestManager        — subject line A/B testing
  SentimentClassifier  — reply sentiment analysis
  ReplyDetector        — IMAP polling for replies
  FollowUpScheduler    — Day-5/12/21 follow-up sequences

DAG node contract (for LangGraph integration):
  Input state:  {"contacts": List[Contact], "jobs": List[Job]}
  Output state: {"outreach_results": List[OutreachResult]}
  Side effects: DB writes, emails sent, background tasks started

Concurrency model:
  AsyncIO    — HTTP, DNS, SMTP I/O (all outreach sending)
  Threads    — IMAP polling (ReplyDetector uses ThreadPoolExecutor)
  Semaphore  — max 10 outreach sends in-flight simultaneously
  TokenBucket— per-domain + global rate limits (DomainRateLimiter)

Architecture diagram:
  ┌─────────────────────────────────────────────────────────────────┐
  │                   OutreachOrchestrator                          │
  │                                                                 │
  │  orchestrate(jobs, contacts)                                    │
  │       │                                                         │
  │       ├── rate_limiter.check()    ← DomainRateLimiter          │
  │       ├── smart_timer.seconds_until_optimal() → schedule delay  │
  │       ├── ab_manager.best_variant() → subject line             │
  │       ├── email_outreach.send_email()                           │
  │       │       └── rate_limiter.consume()                        │
  │       │       └── ab_manager.record_send()                      │
  │       │       └── followup_scheduler.schedule_initial_followup()│
  │       │                                                         │
  │  [background tasks]:                                            │
  │       ├── FollowUpScheduler._scheduler_loop()                   │
  │       └── ReplyDetector._poll_loop()                            │
  └─────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from src.contact_finder import Contact
from src.database import SessionLocal
from src.email_outreach import EmailOutreach, OutreachConfig
from src.models import OutreachRecord

from src.outreach.ab_test import ABTestManager
from src.outreach.domain_rate_limiter import DomainRateLimiter
from src.outreach.followup_scheduler import FollowUpScheduler
from src.outreach.reply_detector import ReplyDetector
from src.outreach.sentiment import SentimentClassifier
from src.outreach.smart_timer import SmartSendTimer

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class OutreachResult:
    contact_email: str
    contact_name:  str
    company:       str
    job_title:     str
    status:        str          # "sent" | "skipped" | "rate_limited" | "failed"
    reason:        str = ""     # populated on skip/fail
    subject:       str = ""
    ab_variant:    int = 0
    scheduled_at:  str = ""     # ISO datetime if delayed by SmartTimer


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class OutreachOrchestrator:
    """
    Main orchestration engine for multi-channel outreach.

    Instantiate once (e.g., in FastAPI lifespan), keep alive for the process.
    Call `await orchestrate(contacts, jobs)` to send outreach.
    Call `await start_background_tasks()` to start follow-up + reply detection.
    """

    MAX_CONCURRENT_SENDS = 10

    def __init__(
        self,
        dry_run:                bool = False,
        global_daily_limit:     Optional[int] = None,  # None = auto (50 SMTP, 2000 SG/SES)
        domain_weekly_limit:    int  = 3,
        ab_db_path:             Optional[str] = "ab_stats.db",
        followup_poll_interval: int  = 1800,
        reply_poll_interval:    int  = 1800,
        smart_timing:           bool = True,
    ):
        self._dry_run = dry_run

        # EmailOutreach config (needed for provider-aware daily limit)
        config = OutreachConfig()
        self._email_outreach = EmailOutreach(cfg=config)

        # Auto daily limit: 50 for Gmail SMTP, 2000 for SendGrid/SES
        resolved_daily_limit = global_daily_limit if global_daily_limit is not None \
            else config.global_daily_limit

        # Sub-components
        self._rate_limiter  = DomainRateLimiter(
            global_daily_limit  = resolved_daily_limit,
            domain_weekly_limit = domain_weekly_limit,
        )
        self._ab_manager    = ABTestManager(db_path=ab_db_path)
        self._smart_timer   = SmartSendTimer() if smart_timing else None
        self._sentiment     = SentimentClassifier(use_llm=True)

        # Background task components
        self._followup_scheduler = FollowUpScheduler(
            db_session_factory  = SessionLocal,
            email_outreach      = self._email_outreach,
            rate_limiter        = self._rate_limiter,
            smart_timer         = self._smart_timer,
            ab_test_manager     = self._ab_manager,
            poll_interval_secs  = followup_poll_interval,
        )
        self._reply_detector = ReplyDetector(
            db_session_factory  = SessionLocal,
            sentiment_classifier= self._sentiment,
            poll_interval_secs  = reply_poll_interval,
        )

        self._send_sem = asyncio.Semaphore(self.MAX_CONCURRENT_SENDS)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start_background_tasks(self) -> None:
        """
        Start the follow-up scheduler and reply detector as background tasks.
        Call this once after the process starts (e.g., in FastAPI lifespan).
        """
        await self._followup_scheduler.start()
        await self._reply_detector.start()
        log.info("OutreachOrchestrator background tasks started (dry_run=%s)", self._dry_run)

    async def stop_background_tasks(self) -> None:
        await self._followup_scheduler.stop()
        await self._reply_detector.stop()
        if self._smart_timer:
            await self._smart_timer.close()
        log.info("OutreachOrchestrator background tasks stopped")

    # ── Main orchestration entry point ────────────────────────────────────────

    async def orchestrate(
        self,
        contacts:  List[Contact],
        job_title: str,
        job_url:   str  = "",
        job_id:    Optional[int] = None,
        dry_run:   Optional[bool] = None,
    ) -> List[OutreachResult]:
        """
        Send outreach to a list of contacts for a given job.

        Selects best contact(s), applies rate limiting, smart timing,
        A/B subject selection, sends email, schedules follow-ups.

        Args:
            contacts:  Ranked list of Contact objects (highest confidence first)
            job_title: Job title string
            job_url:   Job posting URL
            job_id:    DB job ID (for linking OutreachRecord)
            dry_run:   Override instance dry_run setting

        Returns:
            List of OutreachResult (one per contact attempted)
        """
        effective_dry_run = dry_run if dry_run is not None else self._dry_run
        results: List[OutreachResult] = []

        # Run sends concurrently (bounded by semaphore)
        tasks = [
            asyncio.create_task(
                self._send_one(
                    contact=c,
                    job_title=job_title,
                    job_url=job_url,
                    job_id=job_id,
                    dry_run=effective_dry_run,
                )
            )
            for c in contacts
            if c.email  # skip contacts without email
        ]

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in raw_results:
            if isinstance(r, OutreachResult):
                results.append(r)
            elif isinstance(r, Exception):
                log.error("Outreach task error: %s", r)

        sent    = sum(1 for r in results if r.status == "sent")
        skipped = sum(1 for r in results if r.status != "sent")
        log.info(
            "Orchestration complete for '%s': sent=%d skipped=%d",
            job_title, sent, skipped,
        )
        return results

    # ── Single contact send ───────────────────────────────────────────────────

    async def _send_one(
        self,
        contact:   Contact,
        job_title: str,
        job_url:   str,
        job_id:    Optional[int],
        dry_run:   bool,
    ) -> OutreachResult:
        async with self._send_sem:
            email = contact.email or ""
            name  = contact.name  or "there"

            # ── Rate limit check ──────────────────────────────────────────────
            allowed, reason = await self._rate_limiter.check(email)
            if not allowed:
                log.debug("Rate limited: %s — %s", email, reason)
                return OutreachResult(
                    contact_email=email,
                    contact_name=name,
                    company=contact.company,
                    job_title=job_title,
                    status="rate_limited",
                    reason=reason,
                )

            # ── Smart timing ──────────────────────────────────────────────────
            scheduled_at = ""
            if self._smart_timer and "@" in email:
                domain = email.split("@")[1]
                delay  = await self._smart_timer.seconds_until_optimal(domain)
                if delay > 0:
                    scheduled_at = (
                        datetime.now(timezone.utc)
                        .__add__(__import__("datetime").timedelta(seconds=delay))
                        .isoformat()
                    )
                    if delay > 3600 * 4:  # more than 4h → log and still send
                        log.info(
                            "SmartTimer: %s optimal window in %.1fh — sending anyway (background mode)",
                            email, delay / 3600,
                        )
                    else:
                        log.debug("SmartTimer: waiting %.0fs for optimal window for %s", delay, email)
                        await asyncio.sleep(delay)

            # ── A/B subject selection ─────────────────────────────────────────
            template_type = (
                "engineering_manager"
                if any(k in (contact.title or "").lower() for k in ("engineer", "cto", "vp", "tech"))
                else "hr_outreach"
            )
            variant_idx, subject = self._ab_manager.best_variant(
                template_type,
                company=contact.company or "",
                skill="Python",     # TODO: pull from job skills when Task 2 is built
            )

            # ── Send ──────────────────────────────────────────────────────────
            if dry_run:
                log.info(
                    "[DRY-RUN] Would send to %s | subject: %s | template: %s",
                    email, subject, template_type,
                )
                return OutreachResult(
                    contact_email=email,
                    contact_name=name,
                    company=contact.company,
                    job_title=job_title,
                    status="sent",
                    reason="dry_run",
                    subject=subject,
                    ab_variant=variant_idx,
                    scheduled_at=scheduled_at,
                )

            try:
                await self._email_outreach.send_email(
                    contact=contact,
                    subject=subject,
                    body=self._build_body(contact, job_title, template_type),
                    job_title=job_title,
                    job_url=job_url,
                    template_type=template_type,
                    attach_resume=True,
                )

                # Consume rate limit token
                await self._rate_limiter.consume(email)

                # Record A/B send
                self._ab_manager.record_send(template_type, variant_idx)

                # Persist OutreachRecord + schedule follow-up
                self._persist_and_schedule(
                    contact=contact,
                    job_id=job_id,
                    subject=subject,
                    template_type=template_type,
                    ab_variant=variant_idx,
                )

                return OutreachResult(
                    contact_email=email,
                    contact_name=name,
                    company=contact.company,
                    job_title=job_title,
                    status="sent",
                    subject=subject,
                    ab_variant=variant_idx,
                    scheduled_at=scheduled_at,
                )

            except Exception as e:
                log.error("Send failed for %s: %s", email, e)
                return OutreachResult(
                    contact_email=email,
                    contact_name=name,
                    company=contact.company,
                    job_title=job_title,
                    status="failed",
                    reason=str(e),
                    subject=subject,
                    ab_variant=variant_idx,
                )

    # ── DB persistence ────────────────────────────────────────────────────────

    def _persist_and_schedule(
        self,
        contact:       Contact,
        job_id:        Optional[int],
        subject:       str,
        template_type: str,
        ab_variant:    int,
    ) -> None:
        """Write OutreachRecord to DB and schedule follow-up."""
        db = SessionLocal()
        try:
            record = OutreachRecord(
                job_id        = job_id,
                subject       = subject,
                template_type = template_type,
                status        = "sent",
                sent_at       = datetime.now(timezone.utc),
                email_sent    = True,
                contact_email = contact.email,
                contact_name  = contact.name,
            )
            # Optional new columns (safe to set regardless)
            if hasattr(record, "ab_variant"):
                record.ab_variant = ab_variant

            db.add(record)
            db.flush()   # get record.id before commit

            # Schedule follow-up
            FollowUpScheduler.schedule_initial_followup(record, db)

            db.commit()
            log.debug("Persisted OutreachRecord id=%d for %s", record.id, contact.email)

        except Exception as e:
            db.rollback()
            log.error("Failed to persist OutreachRecord for %s: %s", contact.email, e)
        finally:
            db.close()

    # ── Email body builder ────────────────────────────────────────────────────

    @staticmethod
    def _build_body(contact: Contact, job_title: str, template_type: str) -> str:
        name    = (contact.name or "").split()[0] if contact.name else "there"
        company = contact.company or "your company"

        # Get sender name from config
        try:
            from src.config import settings as _s
            sender_name = getattr(_s, "sender_name", "The Candidate") or "The Candidate"
        except Exception:
            sender_name = "The Candidate"

        if template_type == "engineering_manager":
            return (
                f"Hi {name},\n\n"
                f"I came across an opening at {company} for a {job_title} role and "
                f"wanted to reach out directly.\n\n"
                f"I've been building production systems — distributed backends, APIs, "
                f"and data pipelines — and I'm genuinely excited about the work your "
                f"engineering team is doing.\n\n"
                f"Would you be open to a 15-minute conversation? "
                f"Happy to share more about my background and what I could bring to the team.\n\n"
                f"Best,\n{sender_name}"
            )
        else:
            return (
                f"Hi {name},\n\n"
                f"I noticed {company} is hiring for a {job_title} role and would love "
                f"to be considered.\n\n"
                f"I'm a software engineer with hands-on experience in backend development, "
                f"APIs, and data systems. I've attached my resume for your reference.\n\n"
                f"Would it be possible to connect briefly this week?\n\n"
                f"Thank you for your time,\n{sender_name}"
            )

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "rate_limiter":       self._rate_limiter.stats(),
            "ab_test":            self._ab_manager.summary(),
            "followup_scheduler": self._followup_scheduler.stats(),
        }
