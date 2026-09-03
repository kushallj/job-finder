"""
profile_service.py — Candidate Profile & Target Company Management Service.
Replaces singleton YAML configuration files with a database-backed, multi-user system.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import yaml
from sqlalchemy.orm import Session
from pypdf import PdfReader

from src.models import CandidateProfile, TargetCompanyRecord, OutreachFunnelEvent
from src.ai.unified_ai_service import UnifiedAIService

logger = logging.getLogger("profile_service")


TECH_SKILL_PATTERNS = [
    "Python", "FastAPI", "Django", "Flask", "Go", "Golang", "Rust", "React", "Next.js",
    "Node.js", "TypeScript", "JavaScript", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "Kafka", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "GraphQL", "gRPC",
    "PyTorch", "TensorFlow", "Scikit-Learn", "HuggingFace", "LangChain", "LLMs", "RAG",
    "Distributed Systems", "Microservices", "CI/CD", "Terraform", "C++", "Java", "Spring Boot"
]


class ProfileService:
    """Manages candidate resumes, extracted skills, and target company pipelines."""

    def __init__(self, db: Session, ai_service: Optional[UnifiedAIService] = None):
        self.db = db
        self.ai = ai_service or UnifiedAIService()

    def parse_resume_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from uploaded PDF bytes."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text_chunks = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_chunks.append(t)
            return "\n".join(text_chunks)
        except Exception as exc:
            logger.error(f"Failed to parse PDF bytes: {exc}")
            raise ValueError(f"Could not parse resume PDF: {str(exc)}")

    def extract_profile_from_text(self, text: str) -> Dict[str, Any]:
        """Extract structured profile attributes from resume text."""
        # 1. Email extraction
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        email = email_match.group(0) if email_match else ""

        # 2. Phone extraction
        phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        phone = phone_match.group(0) if phone_match else ""

        # 3. LinkedIn & GitHub
        li_match = re.search(r"https?://(?:www\.)?linkedin\.com/in/[\w-]+", text, re.I)
        linkedin_url = li_match.group(0) if li_match else ""

        gh_match = re.search(r"https?://(?:www\.)?github\.com/[\w-]+", text, re.I)
        github_url = gh_match.group(0) if gh_match else ""

        # 4. Name extraction (first non-empty line or capitalized header)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        full_name = lines[0] if lines else "Applicant"
        if len(full_name.split()) > 4 or "@" in full_name or "http" in full_name:
            full_name = "Candidate"

        # 5. Skills extraction
        found_skills = []
        text_lower = text.lower()
        for skill in TECH_SKILL_PATTERNS:
            pattern = rf"\b{re.escape(skill.lower())}\b"
            if re.search(pattern, text_lower):
                found_skills.append(skill)

        # 6. Experience Years estimation
        years_matches = re.findall(r"(\d+)\+?\s*(?:years|yrs)\b", text_lower)
        yoe = 3.0
        if years_matches:
            try:
                yoe = float(max(int(y) for y in years_matches if int(y) < 30))
            except ValueError:
                yoe = 3.0

        # 7. Summary
        bio_summary = f"Software Engineer with {yoe:g}+ years of experience specializing in {', '.join(found_skills[:5])}."

        return {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "linkedin_url": linkedin_url,
            "github_url": github_url,
            "years_of_experience": yoe,
            "skills": found_skills,
            "bio_summary": bio_summary,
            "target_roles": ["Senior Backend Engineer", "Full Stack Engineer", "Distributed Systems Engineer"],
            "target_locations": ["Remote", "Bengaluru", "Delhi NCR", "United States"],
        }

    def get_or_create_profile(self, user_id: str = "default_user") -> CandidateProfile:
        """Fetch candidate profile from DB, or bootstrap from config/profile.yml / defaults."""
        profile = self.db.query(CandidateProfile).filter(CandidateProfile.user_identifier == user_id).first()
        if profile:
            return profile

        # Bootstrap from config/profile.yml if present
        name = "Kushall Jain"
        email = "applicant@example.com"
        yoe = 3.0
        skills = ["Python", "FastAPI", "React", "PostgreSQL", "Redis"]
        summary = "Full-stack engineer specializing in scalable Python/FastAPI microservices and React web applications."
        li = ""
        gh = ""

        try:
            yaml_path = os.path.join(os.getcwd(), "config", "profile.yml")
            if os.path.exists(yaml_path):
                with open(yaml_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}
                    cand = cfg.get("candidate", {})
                    name = cand.get("name", name)
                    email = cand.get("email", email)
                    yoe = float(cand.get("experience_years", yoe))
                    skills = cand.get("skills", skills)
                    summary = cand.get("summary", summary)
                    li = cand.get("linkedin_url", li)
                    gh = cand.get("github_url", gh)
        except Exception as exc:
            logger.warning(f"Could not load config/profile.yml: {exc}")

        new_profile = CandidateProfile(
            user_identifier=user_id,
            full_name=name,
            email=email,
            years_of_experience=yoe,
            skills=json.dumps(skills),
            bio_summary=summary,
            linkedin_url=li,
            github_url=gh,
            target_roles=json.dumps(["Senior Backend Engineer", "Full Stack Engineer"]),
            target_locations=json.dumps(["Remote", "India", "United States"]),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(new_profile)
        self.db.commit()
        self.db.refresh(new_profile)
        return new_profile

    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> CandidateProfile:
        """Update candidate profile attributes."""
        profile = self.get_or_create_profile(user_id)
        for key, val in updates.items():
            if hasattr(profile, key):
                if key in ["skills", "target_roles", "target_locations"] and isinstance(val, list):
                    setattr(profile, key, json.dumps(val))
                else:
                    setattr(profile, key, val)
        profile.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_target_companies(self, user_id: str = "default_user") -> List[TargetCompanyRecord]:
        """Fetch target company records from DB, or bootstrap from config/target_companies.yml."""
        records = self.db.query(TargetCompanyRecord).filter(
            TargetCompanyRecord.user_identifier == user_id,
            TargetCompanyRecord.is_active == True
        ).all()
        if records:
            return records

        # Bootstrap from config/target_companies.yml if empty
        try:
            yaml_path = os.path.join(os.getcwd(), "config", "target_companies.yml")
            if os.path.exists(yaml_path):
                with open(yaml_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}
                    companies = cfg.get("companies", [])
                    for comp in companies:
                        rec = TargetCompanyRecord(
                            user_identifier=user_id,
                            name=comp.get("name", "Unknown"),
                            domain=comp.get("domain", ""),
                            tier=comp.get("tier", "tier1"),
                            industry=comp.get("industry", "Technology"),
                            headquarters=comp.get("headquarters", "Bengaluru / US"),
                            funding_stage=comp.get("stage", "Growth"),
                            signal_score=float(comp.get("signal_score", 85.0)),
                            signal_notes=comp.get("notes", "High hiring velocity"),
                            is_active=True,
                            created_at=datetime.utcnow(),
                        )
                        self.db.add(rec)
                    self.db.commit()
                    return self.db.query(TargetCompanyRecord).filter(
                        TargetCompanyRecord.user_identifier == user_id
                    ).all()
        except Exception as exc:
            logger.warning(f"Could not load config/target_companies.yml: {exc}")

        return []

    def add_target_company(self, user_id: str, company_data: Dict[str, Any]) -> TargetCompanyRecord:
        """Add a new target company to user's pipeline."""
        rec = TargetCompanyRecord(
            user_identifier=user_id,
            name=company_data["name"],
            domain=company_data.get("domain", ""),
            tier=company_data.get("tier", "tier1"),
            industry=company_data.get("industry", "Technology"),
            headquarters=company_data.get("headquarters", "Remote"),
            funding_stage=company_data.get("funding_stage", "Series B+"),
            signal_score=float(company_data.get("signal_score", 85.0)),
            signal_notes=company_data.get("signal_notes", "Targeted account"),
            is_active=True,
            created_at=datetime.utcnow(),
        )
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def log_funnel_event(
        self,
        event_type: str,
        company: str,
        role_title: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        channel: str = "email",
        match_score: Optional[float] = None,
        notes: Optional[str] = None,
        user_id: str = "default_user",
    ) -> OutreachFunnelEvent:
        """Record an outcome funnel event."""
        evt = OutreachFunnelEvent(
            user_identifier=user_id,
            event_type=event_type,
            company=company,
            role_title=role_title,
            contact_name=contact_name,
            contact_email=contact_email,
            channel=channel,
            match_score=match_score,
            notes=notes,
            created_at=datetime.utcnow(),
        )
        self.db.add(evt)
        self.db.commit()
        self.db.refresh(evt)
        return evt

    def get_funnel_metrics(self, user_id: str = "default_user") -> Dict[str, Any]:
        """Aggregate funnel conversion rates from discovery to interview."""
        events = self.db.query(OutreachFunnelEvent).filter(OutreachFunnelEvent.user_identifier == user_id).all()
        counts: Dict[str, int] = {
            "lead_discovered": 0,
            "packet_generated": 0,
            "review_approved": 0,
            "email_sent": 0,
            "reply_received": 0,
            "interview_scheduled": 0,
            "offer_received": 0,
        }
        for e in events:
            if e.event_type in counts:
                counts[e.event_type] += 1

        total_sent = max(counts["email_sent"], 1)
        reply_rate_pct = round((counts["reply_received"] / total_sent) * 100, 1)
        interview_rate_pct = round((counts["interview_scheduled"] / total_sent) * 100, 1)

        return {
            "funnel_counts": counts,
            "total_sent": counts["email_sent"],
            "replies": counts["reply_received"],
            "interviews": counts["interview_scheduled"],
            "offers": counts["offer_received"],
            "reply_rate_pct": reply_rate_pct,
            "interview_rate_pct": interview_rate_pct,
            "recent_events": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "company": e.company,
                    "role_title": e.role_title,
                    "contact_name": e.contact_name,
                    "channel": e.channel,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in sorted(events, key=lambda x: x.created_at or datetime.min, reverse=True)[:10]
            ],
        }
