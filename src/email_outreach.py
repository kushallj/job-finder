"""
email_outreach.py — Production-grade cold email outreach engine.

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │  PreflightChecker → EmailBuilder → SendQueue → Sheets  │
  │        ↓                                    ↓           │
  │  HealthReport                        DeadLetterQueue    │
  └─────────────────────────────────────────────────────────┘

Key features:
  • Async SMTP connection pool (no login per send)
  • asyncio producer/consumer send queue with configurable workers
  • 6-layer preflight validation with actionable fix hints
  • Finite-state-machine retry (pending→sending→sent/failed→retrying→dead)
  • Trace ID per email — every log line is correlated
  • Error attribution engine — tells you exactly which API key / config is broken
  • MX record DNS pre-validation (catches bad emails before SMTP)
  • Google Sheets dual-tab logging (✅ Sent / ❌ Failed / 💀 Dead)
  • Anti-spam jitter on send delays (gaussian noise)
  • Startup self-test health report printed to console
  • Dead-letter JSON fallback if Sheets is unavailable
"""

from __future__ import annotations

import asyncio
import json
import logging
import logging.handlers
import os
import random
import re
import smtplib
import socket
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.ai.gemini_service import GeminiService
from src.config import settings
from src.contact_finder import Contact

# ── Optional Google Sheets ────────────────────────────────────────────────────
try:
    from src.utils.sheets import GoogleSheetsClient
    _SHEETS_AVAILABLE = True
except ImportError:
    _SHEETS_AVAILABLE = False

# ── Optional DNS (MX) validation ─────────────────────────────────────────────
try:
    import dns.resolver
    _DNS_AVAILABLE = True
except ImportError:
    _DNS_AVAILABLE = False

# =============================================================================
# Logging setup — structured, human-readable, file + console
# =============================================================================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_fmt = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | trace=%(trace_id)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)

_file_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / "email_outreach.log",
    maxBytes=5 * 1024 * 1024,  # 5 MB per file
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setFormatter(_fmt)

# A dedicated log for failures only — easy to grep
_fail_handler = logging.FileHandler(LOG_DIR / "failures.log", encoding="utf-8")
_fail_handler.setLevel(logging.ERROR)
_fail_handler.setFormatter(_fmt)

_root = logging.getLogger("email_outreach")
_root.setLevel(logging.DEBUG)
_root.addHandler(_console_handler)
_root.addHandler(_file_handler)
_root.addHandler(_fail_handler)


class TraceLogger:
    """Wraps stdlib logger and injects a trace_id into every record."""

    def __init__(self, name: str, trace_id: str = "-"):
        self._log = logging.getLogger(f"email_outreach.{name}")
        self.trace_id = trace_id

    def _extra(self) -> dict:
        return {"trace_id": self.trace_id}

    def debug(self, msg, *a, **kw):   self._log.debug(msg, *a, extra=self._extra(), **kw)
    def info(self, msg, *a, **kw):    self._log.info(msg, *a, extra=self._extra(), **kw)
    def warning(self, msg, *a, **kw): self._log.warning(msg, *a, extra=self._extra(), **kw)
    def error(self, msg, *a, **kw):   self._log.error(msg, *a, extra=self._extra(), **kw)
    def critical(self, msg, *a, **kw):self._log.critical(msg, *a, extra=self._extra(), **kw)


# =============================================================================
# Enums & Dataclasses
# =============================================================================

class EmailStatus(str, Enum):
    PENDING   = "pending"
    SENDING   = "sending"
    SENT      = "sent"
    FAILED    = "failed"
    RETRYING  = "retrying"
    DEAD      = "dead"      # exhausted all retries


class TemplateType(str, Enum):
    HR_OUTREACH          = "hr_outreach"
    ENGINEERING_MANAGER  = "engineering_manager"
    FOLLOW_UP_1          = "follow_up_1"
    FOLLOW_UP_2          = "follow_up_2"
    FOLLOW_UP_FINAL      = "follow_up_final"


