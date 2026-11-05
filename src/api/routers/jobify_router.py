"""
jobify_router.py — Phase 1 of the Jobify MVP: current user, subscription, jobs.

Paths and shapes follow jobify/docs/INTEGRATION.md and jobify/src/services/
(authService.js, jobService.js). The frontend is the spec; Jobify calls these with
VITE_API_BASE_URL=https://<host>/api. Auth comes from the app-level
enforce_auth_unless_public dependency; handlers still take get_current_user so
they always have a real user row.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.api.contract import scoped
from src.auth.dependencies import get_current_user
from src.database import get_db
from src.models import Job, User, UserJob
from src.services import jobify_jobs as jj

router = APIRouter(prefix="/api", tags=["Jobify"])

# Match % is computed in Python per user, so list filtering/sorting runs over at most
# this many SQL-prefiltered rows (newest first). Raise it, or precompute scores, once
# the catalog outgrows it.
MAX_SCAN_ROWS = 2000

# subscription_tier values (billing_service) -> Jobify plan ids (jobify/src/data/plans.js)
PLAN_BY_TIER = {"basic": "basic", "starter": "basic", "pro": "pro", "unlimited": "pro"}
STATUS_BY_SUB = {"active": "active", "trialing": "active", "past_due": "past_due",
                 "canceled": "cancelled", "cancelled": "cancelled"}


# --- me ------------------------------------------------------------------------

@router.get("/me")
def get_me(user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return {
        "id": user.clerk_user_id or str(user.id),
        "name": user.full_name or user.email,
        "email": user.email,
        "avatar": None,
        "source": "clerk",
    }


@router.get("/me/subscription")
def get_subscription(user: User = Depends(get_current_user)) -> Dict[str, Any]:
    plan = PLAN_BY_TIER.get((user.subscription_tier or "").lower())
    status = STATUS_BY_SUB.get((user.subscription_status or "").lower(), "none") if plan else "none"
    return {
        "plan": plan,
        "interval": "monthly",  # no interval column yet; set by the Phase 7 billing webhook
        "status": status,
        "creditsRemaining": user.credits_balance or 0,
        "renewsAt": user.current_period_end.isoformat() if user.current_period_end else None,
    }


# --- jobs ----------------------------------------------------------------------

@router.get("/jobs")
def list_jobs(
    q: str = "",
    workModes: List[str] = Query(default=[]),
    types: List[str] = Query(default=[]),
    countries: List[str] = Query(default=[]),
    skills: List[str] = Query(default=[]),
    matchOnly: bool = False,
    minSalaryUsd: float = Query(default=0, ge=0),
    maxYears: Optional[int] = Query(default=None, ge=0, le=50),
    sort: str = Query(default="match", pattern="^(match|recent|salary|title)$"),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    query = db.query(Job).filter(Job.expired_at.is_(None))
    needle = q.strip().lower()
    if needle:
        term = f"%{needle}%"
        query = query.filter(or_(
            func.lower(Job.title).like(term), func.lower(Job.company).like(term),
            func.lower(Job.location).like(term), func.lower(Job.tags).like(term),
        ))
    for skill in skills:  # cheap SQL prefilter; exact match re-checked in filter_and_sort
        query = query.filter(func.lower(Job.tags).like(f"%{skill.strip().lower()}%"))

    rows = query.order_by(Job.fetched_at.desc()).limit(MAX_SCAN_ROWS).all()
    items = jj.filter_and_sort(
        rows, jj.profile_for(db, user),
        work_modes=workModes, types=types, countries=countries, skills=skills,
        match_only=matchOnly, min_salary_usd=minSalaryUsd, max_years=maxYears, sort=sort,
    )
    start = (page - 1) * pageSize
    return {"items": items[start:start + pageSize], "total": len(items), "page": page, "pageSize": pageSize}


@router.get("/jobs/{job_id:int}")
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return jj.to_ui_job(job, jj.profile_for(db, user))


# --- per-user job state ----------------------------------------------------------

def _state(db: Session, user: User) -> Dict[str, List[str]]:
    rows = scoped(db.query(UserJob), UserJob, user).all()
    return {
        "saved": [str(r.job_id) for r in rows if r.saved_at],
        "applied": [str(r.job_id) for r in rows if r.applied_at],
    }


def _user_job(db: Session, user: User, job_id: int) -> UserJob:
    if not db.query(Job.id).filter(Job.id == job_id).first():
        raise HTTPException(404, "Job not found")
    row = scoped(db.query(UserJob), UserJob, user).filter(UserJob.job_id == job_id).first()
    if row is None:
        row = UserJob(user_id=user.id, job_id=job_id)
        db.add(row)
    return row


@router.get("/me/jobs/state")
def get_job_state(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, List[str]]:
    return _state(db, user)


@router.put("/me/jobs/{job_id:int}/saved")
def set_saved(
    job_id: int,
    body: Optional[Dict[str, Any]] = Body(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, List[str]]:
    """Body {"saved": bool} sets the flag; no body toggles (jobService.toggleSaved)."""
    row = _user_job(db, user, job_id)
    saved = (row.saved_at is None) if not body or "saved" not in body else bool(body["saved"])
    row.saved_at = datetime.utcnow() if saved else None
    db.commit()
    return _state(db, user)


@router.post("/me/jobs/{job_id:int}/applied")
def mark_applied(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, List[str]]:
    """Records that the user applied. Never submits anything to the employer.

    Only flags the job: JobsPage.apply() creates the Applications card itself via
    POST /applications, so creating one here too would duplicate it.
    """
    row = _user_job(db, user, job_id)
    if row.applied_at is None:
        row.applied_at = datetime.utcnow()
    db.commit()
    return _state(db, user)
