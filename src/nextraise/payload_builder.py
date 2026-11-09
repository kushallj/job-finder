"""
src/nextraise/payload_builder.py — Tailored ATS Application Packet Builder for NextRaise.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import Job, Application
from src.tsenta.ats_detector import ATSInfo

logger = logging.getLogger("nextraise_payload_builder")


class NextRaisePayloadBuilder:
    """Constructs tailored resume, cover letter, and screening answers for NextRaise submission."""

    def __init__(self, db: Session):
        self.db = db

    def load_candidate_profile(self, account_email: Optional[str] = None,
                               profile_path: str = "config/profile.yml") -> Dict[str, Any]:
        """The candidate's real profile from config/profile.yml + data/resume.txt.

        Nothing is invented (CLAUDE.md section 1): a field missing from the profile stays
        None instead of a placeholder. This used to return hardcoded values (a 555 phone
        number, "Authorized to work in US", "no sponsorship", 5 years) that were submitted
        to employers as if true. Raises if the profile file is missing.
        """
        import yaml

        if not os.path.exists(profile_path):
            raise ValueError(f"{profile_path} not found: auto-apply needs the candidate's real profile")
        with open(profile_path, encoding="utf-8") as fh:
            profile = yaml.safe_load(fh) or {}
        cand = profile.get("candidate") or {}
        answers = profile.get("application_answers") or {}
        stack = profile.get("tech_stack") or {}
        experience = profile.get("experience") or {}

        resume_text = ""
        for path in ("data/resume.txt", "data/resume_profile.json"):
            if os.path.exists(path):
                with open(path, encoding="utf-8", errors="replace") as f:
                    resume_text = f.read()
                break

        full_name = cand.get("full_name") or cand.get("name")
        return {
            "first_name": cand.get("first_name"),
            "last_name": cand.get("last_name"),
            "full_name": full_name,
            "email": account_email or cand.get("email"),
            "phone": cand.get("phone"),
            "location": cand.get("location"),
            "linkedin": cand.get("linkedin_url") or cand.get("linkedin"),
            "github": cand.get("github_url") or cand.get("github"),
            "portfolio": cand.get("portfolio"),
            "work_authorization": cand.get("visa_status") or answers.get("work_authorization_india"),
            "sponsorship_required": answers.get("requires_sponsorship_india"),
            "years_of_experience": experience.get("years_total") or cand.get("experience_years"),
            "availability": answers.get("earliest_start_date") or cand.get("availability"),
            "skills": list(stack.get("strong") or []) + list(stack.get("familiar") or []),
            "resume_raw": resume_text,
        }

    def generate_screening_answers(self, job: Job, candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return answers only when supported by explicit candidate profile data."""
        answers: List[Dict[str, Any]] = []
        for field, question in (
            ("work_authorization", "Are you legally authorized to work in this location?"),
            ("sponsorship_required", "Will you now or in the future require visa sponsorship?"),
        ):
            value = candidate.get(field)
            if isinstance(value, bool):
                value = "Yes" if value else "No"
            elif isinstance(value, str) and value.strip().casefold() in {"yes", "no"}:
                value = value.strip().capitalize()
            else:
                continue
            answers.append({"question": question, "type": "boolean", "answer": value})

        years = candidate.get("years_of_experience")
        if years is not None and str(years).strip():
            answers.append({
                "question": "How many years of experience do you have with modern backend technologies?",
                "type": "numeric",
                "answer": str(years),
            })

        availability = candidate.get("availability")
        if isinstance(availability, str) and availability.strip():
            answers.append({
                "question": "When is your earliest available start date?",
                "type": "text",
                "answer": availability.strip(),
            })

        answers.append({
            "question": "Why are you interested in this position?",
            "type": "text",
            "answer": f"I am interested in applying for the {job.title} position at {job.company}.",
        })
        return answers

    def build_packet(
        self,
        job: Job,
        ats_info: ATSInfo,
        account_email: str = "",
    ) -> Dict[str, Any]:
        """Assembles the complete application submission packet."""
        candidate = self.load_candidate_profile(account_email)
        answers = self.generate_screening_answers(job, candidate)

        tailored_headline = job.title
        signature = "\n".join(
            value for value in (candidate.get("full_name"), candidate.get("email")) if value
        )
        cover_letter = (
            f"Dear Hiring Team at {job.company},\n\n"
            f"I am writing to express my interest in the {job.title} position. "
            "I would welcome the opportunity to discuss how my background aligns with the role.\n\n"
            f"Thank you for your consideration.\n\n"
            f"Sincerely{',' if signature else ''}\n{signature}"
        )

        return {
            "job": {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "url": job.url,
                "source": job.source,
                "ats_type": ats_info.code,
            },
            "candidate": candidate,
            "ats": {
                "code": ats_info.code,
                "name": ats_info.name,
                "category": ats_info.category,
                "supports_direct_api": ats_info.supports_direct_api,
            },
            "answers": answers,
            "tailored_resume_text": candidate.get("resume_raw") or tailored_headline,
            "cover_letter_text": cover_letter,
            "tailored_headline": tailored_headline,
        }