@dataclass
class EmailRecord:
    """Full lifecycle record for one email attempt."""
    trace_id:        str
    contact_email:   str
    contact_name:    str
    company:         str
    job_title:       str
    job_url:         str
    subject:         str
    body:            str
    template_type:   str
    status:          EmailStatus = EmailStatus.PENDING
    attempt_count:   int = 0
    max_attempts:    int = 3
    created_at:      str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_attempt_at: str = ""
    sent_at:         str = ""
    error_message:   str = ""
    error_category:  str = ""
    fix_hint:        str = ""

    def to_sheet_row(self) -> list:
        return [
            self.trace_id, self.contact_name, self.contact_email,
            self.company, self.job_title, self.job_url,
            self.subject, self.template_type, self.status.value,
            self.attempt_count, self.created_at, self.last_attempt_at,
            self.sent_at, self.error_message, self.fix_hint,
        ]

    @classmethod
    def sheet_headers(cls) -> list:
        return [
            "Trace ID", "Name", "Email", "Company", "Job Title", "Job URL",
            "Subject", "Template", "Status", "Attempts",
            "Created At", "Last Attempt", "Sent At", "Error", "Fix Hint",
        ]


@dataclass
class ValidationResult:
    passed: bool
    failures: List[Tuple[str, str]]  # (check_name, fix_hint)

    def summary(self) -> str:
        if self.passed:
            return "✅ All validations passed"
        lines = ["❌ Validation failures:"]
        for check, hint in self.failures:
            lines.append(f"   • [{check}] → {hint}")
        return "\n".join(lines)


@dataclass
class HealthReport:
    smtp_ok:    bool = False
    sheets_ok:  bool = False
    resume_ok:  bool = False
    ai_ok:      bool = False
    dns_ok:     bool = False
    details:    Dict[str, str] = field(default_factory=dict)

    def print(self):
        checks = [
            ("SMTP Connection",   self.smtp_ok,   "smtp"),
            ("Google Sheets",     self.sheets_ok, "sheets"),
            ("Resume PDF",        self.resume_ok, "resume"),
            ("AI (Gemini)",       self.ai_ok,     "ai"),
            ("DNS/MX Validation", self.dns_ok,    "dns"),
        ]
        print("\n" + "═" * 60)
        print("  📋  EMAIL OUTREACH — STARTUP HEALTH REPORT")
        print("═" * 60)
        for label, ok, key in checks:
            icon = "✅" if ok else "❌"
            detail = self.details.get(key, "")
            print(f"  {icon}  {label:<25} {detail}")
        print("═" * 60)
        if not all(ok for _, ok, _ in checks if _ != "dns"):
            print("  ⚠️  Fix the ❌ items above before sending emails.")
            print("  📖  See logs/failures.log for details.\n")
        else:
            print("  🚀  System ready.\n")


# =============================================================================
# Error Attribution Engine
# =============================================================================

_ERROR_ATLAS: List[Tuple[type, str, str]] = [
    # (exception_type, category, fix_hint)
    (smtplib.SMTPAuthenticationError,
     "AUTH_FAILURE",
     "Gmail authentication failed. Go to myaccount.google.com → Security → "
     "App Passwords, create an app password, and set it as GMAIL_PASSWORD in .env. "
     "Do NOT use your normal Gmail password."),

    (smtplib.SMTPRecipientsRefused,
     "BAD_RECIPIENT",
     "The recipient email address was rejected by the server. "
     "Verify the address is correct and the domain accepts mail."),

    (smtplib.SMTPSenderRefused,
     "SENDER_REFUSED",
     "Your sender email was rejected. Check GMAIL_ADDRESS in .env is a valid Gmail."),

    (smtplib.SMTPConnectError,
     "SMTP_CONNECT",
     "Cannot connect to smtp.gmail.com:587. Check your internet connection "
     "and ensure port 587 is not blocked by a firewall or VPN."),

    (smtplib.SMTPDataError,
     "SMTP_DATA",
     "SMTP DATA command rejected. Email body may be too large or contain "
     "content triggering spam filters. Simplify the email body."),

    (TimeoutError,
     "TIMEOUT",
     "Connection timed out. Check network stability. "
     "Consider increasing SMTP_TIMEOUT in settings."),

    (ConnectionRefusedError,
     "CONNECTION_REFUSED",
     "Connection to SMTP server refused. Port 587 may be blocked. "
     "Try from a different network or check firewall rules."),

    (OSError,
     "NETWORK_ERROR",
     "General network error. Check your internet connection."),

    (FileNotFoundError,
     "RESUME_MISSING",
     "Resume PDF not found. Create data/resume.pdf or set RESUME_PDF_PATH in .env."),

    (Exception,
     "UNKNOWN",
     "Unexpected error. Check logs/failures.log for the full traceback. "
     "Open a GitHub issue if this persists."),
]


def attribute_error(exc: Exception) -> Tuple[str, str]:
    """Return (category, fix_hint) for any exception."""
    for exc_type, category, hint in _ERROR_ATLAS:
        if isinstance(exc, exc_type):
            return category, hint
    return "UNKNOWN", "Check logs/failures.log for details."


