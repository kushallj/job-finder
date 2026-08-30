from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class ReferralProfile(BaseModel):
    """Pydantic model representing a discovered LinkedIn contact/profile."""
    id: Optional[str] = None
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    headline: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    mutual_connections: int = 0
    source: Optional[str] = "csv"  # 'api' | 'csv' | 'disk_cache' | 'extension'
    tags: List[str] = Field(default_factory=list)


class ReferralContext(BaseModel):
    """Context for generating personalized referral request letters and notes."""
    job_title: Optional[str] = None
    job_link: Optional[str] = None
    short_bio: Optional[str] = None
    highlight: Optional[str] = None
    sender_name: Optional[str] = "Candidate"
    reason: Optional[str] = None
    company: Optional[str] = None
    max_length: Optional[int] = None
