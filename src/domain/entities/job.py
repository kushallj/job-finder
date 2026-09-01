"""
Domain Entity: Job
Pure business domain model representing a scraped or indexed job opportunity.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Optional, List
from src.domain.value_objects.compensation import Compensation
from src.domain.value_objects.tech_stack import TechStack
from src.domain.value_objects.experience_level import ExperienceLevel


@dataclass
class Job:
    """
    Domain entity encapsulating job attributes and business invariant behaviors.

    Time Complexity:
        Fingerprint hash calculation: O(L) where L is string length of (title + company + location).
    Space Complexity:
        O(1)
    """

    title: str
    company: str
    location: str = "Remote"
    description: str = ""
    url: str = ""
    source: str = "custom"
    job_id: Optional[str] = None
    id: Optional[int] = None
    posted_date: Optional[datetime] = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    compensation: Optional[Compensation] = None
    tech_stack: Optional[TechStack] = None
    experience_level: Optional[ExperienceLevel] = None
    has_remote: bool = False
    work_mode: str = "onsite"
    ghost_probability: float = 0.0
    ghost_risk_level: str = "low"
    ghost_verified_active: bool = True

    def __post_init__(self) -> None:
        """Ensure non-empty mandatory attributes and generate unique fingerprint job_id."""
        if not self.title or not self.title.strip():
            raise ValueError("Job title cannot be empty.")
        if not self.company or not self.company.strip():
            raise ValueError("Company name cannot be empty.")
        if not self.job_id:
            self.job_id = self.generate_fingerprint()

    def generate_fingerprint(self) -> str:
        """
        Generate deterministic SHA-256 fingerprint hash for O(1) deduplication.

        Time Complexity: O(L)
        Space Complexity: O(1)
        """
        payload = f"{self.company.lower().strip()}:{self.title.lower().strip()}:{self.location.lower().strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def is_fresh(self, max_age_days: int = 30) -> bool:
        """Check if job was posted within active recruitment window."""
        ref = self.posted_date or self.fetched_at
        now = datetime.now(timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        return (now - ref).total_seconds() <= (max_age_days * 86400)
