"""
jobify_applications.py — Application rows <-> the Jobify card shape, plus ghosted sweep.

Contract (jobify/docs/INTEGRATION.md, jobify/src/services/applicationService.js):
  Application = { id, company, position, stage: applied|interview|offer|rejected|ghosted,
                  subject, sender, date, messages, notes, events[{id,title,at}],
                  offer: {salary, deadline} | null, source }

The board replaces `events` and `offer` wholesale on update, so they are stored as JSON.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.contract import iso_utc
from src.models import Application, InboundRecruiterMessage, Job

Stage = Literal["applied", "interview", "offer", "rejected", "ghosted"]
STAGES = ("applied", "interview", "offer", "rejected", "ghosted")
GHOSTED_AFTER_DAYS = 30  # no inbound email for this long while still "applied"


class Event(BaseModel):
    id: str = Field(max_length=64)
    title: str = Field(max_length=200)
    at: str = Field(max_length=40)


class Offer(BaseModel):
    salary: str = Field(default="", max_length=100)
    deadline: str = Field(default="", max_length=20)


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")  # the edit form posts the whole card

    company: str = Field(min_length=1, max_length=200)
    position: str = Field(min_length=1, max_length=200)
    stage: Stage = "applied"
    notes: str = Field(default="", max_length=5000)
    subject: str = Field(default="Added manually", max_length=300)
    sender: str = Field(default="", max_length=300)
    source: Literal["manual", "job", "email"] = "manual"
    jobId: Optional[int] = None


class ApplicationPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: Optional[str] = Field(default=None, min_length=1, max_length=200)
    position: Optional[str] = Field(default=None, min_length=1, max_length=200)
    stage: Optional[Stage] = None
    notes: Optional[str] = Field(default=None, max_length=5000)
    subject: Optional[str] = Field(default=None, max_length=300)
    sender: Optional[str] = Field(default=None, max_length=300)
    events: Optional[List[Event]] = Field(default=None, max_length=100)
    offer: Optional[Offer] = None


def _loads(raw: Optional[str], default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def message_counts(db: Session, app_ids: List[int]) -> Dict[int, int]:
    if not app_ids:
        return {}
    rows = (db.query(InboundRecruiterMessage.application_id, func.count())
            .filter(InboundRecruiterMessage.application_id.in_(app_ids))
            .group_by(InboundRecruiterMessage.application_id).all())
    return {app_id: n for app_id, n in rows}


def to_ui(app: Application, job: Optional[Job] = None, inbound: int = 0) -> Dict[str, Any]:
    stage = (app.kanban_stage or "applied").lower()
    return {
        "id": str(app.id),
        "company": app.company or (job.company if job else "") or app.recruiter_company or "",
        "position": app.position or (job.title if job else "") or "",
        "stage": stage if stage in STAGES else "applied",
        "subject": app.email_subject or "Added manually",
        "sender": app.recruiter_email or "",
        "date": iso_utc(app.applied_at or app.created_at or datetime.utcnow()),
        "messages": 1 + inbound,
        "notes": app.notes or "",
        "events": _loads(app.events_json, []),
        "offer": _loads(app.offer_json, None),
        "source": app.source or ("job" if app.job_id else "manual"),
    }


def apply_patch(app: Application, patch: ApplicationPatch) -> None:
    data = patch.model_dump(exclude_unset=True)
    if "company" in data:
        app.company = data["company"]
    if "position" in data:
        app.position = data["position"]
    if "notes" in data:
        app.notes = data["notes"]
    if "subject" in data:
        app.email_subject = data["subject"]
    if "sender" in data:
        app.recruiter_email = data["sender"]
    if "events" in data:
        app.events_json = json.dumps(data["events"] or [])
    if "offer" in data:
        app.offer_json = json.dumps(data["offer"]) if data["offer"] else None
    if data.get("stage") and data["stage"] != app.kanban_stage:
        app.kanban_stage = data["stage"]  # board truth; legacy status keeps its own lifecycle
    app.updated_at = datetime.utcnow()


def sweep_ghosted(db: Session, now: Optional[datetime] = None) -> int:
    """Move 'applied' cards with no inbound email for GHOSTED_AFTER_DAYS to 'ghosted'.

    Runs from Celery beat (src/tasks.py), never from the frontend. Returns cards moved.
    """
    cutoff = (now or datetime.utcnow()) - timedelta(days=GHOSTED_AFTER_DAYS)
    last_seen = func.coalesce(Application.last_email_received_at, Application.applied_at, Application.created_at)
    rows = (db.query(Application)
            .filter(Application.kanban_stage == "applied", Application.user_id.isnot(None))
            .filter(last_seen < cutoff)
            .all())
    for app in rows:
        app.kanban_stage = "ghosted"
        app.updated_at = datetime.utcnow()
    db.commit()
    return len(rows)
