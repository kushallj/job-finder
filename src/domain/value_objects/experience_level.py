"""
Domain Value Object: ExperienceLevel
Encapsulates seniority hierarchy, years of experience, and canonical leveling.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SeniorityTier(str, Enum):
    ENTRY = "Junior / Entry"
    MID = "Mid-Level"
    SENIOR = "Senior"
    STAFF = "Lead / Staff / Principal"
    DIRECTOR = "Director / VP / Exec"


@dataclass(frozen=True)
class ExperienceLevel:
    """
    Immutable value object representing engineering seniority.

    Time Complexity:
        Normalization: O(1)
    Space Complexity:
        O(1)
    """

    tier: SeniorityTier
    min_years: int
    max_years: Optional[int] = None

    @classmethod
    def from_years(cls, years: int) -> "ExperienceLevel":
        """
        Derive canonical tier from numeric years of experience.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        if years <= 2:
            return cls(tier=SeniorityTier.ENTRY, min_years=0, max_years=2)
        if years <= 5:
            return cls(tier=SeniorityTier.MID, min_years=3, max_years=5)
        if years <= 8:
            return cls(tier=SeniorityTier.SENIOR, min_years=5, max_years=8)
        if years <= 12:
            return cls(tier=SeniorityTier.STAFF, min_years=8, max_years=12)
        return cls(tier=SeniorityTier.DIRECTOR, min_years=12, max_years=None)

    @classmethod
    def from_text(cls, raw_title: str) -> "ExperienceLevel":
        """
        Parse seniority from job title text.

        Time Complexity: O(L) where L is string length.
        Space Complexity: O(1)
        """
        title = raw_title.lower()
        if any(k in title for k in ("director", "head", "vp", "chief", "cto")):
            return cls(tier=SeniorityTier.DIRECTOR, min_years=12)
        if any(k in title for k in ("staff", "principal", "lead", "architect", "manager")):
            return cls(tier=SeniorityTier.STAFF, min_years=8, max_years=12)
        if any(k in title for k in ("senior", "sr", "l5", "sde 3", "swe 3")):
            return cls(tier=SeniorityTier.SENIOR, min_years=5, max_years=8)
        if any(k in title for k in ("mid", "swe ii", "sde 2", "sde ii", "l4")):
            return cls(tier=SeniorityTier.MID, min_years=3, max_years=5)
        return cls(tier=SeniorityTier.ENTRY, min_years=0, max_years=2)
