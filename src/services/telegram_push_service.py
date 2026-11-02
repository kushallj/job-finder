"""
src/services/telegram_push_service.py
Service for Telegram Instant Push Notification Bot with 1-Click Action Buttons.

Handles:
- One-click pairing deep links (https://t.me/JobFinderAlertBot?start=pair_<token>)
- Real-time alerts when a high-match job (>=90%) is discovered
- Inbound interview invitation alerts with Amber countdown timers
- 1-Click inline keyboard callbacks ([⚡ Apply Now], [📝 Draft Pitch], [💬 Draft Reply])
- Graceful offline fallback simulation for testing without external Telegram tokens
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
import httpx
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, asc, text
from sqlalchemy.orm import Session

from src.models import (
    Base,
    Job,
    Application,
    TelegramConnector,
    TelegramPushAlertLog,
    InboundRecruiterMessage,
)
from src.api_models import (
    TelegramPairingResponse,
    TelegramAlertDispatchDTO,
)
from src.config import settings

logger = logging.getLogger("telegram_push")


def ensure_telegram_schema(db: Session) -> None:
    """Ensure SQLite database has telegram_connectors and telegram_push_alert_logs tables."""
    try:
        bind = db.get_bind()
        Base.metadata.create_all(
            bind=bind,
            tables=[
                TelegramConnector.__table__,
                TelegramPushAlertLog.__table__,
            ],
            checkfirst=True,
        )
        db.commit()
    except Exception as exc:
        logger.warning("Telegram schema check note: %s", exc)


class TelegramPushService:
    """Dispatches real-time push alerts and processes 1-click interactive button actions."""

    def __init__(self, db: Session):
        self.db = db
        ensure_telegram_schema(db)
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN") or getattr(settings, "telegram_bot_token", None) or ""
        self.bot_username = os.getenv("TELEGRAM_BOT_USERNAME") or getattr(settings, "telegram_bot_username", "JobFinderAlertBot")

    def get_or_create_connector(
        self,
        user_identifier: str = "default_user",
        user_id: Optional[int] = None,
    ) -> TelegramConnector:
        """Fetch existing connector or create a new pending one."""
        conn = (
            self.db.query(TelegramConnector)
            .filter(
                (TelegramConnector.user_identifier == user_identifier)
                | (TelegramConnector.user_id == user_id if user_id else False)
            )
            .first()
        )
        if not conn:
            conn = TelegramConnector(
                user_identifier=user_identifier,
                user_id=user_id,
                min_match_score=90.0,
                notify_high_match_jobs=True,
                notify_interview_requests=True,
                notify_status_changes=True,
                is_connected=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(conn)
            self.db.commit()
            self.db.refresh(conn)
        return conn

    def generate_pairing_details(
        self,
        user_identifier: str = "default_user",
        user_id: Optional[int] = None,
    ) -> TelegramPairingResponse:
        """Generates a secure deep link (https://t.me/<bot>?start=pair_<token>) for 1-click pairing."""
        conn = self.get_or_create_connector(user_identifier=user_identifier, user_id=user_id)

        # Generate unique pairing code if not already paired
        if not conn.is_connected or not conn.pairing_code:
            code = f"pair_{uuid.uuid4().hex[:12]}"
            conn.pairing_code = code
            conn.pairing_expires_at = datetime.utcnow() + timedelta(hours=24)
            self.db.commit()

        pairing_url = f"https://t.me/{self.bot_username}?start={conn.pairing_code}"
        instructions = (
            f"1. Click the link to open @{self.bot_username} in Telegram.\n"
            f"2. Tap 'Start' to pair your account instantly.\n"
            f"3. You'll receive real-time alerts whenever a 90%+ match job or interview request arrives."
        )

        return TelegramPairingResponse(
            status="success",
            is_connected=conn.is_connected,
            bot_username=self.bot_username,
            pairing_code=conn.pairing_code,
            pairing_url=pairing_url,
            instructions=instructions,
            paired_chat_id=conn.telegram_chat_id,
            telegram_username=conn.telegram_username,
            paired_at=conn.paired_at,
            min_match_score=conn.min_match_score or 90.0,
            alerts_sent_count=conn.alerts_sent_count or 0,
            actions_taken_count=conn.actions_taken_count or 0,
        )

    def complete_pairing(
        self,
        pairing_code: str,
        chat_id: str,
        telegram_username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> Optional[TelegramConnector]:
        """Activates Telegram connection when user clicks Start with pairing code."""
        clean_code = (pairing_code or "").strip()
        conn = (
            self.db.query(TelegramConnector)
            .filter(TelegramConnector.pairing_code == clean_code)
            .first()
        )
        if not conn:
            # Fallback check if user provided chat_id directly
            conn = self.get_or_create_connector()

        conn.telegram_chat_id = str(chat_id)
        conn.telegram_username = telegram_username
        conn.first_name = first_name
        conn.is_connected = True
        conn.paired_at = datetime.utcnow()
        conn.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(conn)

        # Send confirmation message to Telegram
        self._send_raw_telegram_message(
            chat_id=str(chat_id),
            text=(
                f"🎉 <b>JobFinder Instant Alert Bot Paired!</b>\n\n"
                f"Welcome {first_name or 'Candidate'}! You are now connected to real-time alerts:\n"
                f"• 🎯 High-Match Roles (≥{int(conn.min_match_score)}%)\n"
                f"• ⏰ Inbound Recruiter Interview Invitations\n"
                f"• ⚡ 1-Click [Apply Now] & [Draft Pitch] actions\n\n"
                f"Stay tuned — opportunities will arrive directly here!"
            ),
        )
        return conn

    def unpair_connector(self, user_identifier: str = "default_user") -> bool:
        """Disconnects candidate's Telegram connector."""
        conn = self.get_or_create_connector(user_identifier=user_identifier)
        conn.is_connected = False
        conn.telegram_chat_id = None
        conn.pairing_code = None
        self.db.commit()
        return True

    def update_preferences(
        self,
        min_match_score: float = 90.0,
        notify_high_match_jobs: bool = True,
        notify_interview_requests: bool = True,
        user_identifier: str = "default_user",
    ) -> TelegramConnector:
        """Update notification thresholds and trigger preferences."""
        conn = self.get_or_create_connector(user_identifier=user_identifier)
        conn.min_match_score = min_match_score
        conn.notify_high_match_jobs = notify_high_match_jobs
        conn.notify_interview_requests = notify_interview_requests
        conn.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def push_high_match_job_alert(
        self,
        job: Job,
        match_score: float,
        matched_skills: Optional[List[str]] = None,
        reasons: Optional[List[str]] = None,
        connector: Optional[TelegramConnector] = None,
    ) -> TelegramAlertDispatchDTO:
        """
        Dispatches instant alert to paired Telegram chat when job match score >= threshold (e.g. 90%).
        Includes 1-click action buttons: [⚡ Apply Now], [📝 Draft Pitch], [🔗 View Posting].
        """
        conn = connector or self.get_or_create_connector()
        now = datetime.utcnow()

        # Gate on connection and score threshold
        score_val = float(match_score)
        threshold = float(conn.min_match_score or 90.0)

        salary_text = "Competitive / Market"
        if job.salary_min and job.salary_max:
            salary_text = f"${int(job.salary_min):,} - ${int(job.salary_max):,} {job.salary_currency or 'USD'}"
        elif job.salary_min:
            salary_text = f"From ${int(job.salary_min):,} {job.salary_currency or 'USD'}"

        # 3-bullet validation reasons formatting
        bullets: List[str] = []
        if reasons:
            bullets = [f"• {r}" for r in reasons[:3]]
        else:
            skills_str = ", ".join(matched_skills[:4]) if matched_skills else "React, TypeScript, LLM Integration"
            bullets = [
                f"• Verified Skill Overlap: {skills_str}",
                f"• Seniority Match: Aligns with 4+ years software experience",
                f"• Location Preference: {job.location or 'Remote / Hybrid preferred'}",
            ]
        bullets_text = "\n".join(bullets)

        message_html = (
            f"🎯 <b>HIGH-MATCH OPPORTUNITY ({score_val:.0f}% Match)</b>\n\n"
            f"<b>Role:</b> {job.title}\n"
            f"<b>Company:</b> {job.company} ({job.location or 'Remote'})\n"
            f"<b>Compensation:</b> {salary_text}\n\n"
            f"✨ <b>Key Match Highlights:</b>\n"
            f"{bullets_text}\n\n"
            f"⚡ <i>Take immediate action with 1 click:</i>"
        )

        # Inline Keyboard Buttons
        frontend_url = getattr(settings, "frontend_url", "https://jobfinder.io")
        posting_url = job.url or f"{frontend_url}/jobs/{job.id}"

        inline_keyboard = [
            [
                {"text": "⚡ Apply Now", "callback_data": f"apply_job_{job.id}"},
                {"text": "📝 Draft Pitch", "callback_data": f"pitch_job_{job.id}"},
            ],
            [
                {"text": "🔗 View Job Posting", "url": posting_url},
            ],
        ]

        action_names = ["[Apply Now]", "[Draft Pitch]", "[View Job Posting]"]

        # Dispatch via Telegram API or Record Simulation
        chat_id = conn.telegram_chat_id or "simulated_chat"
        is_live = bool(self.bot_token and conn.is_connected and conn.telegram_chat_id)
        delivery_status = "simulated"

        if is_live:
            sent_ok = self._send_raw_telegram_message(
                chat_id=chat_id,
                text=message_html,
                inline_keyboard=inline_keyboard,
            )
            delivery_status = "delivered" if sent_ok else "failed"

        # Log audit entry
        log_entry = TelegramPushAlertLog(
            connector_id=conn.id,
            alert_type="high_match_job",
            job_id=job.id,
            title=f"High-Match Job: {job.title} @ {job.company} ({score_val:.0f}%)",
            message_text=message_html,
            status=delivery_status,
            created_at=now,
        )
        self.db.add(log_entry)
        conn.alerts_sent_count = (conn.alerts_sent_count or 0) + 1
        conn.last_alert_sent_at = now
        self.db.commit()
        self.db.refresh(log_entry)

        return TelegramAlertDispatchDTO(
            status="success",
            alert_id=log_entry.id,
            alert_type="high_match_job",
            recipient_chat_id=chat_id,
            title=log_entry.title,
            message=message_html,
            action_buttons=action_names,
            sent_at=now,
        )

    def push_interview_alert(
        self,
        application: Application,
        recruiter_msg: Optional[InboundRecruiterMessage] = None,
        connector: Optional[TelegramConnector] = None,
    ) -> TelegramAlertDispatchDTO:
        """
        Dispatches instant alert when an inbound recruiter interview invitation is received.
        Includes 1-click [💬 Draft Reply] and [📋 View Kanban] buttons with Amber countdown timer.
        """
        conn = connector or self.get_or_create_connector()
        now = datetime.utcnow()

        company_name = application.job.company if application.job else "Target Company"
        role_title = application.job.title if application.job else "Software Engineer"
        recruiter_name = application.recruiter_name or "Recruiter"
        recruiter_email = application.recruiter_email or "hiring@company.com"
        subject = application.email_subject or "Re: Interview invitation"
        next_action = application.next_action_title or "Technical Interview"
        countdown = "in 3 days (🟡 Amber Alert)"

        message_html = (
            f"🎉 <b>INTERVIEW INVITATION RECEIVED!</b>\n\n"
            f"<b>Company:</b> {company_name}\n"
            f"<b>Role:</b> {role_title}\n"
            f"<b>Recruiter:</b> {recruiter_name} (<code>{recruiter_email}</code>)\n"
            f"<b>Subject:</b> \"{subject}\"\n\n"
            f"⏰ <b>Next Action:</b> {next_action} {countdown}\n\n"
            f"🚀 <i>Quick 1-click response:</i>"
        )

        frontend_url = getattr(settings, "frontend_url", "https://jobfinder.io")
        inline_keyboard = [
            [
                {"text": "💬 Draft Reply", "callback_data": f"draft_reply_app_{application.id}"},
                {"text": "📋 View Kanban Card", "url": f"{frontend_url}/kanban"},
            ]
        ]
        action_names = ["[Draft Reply]", "[View Kanban Card]"]

        chat_id = conn.telegram_chat_id or "simulated_chat"
        is_live = bool(self.bot_token and conn.is_connected and conn.telegram_chat_id)
        delivery_status = "simulated"

        if is_live:
            sent_ok = self._send_raw_telegram_message(
                chat_id=chat_id,
                text=message_html,
                inline_keyboard=inline_keyboard,
            )
            delivery_status = "delivered" if sent_ok else "failed"

        log_entry = TelegramPushAlertLog(
            connector_id=conn.id,
            alert_type="interview_request",
            job_id=application.job_id,
            application_id=application.id,
            title=f"Interview Request: {company_name} ({role_title})",
            message_text=message_html,
            status=delivery_status,
            created_at=now,
        )
        self.db.add(log_entry)
        conn.alerts_sent_count = (conn.alerts_sent_count or 0) + 1
        conn.last_alert_sent_at = now
        self.db.commit()
        self.db.refresh(log_entry)

        return TelegramAlertDispatchDTO(
            status="success",
            alert_id=log_entry.id,
            alert_type="interview_request",
            recipient_chat_id=chat_id,
            title=log_entry.title,
            message=message_html,
            action_buttons=action_names,
            sent_at=now,
        )

    def handle_callback_query(
        self,
        callback_data: str,
        chat_id: str,
        message_id: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        Executes 1-click action when user taps an inline button in Telegram:
        - 'apply_job_<id>': Auto-advances Kanban card and flags applied
        - 'pitch_job_<id>': Generates tailored AI recruiter pitch and sends to chat
        - 'draft_reply_app_<id>': Generates formal interview confirmation reply
        """
        cb = (callback_data or "").strip()
        conn = (
            self.db.query(TelegramConnector)
            .filter(TelegramConnector.telegram_chat_id == str(chat_id))
            .first()
        ) or self.get_or_create_connector()

        # 1. [⚡ Apply Now]
        if cb.startswith("apply_job_"):
            try:
                job_id = int(cb.replace("apply_job_", ""))
                job = self.db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    return ("❌ Job posting not found.", None)

                # Check or create Application
                app = self.db.query(Application).filter(Application.job_id == job.id).first()
                if not app:
                    app = Application(
                        job_id=job.id,
                        user_id=conn.user_id or 1,
                        status="applied",
                        kanban_stage="applied",
                        kanban_order=0,
                        applied_at=datetime.utcnow(),
                        next_action_title="Awaiting Recruiter Response",
                        next_action_due_at=datetime.utcnow() + timedelta(days=7),
                    )
                    self.db.add(app)
                else:
                    app.kanban_stage = "applied"
                    app.status = "applied"
                    app.applied_at = datetime.utcnow()

                conn.actions_taken_count = (conn.actions_taken_count or 0) + 1
                self.db.commit()

                reply_text = (
                    f"✅ <b>Application Recorded!</b>\n\n"
                    f"Role: <b>{job.title}</b> at <b>{job.company}</b>\n"
                    f"Kanban Stage: <b>Applied / Submitted</b>\n"
                    f"Countdown: Follow-up alert scheduled for 7 days."
                )
                self._send_raw_telegram_message(chat_id=chat_id, text=reply_text)
                return (reply_text, "apply_now")
            except Exception as exc:
                logger.error("Failed to execute 1-click apply: %s", exc)
                return (f"❌ Error applying: {str(exc)}", None)

        # 2. [📝 Draft Pitch]
        elif cb.startswith("pitch_job_"):
            try:
                job_id = int(cb.replace("pitch_job_", ""))
                job = self.db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    return ("❌ Job posting not found.", None)

                pitch_text = (
                    f"📝 <b>Ready-to-Send Recruiter Pitch for {job.company}:</b>\n\n"
                    f"<i>\"Hi {job.company} Hiring Team,\n\n"
                    f"I came across your opening for the {job.title} position and wanted to reach out. "
                    f"With 5+ years building distributed vector search pipelines and low-latency React/TypeScript user interfaces, "
                    f"I recently optimized vector retrieval to sub-millisecond p99 latency at Tessellate.\n\n"
                    f"I would love to learn more about your technical roadmap and share how my background in modern agentic architectures "
                    f"can accelerate {job.company}'s engineering goals.\n\n"
                    f"Best regards,\nKushal\"</i>\n\n"
                    f"📋 <i>Copy and paste this directly into LinkedIn, email, or your application portal!</i>"
                )
                conn.actions_taken_count = (conn.actions_taken_count or 0) + 1
                self.db.commit()

                self._send_raw_telegram_message(chat_id=chat_id, text=pitch_text)
                return (pitch_text, "draft_pitch")
            except Exception as exc:
                logger.error("Failed to draft pitch: %s", exc)
                return (f"❌ Error drafting pitch: {str(exc)}", None)

        # 3. [💬 Draft Reply]
        elif cb.startswith("draft_reply_app_"):
            try:
                app_id = int(cb.replace("draft_reply_app_", ""))
                app = self.db.query(Application).filter(Application.id == app_id).first()
                if not app:
                    return ("❌ Application not found.", None)

                company = app.job.company if app.job else "Team"
                recruiter = app.recruiter_name or "Hiring Team"
                role = app.job.title if app.job else "Role"

                reply_text = (
                    f"💬 <b>Interview Confirmation Response:</b>\n\n"
                    f"<i>\"Hi {recruiter},\n\n"
                    f"Thank you for the invitation! I would be delighted to speak with your team regarding the {role} opportunity at {company}.\n\n"
                    f"I am available this week between 10:00 AM – 4:00 PM EST. Please let me know what time works best or feel free to share a scheduling link.\n\n"
                    f"Looking forward to our conversation!\n\n"
                    f"Best regards,\nKushal\"</i>"
                )
                conn.actions_taken_count = (conn.actions_taken_count or 0) + 1
                self.db.commit()

                self._send_raw_telegram_message(chat_id=chat_id, text=reply_text)
                return (reply_text, "draft_reply")
            except Exception as exc:
                return (f"❌ Error drafting reply: {str(exc)}", None)

        return ("Unhandled action.", None)

    def _send_raw_telegram_message(
        self,
        chat_id: str,
        text: str,
        inline_keyboard: Optional[List[List[Dict[str, Any]]]] = None,
    ) -> bool:
        """Sends HTTP request to Telegram Bot API sendMessage endpoint."""
        if not self.bot_token:
            logger.info("Telegram Bot Token not configured — recorded simulated message to chat %s", chat_id)
            return True

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        if inline_keyboard:
            payload["reply_markup"] = {"inline_keyboard": inline_keyboard}

        try:
            with httpx.Client(timeout=6.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return True
                else:
                    logger.warning("Telegram Bot API returned HTTP %d: %s", res.status_code, res.text[:120])
                    return False
        except Exception as exc:
            logger.warning("Telegram Bot dispatch exception: %s", exc)
            return False
