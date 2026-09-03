"""
src/tsenta/payload_builder.py — Constructs AI-Tailored Submission Packets for Tsenta.

Integrates:
1. Candidate profile (Name, email, LinkedIn, GitHub, Portfolio, 4 YOE).
2. Tech stack keyword matching and tailored resume text synthesis.
3. Contextual cover letter generation.
4. Screening question resolution via AnswerBankService in candidate's voice.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.answer_bank.service import AnswerBankService
from src.ai.unified_ai_service import UnifiedAIService
from src.models import Job, Resume

logger = logging.getLogger("tsenta_payload_builder")


class TsentaPayloadBuilder:
    """Builds complete, ATS-optimized application packets for Tsenta."""

    def __init__(self, db: Session, ai_service: Optional[UnifiedAIService] = None):
        self.db = db
        self.ai_service = ai_service or UnifiedAIService()
        self.answer_bank = AnswerBankService(db=self.db, ai_service=self.ai_service)
        
        # Default candidate profile
        self.candidate_name = os.getenv("SENDER_NAME", "Kushall Jain")
        self.candidate_email = os.getenv("GMAIL_ADDRESS", "canaby007@gmail.com")
        self.candidate_phone = os.getenv("CANDIDATE_PHONE", "+91 98765 43210")
        self.candidate_linkedin = os.getenv("LINKEDIN_URL", "https://linkedin.com/in/kushall-jain-263009261")
        self.candidate_github = os.getenv("GITHUB_URL", "https://github.com/kushallj")
        self.candidate_location = os.getenv("CANDIDATE_LOCATION", "Bengaluru, India / Remote")
        self.yoe = 4.0

    def extract_job_keywords(self, job_desc: str, title: str) -> List[str]:
        """Extract prominent tech tokens and requirements from job details."""
        combined = f"{title} {job_desc}".lower()
        KNOWN_TOKENS = [
            "python", "fastapi", "react", "next.js", "typescript", "javascript",
            "postgresql", "redis", "kafka", "docker", "kubernetes", "aws", "gcp",
            "microservices", "distributed systems", "graphql", "rest api", "ci/cd",
            "asyncio", "celery", "sql", "nosql", "mongodb", "terraform", "llm", "ai"
        ]
        matched = [token for token in KNOWN_TOKENS if re.search(rf"\b{re.escape(token)}\b", combined)]
        return matched or ["python", "fastapi", "react", "distributed systems"]

    def tailor_resume_summary(self, job: Job, base_skills: List[str]) -> str:
        """Create ATS-tailored resume summary emphasizing matched keywords."""
        company = job.company or "the engineering organization"
        title = job.title or "Software Engineer"
        keywords_str = ", ".join(base_skills[:6])

        summary = (
            f"Results-driven Software Engineer with {self.yoe} years of experience designing and scaling "
            f"high-throughput backend microservices and modern full-stack web applications. "
            f"Proven expertise in {keywords_str}, asynchronous distributed systems, and low-latency API architecture. "
            f"Eager to contribute immediately to {company}'s {title} roadmap."
        )
        return summary

    def generate_cover_letter(self, job: Job, matched_keywords: List[str]) -> str:
        """Generate high-conversion, concise cover letter."""
        first_name = self.candidate_name.split()[0]
        company = job.company or "your team"
        title = job.title or "Software Engineer"
        stack_str = ", ".join(matched_keywords[:5])

        letter = f"""Dear Hiring Team at {company},

I am writing to express my strong interest in the {title} position at {company}. With {self.yoe} years of hands-on experience building fault-tolerant backend systems and modern full-stack applications ({stack_str}), I am confident in my ability to make an immediate, meaningful impact on your engineering initiatives.

Throughout my career, I have specialized in designing high-concurrency microservices, optimizing database throughput (PostgreSQL, Redis, Kafka), and building clean, test-driven RESTful architectures with FastAPI and Python. Furthermore, I have extensive experience collaborating cross-functionally to ship robust products with strict SLA and performance requirements.

What excites me most about {company} is your commitment to technical excellence and product innovation. I would welcome the opportunity to discuss how my technical depth, scalable system design background, and passion for engineering align with your current goals.

Thank you for your time and consideration.

Sincerely,
{self.candidate_name}
{self.candidate_linkedin}
{self.candidate_email}
"""
        return letter

    async def resolve_screening_questions(
        self, job: Job, sample_questions: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """Resolve screening questions via AnswerBankService in candidate's voice."""
        default_screening = sample_questions or [
            "How many years of work experience do you have with Python and backend development?",
            "Do you now or in the future require visa sponsorship?",
            "What is your expected salary range?",
            "Why are you interested in joining our engineering team?",
            "Are you comfortable working in a fast-paced environment or remote setup?",
        ]

        candidate_ctx = {
            "name": self.candidate_name,
            "years_of_experience": self.yoe,
            "core_skills": "Python, FastAPI, React, PostgreSQL, Redis, Kafka, Cloud Distributed Systems",
            "location": self.candidate_location,
            "current_title": "Software Engineer",
            "target_company": job.company or "Tech Company",
            "target_role": job.title or "Software Engineer",
        }

        qa_pairs: List[Dict[str, str]] = []
        for q in default_screening:
            answer = await self.answer_bank.get_or_generate_answer(
                question_text=q,
                candidate_context=candidate_ctx,
                category="ats_screening",
                context="tsenta_auto_apply",
            )
            qa_pairs.append({
                "question": q,
                "answer": answer.strip() if answer else f"Yes, I bring {self.yoe} years of relevant engineering experience.",
            })

        return qa_pairs

    async def build_submission_packet(
        self, job: Job, sample_questions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Assemble the complete Tsenta application payload."""
        keywords = self.extract_job_keywords(job.description or "", job.title or "")
        tailored_summary = self.tailor_resume_summary(job, keywords)
        cover_letter = self.generate_cover_letter(job, keywords)
        screening_qa = await self.resolve_screening_questions(job, sample_questions)

        # Standard structured candidate data
        packet = {
            "applicant": {
                "full_name": self.candidate_name,
                "first_name": self.candidate_name.split()[0],
                "last_name": self.candidate_name.split()[-1] if len(self.candidate_name.split()) > 1 else "",
                "email": self.candidate_email,
                "phone": self.candidate_phone,
                "linkedin": self.candidate_linkedin,
                "github": self.candidate_github,
                "location": self.candidate_location,
                "years_experience": self.yoe,
            },
            "job": {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "url": job.url,
                "location": job.location,
            },
            "tailored_resume": {
                "headline": f"Software Engineer | {', '.join(keywords[:4])}",
                "summary": tailored_summary,
                "matched_skills": keywords,
                "experience_years": self.yoe,
            },
            "cover_letter": cover_letter,
            "screening_questions": screening_qa,
            "eeo_disclosures": {
                "authorized_to_work": True,
                "requires_sponsorship": False,
                "veteran_status": "Decline to state",
                "disability_status": "Decline to state",
            },
        }

        return packet