# =============================================================================
# Preflight Validator (6 layers)
# =============================================================================

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class PreflightValidator:
    """Runs before any send attempt. Fast-fail with actionable messages."""

    def __init__(self, cfg: "OutreachConfig", log: TraceLogger):
        self.cfg = cfg
        self.log = log

    def run(self, contact: Contact) -> ValidationResult:
        failures = []

        # 1. Credentials
        if not self.cfg.sender_email:
            failures.append(("CREDENTIALS",
                "GMAIL_ADDRESS missing in .env — add your Gmail address"))
        if not self.cfg.sender_password:
            failures.append(("CREDENTIALS",
                "GMAIL_PASSWORD missing in .env — add your Gmail App Password "
                "(NOT your regular password). Get one at: "
                "myaccount.google.com → Security → App Passwords"))

        # 2. Resume PDF
        if not Path(self.cfg.resume_pdf_path).exists():
            failures.append(("RESUME",
                f"Resume PDF not found at '{self.cfg.resume_pdf_path}'. "
                "Create it or set RESUME_PDF_PATH in .env"))

        # 3. Email format
        if not contact.email or not _EMAIL_RE.match(contact.email):
            failures.append(("EMAIL_FORMAT",
                f"Invalid email address: '{contact.email}'. "
                "Verify the contact's email from the source."))

        # 4. Contact quality
        if not contact.name or contact.name.lower() in ("unknown", "n/a", "", "none"):
            failures.append(("CONTACT_QUALITY",
                f"Contact name is '{contact.name}'. "
                "Only emailing named contacts to avoid spam flags."))

        # 5. MX record (DNS)
        if _DNS_AVAILABLE and contact.email and "@" in contact.email:
            domain = contact.email.split("@")[1]
            try:
                dns.resolver.resolve(domain, "MX", lifetime=3)
            except Exception as e:
                failures.append(("MX_RECORD",
                    f"Domain '{domain}' has no MX record ({e}). "
                    "This email will definitely bounce. Skip it."))

        # 6. Sender email domain sanity
        if self.cfg.sender_email and "gmail" not in self.cfg.sender_email.lower():
            failures.append(("SENDER_DOMAIN",
                "Sender is not a Gmail address but SMTP is configured for Gmail. "
                "Either use a @gmail.com address or update smtp_server in OutreachConfig."))

        passed = len(failures) == 0
        result = ValidationResult(passed=passed, failures=failures)

        if not passed:
            for check, hint in failures:
                self.log.warning("PREFLIGHT FAIL [%s]: %s", check, hint)
        else:
            self.log.debug("Preflight passed for %s", contact.email)

        return result


# =============================================================================
# SMTP Connection Pool
# =============================================================================

class SMTPPool:
    """
    A small pool of persistent authenticated SMTP connections.
    Reusing connections is ~10x faster than login/logout per email.
    Falls back to creating a new connection if pool is exhausted.
    """

    def __init__(self, cfg: "OutreachConfig", size: int = 3):
        self.cfg = cfg
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=size)
        self._size = size
        self._log = TraceLogger("SMTPPool")
        self._lock = asyncio.Lock()
        self._initialised = False

    async def initialise(self):
        async with self._lock:
            if self._initialised:
                return
            self._log.info("Initialising SMTP pool (size=%d)…", self._size)
            for _ in range(self._size):
                conn = await self._create_connection()
                if conn:
                    await self._pool.put(conn)
            self._initialised = True
            self._log.info("SMTP pool ready (%d/%d connections)", self._pool.qsize(), self._size)

    async def _create_connection(self) -> Optional[smtplib.SMTP]:
        loop = asyncio.get_event_loop()
        try:
            conn = await loop.run_in_executor(None, self._blocking_connect)
            return conn
        except Exception as exc:
            cat, hint = attribute_error(exc)
            self._log.error("SMTP connect failed [%s]: %s | FIX: %s", cat, exc, hint)
            return None

    def _blocking_connect(self) -> smtplib.SMTP:
        server = smtplib.SMTP(self.cfg.smtp_host, self.cfg.smtp_port,
                               timeout=self.cfg.smtp_timeout)
        server.starttls()
        server.login(self.cfg.sender_email, self.cfg.sender_password)
        return server

    @asynccontextmanager
    async def acquire(self):
        """Get a connection from the pool; return it when done."""
        conn = None
        try:
            conn = self._pool.get_nowait()
        except asyncio.QueueEmpty:
            self._log.debug("Pool exhausted — creating on-demand connection")
            conn = await self._create_connection()

        if conn is None:
            raise ConnectionError(
                "Could not obtain SMTP connection. "
                "Check GMAIL_ADDRESS / GMAIL_PASSWORD in .env and network connectivity."
            )
        try:
            yield conn
        except smtplib.SMTPServerDisconnected:
            self._log.warning("Connection dropped mid-send; replacing…")
            conn = await self._create_connection()
            yield conn
        finally:
            if conn:
                try:
                    conn.noop()  # connection still alive?
                    await self._pool.put(conn)
                except Exception:
                    self._log.debug("Stale connection discarded")

    async def close(self):
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.quit()
            except Exception:
                pass
        self._log.info("SMTP pool closed")


