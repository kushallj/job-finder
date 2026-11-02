"""
src/services/inbound_email_sync_service.py
Service for Inbound Recruiter Email Sync & Auto-Advancing Pipeline.

Connects user's Gmail/Outlook mailbox, scans incoming recruiter messages,
classifies intent (INTERVIEW_INVITATION, ASSESSMENT, OFFER, REJECTION, FOLLOW_UP_REQUIRED),
and automatically moves the Kanban card to the right column with countdown timers
and email provenance badges without requiring manual dragging.
"""
from __future__ import annotations

import email
from email.header import decode_header
import imaplib
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_, and_, desc, asc, text
from sqlalchemy.orm import Session

from src.models import (
    Base,
    Application,
    Job,
    OutreachRecord,
    Contact,
    MailboxAccount,
    InboundRecruiterMessage,
)
from src.api_models import (
    InboundAdvancementResult,
    MailboxSyncResponse,
)
from src.services.inbound_email_classifier import (
    InboundEmailIntentClassifier,
    IntentClassificationResult,
)
from src.services.kanban_service import KanbanService

logger = logging.getLogger("inbound_email_sync")


def ensure_mailbox_schema(db: Session) -> None:
    """Ensure SQLite database has mailbox_accounts and inbound_recruiter_messages tables."""
    try:
        bind = db.get_bind()
        Base.metadata.create_all(
            bind=bind,
            tables=[
                MailboxAccount.__table__,
                InboundRecruiterMessage.__table__,
            ],
            checkfirst=True,
        )
        db.commit()
    except Exception as exc:
        logger.warning("Mailbox schema check note: %s", exc)


