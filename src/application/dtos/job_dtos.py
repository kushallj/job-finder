"""
Application DTOs: JobDTOs
Data Transfer Objects for job querying, ingestion, and response presentation.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class JobQueryParamsDTO:
    """Input parameters for filtered job search."""

    page: int = 1
    limit: int = 50
    search: Optional[str] = None
    region: Optional[str] = None
    experience_level: Optional[str] = None
    years_of_experience: Optional[int] = None
    date_posted: Optional[str] = None
    tech_stack: Optional[str] = None
    source: Optional[str] = None
    has_remote: Optional[bool] = None
    sort_by: str = "fetched_at"
    sort_order: str = "desc"


@dataclass
class JobResponseDTO:
    """Output presentation DTO for individual job entity."""

    id: int
    job_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_date: Optional[str]
    fetched_at: str
    match_score: Optional[int] = None
    application_status: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    has_remote: bool = False
    work_mode: str = "onsite"
    experience_level: Optional[str] = None
    tags: List[str] = None
    ghost_probability: float = 0.0
    ghost_risk_level: str = "low"
    ghost_verified_active: bool = True
    matched_skills: List[str] = None
    missing_skills: List[str] = None
    reasons: List[str] = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []
        if self.matched_skills is None:
            self.matched_skills = []
        if self.missing_skills is None:
            self.missing_skills = []
        if self.reasons is None:
            self.reasons = []


@dataclass
class PaginatedJobsResultDTO:
    """Paginated result envelope for job listings."""

    status: str
    jobs: List[JobResponseDTO]
    page: int
    limit: int
    total: int
    pages: int
