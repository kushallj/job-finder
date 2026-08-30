from __future__ import annotations

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from src.models import Job, Contact
from .models import GhostAnalysisResult
from .detector import ghost_job_detector, GhostJobDetector


class GhostHunterService:
    """Orchestrates Ghost Job analysis across raw postings and database records."""

    def __init__(self, detector: Optional[GhostJobDetector] = None):
        self.detector = detector or ghost_job_detector

    def analyze(
        self,
        title: str,
        company: str,
        description: str,
        posted_date: Optional[str] = None,
        has_decision_maker: bool = False,
    ) -> GhostAnalysisResult:
        return self.detector.analyze_job(
            title=title,
            company=company,
            description=description,
            posted_date=posted_date,
            has_decision_maker=has_decision_maker,
        )

    def analyze_db_job(self, db: Session, job_id: int) -> GhostAnalysisResult:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job #{job_id} not found")

        has_dm = db.query(Contact).filter(Contact.company == job.company).count() > 0

        return self.detector.analyze_job(
            title=job.title,
            company=job.company or "Company",
            description=job.description or "",
            posted_date=job.posted_date,
            fetched_at=job.fetched_at,
            has_decision_maker=has_dm,
        )


ghost_hunter_service = GhostHunterService()
