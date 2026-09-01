"""
Domain Entity: Application
Tracks matching score, tailoring state, and stage transitions for a target job.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    READY = "ready"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"


@dataclass
class Application:
    """
    Domain entity encapsulating candidate application status and match score.

    Time Complexity:
        State transition & validation: O(1)
    Space Complexity:
        O(1)
    """

    job_id: int
    id: Optional[int] = None
    match_score: int = 0
    status: ApplicationStatus = ApplicationStatus.SAVED
    tailored_resume_text: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    key_strengths: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)

    def transition_to(self, new_status: ApplicationStatus) -> None:
        """
        State machine transition with timestamp refresh.

        Time Complexity: O(1)
        """
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def is_high_match(self, threshold: int = 70) -> bool:
        """Check if match score qualifies for autonomous outreach."""
        return self.match_score >= threshold