# =============================================================================
# Google Sheets Logger
# =============================================================================

SHEET_SENT_TAB  = "✅ Sent"
SHEET_FAIL_TAB  = "❌ Failed"
SHEET_DEAD_TAB  = "💀 Dead Letters"
SHEET_HEALTH_TAB = "📊 Health"


class SheetsLogger:
    """Appends email records to the right Sheets tab based on status."""

    def __init__(self, client: Optional[Any]):
        self._client = client
        self._log = TraceLogger("SheetsLogger")
        self._available = client is not None and _SHEETS_AVAILABLE

        if self._available:
            for tab in (SHEET_SENT_TAB, SHEET_FAIL_TAB, SHEET_DEAD_TAB, SHEET_HEALTH_TAB):
                try:
                    self._client.ensure_worksheet(name=tab)
                    ws = self._client.spreadsheet.worksheet(tab)
                    if not ws.get_all_values():
                        ws.append_row(EmailRecord.sheet_headers())
                except Exception as e:
                    self._log.warning("Could not initialise tab '%s': %s", tab, e)

    def log(self, record: EmailRecord):
        if not self._available:
            return
        tab = {
            EmailStatus.SENT:    SHEET_SENT_TAB,
            EmailStatus.FAILED:  SHEET_FAIL_TAB,
            EmailStatus.DEAD:    SHEET_DEAD_TAB,
        }.get(record.status, SHEET_FAIL_TAB)

        try:
            ws = self._client.spreadsheet.worksheet(tab)
            ws.append_row(record.to_sheet_row())
            self._log.debug("Logged %s → %s", record.trace_id, tab)
        except Exception as e:
            self._log.error("Sheet write failed for %s: %s", record.trace_id, e)
            # Fallback to dead-letter JSON
            self._json_fallback(record)

    def _json_fallback(self, record: EmailRecord):
        path = Path("logs/dead_letter.json")
        try:
            existing = json.loads(path.read_text()) if path.exists() else []
            existing.append(asdict(record))
            path.write_text(json.dumps(existing, indent=2))
        except Exception as e:
            self._log.critical("Dead-letter JSON write also failed: %s", e)

    def log_health(self, report: HealthReport):
        if not self._available:
            return
        try:
            ws = self._client.spreadsheet.worksheet(SHEET_HEALTH_TAB)
            ws.append_row([
                datetime.utcnow().isoformat(),
                "✅" if report.smtp_ok else "❌",
                "✅" if report.sheets_ok else "❌",
                "✅" if report.resume_ok else "❌",
                "✅" if report.ai_ok else "❌",
                str(report.details),
            ])
        except Exception as e:
            self._log.warning("Health sheet write failed: %s", e)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class OutreachConfig:
    # Identity
    sender_name:      str = getattr(settings, "sender_name", "Your Name")
    sender_email:     str = getattr(settings, "gmail_address", "") or ""
    sender_password:  str = getattr(settings, "gmail_password", "") or ""

    # SMTP
    smtp_host:        str   = "smtp.gmail.com"
    smtp_port:        int   = 587
    smtp_timeout:     float = 15.0
    smtp_pool_size:   int   = 3

    # Resume
    resume_pdf_path:  str = getattr(settings, "resume_pdf_path", "data/resume.pdf") or "data/resume.pdf"

    # Sending behaviour
    worker_count:     int   = 3          # concurrent send workers
    max_retries:      int   = 3
    retry_base_delay: float = 5.0        # seconds; doubles each attempt
    # Anti-spam jitter: actual delay = base ± gaussian(0, jitter_sigma)
    delay_base:       float = getattr(settings, "email_delay_seconds", 30.0)
    delay_jitter:     float = 8.0


