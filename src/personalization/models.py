"""
models.py — Dataclasses for the Personalization Engine.

All dataclasses are plain (no SQLAlchemy) — the engine is stateless per call.
Caching of CompanyProfile / ContactProfile is done in SQLite inside
the engine itself (7-day TTL).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Research profiles
# ---------------------------------------------------------------------------

@dataclass
class CompanyProfile:
    """Everything we know about a company from public signals."""
    domain:           str
    name:             str
    tagline:          str             = ""
    tech_stack:       List[str]       = field(default_factory=list)
    recent_news:      List[str]       = field(default_factory=list)   # headlines / blog titles
    growth_signals:   List[str]       = field(default_factory=list)   # hiring, funding, launch
    pain_points:      List[str]       = field(default_factory=list)   # inferred from JD + blog
    culture_keywords: List[str]       = field(default_factory=list)   # "ownership", "async-first"
    github_org:       str             = ""
    recent_repos:     List[str]       = field(default_factory=list)   # repo names + descriptions
    hn_mentions:      List[str]       = field(default_factory=list)   # HN story titles
    research_sources: List[str]       = field(default_factory=list)   # URLs actually fetched

    @property
    def is_rich(self) -> bool:
        """True if we have enough data to generate non-generic hooks."""
        return bool(self.recent_news or self.recent_repos or self.hn_mentions)


@dataclass
class ContactProfile:
    """Everything we know about a specific person from public signals."""
    name:               str
    github_username:    str             = ""
    bio:                str             = ""
    languages:          List[str]       = field(default_factory=list)
    recent_repos:       List[str]       = field(default_factory=list)  # "repo_name: description"
    pinned_repos:       List[str]       = field(default_factory=list)
    recent_topics:      List[str]       = field(default_factory=list)  # GitHub topics / starred
    blog_posts:         List[str]       = field(default_factory=list)  # titles from personal site
    technical_keywords: List[str]       = field(default_factory=list)  # distilled tech interests
    research_sources:   List[str]       = field(default_factory=list)

    @property
    def is_rich(self) -> bool:
        return bool(self.bio or self.recent_repos or self.pinned_repos or self.blog_posts)


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

class HookType(str, Enum):
    TECH_ALIGNMENT    = "tech_alignment"    # shared tech / architecture interest
    COMPANY_SIGNAL    = "company_signal"    # recent company news / launch / repo
    CONTACT_RESONANCE = "contact_resonance" # contact's own work / writing / project
    ROLE_FIT          = "role_fit"          # specific JD requirement ↔ resume achievement
    CULTURE_FIT       = "culture_fit"       # culture keyword alignment
    GENERIC           = "generic"           # fallback — no specific data found


@dataclass
class Hook:
    type:      HookType
    text:      str            # 1-2 sentence hook ready to drop into email
    evidence:  str            # data point that generated this ("repo: xyz", "blog: abc")
    strength:  float = 0.5    # 0-1; drives personalization_score

    def __str__(self) -> str:
        return self.text


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class PersonalizedEmail:
    subject:              str
    body:                 str
    hooks_used:           List[Hook]         = field(default_factory=list)
    personalization_score: float             = 0.0    # 0-100
    word_count:           int                = 0
    subject_variants:     List[str]          = field(default_factory=list)  # A/B pool

    def is_personalized(self) -> bool:
        """True if the email uses at least one non-generic hook."""
        return any(h.type != HookType.GENERIC for h in self.hooks_used)


@dataclass
class PersonalizedOutreach:
    """Complete personalized outreach package for one contact × one job."""
    contact_name:          str
    company:               str
    email:                 PersonalizedEmail
    cover_letter:          str
    personalization_score: float
    company_profile:       Optional[CompanyProfile] = None
    contact_profile:       Optional[ContactProfile] = None
    research_time_ms:      int                      = 0   # wall-clock research duration
