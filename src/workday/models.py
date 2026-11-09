"""
src/workday/models.py — Database Models for Workday Candidate Profile & Multi-Tenant Auto-Apply Engine.
"""
from __future__ import annotations

import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship

from src.models import Base


class WorkdayCandidateProfile(Base):
    """Stores complete candidate master profile for autonomous Workday form autofill."""
    __tablename__ = "workday_candidate_profiles"

    id = Column(Integer, primary_key=True, index=True)
    account_email = Column(String(255), unique=True, nullable=False)
    
    # ── Personal Information ──
    first_name = Column(String(100))
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100))
    preferred_name = Column(String(100))
    phone = Column(String(50))
    phone_device_type = Column(String(50))
    
    # ── Address Information ──
    country = Column(String(100))
    address_line1 = Column(String(255))
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100))
    state_province = Column(String(100))
    postal_code = Column(String(50))
    
    # ── Online Presence & Links ──
    linkedin_url = Column(String(255))
    github_url = Column(String(255))
    portfolio_url = Column(String(255))
    twitter_url = Column(String(255), nullable=True)
    
    # ── Professional Experience & Education ──
    headline = Column(
        String(255),
    )
    years_of_experience = Column(Float)
    current_company = Column(String(100))
    current_title = Column(String(100))
    skills_json = Column(Text, default=json.dumps([]))
    work_history_json = Column(Text, default=json.dumps([]))
    education_json = Column(Text, default=json.dumps([]))
    
    # ── Standard Workday Legal & Screening Preferences ──
    legally_authorized = Column(Boolean)
    requires_sponsorship = Column(Boolean)
    notice_period_days = Column(Integer)
    target_salary_min = Column(Float)
    target_salary_max = Column(Float)
    salary_currency = Column(String(10))
    willing_to_relocate = Column(Boolean)
    
    # ── Voluntary EEO & Diversity Disclosures ──
    gender = Column(String(50))
    hispanic_latino = Column(String(50))
    race_ethnicity = Column(String(100))
    veteran_status = Column(String(100))
    disability_status = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        try:
            skills = json.loads(self.skills_json) if self.skills_json else []
        except Exception:
            skills = []
        try:
            work_history = json.loads(self.work_history_json) if self.work_history_json else []
        except Exception:
            work_history = []
        try:
            education = json.loads(self.education_json) if self.education_json else []
        except Exception:
            education = []

        return {
            "id": self.id,
            "account_email": self.account_email,
            "email": self.account_email,
            "full_name": " ".join(part for part in (self.first_name, self.last_name) if part),
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "last_name": self.last_name,
            "preferred_name": self.preferred_name,
            "phone": self.phone,
            "phone_device_type": self.phone_device_type,
            "country": self.country,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state_province": self.state_province,
            "postal_code": self.postal_code,
            "linkedin_url": self.linkedin_url,
            "github_url": self.github_url,
            "portfolio_url": self.portfolio_url,
            "twitter_url": self.twitter_url,
            "headline": self.headline,
            "years_of_experience": self.years_of_experience,
            "experience_years": self.years_of_experience,
            "current_company": self.current_company,
            "current_title": self.current_title,
            "skills": skills,
            "work_history": work_history,
            "education": education,
            "legally_authorized": self.legally_authorized,
            "requires_sponsorship": self.requires_sponsorship,
            "notice_period_days": self.notice_period_days,
            "target_salary_min": self.target_salary_min,
            "target_salary_max": self.target_salary_max,
            "salary_currency": self.salary_currency,
            "willing_to_relocate": self.willing_to_relocate,
            "gender": self.gender,
            "hispanic_latino": self.hispanic_latino,
            "race_ethnicity": self.race_ethnicity,
            "veteran_status": self.veteran_status,
            "disability_status": self.disability_status,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkdayAccountRecord(Base):
    """Stores provisioned candidate accounts per company Workday tenant."""
    __tablename__ = "workday_accounts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_domain = Column(String(255), nullable=False, index=True)  # e.g. gartner.wd5.myworkdayjobs.com
    career_site_name = Column(String(100), nullable=False, default="EXT")  # e.g. EXT, Careers, targetcareers
    company_name = Column(String(255), nullable=False)
    account_email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(50), default="active")  # active, registered, session_expired
    session_cookies_json = Column(Text, nullable=True)
    auth_token = Column(Text, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def email(self) -> str:
        return self.account_email

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_domain": self.tenant_domain,
            "career_site_name": self.career_site_name,
            "company_name": self.company_name,
            "account_email": self.account_email,
            "email": self.account_email,
            "status": self.status,
            "has_session": bool(self.session_cookies_json or self.auth_token),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkdayApplicationSubmission(Base):
    """Audit trail of Workday multi-step auto-applied submissions."""
    __tablename__ = "workday_submissions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    tenant_domain = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    account_email = Column(String(255), nullable=False)
    status = Column(String(50), default="submitted")  # account_created, resume_tailored, form_filled, submitted, failed
    receipt_id = Column(String(100), unique=True, nullable=True, index=True)
    proof_url = Column(Text, nullable=True)
    confirmation_number = Column(String(100), nullable=True)
    
    # Generated artifacts
    tailored_resume_path = Column(Text, nullable=True)
    tailored_resume_text = Column(Text, nullable=True)
    cover_letter_text = Column(Text, nullable=True)
    match_score = Column(Float, default=88.0)
    
    # Audit payloads
    submission_packet_json = Column(Text, nullable=True)
    answers_json = Column(Text, nullable=True)  # Screening Q&A pairs
    error_detail = Column(Text, nullable=True)
    execution_time_ms = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    @property
    def email(self) -> str:
        return self.account_email

    def to_dict(self) -> Dict[str, Any]:
        answers = []
        if self.answers_json:
            try:
                answers = json.loads(self.answers_json)
            except Exception:
                answers = []

        return {
            "id": self.id,
            "job_id": self.job_id,
            "tenant_domain": self.tenant_domain,
            "company_name": self.company_name,
            "job_title": self.job_title,
            "account_email": self.account_email,
            "status": self.status,
            "receipt_id": self.receipt_id,
            "proof_url": self.proof_url,
            "confirmation_number": self.confirmation_number,
            "match_score": self.match_score,
            "tailored_resume_path": self.tailored_resume_path,
            "has_tailored_resume": bool(self.tailored_resume_path or self.tailored_resume_text),
            "answers_count": len(answers),
            "answers": answers,
            "error_detail": self.error_detail,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }


class WorkdayConfigRecord(Base):
    """Global configuration for Workday Autopilot Engine."""
    __tablename__ = "workday_configs"

    id = Column(Integer, primary_key=True, index=True)
    account_email = Column(String(255))
    auto_apply_enabled = Column(Boolean, default=False)
    mode = Column(String(50), default="review_gate")
    min_fit_score = Column(Float, default=65.0)
    daily_limit = Column(Integer, default=0)
    daily_used = Column(Integer, default=0)
    total_submitted = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    tailor_resumes = Column(Boolean, default=True)
    generate_cover_letters = Column(Boolean, default=True)
    batch_concurrency = Column(Integer, default=4)
    last_reset_date = Column(Date, default=date.today)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "account_email": self.account_email,
            "auto_apply_enabled": self.auto_apply_enabled,
            "mode": self.mode,
            "min_fit_score": self.min_fit_score,
            "daily_limit": self.daily_limit,
            "daily_used": self.daily_used,
            "daily_remaining": max(0, self.daily_limit - self.daily_used),
            "daily_percent": round((self.daily_used / max(1, self.daily_limit)) * 100, 1),
            "total_submitted": self.total_submitted,
            "total_failed": self.total_failed,
            "tailor_resumes": self.tailor_resumes,
            "generate_cover_letters": self.generate_cover_letters,
            "batch_concurrency": self.batch_concurrency,
            "last_reset_date": self.last_reset_date.isoformat() if self.last_reset_date else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