# =============================================================================
# Email Builder
# =============================================================================

class EmailBuilder:
    """Generates personalized email content via AI with a solid fallback."""

    def __init__(self, ai: GeminiService, cfg: OutreachConfig):
        self.ai = ai
        self.cfg = cfg

    def _detect_template_type(self, contact: Contact) -> TemplateType:
        title_lower = (contact.title or "").lower()
        hr_keywords = {"hr", "human resource", "people", "talent", "recruit", "hiring"}
        if any(k in title_lower for k in hr_keywords):
            return TemplateType.HR_OUTREACH
        return TemplateType.ENGINEERING_MANAGER

    async def build(
        self,
        contact: Contact,
        job_title: str,
        job_description: str,
        resume_text: str,
        template_type: Optional[TemplateType] = None,
    ) -> Tuple[str, str, TemplateType]:
        """Returns (subject, body, template_type)."""
        t = template_type or self._detect_template_type(contact)
        subject, body = await self._generate(contact, job_title, job_description, resume_text, t)
        return subject, body, t

    async def _generate(
        self,
        contact: Contact,
        job_title: str,
        job_description: str,
        resume_text: str,
        t: TemplateType,
    ) -> Tuple[str, str]:
        role_context = (
            "HR manager / recruiter" if t == TemplateType.HR_OUTREACH else "engineering manager / tech lead"
        )
        prompt = f"""Write a concise, professional cold email to a {role_context} at {contact.company}.

DETAILS:
- Contact: {contact.name}, {contact.title}
- Job: {job_title}
- Job description excerpt: {job_description[:600]}
- Sender: {self.cfg.sender_name}
- Sender background (first 800 chars of resume): {resume_text[:800]}

RULES:
1. Start with: "Dear {contact.name},"
2. 150–200 words max
3. Mention 2–3 specific skills from the job description that match the resume
4. End with: "Best regards,\\n{self.cfg.sender_name}"
5. No generic filler. No "I hope this email finds you well."

OUTPUT FORMAT (exactly):
Subject: <subject line>

Body:
<email body>
"""
        try:
            raw = await self.ai._call_gemini(prompt, max_tokens=512)
            return self._parse(raw, contact, job_title)
        except Exception as exc:
            cat, hint = attribute_error(exc)
            logging.getLogger("email_outreach.builder").error(
                "AI generation failed [%s]: %s | FIX: %s", cat, exc, hint,
                extra={"trace_id": "-"},
            )
            return self._fallback(contact, job_title)

    @staticmethod
    def _parse(raw: str, contact: Contact, job_title: str) -> Tuple[str, str]:
        subject, body = "", ""
        lines = raw.strip().splitlines()
        in_body = False
        body_lines = []
        for line in lines:
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif line.lower().startswith("body:"):
                in_body = True
            elif in_body:
                body_lines.append(line)
        body = "\n".join(body_lines).strip()
        if not subject:
            subject = f"Interest in {job_title} role at {contact.company}"
        if not body:
            body = f"Dear {contact.name},\n\nPlease see attached resume for the {job_title} role.\n\nBest regards,\n{contact.company}"
        return subject, body

    def _fallback(self, contact: Contact, job_title: str) -> Tuple[str, str]:
        subject = f"Application for {job_title} at {contact.company}"
        body = (
            f"Dear {contact.name},\n\n"
            f"I am writing to express my interest in the {job_title} position at {contact.company}. "
            f"With my background in software engineering, I believe I can contribute meaningfully to your team. "
            f"I have attached my resume for your review.\n\n"
            f"Would you be available for a brief call this week?\n\n"
            f"Best regards,\n{self.cfg.sender_name}"
        )
        return subject, body


# =============================================================================
# Main EmailOutreach Class
# =============================================================================

