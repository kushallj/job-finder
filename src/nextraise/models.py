"""
src/nextraise/models.py — Database Models for NextRaise Auto-Apply Suite & High-Volume Dispatching.
"""
from __future__ import annotations

import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship

from src.models import Base


class NextRaiseSubmission(Base):
    """Tracks every automated application dispatched or queued through NextRaise."""
    __tablename__ = "nextraise_submissions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    ats_type = Column(String(50), nullable=False, default="workday")  # workday, greenhouse, lever, ashby, bamboohr, etc.
    status = Column(String(50), nullable=False, default="queued")    # queued, processing, applied, review_ready, failed
    receipt_id = Column(String(100), unique=True, nullable=True, index=True)
    proof_url = Column(Text, nullable=True)

    # Submission artifacts & packets
    submission_packet = Column(Text, nullable=True)  # JSON representation of all form fields & candidate answers
    answers_json = Column(Text, nullable=True)       # JSON array of screening Q&A pairs
    tailored_resume_path = Column(Text, nullable=True)
    cover_letter_path = Column(Text, nullable=True)
    tailored_resume_text = Column(Text, nullable=True)
    cover_letter_text = Column(Text, nullable=True)

    # Metadata & Tracking
    account_email = Column(String(255), default="canaby007@gmail.com", index=True)
    company_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    match_score = Column(Float, default=0.0)
    error_detail = Column(Text, nullable=True)
    execution_time_ms = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        answers = []
        if self.answers_json:
            try:
                answers = json.loads(self.answers_json)
            except Exception:
                answers = []

        packet = {}
        if self.submission_packet:
            try:
                packet = json.loads(self.submission_packet)
            except Exception:
                packet = {}

        return {
            "id": self.id,
            "job_id": self.job_id,
            "ats_type": self.ats_type,
            "status": self.status,
            "receipt_id": self.receipt_id,
            "proof_url": self.proof_url,
            "account_email": self.account_email,
            "company_name": self.company_name,
            "job_title": self.job_title,
            "match_score": self.match_score,
            "answers_count": len(answers),
            "tailored_resume_path": self.tailored_resume_path,
            "has_cover_letter": bool(self.cover_letter_text or self.cover_letter_path),
            "error_detail": self.error_detail,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "submission_packet": packet,
            "answers": answers,
        }


class NextRaiseConfigRecord(Base):
    """Configuration record for NextRaise OAuth account, daily target, and ATS filters."""
    __tablename__ = "nextraise_config"

    id = Column(Integer, primary_key=True)
    account_email = Column(String(255), default="canaby007@gmail.com", nullable=False)
    oauth_access_token = Column(Text, nullable=True)
    oauth_refresh_token = Column(Text, nullable=True)
    session_token = Column(Text, nullable=True)
    oauth_connected = Column(Boolean, default=True)

    # Operational settings
    mode = Column(String(50), default="instant_auto")  # instant_auto, review_required
    daily_target = Column(Integer, default=300)        # 200 - 300 jobs daily target
    min_fit_score = Column(Float, default=60.0)
    auto_batch_enabled = Column(Boolean, default=True)
    batch_concurrency = Column(Integer, default=5)
    enabled_ats_json = Column(Text, default=json.dumps([
        "workday", "greenhouse", "lever", "ashby", "bamboohr",
        "smartrecruiters", "taleo", "icims", "successfactors", "custom_ats"
    ]))

    api_url = Column(String(255), default="https://api.nextraise.com/v1")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        ats_list = []
        try:
            ats_list = json.loads(self.enabled_ats_json or "[]")
        except Exception:
            ats_list = []

        return {
            "account_email": self.account_email,
            "oauth_connected": self.oauth_connected,
            "has_token": bool(self.oauth_access_token or self.session_token),
            "mode": self.mode,
            "daily_target": self.daily_target,
            "min_fit_score": self.min_fit_score,
            "auto_batch_enabled": self.auto_batch_enabled,
            "batch_concurrency": self.batch_concurrency,
            "enabled_ats": ats_list,
            "api_url": self.api_url,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NextRaiseQuota(Base):
    """Tracks daily application consumption towards the 200-300 quota target."""
    __tablename__ = "nextraise_quota"

    id = Column(Integer, primary_key=True)
    daily_used = Column(Integer, default=0)
    daily_limit = Column(Integer, default=300)
    total_submitted = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    active_tier = Column(String(50), default="nextraise_pro_unlimited")
    last_reset_date = Column(Date, default=date.today)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "daily_used": self.daily_used,
            "daily_limit": self.daily_limit,
            "daily_remaining": max(0, self.daily_limit - self.daily_used),
            "daily_progress_percent": round((self.daily_used / max(1, self.daily_limit)) * 100, 1),
            "total_submitted": self.total_submitted,
            "total_failed": self.total_failed,
            "active_tier": self.active_tier,
            "last_reset_date": str(self.last_reset_date),
        }
