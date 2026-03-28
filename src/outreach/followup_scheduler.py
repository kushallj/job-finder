"""
followup_scheduler.py — Async background scheduler for follow-up sequences.

Sequence (configurable):
  Day 0:  Initial outreach (handled by OutreachOrchestrator)
  Day 5:  Follow-up 1 — gentle check-in ("wanted to make sure this didn't slip")
  Day 12: Follow-up 2 — new angle / value add
  Day 21: Final follow-up — closing the loop ("last note from me")

Rules:
  - Skip if OutreachRecord.replied_at is set (they already replied)
  - Skip if follow_up_count >= MAX_FOLLOWUPS (3 by default)
  - Skip if status == "bounced" or "unsubscribed"
  - Respect DomainRateLimiter (no token = skip this cycle, retry next poll)
  - Send using existing EmailOutreach (reuses all SMTP infrastructure)

Design:
  - Runs as an asyncio background task (started by OutreachOrchestrator)
  - Polls DB every `poll_interval_secs` for overdue follow-ups
  - Uses `follow_up_scheduled` column (set on initial send = Day 0 + 5 days)
  - After each send: increments follow_up_count, sets next follow_up_scheduled
  - Bounded concurrency: asyncio.Semaphore(5) — max 5 follow-ups in flight
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# Follow-up schedule: (follow_up_count_before_this_send → days_since_last_send)
FOLLOWUP_SCHEDULE = [
    (0, 5),    # First follow-up: 5 days after initial
    (1, 7),    # Second follow-up: 7 days after first
    (2, 9),    # Final follow-up: 9 days after second
]
MAX_FOLLOWUPS = len(FOLLOWUP_SCHEDULE)

# Templates to use for each follow-up number
FOLLOWUP_TEMPLATES = [
    "follow_up_1",
    "follow_up_2",
    "follow_up_final",
]

# Statuses that disqualify from follow-up
SKIP_STATUSES = {"replied", "bounced", "unsubscribed", "dead"}


class FollowUpScheduler:
    """
    Background task that monitors the DB and sends scheduled follow-ups.

    Usage:
        scheduler = FollowUpScheduler(db_factory, email_outreach, rate_limiter)
        await scheduler.start()
        # runs forever in background
        await scheduler.stop()
    """

    def __init__(
        self,
        db_session_factory,
        email_outreach,                     # EmailOutreach instance
        rate_limiter=None,                  # DomainRateLimiter (optional)
        smart_timer=None,                   # SmartSendTimer (optional)
        ab_test_manager=None,               # ABTestManager (optional)
        poll_interval_secs: int = 1800,     # 30 minutes
        max_concurrent: int = 5,
    ):
        self._db_factory    = db_session_factory
        self._outreach      = email_outreach
        self._rate_limiter  = rate_limiter
        self._smart_timer   = smart_timer
        self._ab_manager    = ab_test_manager
        self._poll_interval = poll_interval_secs
        self._sem           = asyncio.Semaphore(max_concurrent)
        self._task: Optional[asyncio.Task] = None
        self._running = False

        # Stats
        self._sent_total  = 0
        self._skip_total  = 0
        self._error_total = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop(), name="followup_scheduler")
        log.info("FollowUpScheduler started (interval=%ds)", self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info(
            "FollowUpScheduler stopped. sent=%d skipped=%d errors=%d",
            self._sent_total, self._skip_total, self._error_total,
        )

    def stats(self) -> dict:
        return {
            "sent":   self._sent_total,
            "skipped": self._skip_total,
            "errors": self._error_total,
        }

    # ── Scheduler loop ────────────────────────────────────────────────────────

    async def _scheduler_loop(self) -> None:
        while self._running:
            try:
                overdue = self._fetch_overdue_records()
                if overdue:
                    log.info("Found %d overdue follow-ups", len(overdue))
                    tasks = [
                        asyncio.create_task(self._process_record(record_id))
                        for record_id in overdue
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error("Follow-up scheduler error: %s", e, exc_info=True)
            await asyncio.sleep(self._poll_interval)

    # ── DB polling ────────────────────────────────────────────────────────────

    def _fetch_overdue_records(self) -> List[int]:
        """
        Query for OutreachRecords where:
          - follow_up_scheduled <= now
          - follow_up_sent = False (or None)
          - replied_at IS NULL
          - status NOT IN SKIP_STATUSES
          - follow_up_count < MAX_FOLLOWUPS
        Returns list of record IDs.
        """
        from src.models import OutreachRecord

        now = datetime.now(timezone.utc)
        db: Session = self._db_factory()
        try:
            records = (
                db.query(OutreachRecord.id)
                .filter(
                    OutreachRecord.follow_up_scheduled <= now,
                    OutreachRecord.follow_up_sent.is_(False),
                    OutreachRecord.replied_at.is_(None),
                    OutreachRecord.follow_up_count < MAX_FOLLOWUPS,
                    ~OutreachRecord.status.in_(SKIP_STATUSES),
                )
                .all()
            )
            return [r.id for r in records]
        except Exception as e:
            log.error("Failed to fetch overdue records: %s", e)
            return []
        finally:
            db.close()

    # ── Per-record processing ─────────────────────────────────────────────────

    async def _process_record(self, record_id: int) -> None:
        async with self._sem:
            from src.models import OutreachRecord, Job, Contact

            db: Session = self._db_factory()
            try:
                record = db.query(OutreachRecord).get(record_id)
                if not record:
                    return

                # Re-check conditions (may have changed since fetch)
                if (
                    record.replied_at
                    or record.follow_up_count >= MAX_FOLLOWUPS
                    or record.status in SKIP_STATUSES
                ):
                    self._skip_total += 1
                    return

                contact_email = record.contact_email or ""
                contact_name  = record.contact_name  or "there"

                # Rate limiter check
                if self._rate_limiter:
                    allowed, reason = await self._rate_limiter.check(contact_email)
                    if not allowed:
                        log.debug("Rate limited follow-up to %s: %s", contact_email, reason)
                        self._skip_total += 1
                        return

                # Smart timing — compute delay
                delay = 0.0
                if self._smart_timer and "@" in contact_email:
                    domain = contact_email.split("@")[1]
                    delay  = await self._smart_timer.seconds_until_optimal(domain)
                    if delay > 3600:   # more than 1 hour → reschedule, don't wait inline
                        log.debug(
                            "Follow-up to %s deferred %.1fh by SmartTimer",
                            contact_email, delay / 3600,
                        )
                        self._skip_total += 1
                        return

                if delay > 0:
                    await asyncio.sleep(delay)

                # Build follow-up email
                follow_up_num    = record.follow_up_count  # 0, 1, 2
                template_type    = FOLLOWUP_TEMPLATES[min(follow_up_num, len(FOLLOWUP_TEMPLATES) - 1)]
                original_subject = record.subject or ""

                # Get A/B variant for subject
                variant_idx = 0
                subject     = f"Re: {original_subject}"
                if self._ab_manager:
                    job = db.query(Job).get(record.job_id) if record.job_id else None
                    company = job.company if job else ""
                    variant_idx, ab_subject = self._ab_manager.best_variant(
                        template_type, company=company, skill=""
                    )
                    subject = ab_subject or subject

                # Build body
                body = self._build_followup_body(
                    follow_up_num=follow_up_num,
                    contact_name=contact_name,
                    original_subject=original_subject,
                )

                # Send
                from src.contact_finder import Contact as ContactData
                contact_data = ContactData(
                    name=contact_name,
                    title="",
                    email=contact_email,
                    company="",
                )

                try:
                    await self._outreach.send_email(
                        contact=contact_data,
                        subject=subject,
                        body=body,
                        job_title=original_subject,
                        job_url="",
                        template_type=template_type,
                        attach_resume=False,    # no resume on follow-ups
                    )

                    # Consume rate limit token
                    if self._rate_limiter:
                        await self._rate_limiter.consume(contact_email)

                    # Record A/B send
                    if self._ab_manager:
                        self._ab_manager.record_send(template_type, variant_idx)
                        if hasattr(record, "ab_variant"):
                            record.ab_variant = variant_idx

                    # Update record
                    now = datetime.now(timezone.utc)
                    record.follow_up_count    += 1
                    record.last_follow_up_at   = now
                    record.follow_up_sent      = True

                    # Schedule next follow-up if any remain
                    next_count = record.follow_up_count
                    if next_count < MAX_FOLLOWUPS:
                        days_until_next = FOLLOWUP_SCHEDULE[next_count][1]
                        record.follow_up_scheduled = now + timedelta(days=days_until_next)
                        record.follow_up_sent      = False    # reset for next round

                    db.commit()
                    self._sent_total += 1
                    log.info(
                        "Follow-up #%d sent to %s (template=%s)",
                        follow_up_num + 1, contact_email, template_type,
                    )

                except Exception as e:
                    self._error_total += 1
                    log.error("Failed to send follow-up to %s: %s", contact_email, e)

            except Exception as e:
                log.error("Error processing record %d: %s", record_id, e, exc_info=True)
            finally:
                db.close()

    # ── Email body templates ──────────────────────────────────────────────────

    @staticmethod
    def _build_followup_body(
        follow_up_num: int,
        contact_name: str,
        original_subject: str,
    ) -> str:
        name = contact_name.split()[0] if contact_name and contact_name.lower() != "there" else "there"

        if follow_up_num == 0:
            return (
                f"Hi {name},\n\n"
                f"I wanted to follow up on my note about {original_subject} — "
                f"I just wanted to make sure it didn't get buried.\n\n"
                f"I'm genuinely excited about the possibility of contributing to your team. "
                f"Would you have 15 minutes this week for a quick chat?\n\n"
                f"Best,\nKushall"
            )
        elif follow_up_num == 1:
            return (
                f"Hi {name},\n\n"
                f"I'm circling back one more time. I know inboxes get busy.\n\n"
                f"Since my last note, I've been thinking about how my background could "
                f"specifically help with your engineering challenges. "
                f"I'd love to share a few ideas if you're open to it.\n\n"
                f"Either way, thanks for your time.\n\nBest,\nKushall"
            )
        else:
            return (
                f"Hi {name},\n\n"
                f"This is my last follow-up — I don't want to be a bother.\n\n"
                f"If the timing isn't right, I completely understand. "
                f"I'll leave it here, but I'd genuinely love to stay in touch "
                f"for future opportunities.\n\n"
                f"Wishing you and the team all the best.\n\nKushall"
            )

    # ── Utility: schedule initial follow-up ───────────────────────────────────

    @staticmethod
    def schedule_initial_followup(record, db: Session) -> None:
        """
        Called right after the initial email is sent.
        Sets follow_up_scheduled = now + 5 days, follow_up_sent = False.
        """
        from datetime import datetime, timedelta, timezone
        record.follow_up_scheduled = datetime.now(timezone.utc) + timedelta(days=5)
        record.follow_up_sent      = False
        record.follow_up_count     = 0
        db.commit()