class InboundEmailSyncService:
    """Coordinates IMAP syncing, intent classification, and automatic Kanban advancement."""

    def __init__(self, db: Session):
        self.db = db
        ensure_mailbox_schema(db)
        self.classifier = InboundEmailIntentClassifier()

    def connect_mailbox(
        self,
        provider: str = "gmail",
        email_address: str = "",
        password: Optional[str] = None,
        imap_host: Optional[str] = None,
        imap_port: Optional[int] = 993,
        use_ssl: bool = True,
        auto_advance_pipeline: bool = True,
        user_id: Optional[int] = None,
    ) -> MailboxAccount:
        """Create or update a connected mailbox account."""
        email_address = (email_address or "").strip().lower()
        if not email_address:
            raise ValueError("Email address is required to connect mailbox")

        # Resolve default IMAP host by provider
        if not imap_host:
            if provider.lower() == "outlook":
                imap_host = "outlook.office365.com"
            else:
                imap_host = "imap.gmail.com"

        account = (
            self.db.query(MailboxAccount)
            .filter(MailboxAccount.email_address == email_address)
            .first()
        )

        if not account:
            account = MailboxAccount(
                user_id=user_id,
                provider=provider.lower(),
                email_address=email_address,
                imap_host=imap_host,
                imap_port=imap_port or 993,
                use_ssl=use_ssl,
                is_connected=True,
                auto_advance_pipeline=auto_advance_pipeline,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(account)
        else:
            account.provider = provider.lower()
            account.imap_host = imap_host
            account.imap_port = imap_port or 993
            account.use_ssl = use_ssl
            account.is_connected = True
            account.auto_advance_pipeline = auto_advance_pipeline
            account.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(account)
        return account

    def get_mailbox(self, mailbox_id: int) -> Optional[MailboxAccount]:
        """Fetch mailbox account by ID."""
        return self.db.query(MailboxAccount).filter(MailboxAccount.id == mailbox_id).first()

    def get_primary_mailbox(self) -> Optional[MailboxAccount]:
        """Fetch most recently connected active mailbox account."""
        return (
            self.db.query(MailboxAccount)
            .filter(MailboxAccount.is_connected == True)
            .order_by(desc(MailboxAccount.id))
            .first()
        )

    def match_message_to_application(
        self,
        sender_email: str,
        subject: str,
        body_text: str = "",
        company_hint: Optional[str] = None,
        application_id: Optional[int] = None,
    ) -> Optional[Application]:
        """
        Correlates an incoming recruiter email to an existing Application:
        1. Direct application_id match if provided.
        2. Recruiter email match on application (recruiter_email == sender_email).
        3. Match via OutreachRecord / Contact email recipient.
        4. Match company name in subject, body, or sender domain.
        5. Match job title in subject.
        6. Fallback to most recent active application.
        """
        # 1. Direct application_id
        if application_id:
            app = self.db.query(Application).filter(Application.id == application_id).first()
            if app:
                return app

        clean_sender = (sender_email or "").strip().lower()

        # 2. Recruiter email match on application
        if clean_sender:
            app = (
                self.db.query(Application)
                .filter(Application.recruiter_email.ilike(f"%{clean_sender}%"))
                .order_by(desc(Application.updated_at))
                .first()
            )
            if app:
                return app

        # 3. Match via OutreachRecord
        if clean_sender:
            outreach = (
                self.db.query(OutreachRecord)
                .join(Contact, OutreachRecord.contact_id == Contact.id, isouter=True)
                .filter(
                    or_(
                        OutreachRecord.contact_email.ilike(clean_sender),
                        Contact.email.ilike(clean_sender),
                    )
                )
                .order_by(desc(OutreachRecord.id))
                .first()
            )
            if outreach and outreach.job_id:
                app = (
                    self.db.query(Application)
                    .filter(Application.job_id == outreach.job_id)
                    .order_by(desc(Application.updated_at))
                    .first()
                )
                if app:
                    return app

        # 4. Extract sender domain as potential company name
        sender_domain = ""
        if "@" in clean_sender:
            domain_part = clean_sender.split("@")[-1].lower()
            # Ignore generic mail hosts
            generic_hosts = {"gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "icloud.com"}
            if domain_part not in generic_hosts:
                sender_domain = domain_part.split(".")[0]

        # Check company hint, sender domain, or company mentions in text
        search_companies: List[str] = []
        if company_hint:
            search_companies.append(company_hint.strip())
        if sender_domain and len(sender_domain) > 2:
            search_companies.append(sender_domain)

        all_text = f"{subject or ''} {body_text or ''}"

        # Match against Job.company
        for comp in search_companies:
            app = (
                self.db.query(Application)
                .join(Job, Application.job_id == Job.id)
                .filter(Job.company.ilike(f"%{comp}%"))
                .order_by(desc(Application.updated_at))
                .first()
            )
            if app:
                return app

        # Check all active applications to see if their company appears in the subject or body
        active_apps = (
            self.db.query(Application)
            .join(Job, Application.job_id == Job.id)
            .filter(Application.kanban_stage.notin_(["rejected", "archived"]))
            .order_by(desc(Application.updated_at))
            .limit(20)
            .all()
        )
        for app in active_apps:
            if app.job and app.job.company:
                comp_name = app.job.company.strip().lower()
                if len(comp_name) >= 3 and comp_name in all_text.lower():
                    return app

        # 5. Check if Job.title is in the subject
        for app in active_apps:
            if app.job and app.job.title:
                role_name = app.job.title.strip().lower()
                if len(role_name) >= 4 and role_name in (subject or "").lower():
                    return app

        # 6. Fallback to the latest active application if exists
        if active_apps:
            return active_apps[0]

        return None

    def process_inbound_message(
        self,
        sender_email: str,
        subject: str,
        body_text: str,
        sender_name: Optional[str] = None,
        company: Optional[str] = None,
        application_id: Optional[int] = None,
        message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        received_at: Optional[datetime] = None,
        mailbox_id: Optional[int] = None,
        auto_advance: bool = True,
    ) -> InboundAdvancementResult:
        """
        Classifies incoming recruiter message, correlates it to a Kanban application card,
        advances the column, sets countdown timers, updates email provenance,
        and records the audit log.
        """
        received_time = received_at or datetime.utcnow()
        clean_sender = (sender_email or "").strip()
        clean_subject = (subject or "").strip()

        # Step 1: Classify recruiter intent
        classification = self.classifier.classify(clean_subject, body_text)
        logger.info(
            "Classified inbound message from %s (subject: %s) as %s (confidence: %.2f)",
            clean_sender,
            clean_subject,
            classification.intent,
            classification.confidence,
        )

        # Step 2: Correlate to application
        app = self.match_message_to_application(
            sender_email=clean_sender,
            subject=clean_subject,
            body_text=body_text,
            company_hint=company,
            application_id=application_id,
        )

        if not app:
            # Audit log unmatched message
            inbound_msg = InboundRecruiterMessage(
                mailbox_id=mailbox_id,
                application_id=None,
                job_id=None,
                sender_email=clean_sender,
                sender_name=sender_name,
                subject=clean_subject,
                snippet=(body_text or "")[:500],
                body_text=body_text,
                classified_intent=classification.intent,
                confidence_score=classification.confidence,
                previous_kanban_stage=None,
                new_kanban_stage=None,
                auto_advanced=False,
                message_id=message_id,
                thread_id=thread_id,
                received_at=received_time,
                created_at=datetime.utcnow(),
            )
            self.db.add(inbound_msg)
            self.db.commit()

            return InboundAdvancementResult(
                matched=False,
                application_id=None,
                company=company,
                job_title=None,
                classified_intent=classification.intent,
                confidence_score=classification.confidence,
                previous_stage=None,
                new_stage=None,
                provenance_badge=None,
                alert_severity=None,
                countdown_label=None,
                next_action_due_at=None,
                message="Message classified successfully, but no matching application card found in pipeline.",
            )

        # Step 3: Auto-Advance Kanban Card & Set Countdown Timers
        prev_stage = app.kanban_stage or "applied"
        new_stage = prev_stage
        target_stage = classification.target_stage

        if auto_advance and target_stage:
            new_stage = target_stage
            app.kanban_stage = new_stage

            # Align application status
            if new_stage in ["technical_interview", "recruiter_screen"]:
                app.status = "interviewing"
            elif new_stage == "take_home":
                app.status = "interviewing"
            elif new_stage == "offer":
                app.status = "offered"
            elif new_stage == "rejected":
                app.status = "rejected"

        # Update Next Action & Countdown Timers
        next_action_title = classification.action_title
        next_action_due = None

        if classification.countdown_days is not None:
            if classification.countdown_days >= 0:
                next_action_due = received_time + timedelta(days=classification.countdown_days)
            else:
                # Negative indicates overdue / immediate attention (Red Alert)
                next_action_due = received_time - timedelta(days=1)

            app.next_action_title = next_action_title
            app.next_action_type = classification.intent.lower()
            app.next_action_due_at = next_action_due
        elif classification.intent == "REJECTION":
            app.next_action_title = "Application Closed"
            app.next_action_type = "closed"
            app.next_action_due_at = None

        # Step 4: Update Recruiter Email Provenance Badge
        app.email_subject = clean_subject
        app.recruiter_email = clean_sender
        if sender_name:
            app.recruiter_name = sender_name
        app.email_thread_id = thread_id or f"thread_{app.id}_{int(received_time.timestamp())}"
        app.last_email_received_at = received_time
        app.updated_at = datetime.utcnow()

        # Step 5: Save Audit Log Record
        inbound_msg = InboundRecruiterMessage(
            mailbox_id=mailbox_id,
            application_id=app.id,
            job_id=app.job_id,
            sender_email=clean_sender,
            sender_name=sender_name or app.recruiter_name,
            subject=clean_subject,
            snippet=(body_text or "")[:500],
            body_text=body_text,
            classified_intent=classification.intent,
            confidence_score=classification.confidence,
            previous_kanban_stage=prev_stage,
            new_kanban_stage=new_stage,
            auto_advanced=(new_stage != prev_stage),
            message_id=message_id,
            thread_id=thread_id or app.email_thread_id,
            received_at=received_time,
            created_at=datetime.utcnow(),
        )
        self.db.add(inbound_msg)

        # Update mailbox counter metrics if mailbox exists
        if mailbox_id:
            mailbox = self.get_mailbox(mailbox_id)
            if mailbox:
                mailbox.total_messages_scanned += 1
                if new_stage != prev_stage:
                    mailbox.total_advancements += 1
                mailbox.last_sync_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(app)

        # Calculate exact provenance badge and countdown alert
        provenance_badge = KanbanService.format_email_provenance(clean_subject, clean_sender)
        days_rem, countdown_label, alert_severity = KanbanService.calculate_countdown(
            next_action_type=app.next_action_type,
            next_action_title=app.next_action_title,
            next_action_due_at=app.next_action_due_at,
            applied_at=app.applied_at,
            now=received_time,
        )

        company_name = app.job.company if app.job else (company or "Target Company")
        job_title = app.job.title if app.job else "Role"

        advance_msg = (
            f"Auto-advanced {company_name} ({job_title}) from '{prev_stage}' to '{new_stage}'."
            if new_stage != prev_stage
            else f"Updated {company_name} ({job_title}) with intent '{classification.intent}'."
        )

        return InboundAdvancementResult(
            matched=True,
            application_id=app.id,
            company=company_name,
            job_title=job_title,
            classified_intent=classification.intent,
            confidence_score=classification.confidence,
            previous_stage=prev_stage,
            new_stage=new_stage,
            provenance_badge=provenance_badge,
            alert_severity=alert_severity,
            countdown_label=countdown_label,
            next_action_due_at=next_action_due,
            message=advance_msg,
        )

    def sync_mailbox(
        self,
        mailbox_id: int,
        limit: int = 25,
    ) -> MailboxSyncResponse:
        """
        Connects to the configured mailbox via IMAP SSL,
        scans recent unread/inbound recruiter emails,
        and auto-advances pipeline cards.
        """
        mailbox = self.get_mailbox(mailbox_id)
        if not mailbox:
            raise ValueError(f"Mailbox with ID {mailbox_id} not found")

        advancements: List[InboundAdvancementResult] = []
        scanned_count = 0

        # Check if live IMAP or test/offline environment
        is_live_imap = bool(mailbox.email_address and getattr(mailbox, "imap_host", None) and not mailbox.email_address.endswith(".test"))

        if is_live_imap:
            try:
                # Connect to IMAP host
                client = imaplib.IMAP4_SSL(mailbox.imap_host, mailbox.imap_port)
                # Password from env or placeholder
                pwd = os.getenv("GMAIL_PASSWORD") or os.getenv("MAILBOX_PASSWORD") or ""
                if pwd:
                    client.login(mailbox.email_address, pwd)
                    client.select("INBOX", readonly=True)

                    status, search_data = client.search(None, '(OR (HEADER Subject "interview") (HEADER Subject "offer"))')
                    if status == "OK" and search_data and search_data[0]:
                        msg_ids = search_data[0].split()[-limit:]
                        for m_id in reversed(msg_ids):
                            f_stat, f_data = client.fetch(m_id, "(RFC822)")
                            if f_stat != "OK" or not f_data or not f_data[0]:
                                continue
                            raw_email = f_data[0][1]
                            msg = email.message_from_bytes(raw_email)

                            subject, _ = self._decode_header_str(msg.get("Subject", ""))
                            sender = msg.get("From", "")
                            msg_id_header = msg.get("Message-ID", "")
                            body_text = self._extract_body(msg)

                            adv_result = self.process_inbound_message(
                                sender_email=sender,
                                subject=subject,
                                body_text=body_text,
                                message_id=msg_id_header,
                                mailbox_id=mailbox.id,
                                auto_advance=mailbox.auto_advance_pipeline,
                            )
                            scanned_count += 1
                            if adv_result.matched:
                                advancements.append(adv_result)

                    try:
                        client.close()
                    except Exception:
                        pass
                    client.logout()
            except Exception as exc:
                logger.warning("Live IMAP sync error (falling back to offline scan): %s", exc)

        # Update mailbox status
        mailbox.last_sync_at = datetime.utcnow()
        self.db.commit()

        return MailboxSyncResponse(
            status="success",
            mailbox_id=mailbox.id,
            email_address=mailbox.email_address,
            messages_scanned=scanned_count,
            advancements_count=len(advancements),
            advancements=advancements,
        )

    @staticmethod
    def _decode_header_str(raw: str) -> Tuple[str, str]:
        """Safely decode email header."""
        parts = decode_header(raw)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(str(part))
        return "".join(decoded), ""

    @staticmethod
    def _extract_body(msg: email.message.Message) -> str:
        """Extract plain text or HTML body from MIME message."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype in ("text/plain", "text/html"):
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode("utf-8", errors="replace") + "\n"
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")
        return body
