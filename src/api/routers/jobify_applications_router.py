"""
jobify_applications_router.py — Phase 2 of the Jobify MVP: the Applications board.

GET/POST /api/applications, PATCH/DELETE /api/applications/{id} with the card shape from
jobify/src/services/applicationService.js. Every query is scoped to the current user.
Moving a card only records the change; nothing is sent to an employer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.api.contract import scoped
from src.auth.dependencies import get_current_user
from src.database import get_db
from src.models import Application, Job, User
from src.services import jobify_applications as ja

router = APIRouter(prefix="/api/applications", tags=["Jobify"])

MAX_APPLICATIONS = 1000  # the board loads everything at once; cap the payload


def _card(db: Session, app: Application) -> Dict[str, Any]:
    job = db.query(Job).filter(Job.id == app.job_id).first() if app.job_id else None
    return ja.to_ui(app, job, ja.message_counts(db, [app.id]).get(app.id, 0))


def _owned(db: Session, user: User, app_id: int) -> Application:
    app = scoped(db.query(Application), Application, user).filter(Application.id == app_id).first()
    if app is None:
        raise HTTPException(404, "Application not found")
    return app


@router.get("")
def list_applications(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    apps = (scoped(db.query(Application), Application, user)
            .order_by(Application.created_at.desc(), Application.id.desc())
            .limit(MAX_APPLICATIONS).all())
    job_ids = {a.job_id for a in apps if a.job_id}
    jobs = {j.id: j for j in db.query(Job).filter(Job.id.in_(job_ids)).all()} if job_ids else {}
    counts = ja.message_counts(db, [a.id for a in apps])
    items = [ja.to_ui(a, jobs.get(a.job_id), counts.get(a.id, 0)) for a in apps]
    return {"items": items, "total": len(items), "page": 1, "pageSize": len(items)}


@router.post("", status_code=201)
def create_application(body: ja.ApplicationCreate, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)) -> Dict[str, Any]:
    if body.jobId is not None and not db.query(Job.id).filter(Job.id == body.jobId).first():
        raise HTTPException(404, "Job not found")
    now = datetime.utcnow()
    app = Application(
        user_id=user.id, job_id=body.jobId, company=body.company, position=body.position,
        kanban_stage=body.stage, status="applied", notes=body.notes, email_subject=body.subject,
        recruiter_email=body.sender or None, source=body.source, applied_at=now, created_at=now,
        updated_at=now,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _card(db, app)


@router.patch("/{app_id:int}")
def update_application(app_id: int, body: ja.ApplicationPatch, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)) -> Dict[str, Any]:
    app = _owned(db, user, app_id)
    ja.apply_patch(app, body)
    db.commit()
    db.refresh(app)
    return _card(db, app)


@router.delete("/{app_id:int}", status_code=204)
def delete_application(app_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    db.delete(_owned(db, user, app_id))
    db.commit()
    return Response(status_code=204)
