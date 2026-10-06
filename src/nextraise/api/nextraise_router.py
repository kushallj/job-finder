"""
src/nextraise/api/nextraise_router.py — FastAPI Endpoints for NextRaise Auto-Apply & OAuth Engine.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.nextraise.service import NextRaiseService
from src.nextraise.models import NextRaiseConfigRecord, NextRaiseQuota, NextRaiseSubmission

router = APIRouter(prefix="/api/nextraise", tags=["nextraise-auto-apply"])


class NextRaiseOAuthAuthorizeRequest(BaseModel):
    account_email: str = Field(default="canaby007@gmail.com")
    oauth_access_token: str
    oauth_refresh_token: Optional[str] = None
    session_token: Optional[str] = None


class NextRaiseBatchApplyRequest(BaseModel):
    target_count: int = Field(default=250, ge=1, le=500)
    min_fit_score: float = Field(default=50.0, ge=0.0, le=100.0)


class NextRaiseConfigUpdateRequest(BaseModel):
    account_email: Optional[str] = "canaby007@gmail.com"
    daily_target: Optional[int] = Field(default=300, ge=50, le=1000)
    min_fit_score: Optional[float] = Field(default=60.0, ge=0.0, le=100.0)
    mode: Optional[str] = "instant_auto"
    auto_batch_enabled: Optional[bool] = True
    batch_concurrency: Optional[int] = 5
    enabled_ats: Optional[List[str]] = None


@router.get("/status")
def get_nextraise_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns NextRaise OAuth account status, daily 200-300 quota gauge, and recent receipts."""
    service = NextRaiseService(db)
    return service.get_progress_telemetry()


@router.post("/oauth/authorize")
def authorize_nextraise_oauth(req: NextRaiseOAuthAuthorizeRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Updates OAuth tokens and connects account (canaby007@gmail.com)."""
    cfg = db.query(NextRaiseConfigRecord).first()
    if not cfg:
        cfg = NextRaiseConfigRecord()
        db.add(cfg)

    cfg.account_email = req.account_email
    cfg.oauth_access_token = req.oauth_access_token
    cfg.oauth_refresh_token = req.oauth_refresh_token
    cfg.session_token = req.session_token
    cfg.oauth_connected = True
    db.commit()
    db.refresh(cfg)

    return {
        "status": "connected",
        "account_email": cfg.account_email,
        "message": f"Successfully authorized NextRaise account for {cfg.account_email}.",
    }


@router.post("/batch-apply")
async def trigger_high_volume_batch_apply(req: Optional[NextRaiseBatchApplyRequest] = None, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Launches high-volume batch auto-apply for 200–300 jobs via NextRaise.
    """
    target = req.target_count if req else 250
    min_score = req.min_fit_score if req else 50.0

    service = NextRaiseService(db)
    results = await service.batch_auto_apply(target_count=target, min_score=min_score)
    return results


@router.post("/apply/{job_id}")
async def apply_single_job_via_nextraise(job_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Submits a single job application via NextRaise."""
    service = NextRaiseService(db)
    res = await service.auto_apply_job(job_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Application failed"))
    return res


@router.get("/submissions")
def list_nextraise_submissions(
    limit: int = Query(50, ge=1, le=300),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Lists audit trail of NextRaise applications with verified receipt IDs."""
    q = db.query(NextRaiseSubmission)
    if status:
        q = q.filter(NextRaiseSubmission.status == status)
    subs = q.order_by(NextRaiseSubmission.id.desc()).limit(limit).all()

    return {
        "total_count": len(subs),
        "submissions": [s.to_dict() for s in subs],
    }


@router.get("/config")
def get_nextraise_config(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns NextRaise configuration settings."""
    service = NextRaiseService(db)
    return service.config.to_dict()


@router.post("/config")
def update_nextraise_config(req: NextRaiseConfigUpdateRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Updates NextRaise settings such as daily quota target (200-300) and ATS filters."""
    cfg = db.query(NextRaiseConfigRecord).first()
    if not cfg:
        cfg = NextRaiseConfigRecord()
        db.add(cfg)

    if req.account_email is not None:
        cfg.account_email = req.account_email
    if req.daily_target is not None:
        cfg.daily_target = req.daily_target
    if req.min_fit_score is not None:
        cfg.min_fit_score = req.min_fit_score
    if req.mode is not None:
        cfg.mode = req.mode
    if req.auto_batch_enabled is not None:
        cfg.auto_batch_enabled = req.auto_batch_enabled
    if req.batch_concurrency is not None:
        cfg.batch_concurrency = req.batch_concurrency
    if req.enabled_ats is not None:
        cfg.enabled_ats_json = json.dumps(req.enabled_ats)

    # Also sync daily limit in quota table
    quota = db.query(NextRaiseQuota).first()
    if quota and req.daily_target is not None:
        quota.daily_limit = req.daily_target

    db.commit()
    db.refresh(cfg)

    return {
        "status": "updated",
        "config": cfg.to_dict(),
    }