class EmailOutreach:
    """
    Production email outreach engine.

    Usage:
        async with EmailOutreach.create() as outreach:
            await outreach.send_bulk_outreach(contacts, job)
    """

    def __init__(self, cfg: Optional[OutreachConfig] = None, sheets_client=None):
        self.cfg = cfg or OutreachConfig()
        self.ai = GeminiService()
        self.builder = EmailBuilder(self.ai, self.cfg)
        self.pool = SMTPPool(self.cfg, size=self.cfg.smtp_pool_size)
        self.validator = PreflightValidator(self.cfg, TraceLogger("validator"))
        self.sheets = SheetsLogger(sheets_client)
        self._queue: asyncio.Queue[Optional[EmailRecord]] = asyncio.Queue()
        self._records: List[EmailRecord] = []
        self._lock = asyncio.Lock()

    @classmethod
    async def create(cls, cfg: Optional[OutreachConfig] = None) -> "EmailOutreach":
        """Factory: runs health check, inits pool, returns ready instance."""
        inst = cls(cfg)
        report = await inst.health_check()
        report.print()
        inst.sheets.log_health(report)
        if report.smtp_ok:
            await inst.pool.initialise()
        return inst

    async def __aenter__(self):
        return await self.create(self.cfg)

    async def __aexit__(self, *_):
        await self.close()

    # ── Health check ─────────────────────────────────────────────────────────

    async def health_check(self) -> HealthReport:
        report = HealthReport()
        loop = asyncio.get_event_loop()
        log = TraceLogger("health", trace_id="startup")

        # 1. SMTP
        if self.cfg.sender_email and self.cfg.sender_password:
            try:
                await loop.run_in_executor(None, self.pool._blocking_connect)
                report.smtp_ok = True
                report.details["smtp"] = f"Connected to {self.cfg.smtp_host}:{self.cfg.smtp_port}"
                log.info("SMTP OK")
            except Exception as exc:
                cat, hint = attribute_error(exc)
                report.details["smtp"] = f"FAILED [{cat}]: {hint}"
                log.error("SMTP FAILED: %s | FIX: %s", exc, hint)
        else:
            report.details["smtp"] = "No credentials set (GMAIL_ADDRESS / GMAIL_PASSWORD)"
            log.warning("SMTP skipped — credentials missing")

        # 2. Google Sheets
        report.sheets_ok = self.sheets._available
        report.details["sheets"] = "OK" if report.sheets_ok else (
            "Not configured — set GOOGLE_SHEET_ID. Falling back to logs/dead_letter.json"
        )

        # 3. Resume PDF
        report.resume_ok = Path(self.cfg.resume_pdf_path).exists()
        report.details["resume"] = (
            f"Found: {self.cfg.resume_pdf_path}" if report.resume_ok
            else f"MISSING: {self.cfg.resume_pdf_path} — create or set RESUME_PDF_PATH in .env"
        )

        # 4. AI
        try:
            await self.ai._call_gemini("ping", max_tokens=5)
            report.ai_ok = True
            report.details["ai"] = "Gemini API responsive"
        except Exception as exc:
            cat, hint = attribute_error(exc)
            report.details["ai"] = f"FAILED [{cat}]: {hint}"

        # 5. DNS
        report.dns_ok = _DNS_AVAILABLE
        report.details["dns"] = (
            "dnspython available" if _DNS_AVAILABLE
            else "dnspython not installed — run: pip install dnspython"
        )

        return report

    # ── Single send ───────────────────────────────────────────────────────────

    async def send_outreach_email(self, contact: Contact, job) -> bool:
        """Simple entry point used by job_processor.py"""
        record = await self._prepare_record(contact, job)
        if record is None:
            return False
        success = await self._send_with_retry(record)
        self.sheets.log(record)
        async with self._lock:
            self._records.append(record)
        return success

    # ── Bulk send ─────────────────────────────────────────────────────────────

    async def send_bulk_outreach(
        self,
        contacts: List[Contact],
        job,
        resume_text: str = "",
    ) -> Dict[str, int]:
        """
        Producer/consumer: enqueue all contacts, N workers drain the queue.
        Returns {'sent': N, 'failed': N, 'dead': N, 'skipped': N}
        """
        log = TraceLogger("bulk", trace_id="bulk-run")
        log.info("Bulk send: %d contacts, %d workers", len(contacts), self.cfg.worker_count)

        # Enqueue
        for contact in contacts:
            record = await self._prepare_record(contact, job, resume_text=resume_text)
            if record:
                await self._queue.put(record)

        # Poison pills to stop workers
        for _ in range(self.cfg.worker_count):
            await self._queue.put(None)

        # Start workers
        workers = [asyncio.create_task(self._worker(i)) for i in range(self.cfg.worker_count)]
        await asyncio.gather(*workers)

        # Tally
        counts = {"sent": 0, "failed": 0, "dead": 0, "skipped": 0}
        for r in self._records:
            counts[r.status.value if r.status in (
                EmailStatus.SENT, EmailStatus.DEAD
            ) else "failed"] = counts.get(r.status.value, 0) + 1

        log.info("Bulk send complete: %s", counts)
        return counts

    async def _worker(self, worker_id: int):
        log = TraceLogger(f"worker-{worker_id}", trace_id="bulk-run")
        while True:
            record = await self._queue.get()
            if record is None:
                log.debug("Worker %d received stop signal", worker_id)
                break
            log.info("Worker %d processing trace=%s", worker_id, record.trace_id)
            await self._send_with_retry(record)
            self.sheets.log(record)
            async with self._lock:
                self._records.append(record)

            # Anti-spam jitter delay
            delay = max(1.0, random.gauss(self.cfg.delay_base, self.cfg.delay_jitter))
            log.debug("Worker %d sleeping %.1fs before next send", worker_id, delay)
            await asyncio.sleep(delay)
            self._queue.task_done()

    # ── Record preparation ────────────────────────────────────────────────────

    async def _prepare_record(
        self,
        contact: Contact,
        job,
        resume_text: str = "",
        template_type: Optional[TemplateType] = None,
    ) -> Optional[EmailRecord]:
        trace_id = str(uuid.uuid4())[:8]
        log = TraceLogger("prepare", trace_id=trace_id)

        # Preflight
        result = self.validator.run(contact)
        if not result.passed:
            log.warning("Skipping %s — preflight failed:\n%s", contact.email, result.summary())
            return None

        # Build email content
        try:
            subject, body, t = await self.builder.build(
                contact,
                job.title,
                getattr(job, "description", ""),
                resume_text,
                template_type,
            )
        except Exception as exc:
            log.error("Email build failed: %s", exc)
            return None

        return EmailRecord(
            trace_id=trace_id,
            contact_email=contact.email,
            contact_name=contact.name,
            company=contact.company or getattr(job, "company", ""),
            job_title=job.title,
            job_url=getattr(job, "url", ""),
            subject=subject,
            body=body,
            template_type=t.value,
        )

    # ── Retry FSM ─────────────────────────────────────────────────────────────

    async def _send_with_retry(self, record: EmailRecord) -> bool:
        log = TraceLogger("send", trace_id=record.trace_id)

        for attempt in range(1, record.max_attempts + 1):
            record.attempt_count = attempt
            record.last_attempt_at = datetime.utcnow().isoformat()
            record.status = EmailStatus.SENDING
            log.info("Attempt %d/%d → %s", attempt, record.max_attempts, record.contact_email)

            try:
                loop = asyncio.get_event_loop()
                async with self.pool.acquire() as conn:
                    msg = self._build_mime(record)
                    await loop.run_in_executor(
                        None,
                        lambda: conn.sendmail(self.cfg.sender_email, record.contact_email, msg.as_string()),
                    )

                record.status = EmailStatus.SENT
                record.sent_at = datetime.utcnow().isoformat()
                log.info("✅ Sent to %s (attempt %d)", record.contact_email, attempt)
                return True

            except Exception as exc:
                cat, hint = attribute_error(exc)
                record.error_message  = f"[{cat}] {exc}"
                record.error_category = cat
                record.fix_hint       = hint
                record.status = EmailStatus.FAILED

                log.error(
                    "❌ Send failed (attempt %d) [%s]: %s\n"
                    "   🔧 FIX: %s",
                    attempt, cat, exc, hint,
                )

                # Non-retriable errors — abort immediately
                if cat in ("AUTH_FAILURE", "BAD_RECIPIENT", "SENDER_REFUSED", "RESUME_MISSING"):
                    log.error("Non-retriable error — aborting retries for %s", record.contact_email)
                    break

                if attempt < record.max_attempts:
                    delay = self.cfg.retry_base_delay * (2 ** (attempt - 1))
                    log.info("Retrying in %.1fs…", delay)
                    record.status = EmailStatus.RETRYING
                    await asyncio.sleep(delay)

        record.status = EmailStatus.DEAD
        log.critical(
            "💀 DEAD LETTER: %s exhausted %d attempts. Last error: %s. FIX: %s",
            record.contact_email, record.max_attempts,
            record.error_message, record.fix_hint,
        )
        return False

    # ── MIME construction ─────────────────────────────────────────────────────

    def _build_mime(self, record: EmailRecord) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg["From"]    = f"{self.cfg.sender_name} <{self.cfg.sender_email}>"
        msg["To"]      = record.contact_email
        msg["Subject"] = record.subject
        msg["X-Trace-ID"] = record.trace_id  # useful for debugging replies
        msg.attach(MIMEText(record.body, "plain", "utf-8"))

        pdf = Path(self.cfg.resume_pdf_path)
        if pdf.exists():
            with pdf.open("rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header(
                    "Content-Disposition", "attachment",
                    filename=f"{self.cfg.sender_name.replace(' ', '_')}_Resume.pdf",
                )
                msg.attach(attachment)
        return msg

    # ── Follow-ups ────────────────────────────────────────────────────────────

    async def send_followup_email(
        self, contact: Contact, job, follow_up_number: int = 1
    ) -> bool:
        templates = {
            1: (
                f"Following up: {job.title} at {job.company}",
                f"Hi {contact.name.split()[0]},\n\n"
                f"I wanted to follow up on my earlier note about the {job.title} role.\n"
                f"I remain very interested and would love a quick chat if you have 15 minutes.\n\n"
                f"Best regards,\n{self.cfg.sender_name}",
            ),
            2: (
                f"Re: {job.title} opportunity at {job.company}",
                f"Hi {contact.name.split()[0]},\n\n"
                f"I appreciate your time. If the timing isn't right, I completely understand — "
                f"I'd still love to stay connected for future opportunities.\n\n"
                f"Best regards,\n{self.cfg.sender_name}",
            ),
            3: (
                f"Final note — {job.title} at {job.company}",
                f"Hi {contact.name.split()[0]},\n\n"
                f"This is my last follow-up. I wish you and the team all the best.\n\n"
                f"Best regards,\n{self.cfg.sender_name}",
            ),
        }
        subject, body = templates.get(follow_up_number, templates[1])
        t_type = {1: TemplateType.FOLLOW_UP_1, 2: TemplateType.FOLLOW_UP_2}.get(
            follow_up_number, TemplateType.FOLLOW_UP_FINAL
        )
        job_title = getattr(job, "title", "Role")
        # Build a stub record so we get full retry + sheets logging
        record = EmailRecord(
            trace_id=str(uuid.uuid4())[:8],
            contact_email=contact.email,
            contact_name=contact.name,
            company=contact.company,
            job_title=job_title,
            job_url=getattr(job, "url", ""),
            subject=subject,
            body=body,
            template_type=t_type.value,
        )
        success = await self._send_with_retry(record)
        self.sheets.log(record)
        return success

    # ── Stats & persistence ───────────────────────────────────────────────────

    def get_outreach_stats(self) -> Dict:
        if not self._records:
            return {"total": 0}
        counts = {}
        for r in self._records:
            counts[r.status.value] = counts.get(r.status.value, 0) + 1
        companies = {}
        for r in self._records:
            companies[r.company] = companies.get(r.company, 0) + 1
        return {
            "total": len(self._records),
            "by_status": counts,
            "companies_contacted": len(companies),
            "top_companies": sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5],
        }

    def save_outreach_log(self, path: str = "logs/outreach_log.json"):
        Path(path).parent.mkdir(exist_ok=True)
        with open(path, "w") as f:
            json.dump([asdict(r) for r in self._records], f, indent=2, default=str)
        logging.getLogger("email_outreach").info(
            "Outreach log saved to %s (%d records)", path, len(self._records),
            extra={"trace_id": "-"},
        )

    def load_outreach_log(self, path: str = "logs/outreach_log.json"):
        try:
            with open(path) as f:
                data = json.load(f)
            self._records = [EmailRecord(**d) for d in data]
            logging.getLogger("email_outreach").info(
                "Loaded %d records from %s", len(self._records), path,
                extra={"trace_id": "-"},
            )
        except FileNotFoundError:
            logging.getLogger("email_outreach").info(
                "No existing log at %s", path, extra={"trace_id": "-"}
            )

    # ── Retry dead letters ────────────────────────────────────────────────────

    async def retry_dead_letters(self):
        """Re-queue any DEAD records from the current session for one more attempt."""
        log = TraceLogger("retry_dead", trace_id="retry")
        dead = [r for r in self._records if r.status == EmailStatus.DEAD]
        log.info("Retrying %d dead-letter emails…", len(dead))
        for record in dead:
            record.status = EmailStatus.PENDING
            record.attempt_count = 0
            record.max_attempts = 1  # one final chance
            success = await self._send_with_retry(record)
            self.sheets.log(record)
            log.info("%s → %s", record.contact_email, "SENT" if success else "DEAD again")

    # ── Cleanup ───────────────────────────────────────────────────────────────

    async def close(self):
        self.save_outreach_log()
        await self.pool.close()
        logging.getLogger("email_outreach").info(
            "EmailOutreach shut down cleanly", extra={"trace_id": "-"}
        )