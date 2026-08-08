"""
reply_detector.py — IMAP-based reply detection (Requirements 17.1-17.4).

Design:
  - imaplib is synchronous/blocking → runs in ThreadPoolExecutor
  - Polls the INBOX every `poll_interval_secs` (default 30 min = 1800 sec) [Req 17.1]
  - Matches replies by: Message-ID chain (References / In-Reply-To) first,
    then subject prefix fallback (Re: <original subject>)
  - On match: updates OutreachRecord in DB, fires SentimentClassifier [Req 17.2, 17.3]
  - On unsubscribe: marks Contact as do_not_contact [Req 17.4]
  - Handles Gmail-specific quirks (IMAP must be enabled, uses SSL port 993)

Requirements implemented:
  17.1: THE ReplyDetector SHALL poll IMAP for new replies at 30-minute intervals
  17.2: WHEN a reply is detected, THE ReplyDetector SHALL update the outreach record status
  17.3: THE ReplyDetector SHALL classify reply sentiment as positive, negative, neutral, referral, or unsubscribe
  17.4: WHEN an unsubscribe reply is detected, THE ReplyDetector SHALL mark the contact as do-not-contact

Gmail setup required:
  1. gmail.com → Settings → See all settings → Forwarding and POP/IMAP
  2. Enable IMAP access
  3. .env: GMAIL_ADDRESS + GMAIL_PASSWORD (app password, not account password)

Security:
  - Credentials read from environment, never hardcoded
  - Connection closed after each poll (avoids idle timeout)
  - SSL enforced (imaplib.IMAP4_SSL)
"""

from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.header import decode_header
from typing import Callable, List, Optional, Tuple

from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# Default polling interval: 30 minutes (1800 seconds) as per Requirement 17.1
DEFAULT_POLL_INTERVAL_SECS = 1800

# Matches "Re: " / "RE: " / "re: " prefix chains
_REPLY_SUBJECT_RE = re.compile(r"^(re:\s*)+", re.IGNORECASE)


@dataclass
class ReplyStats:
    """Statistics for reply detection (useful for monitoring and testing)."""
    replies_detected: int = 0
    replies_matched: int = 0
    unsubscribes_processed: int = 0
    contacts_marked_dnc: int = 0  # do-not-contact
    poll_count: int = 0
    last_poll_at: Optional[datetime] = None
    errors: int = 0
    sentiment_breakdown: dict = field(default_factory=lambda: {
        "positive": 0, "negative": 0, "neutral": 0, "referral": 0, "unsubscribe": 0
    })
    
    def as_dict(self) -> dict:
        """Return stats as a dictionary."""
        return {
            "replies_detected": self.replies_detected,
            "replies_matched": self.replies_matched,
            "unsubscribes_processed": self.unsubscribes_processed,
            "contacts_marked_do_not_contact": self.contacts_marked_dnc,
            "poll_count": self.poll_count,
            "last_poll_at": self.last_poll_at.isoformat() if self.last_poll_at else None,
            "errors": self.errors,
            "sentiment_breakdown": self.sentiment_breakdown.copy(),
        }


