"""
src/services/kanban_service.py
Service for Kanban Application Tracker with Countdown Timers and Recruiter Email Provenance Badges.
Powers time-sensitive action alerts (🟡 Amber in 1-3d, 🔵 Blue in 4-7d, 🔴 Red overdue)
and recruiter email provenance badges.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_, and_, desc, asc, text
from sqlalchemy.orm import Session

from src.models import Application, Job, OutreachRecord, Contact
from src.api_models import (
    KanbanCardResponse,
    KanbanBoardResponse,
    KanbanNextActionRequest,
    KanbanEmailProvenanceRequest,
    KanbanStageTransitionRequest,
)

logger = logging.getLogger("kanban_service")

# Canonical Kanban Column Stages
KANBAN_COLUMNS = [
    {"id": "saved", "title": "Saved / Target Roles", "color": "#94A3B8"},
    {"id": "applied", "title": "Applied / Submitted", "color": "#00F0FF"},
    {"id": "recruiter_screen", "title": "Recruiter Screen", "color": "#A855F7"},
    {"id": "technical_interview", "title": "Technical Interview", "color": "#FFE600"},
    {"id": "take_home", "title": "Take-Home Assignment", "color": "#3B82F6"},
    {"id": "offer", "title": "Offer / Negotiation", "color": "#00FFA3"},
    {"id": "rejected", "title": "Archived / Closed", "color": "#64748B"},
]


def ensure_kanban_schema(db: Session) -> None:
    """
    Ensure SQLite applications table has all required columns for Kanban,
    countdown timers, and recruiter email thread provenance.
    """
    try:
        cursor = db.connection().connection.cursor()
        cursor.execute("PRAGMA table_info(applications)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        col_defs = [
            ("kanban_stage", "VARCHAR(50) DEFAULT 'applied'"),
            ("kanban_order", "INTEGER DEFAULT 0"),
            ("next_action_type", "VARCHAR(50)"),
            ("next_action_title", "VARCHAR(255)"),
            ("next_action_due_at", "DATETIME"),
            ("recruiter_name", "VARCHAR(255)"),
            ("recruiter_email", "VARCHAR(255)"),
            ("recruiter_company", "VARCHAR(255)"),
            ("email_subject", "VARCHAR(500)"),
            ("email_thread_id", "VARCHAR(255)"),
            ("last_email_received_at", "DATETIME"),
        ]

        for col_name, col_type in col_defs:
            if col_name not in existing_cols:
                db.execute(text(f"ALTER TABLE applications ADD COLUMN {col_name} {col_type}"))
                logger.info("Migrated applications table: added column %s", col_name)

        db.commit()
    except Exception as exc:
        logger.warning("Kanban schema check / migration note: %s", exc)


class KanbanService:
    """Orchestrates countdown alerts, recruiter thread provenance, and Kanban stages."""

    def __init__(self, db: Session):
        self.db = db
        ensure_kanban_schema(db)

    @staticmethod
    def calculate_countdown(
        next_action_type: Optional[str],
        next_action_title: Optional[str],
        next_action_due_at: Optional[datetime],
        applied_at: Optional[datetime] = None,
        now: Optional[datetime] = None,
    ) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """
        Calculate countdown time, label, and alert severity.
        
        Returns:
            (days_remaining, countdown_label, alert_severity)
            where alert_severity is 'amber', 'blue', 'red', 'neutral', or None.
        """
        current_time = now or datetime.utcnow()

        if next_action_due_at is not None:
            # Normalize to naive UTC for consistent timedelta calculation
            due = next_action_due_at.replace(tzinfo=None) if next_action_due_at.tzinfo else next_action_due_at
            now_dt = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
            
            diff_seconds = (due - now_dt).total_seconds()
            days_remaining = round(diff_seconds / 86400.0, 1)
            title = next_action_title or "Next Action"

            # 🔴 Red: Overdue (0 or negative days)
            if days_remaining <= 0:
                return (days_remaining, "Overdue / Follow-up required", "red")

            # 🟡 Amber: Next action in 1 to 3 days
            if days_remaining <= 3.0:
                days_int = max(1, int(round(days_remaining)))
                day_word = "day" if days_int == 1 else "days"
                label = f"Next: {title} in {days_int} {day_word}"
                return (days_remaining, label, "amber")

            # 🔵 Blue: Next action in 4 to 7 days
            if days_remaining <= 7.0:
                days_int = int(round(days_remaining))
                label = f"Next: {title} in {days_int} days"
                return (days_remaining, label, "blue")

            # Neutral: More than 7 days ahead
            days_int = int(round(days_remaining))
            label = f"Next: {title} in {days_int} days"
            return (days_remaining, label, "neutral")

        # Fallback if no next_action_due_at, check if overdue for follow-up (> 7 days since application)
        if applied_at is not None:
            applied = applied_at.replace(tzinfo=None) if applied_at.tzinfo else applied_at
            now_dt = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
            since_applied = (now_dt - applied).total_seconds() / 86400.0
            if since_applied > 7.0:
                return (0.0, "Overdue / Follow-up required", "red")

        return (None, None, None)

    @staticmethod
    def format_email_provenance(
        email_subject: Optional[str],
        recruiter_email: Optional[str],
    ) -> Optional[str]:
        """Format the exact email provenance badge."""
        if email_subject and recruiter_email:
            return f'"{email_subject}" from {recruiter_email}'
        if email_subject:
            return f'"{email_subject}"'
        if recruiter_email:
            return f"Thread with {recruiter_email}"
        return None

    def to_card_response(
        self,
        app: Application,
        job: Optional[Job] = None,
        now: Optional[datetime] = None,
    ) -> KanbanCardResponse:
        """Map Application and Job ORM models into KanbanCardResponse DTO."""
        j = job or app.job
        job_id = app.job_id
        job_title = j.title if j else "Software Engineer"
        company = j.company if j else "Hiring Company"
        location = j.location if j else "Remote"
        work_mode = j.work_mode if j else "remote"
        salary_min = j.salary_min if j else None
        salary_max = j.salary_max if j else None
        salary_currency = j.salary_currency if j else "USD"
        match_score = app.match_score

        # Auto-fallback for provenance badge from OutreachRecord if not explicitly on Application
        email_subj = app.email_subject
        recruiter_mail = app.recruiter_email
        recruiter_name = app.recruiter_name
        recruiter_comp = app.recruiter_company

        if not email_subj or not recruiter_mail:
            outreach = (
                self.db.query(OutreachRecord)
                .filter(OutreachRecord.job_id == job_id)
                .order_by(desc(OutreachRecord.replied_at), desc(OutreachRecord.sent_at))
                .first()
            )
            if outreach:
                if not email_subj and outreach.subject:
                    email_subj = f"Re: {outreach.subject}" if not outreach.subject.lower().startswith("re:") else outreach.subject
                if not recruiter_mail and outreach.contact_email:
                    recruiter_mail = outreach.contact_email
                if not recruiter_name and outreach.contact_name:
                    recruiter_name = outreach.contact_name

        days_remaining, countdown_label, alert_severity = self.calculate_countdown(
            next_action_type=app.next_action_type,
            next_action_title=app.next_action_title,
            next_action_due_at=app.next_action_due_at,
            applied_at=app.applied_at,
            now=now,
        )

        provenance_badge = self.format_email_provenance(email_subj, recruiter_mail)
        stage = (app.kanban_stage or app.status or "applied").lower()
        if stage in ("pending", "ready"):
            stage = "applied"

        return KanbanCardResponse(
            id=app.id,
            job_id=job_id,
            job_title=job_title,
            company=company,
            location=location,
            work_mode=work_mode,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            match_score=match_score,
            status=app.status or "applied",
            kanban_stage=stage,
            kanban_order=app.kanban_order or 0,
            next_action_type=app.next_action_type,
            next_action_title=app.next_action_title,
            next_action_due_at=app.next_action_due_at,
            days_remaining=days_remaining,
            countdown_label=countdown_label,
            alert_severity=alert_severity,
            recruiter_name=recruiter_name,
            recruiter_email=recruiter_mail,
            recruiter_company=recruiter_comp or company,
            email_subject=email_subj,
            email_thread_id=app.email_thread_id,
            last_email_received_at=app.last_email_received_at,
            provenance_badge=provenance_badge,
            applied_at=app.applied_at,
            created_at=app.created_at or datetime.utcnow(),
            updated_at=app.updated_at or datetime.utcnow(),
        )

    def get_board(self, user_id: Optional[int] = None) -> KanbanBoardResponse:
        """Fetch all applications partitioned into canonical columns with counters."""
        query = self.db.query(Application).join(Job)
        if user_id is not None:
            query = query.filter(Application.user_id == user_id)

        applications = query.order_by(asc(Application.kanban_order), desc(Application.updated_at)).all()

        column_dict: Dict[str, List[KanbanCardResponse]] = {
            col["id"]: [] for col in KANBAN_COLUMNS
        }

        amber_count = 0
        blue_count = 0
        red_count = 0
        active_countdown_count = 0

        for app in applications:
            card = self.to_card_response(app)
            stage_key = card.kanban_stage if card.kanban_stage in column_dict else "applied"
            column_dict[stage_key].append(card)

            if card.alert_severity:
                active_countdown_count += 1
                if card.alert_severity == "amber":
                    amber_count += 1
                elif card.alert_severity == "blue":
                    blue_count += 1
                elif card.alert_severity == "red":
                    red_count += 1

        return KanbanBoardResponse(
            status="success",
            total_applications=len(applications),
            active_countdown_alerts=active_countdown_count,
            amber_count=amber_count,
            blue_count=blue_count,
            red_count=red_count,
            columns=column_dict,
            column_metadata=KANBAN_COLUMNS,
        )

    def get_cards(
        self,
        stage: Optional[str] = None,
        alert_severity: Optional[str] = None,
        overdue_only: bool = False,
    ) -> List[KanbanCardResponse]:
        """Fetch flat list of cards with optional filtering."""
        query = self.db.query(Application).join(Job)
        if stage:
            query = query.filter(Application.kanban_stage == stage.lower())

        apps = query.order_by(asc(Application.kanban_order), desc(Application.updated_at)).all()
        cards = [self.to_card_response(a) for a in apps]

        if overdue_only:
            cards = [c for c in cards if c.alert_severity == "red"]
        elif alert_severity:
            cards = [c for c in cards if c.alert_severity == alert_severity.lower()]

        return cards

    def transition_stage(
        self,
        application_id: int,
        target_stage: str,
        order: int = 0,
    ) -> KanbanCardResponse:
        """Update Kanban column stage and ordering sequence."""
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        valid_stages = {col["id"] for col in KANBAN_COLUMNS}
        normalized_stage = target_stage.lower()
        if normalized_stage not in valid_stages:
            normalized_stage = "applied"

        app.kanban_stage = normalized_stage
        app.kanban_order = order
        app.status = normalized_stage
        app.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(app)
        return self.to_card_response(app)

    def set_next_action(
        self,
        application_id: int,
        action_type: str,
        action_title: str,
        due_at: datetime,
    ) -> KanbanCardResponse:
        """Schedule or update countdown timer next action."""
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        app.next_action_type = action_type
        app.next_action_title = action_title
        app.next_action_due_at = due_at
        app.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(app)
        return self.to_card_response(app)

    def set_email_provenance(
        self,
        application_id: int,
        recruiter_email: str,
        email_subject: str,
        recruiter_name: Optional[str] = None,
        recruiter_company: Optional[str] = None,
        thread_id: Optional[str] = None,
        received_at: Optional[datetime] = None,
    ) -> KanbanCardResponse:
        """Link recruiter email thread provenance directly to application card."""
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        app.recruiter_email = recruiter_email
        app.email_subject = email_subject
        if recruiter_name:
            app.recruiter_name = recruiter_name
        if recruiter_company:
            app.recruiter_company = recruiter_company
        if thread_id:
            app.email_thread_id = thread_id
        app.last_email_received_at = received_at or datetime.utcnow()
        app.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(app)
        return self.to_card_response(app)

    def seed_sample_kanban(self) -> KanbanBoardResponse:
        """Seed realistic amber, blue, and red countdown cards with recruiter email provenance."""
        now = datetime.utcnow()

        # Check or create 3 sample jobs
        sample_jobs_data = [
            {
                "job_id": "seed_tessellate_01",
                "title": "Senior Frontend Engineer",
                "company": "Tessellate.io",
                "location": "Bengaluru (Hybrid)",
                "work_mode": "hybrid",
                "source": "greenhouse",
                "salary_min": 140000,
                "salary_max": 180000,
                "stage": "technical_interview",
                "action_type": "technical_interview",
                "action_title": "Technical Interview",
                "due_at": now + timedelta(days=3),  # 🟡 Amber
                "recruiter_email": "recruiter@tessellate.io",
                "recruiter_name": "Sarah Lin",
                "subject": "Re: Interview invitation — Senior Frontend Engineer",
            },
            {
                "job_id": "seed_vercel_02",
                "title": "Full Stack Engineer (Next.js / AI)",
                "company": "Vercel",
                "location": "Remote",
                "work_mode": "remote",
                "source": "lever",
                "salary_min": 160000,
                "salary_max": 200000,
                "stage": "take_home",
                "action_type": "take_home",
                "action_title": "Take-home assessment",
                "due_at": now + timedelta(days=6),  # 🔵 Blue
                "recruiter_email": "talent@vercel.com",
                "recruiter_name": "Guillermo Hiring Team",
                "subject": "Take-home Assessment Assignment — Full Stack Engineer",
            },
            {
                "job_id": "seed_databricks_03",
                "title": "Distributed Systems Infrastructure Engineer",
                "company": "Databricks",
                "location": "San Francisco, CA",
                "work_mode": "onsite",
                "source": "greenhouse",
                "salary_min": 190000,
                "salary_max": 240000,
                "stage": "applied",
                "action_type": "follow_up",
                "action_title": "Follow-up required",
                "due_at": now - timedelta(days=1),  # 🔴 Red (Overdue)
                "recruiter_email": "careers@databricks.com",
                "recruiter_name": "Ali Staffing",
                "subject": "Application Received — Databricks Systems",
            },
        ]

        for s in sample_jobs_data:
            existing_job = self.db.query(Job).filter(Job.job_id == s["job_id"]).first()
            if not existing_job:
                existing_job = Job(
                    job_id=s["job_id"],
                    title=s["title"],
                    company=s["company"],
                    location=s["location"],
                    work_mode=s["work_mode"],
                    source=s["source"],
                    salary_min=s["salary_min"],
                    salary_max=s["salary_max"],
                    fetched_at=now,
                )
                self.db.add(existing_job)
                self.db.commit()
                self.db.refresh(existing_job)

            existing_app = self.db.query(Application).filter(Application.job_id == existing_job.id).first()
            if not existing_app:
                existing_app = Application(
                    job_id=existing_job.id,
                    match_score=92.0,
                    status=s["stage"],
                    kanban_stage=s["stage"],
                    kanban_order=1,
                    next_action_type=s["action_type"],
                    next_action_title=s["action_title"],
                    next_action_due_at=s["due_at"],
                    recruiter_email=s["recruiter_email"],
                    recruiter_name=s["recruiter_name"],
                    recruiter_company=s["company"],
                    email_subject=s["subject"],
                    applied_at=now - timedelta(days=5),
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(existing_app)
            else:
                existing_app.kanban_stage = s["stage"]
                existing_app.next_action_type = s["action_type"]
                existing_app.next_action_title = s["action_title"]
                existing_app.next_action_due_at = s["due_at"]
                existing_app.recruiter_email = s["recruiter_email"]
                existing_app.recruiter_name = s["recruiter_name"]
                existing_app.recruiter_company = s["company"]
                existing_app.email_subject = s["subject"]
                existing_app.updated_at = now

        self.db.commit()
        return self.get_board()
