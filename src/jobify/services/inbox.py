"""
jobify_inbox.py — each user's job-hunt email address (name.xxxx@INBOX_DOMAIN).

Receiving (free): Cloudflare Email Routing catch-all -> Email Worker
(infra/cloudflare/inbox-worker/worker.js) -> POST /api/inbound/email with the raw message,
signed HMAC-SHA256(INBOUND_WEBHOOK_SECRET, "<timestamp>.<raw bytes>").
Sending: plain SMTP (any provider's free tier), reply-only, after an explicit user click.

The address exists only for job hunting, so every message is stored (unlike Gmail sync,
which keeps only messages matching an application) and shown in the in-app inbox.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import getaddresses, make_msgid, parseaddr, parsedate_to_datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.api.contract import iso_utc
from src.config import settings
from src.models import Application, InboundRecruiterMessage, MailboxAccount, User
from src.services.inbound_email_classifier import InboundEmailIntentClassifier
from src.jobify.services.mail_ingest import ParsedMessage, ingest_message

PROVIDER = "jobify"
SIGNATURE_MAX_SKEW = 300  # seconds; rejects replayed deliveries
_SUFFIX_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0/o/1/l/i: easy to read off a resume


class InboxError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def receiving_configured() -> bool:
    return bool(settings.inbox_domain and settings.inbound_webhook_secret)


def sending_configured() -> bool:
    return bool(settings.inbox_domain and settings.inbox_smtp_host and settings.inbox_smtp_username
                and settings.inbox_smtp_password)


# --- address ------------------------------------------------------------------------------

_CLERK_ID = re.compile(r"^user_[a-z0-9]{10,}$", re.I)


def _base_name(user: User) -> str:
    # Auto-provisioned users without a Clerk name/email claim get full_name derived from the
    # Clerk id ("User_3Lhdz48..."); never put that on someone's permanent address.
    source = user.full_name or ""
    if _CLERK_ID.match(source.strip()):
        source = ""
    if not source and user.email and not user.email.endswith("@clerk.user"):
        source = user.email.split("@", 1)[0]
    base = re.sub(r"[^a-z0-9]+", ".", source.lower()).strip(".")
    base = re.sub(r"\.{2,}", ".", base)[:24].strip(".")
    return base or "jobseeker"


def get_or_create_inbox(db: Session, user: User) -> Optional[MailboxAccount]:
    mb = (db.query(MailboxAccount).filter(MailboxAccount.user_id == user.id, MailboxAccount.provider == PROVIDER)
          .first())
    if mb is not None or not settings.inbox_domain:
        return mb
    domain = settings.inbox_domain.lower()
    base = _base_name(user)
    for _ in range(20):
        suffix = "".join(secrets.choice(_SUFFIX_ALPHABET) for _ in range(4))
        address = f"{base}.{suffix}@{domain}"
        if not db.query(MailboxAccount.id).filter(MailboxAccount.email_address == address).first():
            break
    else:  # pragma: no cover - 31^4 combinations per name
        raise InboxError("ADDRESS_UNAVAILABLE", "Could not allocate an address, try again", 503)
    mb = MailboxAccount(user_id=user.id, provider=PROVIDER, email_address=address, imap_host=None,
                        is_connected=True, auto_advance_pipeline=True, sync_status="connected")
    db.add(mb)
    db.commit()
    return mb


# --- inbound webhook ------------------------------------------------------------------------

def sign(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def verify_signature(timestamp: Optional[str], signature: Optional[str], body: bytes, now: Optional[float] = None) -> None:
    if not settings.inbound_webhook_secret:
        raise InboxError("INBOX_NOT_CONFIGURED", "Inbound email is not configured", 503)
    if not timestamp or not signature or not timestamp.isdigit():
        raise InboxError("BAD_SIGNATURE", "Missing signature", 401)
    if abs((now or time.time()) - int(timestamp)) > SIGNATURE_MAX_SKEW:
        raise InboxError("BAD_SIGNATURE", "Stale delivery", 401)
    expected = sign(settings.inbound_webhook_secret, timestamp, body)
    if not hmac.compare_digest(expected, signature.strip().lower()):
        raise InboxError("BAD_SIGNATURE", "Invalid signature", 401)


def _sender_verified(msg) -> Optional[bool]:
    """Read SPF/DKIM/DMARC from Authentication-Results (added by the receiving MTA)."""
    results = " ".join(str(v) for v in (msg.get_all("Authentication-Results") or [])
                       + (msg.get_all("ARC-Authentication-Results") or [])).lower()
    if not results:
        return None
    if "dmarc=fail" in results:
        return False
    if "dkim=pass" in results or "dmarc=pass" in results:
        return True
    if "spf=fail" in results or "spf=softfail" in results:
        return False
    return True if "spf=pass" in results else None


def parse_raw(raw: bytes, envelope_to: str = "") -> ParsedMessage:
    msg = message_from_bytes(raw, policy=policy.default)
    name, addr = parseaddr(str(msg.get("From", "")))
    body_part = msg.get_body(preferencelist=("plain", "html"))
    body = ""
    if body_part is not None:
        try:
            body = body_part.get_content()
        except (LookupError, UnicodeDecodeError):
            body = body_part.get_payload(decode=True).decode("utf-8", "replace") if body_part.get_payload(decode=True) else ""
        if body_part.get_content_type() == "text/html":
            body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
            body = re.sub(r"<[^>]+>", " ", body)
    body = body[:20_000]
    received = None
    if msg.get("Date"):
        try:
            dt = parsedate_to_datetime(str(msg.get("Date")))
            received = dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt  # stored as naive UTC
        except (TypeError, ValueError):
            received = None
    message_id = str(msg.get("Message-ID", "")).strip() or f"<no-id-{secrets.token_hex(8)}@jobify>"
    refs = re.findall(r"<[^>]+>", str(msg.get("References", "")))
    in_reply_to = str(msg.get("In-Reply-To", "")).strip()
    to_addrs = [a.lower() for _, a in getaddresses([str(msg.get("To", "")), str(msg.get("Cc", ""))]) if a]
    return ParsedMessage(
        id=message_id, thread_id=(refs[0] if refs else in_reply_to or message_id),
        sender_email=addr.lower(), sender_name=name, subject=str(msg.get("Subject", ""))[:500],
        snippet=re.sub(r"\s+", " ", body).strip()[:200], body=body,
        received_at=received or datetime.utcnow(),
        recipient_email=(envelope_to or (to_addrs[0] if to_addrs else "")).lower(),
        in_reply_to=in_reply_to, references=refs, sender_verified=_sender_verified(msg))


def receive(db: Session, raw: bytes, envelope_to: str) -> Dict[str, Any]:
    """Store one inbound message for the inbox it was addressed to. Unknown recipients are dropped."""
    address = (envelope_to or "").strip().lower()
    mb = db.query(MailboxAccount).filter(MailboxAccount.provider == PROVIDER, MailboxAccount.email_address == address).first()
    if mb is None:
        return {"accepted": True, "stored": False}  # same response as success: don't reveal which addresses exist
    msg = parse_raw(raw, address)
    if db.query(InboundRecruiterMessage.id).filter(InboundRecruiterMessage.mailbox_id == mb.id,
                                                   InboundRecruiterMessage.message_id == msg.id[:255]).first():
        return {"accepted": True, "stored": False}
    apps = db.query(Application).filter(Application.user_id == mb.user_id).order_by(Application.updated_at.desc()).all()
    row = ingest_message(db, mb, msg, apps, InboundEmailIntentClassifier(), store_unmatched=True)
    mb.total_messages_scanned = (mb.total_messages_scanned or 0) + 1
    mb.total_advancements = (mb.total_advancements or 0) + int(bool(row.auto_advanced))
    mb.last_sync_at = datetime.utcnow()
    db.commit()
    return {"accepted": True, "stored": True}


# --- in-app inbox -----------------------------------------------------------------------------

def to_ui(row: InboundRecruiterMessage, full: bool = False) -> Dict[str, Any]:
    out = {
        "id": str(row.id),
        "direction": row.direction or "in",
        "from": {"name": row.sender_name or "", "email": row.sender_email},
        "to": row.recipient_email or "",
        "subject": row.subject,
        "snippet": row.snippet or "",
        "receivedAt": iso_utc(row.received_at or row.created_at),
        "read": bool(row.is_read),
        "applicationId": str(row.application_id) if row.application_id else None,
        "intent": row.classified_intent,
        "movedTo": row.new_kanban_stage if row.auto_advanced else None,
        "senderVerified": row.sender_verified,
    }
    if full:
        out["body"] = row.body_text or ""
    return out


def owned_message(db: Session, user: User, msg_id: int) -> InboundRecruiterMessage:
    row = (db.query(InboundRecruiterMessage).join(MailboxAccount, InboundRecruiterMessage.mailbox_id == MailboxAccount.id)
           .filter(InboundRecruiterMessage.id == msg_id, MailboxAccount.user_id == user.id,
                   MailboxAccount.provider == PROVIDER).first())
    if row is None:
        raise InboxError("NOT_FOUND", "Message not found", 404)
    return row


# --- replies (SMTP) ------------------------------------------------------------------------------

def _smtp_send(msg: EmailMessage) -> None:
    with smtplib.SMTP(settings.inbox_smtp_host, settings.inbox_smtp_port, timeout=20) as smtp:
        if settings.inbox_smtp_starttls:
            smtp.starttls()
        smtp.login(settings.inbox_smtp_username, settings.inbox_smtp_password)
        smtp.send_message(msg)


def reply(db: Session, user: User, msg_id: int, body: str) -> InboundRecruiterMessage:
    """Reply to a message the user received. Reply-only by design: Jobify addresses can't cold-email."""
    if not sending_configured():
        raise InboxError("INBOX_SENDING_NOT_CONFIGURED", "Sending replies isn't available yet", 503)
    original = owned_message(db, user, msg_id)
    if (original.direction or "in") != "in" or not original.sender_email or "@" not in original.sender_email:
        raise InboxError("CANNOT_REPLY", "You can only reply to messages you received", 400)
    mb = db.query(MailboxAccount).filter(MailboxAccount.id == original.mailbox_id).one()
    since = datetime.utcnow() - timedelta(days=1)
    sent_today = (db.query(InboundRecruiterMessage)
                  .filter(InboundRecruiterMessage.mailbox_id == mb.id, InboundRecruiterMessage.direction == "out",
                          InboundRecruiterMessage.created_at >= since).count())
    if sent_today >= settings.inbox_daily_send_limit:
        raise InboxError("SEND_LIMIT_REACHED", "Daily reply limit reached. Try again tomorrow.", 429)

    subject = original.subject or ""
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    message_id = make_msgid(domain=settings.inbox_domain)
    email = EmailMessage()
    email["From"] = f"{user.full_name or _base_name(user)} <{mb.email_address}>"
    email["To"] = original.sender_email
    email["Subject"] = subject[:500]
    email["Message-ID"] = message_id
    if original.message_id:
        email["In-Reply-To"] = original.message_id
        email["References"] = " ".join(filter(None, [original.thread_id if original.thread_id != original.message_id else "", original.message_id]))
    email.set_content(body)
    try:
        _smtp_send(email)
    except (smtplib.SMTPException, OSError) as exc:
        raise InboxError("SEND_FAILED", "The reply couldn't be sent. Try again.", 502) from exc

    now = datetime.utcnow()
    out = InboundRecruiterMessage(
        mailbox_id=mb.id, application_id=original.application_id, job_id=original.job_id,
        sender_email=mb.email_address, sender_name=user.full_name, recipient_email=original.sender_email,
        subject=subject[:500], snippet=re.sub(r"\s+", " ", body).strip()[:200], body_text=body,
        classified_intent="OUTBOUND", auto_advanced=False, message_id=message_id[:255],
        thread_id=original.thread_id, in_reply_to=(original.message_id or "")[:500] or None,
        direction="out", is_read=True, sender_verified=True, received_at=now, created_at=now)
    db.add(out)
    db.commit()
    db.refresh(out)
    return out
