"""
src/tsenta/models.py — Database Models for Tsenta Auto-Apply Engine & Submissions.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.database import Base


class TsentaSubmission(Base):
    """Tracks every automated application dispatched or queued through the Tsenta engine."""
    __tablename__ = "tsenta_submissions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    ats_type = Column(String(50), nullable=False, default="custom_ats")  # greenhouse, lever, workday, ashby, etc.
    status = Column(String(50), nullable=False, default="queued")  # queued, review_ready, submitting, submitted, failed
    receipt_id = Column(String(100), unique=True, nullable=True, index=True)
    proof_url = Column(Text, nullable=True)
    
    # Submission artifacts & packets
    submission_packet = Column(Text, nullable=True)  # JSON representation of all fields sent
    answers_json = Column(Text, nullable=True)  # JSON array of screening Q&A pairs
    tailored_resume_path = Column(Text, nullable=True)
    cover_letter_path = Column(Text, nullable=True)
    tailored_resume_text = Column(Text, nullable=True)
    cover_letter_text = Column(Text, nullable=True)
    
    # Audit & Diagnostics
    match_score = Column(Float, default=0.0)
    company_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
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
            "match_score": self.match_score,
            "company_name": self.company_name,
            "job_title": self.job_title,
            "answers": answers,
            "submission_packet": packet,
            "tailored_resume_path": self.tailored_resume_path,
            "cover_letter_path": self.cover_letter_path,
            "tailored_resume_text": self.tailored_resume_text,
            "cover_letter_text": self.cover_letter_text,
            "error_detail": self.error_detail,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }


class TsentaQuota(Base):
    """Tracks daily application limits, lifetime usage, and subscription tier for Tsenta."""
    __tablename__ = "tsenta_quotas"

    id = Column(Integer, primary_key=True, index=True)
    daily_used = Column(Integer, default=0)
    daily_limit = Column(Integer, default=50)
    total_submitted = Column(Integer, default=0)
    lifetime_free_remaining = Column(Integer, default=25)  # Tsenta YC S26 default free tier
    active_tier = Column(String(50), default="free_starter")  # free_starter, pro_unlimited, enterprise
    last_reset_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "daily_used": self.daily_used,
            "daily_limit": self.daily_limit,
            "daily_remaining": max(0, self.daily_limit - self.daily_used),
            "total_submitted": self.total_submitted,
            "lifetime_free_remaining": self.lifetime_free_remaining,
            "active_tier": self.active_tier,
            "last_reset_at": self.last_reset_at.isoformat() if self.last_reset_at else None,
        }


class TsentaConfigRecord(Base):
    """Global configuration settings for Tsenta auto-apply automation."""
    __tablename__ = "tsenta_configs"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(255), nullable=True)
    api_url = Column(String(255), default="https://api.tsenta.com/v1")
    mode = Column(String(50), default="review_required")  # review_required (Diff Gate) | full_auto
    min_fit_score = Column(Integer, default=75)
    auto_apply_enabled = Column(Boolean, default=True)
    notification_webhook = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "api_key_configured": bool(self.api_key),
            "api_url": self.api_url,
            "mode": self.mode,
            "min_fit_score": self.min_fit_score,
            "auto_apply_enabled": self.auto_apply_enabled,
            "notification_webhook": self.notification_webhook,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
