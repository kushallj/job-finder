"""
src/workday/models.py — Database Models for Workday Candidate Profile & Multi-Tenant Auto-Apply Engine.
"""
from __future__ import annotations

import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship

from src.database import Base


class WorkdayCandidateProfile(Base):
    """Stores complete candidate master profile for autonomous Workday form autofill."""
    __tablename__ = "workday_candidate_profiles"

    id = Column(Integer, primary_key=True, index=True)
    account_email = Column(String(255), unique=True, nullable=False, default="canaby007@gmail.com")
    
    # ── Personal Information ──
    first_name = Column(String(100), default="Kushall")
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), default="Jain")
    preferred_name = Column(String(100), default="Kushall")
    phone = Column(String(50), default="+91 9876543210")
    phone_device_type = Column(String(50), default="Mobile")  # Mobile, Landline
    
    # ── Address Information ──
    country = Column(String(100), default="India")
    address_line1 = Column(String(255), default="Sector 62, Electronic City")
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), default="Bengaluru")
    state_province = Column(String(100), default="Karnataka")
    postal_code = Column(String(50), default="560100")
    
    # ── Online Presence & Links ──
    linkedin_url = Column(String(255), default="https://www.linkedin.com/in/kushall-jain")
    github_url = Column(String(255), default="https://github.com/kushallj")
    portfolio_url = Column(String(255), default="https://kushallj.github.io")
    twitter_url = Column(String(255), nullable=True)
    
    # ── Professional Experience & Education ──
    headline = Column(
        String(255),
        default="Software Development Engineer – Full Stack Web Development • RESTful APIs • Cloud & IoT Architecture"
    )
    years_of_experience = Column(Float, default=4.0)
    current_company = Column(String(100), default="Tech Innovations")
    current_title = Column(String(100), default="Senior Software Engineer")
    skills_json = Column(
        Text,
        default=json.dumps([
            "Python", "FastAPI", "React", "TypeScript", "Node.js", "Java",
            "PostgreSQL", "Docker", "Kubernetes", "AWS", "Redis", "Distributed Systems"
        ])
    )
    work_history_json = Column(
        Text,
        default=json.dumps([
            {
                "company": "Tech Innovations",
                "title": "Senior Software Engineer",
                "location": "Bengaluru, India",
                "start_date": "2023-01",
                "end_date": "Present",
                "is_current": True,
                "description": "Architected high-throughput microservices using FastAPI and PostgreSQL, serving 5M+ daily requests with 99.99% uptime."
            },
            {
                "company": "CloudScale Solutions",
                "title": "Software Development Engineer",
                "location": "Bengaluru, India",
                "start_date": "2021-06",
                "end_date": "2022-12",
                "is_current": False,
                "description": "Built resilient RESTful APIs and real-time event pipelines with Python, React, and AWS."
            }
        ])
    )
    education_json = Column(
        Text,
        default=json.dumps([
            {
                "school": "Visvesvaraya Technological University",
                "degree": "Bachelor of Engineering",
                "field_of_study": "Computer Science & Engineering",
                "start_date": "2017",
                "end_date": "2021",
                "gpa": "8.8/10.0"
            }
        ])
    )
    
    # ── Standard Workday Legal & Screening Preferences ──
    legally_authorized = Column(Boolean, default=True)
    requires_sponsorship = Column(Boolean, default=False)
    notice_period_days = Column(Integer, default=30)
    target_salary_min = Column(Float, default=120000.0)
    target_salary_max = Column(Float, default=180000.0)
    salary_currency = Column(String(10), default="USD")
    willing_to_relocate = Column(Boolean, default=True)
    
    # ── Voluntary EEO & Diversity Disclosures ──
    gender = Column(String(50), default="Male")  # Male, Female, Non-Binary, Prefer not to say
    hispanic_latino = Column(String(50), default="No")  # Yes, No, Decline
    race_ethnicity = Column(String(100), default="Asian")  # Asian, White, Black, Decline, etc.
    veteran_status = Column(String(100), default="I am not a protected veteran")
    disability_status = Column(String(100), default="No, I do not have a disability")
    
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
            "full_name": f"{self.first_name} {self.last_name}".strip(),
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
    account_email = Column(String(255), nullable=False, default="canaby007@gmail.com")
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
    account_email = Column(String(255), default="canaby007@gmail.com")
    auto_apply_enabled = Column(Boolean, default=True)
    mode = Column(String(50), default="instant_auto")  # instant_auto | review_gate
    min_fit_score = Column(Float, default=65.0)
    daily_limit = Column(Integer, default=100)
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
