"""
Domain Entity: Contact
Represents decision makers (Engineering Managers, Recruiters, Founders) at target companies.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from src.domain.value_objects.email_address import EmailAddress


@dataclass
class Contact:
    """
    Domain model for discovered company hiring contacts.

    Time Complexity:
        Initialization & Field Assignment: O(1)
    Space Complexity:
        O(1)
    """

    company: str
    name: str
    email: Optional[EmailAddress] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    confidence_score: int = 50
    source: str = "enrichment"
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = False

    def __post_init__(self) -> None:
        """Validate company and name boundaries."""
        if not self.company or not self.company.strip():
            raise ValueError("Contact company cannot be empty.")
        if not self.name or not self.name.strip():
            raise ValueError("Contact name cannot be empty.")

    def is_engineering_leader(self) -> bool:
        """Heuristic check for technical decision makers."""
        if not self.title:
            return False
        t = self.title.lower()
        return any(
            k in t
            for k in (
                "vp of engineering",
                "engineering manager",
                "head of engineering",
                "director of engineering",
                "cto",
                "tech lead",
                "chief technology officer",
            )
        )