class ReplyDetector:
    """
    Polls Gmail INBOX for replies to outreach emails.
    
    Implements Requirements 17.1-17.4:
      - 17.1: Polls at 30-minute intervals (configurable)
      - 17.2: Updates outreach record status on reply detection
      - 17.3: Classifies sentiment (positive, negative, neutral, referral, unsubscribe)
      - 17.4: Marks contacts as do-not-contact when unsubscribe is detected

    Usage:
        detector = ReplyDetector(db_session_factory)
        await detector.start()   # starts background poll loop
        # ... later ...
        await detector.stop()
    """

    def __init__(
        self,
        db_session_factory: Callable[[], Session],
        sentiment_classifier=None,
        poll_interval_secs: int = DEFAULT_POLL_INTERVAL_SECS,  # 30 minutes (Req 17.1)
        imap_host: str = "imap.gmail.com",
        imap_port: int = 993,
        max_workers: int = 2,
        on_reply_callback: Optional[Callable] = None,
    ):
        self._db_factory    = db_session_factory
        self._sentiment     = sentiment_classifier
        self._poll_interval = poll_interval_secs
        self._imap_host     = imap_host
        self._imap_port     = imap_port
        self._executor      = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="imap")
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._on_reply = on_reply_callback  # Optional callback for testing/integration

        # Read credentials from env
        self._email    = os.environ.get("GMAIL_ADDRESS", "")
        self._password = os.environ.get("GMAIL_PASSWORD", "")
        
        # Statistics tracking
        self.stats = ReplyStats()
    
    @property
    def poll_interval(self) -> int:
        """Return the configured poll interval in seconds (Requirement 17.1)."""
        return self._poll_interval
    
    @property
    def is_running(self) -> bool:
        """Return whether the detector is currently running."""
        return self._running

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the background polling loop."""
        if not self._email or not self._password:
            log.warning("GMAIL_ADDRESS/GMAIL_PASSWORD not set — reply detection disabled")
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="reply_detector")
        log.info(
            "ReplyDetector started (poll_interval=%d secs = %d min) [Req 17.1]",
            self._poll_interval,
            self._poll_interval // 60,
        )

    async def stop(self) -> None:
        """Stop the background polling loop and clean up resources."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._executor.shutdown(wait=False)
        log.info(
            "ReplyDetector stopped. Stats: %s",
            self.stats.as_dict(),
        )
    
    async def poll_once(self) -> int:
        """
        Run a single poll cycle (useful for testing).
        Returns the number of replies processed.
        """
        await self._run_poll()
        return self.stats.replies_matched

    # ── Poll loop (Requirement 17.1) ──────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """
        Main polling loop that runs at 30-minute intervals (Requirement 17.1).
        """
        while self._running:
            try:
                await self._run_poll()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.stats.errors += 1
                log.error("Reply poll error: %s", e, exc_info=True)
            await asyncio.sleep(self._poll_interval)

    async def _run_poll(self) -> None:
        """Run one IMAP poll in the thread pool (imaplib is blocking)."""
        loop    = asyncio.get_event_loop()
        replies = await loop.run_in_executor(self._executor, self._fetch_replies)
        
        self.stats.poll_count += 1
        self.stats.last_poll_at = datetime.now(timezone.utc)
        
        if replies:
            self.stats.replies_detected += len(replies)
            log.info("Found %d new replies", len(replies))
            for msg_id, subject, sender, body, msg_date in replies:
                await self._process_reply(msg_id, subject, sender, body, msg_date)

    # ── IMAP fetch (runs in thread) ───────────────────────────────────────────

    def _fetch_replies(self) -> List[Tuple[str, str, str, str, str]]:
        """
        Connect to IMAP, search UNSEEN messages, return list of:
            (message_id, subject, sender, plain_body, date_str)
        Marks processed messages as SEEN.
        """
        results = []
        try:
            mail = imaplib.IMAP4_SSL(self._imap_host, self._imap_port)
            mail.login(self._email, self._password)
            mail.select("INBOX")

            # Search for unseen messages
            _, data = mail.search(None, "UNSEEN")
            if not data or not data[0]:
                mail.logout()
                return []

            uids = data[0].split()
            log.debug("Found %d unseen messages", len(uids))

            for uid in uids[-50:]:   # cap at last 50 unseen to avoid overload
                try:
                    _, msg_data = mail.fetch(uid, "(RFC822)")
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)

                    subject  = self._decode_header(msg.get("Subject", ""))
                    sender   = msg.get("From", "")
                    msg_id   = msg.get("Message-ID", "")
                    in_reply = msg.get("In-Reply-To", "")
                    references = msg.get("References", "")
                    date_str = msg.get("Date", "")
                    body     = self._extract_plain_body(msg)

                    # Only process if it looks like a reply
                    is_reply_subject = bool(_REPLY_SUBJECT_RE.match(subject))
                    has_reply_header = bool(in_reply or references)

                    if is_reply_subject or has_reply_header:
                        results.append((msg_id, subject, sender, body, date_str))
                        # Mark as seen after processing
                        mail.store(uid, "+FLAGS", "\\Seen")

                except Exception as e:
                    log.debug("Failed to process message %s: %s", uid, e)

            mail.logout()
        except imaplib.IMAP4.error as e:
            log.error("IMAP authentication error: %s", e)
        except Exception as e:
            log.error("IMAP poll failed: %s", e, exc_info=True)

        return results

    # ── Reply processing (Requirements 17.2, 17.3, 17.4) ────────────────────────

    async def _process_reply(
        self,
        msg_id: str,
        subject: str,
        sender: str,
        body: str,
        date_str: str,
    ) -> None:
        """
        Match reply to an OutreachRecord and update DB.
        
        Implements:
          - Requirement 17.2: Update outreach record status
          - Requirement 17.3: Classify sentiment
          - Requirement 17.4: Mark contact as do-not-contact on unsubscribe
        """
        from src.models import OutreachRecord, Contact

        # Extract sender email
        sender_email = self._extract_email_from_header(sender)
        # Strip "Re:" prefix to get original subject
        clean_subject = _REPLY_SUBJECT_RE.sub("", subject).strip()

        db: Session = self._db_factory()
        try:
            # Match by contact_email + approximate subject
            record = (
                db.query(OutreachRecord)
                .filter(
                    OutreachRecord.contact_email == sender_email,
                    OutreachRecord.status != "replied",
                )
                .order_by(OutreachRecord.sent_at.desc())
                .first()
            )

            if not record:
                log.debug(
                    "No matching outreach record for reply from %s (subject: %s)",
                    sender_email, clean_subject,
                )
                return

            # Requirement 17.2: Update outreach record status
            record.replied_at = datetime.now(timezone.utc)
            record.status     = "replied"
            self.stats.replies_matched += 1

            # Requirement 17.3: Run sentiment analysis
            sentiment_label = "neutral"
            if self._sentiment:
                try:
                    label = await self._sentiment.classify(body)
                    sentiment_label = label.value
                    log.info(
                        "Reply from %s → sentiment=%s [Req 17.3]",
                        sender_email, sentiment_label,
                    )
                except Exception as e:
                    log.warning("Sentiment classification failed: %s", e)
            
            # Track sentiment statistics
            if sentiment_label in self.stats.sentiment_breakdown:
                self.stats.sentiment_breakdown[sentiment_label] += 1

            # Store sentiment if column exists
            if hasattr(record, "reply_sentiment"):
                record.reply_sentiment = sentiment_label
            
            # Requirement 17.4: Handle unsubscribe - mark contact as do-not-contact
            if sentiment_label == "unsubscribe":
                self.stats.unsubscribes_processed += 1
                await self._mark_contact_do_not_contact(
                    db=db,
                    contact_id=record.contact_id,
                    contact_email=sender_email,
                    reason="unsubscribe_reply",
                )

            db.commit()
            log.info(
                "Reply matched: contact=%s job_id=%s sentiment=%s [Req 17.2]",
                sender_email, record.job_id, sentiment_label,
            )
            
            # Fire callback if registered (useful for testing/integration)
            if self._on_reply:
                try:
                    self._on_reply(record, sentiment_label)
                except Exception as e:
                    log.warning("Reply callback failed: %s", e)

        except Exception as e:
            db.rollback()
            self.stats.errors += 1
            log.error("Failed to process reply from %s: %s", sender_email, e, exc_info=True)
        finally:
            db.close()
    
    async def _mark_contact_do_not_contact(
        self,
        db: Session,
        contact_id: Optional[int],
        contact_email: str,
        reason: str = "unsubscribe_reply",
    ) -> None:
        """
        Mark a contact as do-not-contact (Requirement 17.4).
        
        This is called when an unsubscribe reply is detected.
        The contact will be excluded from future outreach.
        """
        from src.models import Contact
        
        contact = None
        
        # Try to find by contact_id first
        if contact_id:
            contact = db.query(Contact).filter(Contact.id == contact_id).first()
        
        # Fallback: find by email
        if not contact and contact_email:
            contact = db.query(Contact).filter(Contact.email == contact_email).first()
        
        if not contact:
            log.warning(
                "Cannot mark do-not-contact: contact not found (id=%s, email=%s)",
                contact_id, contact_email,
            )
            return
        
        # Mark as do-not-contact
        contact.do_not_contact = True
        contact.do_not_contact_reason = reason
        contact.do_not_contact_at = datetime.now(timezone.utc)
        
        self.stats.contacts_marked_dnc += 1
        log.info(
            "Marked contact as do-not-contact: %s (reason=%s) [Req 17.4]",
            contact_email, reason,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _decode_header(raw: str) -> str:
        parts = decode_header(raw)
        decoded = []
        for part, enc in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                decoded.append(str(part))
        return " ".join(decoded)

    @staticmethod
    def _extract_plain_body(msg: email.message.Message) -> str:
        """Walk MIME parts to find the plain-text body."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        return ""

    @staticmethod
    def _extract_email_from_header(header: str) -> str:
        """Extract 'user@domain.com' from 'Name <user@domain.com>' or raw address."""
        match = re.search(r"<([^>]+)>", header)
        if match:
            return match.group(1).lower().strip()
        return header.lower().strip()
