from __future__ import annotations

import re
from typing import List
from .models import DiscoveredContact

PERSONA_TIERS = [
    (100, ["engineering manager", "eng manager", "em", "software engineering manager", "manager of engineering"]),
    (90, ["head of engineering", "head of tech", "head of software"]),
    (85, ["vp of engineering", "vice president", "vp engineering", "vp tech"]),
    (80, ["technical recruiter", "lead recruiter", "talent acquisition", "head of talent", "recruiter", "talent partner", "talent lead"]),
    (75, ["director of engineering", "engineering director", "director engineering", "director"]),
    (70, ["principal", "staff", "lead architect", "tech lead", "distinguished"]),
    (65, ["founder", "co-founder", "cto", "chief technology officer", "ceo"]),
    (50, ["software engineer", "backend engineer", "frontend engineer", "full stack", "developer", "engineer"]),
]


class PersonaScorer:
    """Ranks contacts by outreach effectiveness and decision-maker seniority."""

    @staticmethod
    def score_title(title: str) -> int:
        """Assigns hiring impact score (0-100) based on title."""
        if not title:
            return 30
        t_low = title.lower()
        for score, keywords in PERSONA_TIERS:
            if any(k in t_low for k in keywords):
                return score
        return 30

    @classmethod
    def rank_contacts(cls, contacts: List[DiscoveredContact]) -> List[DiscoveredContact]:
        """Calculates persona scores and sorts contacts in priority order."""
        for c in contacts:
            c.persona_score = cls.score_title(c.title)
        # Sort by (persona_score + confidence_score)
        return sorted(contacts, key=lambda c: (c.persona_score * 0.6 + c.confidence_score * 0.4), reverse=True)


persona_scorer = PersonaScorer()
