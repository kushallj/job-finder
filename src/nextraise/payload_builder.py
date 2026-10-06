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

    def load_candidate_profile(self, account_email: str = "canaby007@gmail.com") -> Dict[str, Any]:
        """Loads baseline candidate profile, skills, and contact information."""
        resume_text = ""
        for path in ["data/resume.txt", "data/resume_profile.json", "resume.txt"]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        resume_text = f.read()
                    break
                except Exception:
                    pass

        return {
            "first_name": "Kushal",
            "last_name": "Jain",
            "full_name": "Kushal Jain",
            "email": account_email,
            "phone": "+1-415-555-0199",
            "location": "San Francisco, CA / Remote",
            "linkedin": "https://linkedin.com/in/kushal-jain",
            "github": "https://github.com/canaby007",
            "portfolio": "https://kushaljain.dev",
            "work_authorization": "Authorized to work in US / Remote",
            "sponsorship_required": False,
            "years_of_experience": 5,
            "skills": [
                "Python", "FastAPI", "Kotlin", "Java", "Go", "React", "TypeScript",
                "Docker", "Kubernetes", "AWS", "Distributed Systems", "PostgreSQL", "Redis"
            ],
            "resume_raw": resume_text,
        }

    def generate_screening_answers(self, job: Job, candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generates intelligent answers to standard ATS screening questions."""
        return [
            {
                "question": "Are you legally authorized to work in this location?",
                "type": "boolean",
                "answer": "Yes"
            },
            {
                "question": "Will you now or in the future require visa sponsorship?",
                "type": "boolean",
                "answer": "No"
            },
            {
                "question": "How many years of experience do you have with modern backend technologies?",
                "type": "numeric",
                "answer": str(candidate.get("years_of_experience", 5))
            },
            {
                "question": "When is your earliest available start date?",
                "type": "text",
                "answer": "Immediately / 2 weeks notice"
            },
            {
                "question": "Why are you interested in this position?",
                "type": "text",
                "answer": f"Excited by {job.company}'s engineering challenges and scaling {job.title} initiatives."
            }
        ]

    def build_packet(
        self,
        job: Job,
        ats_info: ATSInfo,
        account_email: str = "canaby007@gmail.com",
    ) -> Dict[str, Any]:
        """Assembles the complete application submission packet."""
        candidate = self.load_candidate_profile(account_email)
        answers = self.generate_screening_answers(job, candidate)

        # Generate tailored resume headline & cover letter
        tailored_headline = f"{job.title} — {candidate['full_name']}"
        cover_letter = (
            f"Dear Hiring Team at {job.company},\n\n"
            f"I am writing to express my enthusiastic interest in the {job.title} position. "
            f"With extensive hands-on experience across {', '.join(candidate['skills'][:6])}, "
            f"I am confident in my ability to immediately contribute to {job.company}'s mission.\n\n"
            f"Thank you for your consideration.\n\n"
            f"Sincerely,\n{candidate['full_name']}\n{candidate['email']}"
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
