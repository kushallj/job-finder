"""
reply_detector.py — IMAP-based reply detection.

Design:
  - imaplib is synchronous/blocking → runs in ThreadPoolExecutor
  - Polls the INBOX every `poll_interval_secs` (default 30 min)
  - Matches replies by: Message-ID chain (References / In-Reply-To) first,
    then subject prefix fallback (Re: <original subject>)
  - On match: updates OutreachRecord in DB, fires SentimentClassifier
  - Handles Gmail-specific quirks (IMAP must be enabled, uses SSL port 993)

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
from datetime import datetime, timezone
from email.header import decode_header
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# Matches "Re: " / "RE: " / "re: " prefix chains
_REPLY_SUBJECT_RE = re.compile(r"^(re:\s*)+", re.IGNORECASE)


class ReplyDetector:
    """
    Polls Gmail INBOX for replies to outreach emails.

    Usage:
        detector = ReplyDetector(db_session_factory)
        await detector.start()   # starts background poll loop
        # ... later ...
        await detector.stop()
    """

    def __init__(
        self,
        db_session_factory,
        sentiment_classifier=None,
        poll_interval_secs: int = 1800,   # 30 minutes
        imap_host: str = "imap.gmail.com",
        imap_port: int = 993,
        max_workers: int = 2,
    ):
        self._db_factory    = db_session_factory
        self._sentiment     = sentiment_classifier
        self._poll_interval = poll_interval_secs
        self._imap_host     = imap_host
        self._imap_port     = imap_port
        self._executor      = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="imap")
        self._task: Optional[asyncio.Task] = None
        self._running = False

        # Read credentials from env
        self._email    = os.environ.get("GMAIL_ADDRESS", "")
        self._password = os.environ.get("GMAIL_PASSWORD", "")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if not self._email or not self._password:
            log.warning("GMAIL_ADDRESS/GMAIL_PASSWORD not set — reply detection disabled")
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="reply_detector")
        log.info("ReplyDetector started (interval=%ds)", self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._executor.shutdown(wait=False)
        log.info("ReplyDetector stopped")

    # ── Poll loop ─────────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self._run_poll()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error("Reply poll error: %s", e, exc_info=True)
            await asyncio.sleep(self._poll_interval)

    async def _run_poll(self) -> None:
        """Run one IMAP poll in the thread pool (imaplib is blocking)."""
        loop    = asyncio.get_event_loop()
        replies = await loop.run_in_executor(self._executor, self._fetch_replies)
        if replies:
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

    # ── Reply processing ──────────────────────────────────────────────────────

    async def _process_reply(
        self,
        msg_id: str,
        subject: str,
        sender: str,
        body: str,
        date_str: str,
    ) -> None:
        """Match reply to an OutreachRecord and update DB."""
        from src.models import OutreachRecord

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

            # Update record
            record.replied_at = datetime.now(timezone.utc)
            record.status     = "replied"

            # Run sentiment analysis
            sentiment_label = "neutral"
            if self._sentiment:
                try:
                    label = await self._sentiment.classify(body)
                    sentiment_label = label.value
                    log.info(
                        "Reply from %s → sentiment=%s",
                        sender_email, sentiment_label,
                    )
                except Exception as e:
                    log.warning("Sentiment failed: %s", e)

            # Store sentiment if column exists
            if hasattr(record, "reply_sentiment"):
                record.reply_sentiment = sentiment_label

            db.commit()
            log.info(
                "Reply matched: contact=%s job_id=%s sentiment=%s",
                sender_email, record.job_id, sentiment_label,
            )

        except Exception as e:
            db.rollback()
            log.error("Failed to process reply from %s: %s", sender_email, e, exc_info=True)
        finally:
            db.close()

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
