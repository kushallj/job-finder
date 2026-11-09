"""
mail_ingest.py — one path for recruiter mail, whatever the source.

Used by Gmail sync (src/jobify/services/gmail_sync.py) and the Jobify job-hunt inbox
(src/jobify/services/inbox.py). Matches a message to *the mailbox owner's* applications,
classifies it, moves the card forward only, and records it.

Rules:
  - Matching only ever looks at the owner's applications (passed in by the caller).
  - A card only moves forward (applied/ghosted -> interview -> offer|rejected).
  - Unauthenticated senders (SPF/DKIM/DMARC failure) are recorded but never move a card,
    so a forged "rejection" cannot change the board.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import Application, InboundRecruiterMessage, MailboxAccount
from src.services.inbound_email_classifier import InboundEmailIntentClassifier

# Classifier target_stage -> Jobify board stage. None keeps the current stage.
STAGE_MAP = {"offer": "offer", "rejected": "rejected", "take_home": "interview",
             "technical_interview": "interview", "interview": "interview", "screening": "interview"}
STAGE_RANK = {"ghosted": 0, "applied": 0, "interview": 1, "offer": 2, "rejected": 2}

_GENERIC_DOMAINS = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com",
                    "greenhouse.io", "lever.co", "ashbyhq.com", "workday.com", "myworkday.com", "smartrecruiters.com"}


@dataclass
class ParsedMessage:
    id: str
    thread_id: str
    sender_email: str
    sender_name: str
    subject: str
    snippet: str
    body: str
    received_at: datetime
    recipient_email: str = ""
    in_reply_to: str = ""
    sender_verified: bool | None = None  # None = unknown (no auth results available)
    references: list[str] = field(default_factory=list)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def match_application(apps: list[Application], msg: ParsedMessage) -> Application | None:
    """Best match among the owner's applications, or None."""
    for app in apps:
        if app.recruiter_email and app.recruiter_email.lower() == msg.sender_email:
            return app
    domain = msg.sender_email.rsplit("@", 1)[-1] if "@" in msg.sender_email else ""
    domain_slug = _slug(domain.split(".")[-2] if domain.count(".") >= 1 else domain)
    text = f"{msg.subject} {msg.sender_name} {msg.snippet}".lower()
    best = None
    for app in apps:
        company = (app.company or "").strip()
        if len(_slug(company)) < 3:
            continue
        if domain and domain not in _GENERIC_DOMAINS and _slug(company) in (domain_slug, _slug(domain)):
            return app
        if re.search(rf"\b{re.escape(company.lower())}\b", text):
            best = best or app
    return best


def thread_application(db: Session, mb: MailboxAccount, msg: ParsedMessage) -> Application | None:
    """A reply in an existing thread belongs to the same application as the thread."""
    refs = [r for r in (msg.in_reply_to, *msg.references) if r]
    if not refs:
        return None
    prior = (db.query(InboundRecruiterMessage)
             .filter(InboundRecruiterMessage.mailbox_id == mb.id, InboundRecruiterMessage.message_id.in_(refs),
                     InboundRecruiterMessage.application_id.isnot(None))
             .first())
    if prior is None:
        return None
    return db.query(Application).filter(Application.id == prior.application_id,
                                        Application.user_id == mb.user_id).first()


def ingest_message(db: Session, mb: MailboxAccount, msg: ParsedMessage, apps: list[Application],
                   classifier: InboundEmailIntentClassifier, *, store_unmatched: bool) -> InboundRecruiterMessage | None:
    """Record one inbound message. Returns the stored row, or None if it was discarded."""
    app = thread_application(db, mb, msg) or match_application(apps, msg)
    if app is None and not store_unmatched:
        return None
    result = classifier.classify(msg.subject, msg.body)
    moved = False
    prev = target = None
    if app is not None:
        prev = (app.kanban_stage or "applied").lower()
        target = STAGE_MAP.get(result.target_stage or "")
        moved = bool(target and target != prev and msg.sender_verified is not False
                     and STAGE_RANK.get(target, 0) > STAGE_RANK.get(prev, 0))
        if moved:
            app.kanban_stage = target
        app.last_email_received_at = max(filter(None, [app.last_email_received_at, msg.received_at]))
        app.email_subject = msg.subject or app.email_subject
        app.recruiter_email = app.recruiter_email or msg.sender_email
    row = InboundRecruiterMessage(
        mailbox_id=mb.id, application_id=app.id if app else None, job_id=app.job_id if app else None,
        sender_email=msg.sender_email or "unknown", sender_name=msg.sender_name,
        recipient_email=msg.recipient_email or mb.email_address, subject=msg.subject or "(no subject)",
        snippet=msg.snippet, body_text=msg.body, classified_intent=result.intent,
        confidence_score=result.confidence, previous_kanban_stage=prev,
        new_kanban_stage=(target if moved else prev), auto_advanced=moved,
        message_id=(msg.id or "")[:255] or None, thread_id=(msg.thread_id or "")[:255] or None,
        received_at=msg.received_at, direction="in", is_read=False,
        in_reply_to=(msg.in_reply_to or "")[:500] or None, sender_verified=msg.sender_verified)
    db.add(row)
    return row
