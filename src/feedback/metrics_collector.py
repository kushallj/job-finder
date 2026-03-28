"""
metrics_collector.py — Reads pipeline outcome data from DB, computes funnel metrics.

Data sources:
  - OutreachRecord  (email_sent, status, reply_sentiment, ab_variant, sent_at)
  - Application     (status: interview, rejected, offer)
  - Contact         (company, department)

Metrics computed:
  1. Full funnel: sent → delivered → replied → positive → interview → offer
  2. Segment breakdowns: by hook_type, send_hour, company_domain, template, ab_variant
  3. Top performing subjects and hooks (ranked by reply rate, min 5 sends)

Concurrency: all DB reads are synchronous (SQLAlchemy sync session).
Called from FeedbackLoop which runs in a ThreadPoolExecutor.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from .models import OutreachMetrics, ReplyStats

log = logging.getLogger(__name__)

# Minimum sends in a segment to report it
_MIN_SEGMENT_SENDS = 5


class MetricsCollector:
    """
    Reads OutreachRecord + Application tables and computes OutreachMetrics.

    Usage:
        collector = MetricsCollector(db_session)
        metrics = collector.collect(window_days=7)
    """

    def __init__(self, db_session=None):
        self._db = db_session

    def collect(self, window_days: int = 7) -> OutreachMetrics:
        """
        Collect metrics for the last `window_days` days.
        Returns empty metrics if DB is unavailable.
        """
        if self._db is None:
            return OutreachMetrics(window_days=window_days)

        try:
            return self._collect_from_db(window_days)
        except Exception as exc:
            log.warning("MetricsCollector: DB read failed: %s", exc)
            return OutreachMetrics(window_days=window_days)

    def _collect_from_db(self, window_days: int) -> OutreachMetrics:
        from src.models import OutreachRecord, Application, Contact

        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        db     = self._db

        # ── Core outreach records ──────────────────────────────────────────────
        records = db.query(OutreachRecord).filter(
            OutreachRecord.sent_at >= cutoff
        ).all()

        metrics = OutreachMetrics(window_days=window_days)
        metrics.total_sent = len(records)

        by_hook:     Dict[str, ReplyStats] = defaultdict(ReplyStats)
        by_hour:     Dict[int, ReplyStats] = defaultdict(ReplyStats)
        by_domain:   Dict[str, ReplyStats] = defaultdict(ReplyStats)
        by_template: Dict[str, ReplyStats] = defaultdict(ReplyStats)
        by_variant:  Dict[int, ReplyStats] = defaultdict(ReplyStats)
        subject_replies: Dict[str, int]    = defaultdict(int)
        subject_sends:   Dict[str, int]    = defaultdict(int)

        for rec in records:
            status    = (rec.status or "sent").lower()
            sentiment = (rec.reply_sentiment or "").lower()
            is_bounced   = status == "bounced"
            is_replied   = status in ("replied",) or bool(rec.replied_at)
            is_positive  = sentiment == "positive"
            ab           = rec.ab_variant or 0
            hour         = rec.sent_at.hour if rec.sent_at else -1
            domain       = _extract_domain(rec.contact_email or "")
            template     = rec.template_type or "unknown"

            if not is_bounced:
                metrics.total_delivered += 1
            if is_bounced:
                metrics.total_bounced += 1
            if is_replied:
                metrics.total_replied += 1
            if is_positive:
                metrics.total_positive += 1

            # Subject tracking
            if rec.subject:
                subject_sends[rec.subject] += 1
                if is_replied:
                    subject_replies[rec.subject] += 1

            def _update(seg: ReplyStats) -> None:
                seg.sent += 1
                if is_bounced: seg.bounced += 1
                if is_replied: seg.replied += 1
                if is_positive: seg.positive += 1

            # Hook type from body metadata (stored as JSON comment or template_type prefix)
            hook_type = _infer_hook_type(rec.body or "", rec.template_type or "")
            _update(by_hook[hook_type])
            if hour >= 0:
                _update(by_hour[hour])
            if domain:
                _update(by_domain[domain])
            _update(by_template[template])
            _update(by_variant[ab])

        # ── Interview / offer counts from Application table ────────────────────
        job_ids = {rec.job_id for rec in records if rec.job_id}
        if job_ids:
            apps = db.query(Application).filter(
                Application.job_id.in_(job_ids)
            ).all()
            for app in apps:
                status = (app.status or "").lower()
                if status in ("interview", "interviewing"):
                    metrics.total_interviews += 1
                elif status == "offer":
                    metrics.total_offers += 1
                    metrics.total_interviews += 1   # offer implies interview

        # ── Top subjects ───────────────────────────────────────────────────────
        def _subject_score(subj: str) -> float:
            sends = subject_sends[subj]
            if sends < _MIN_SEGMENT_SENDS:
                return 0.0
            return subject_replies[subj] / sends

        metrics.top_subjects = sorted(
            [s for s, n in subject_sends.items() if n >= _MIN_SEGMENT_SENDS],
            key=_subject_score, reverse=True
        )[:5]

        # ── Segment dicts ──────────────────────────────────────────────────────
        metrics.by_hook_type      = {k: v for k, v in by_hook.items()    if v.sent >= _MIN_SEGMENT_SENDS}
        metrics.by_send_hour      = {k: v for k, v in by_hour.items()    if v.sent >= _MIN_SEGMENT_SENDS}
        metrics.by_company_domain = {k: v for k, v in by_domain.items()  if v.sent >= _MIN_SEGMENT_SENDS}
        metrics.by_template       = {k: v for k, v in by_template.items() if v.sent >= _MIN_SEGMENT_SENDS}
        metrics.by_ab_variant     = {k: v for k, v in by_variant.items() if v.sent >= _MIN_SEGMENT_SENDS}

        # Top hooks by reply rate
        metrics.top_hooks = sorted(
            metrics.by_hook_type,
            key=lambda k: metrics.by_hook_type[k].reply_rate,
            reverse=True,
        )[:3]

        log.info(
            "MetricsCollector: %d records | %s",
            metrics.total_sent, metrics.funnel_str()
        )
        return metrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_domain(email: str) -> str:
    if "@" in email:
        return email.split("@")[1].lower()
    return ""


def _infer_hook_type(body: str, template_type: str) -> str:
    """
    Infer which hook type was used from the email body heuristics.
    Mirrors HookType values from personalization.models.
    """
    body_lower = body.lower()
    if any(kw in body_lower for kw in ("your repo", "your project", "your post", "came across your")):
        return "contact_resonance"
    if any(kw in body_lower for kw in ("open-source", "github.com/", "hit the front page", "congrats on")):
        return "company_signal"
    if any(kw in body_lower for kw in ("seeing", "in your stack", "primary language")):
        return "tech_alignment"
    if any(kw in body_lower for kw in ("jd mentions", "role calls for", "tackled this:")):
        return "role_fit"
    if any(kw in body_lower for kw in ("culture", "ownership", "open source culture")):
        return "culture_fit"
    return "generic"
