"""
role_hierarchy.py — Role taxonomy, seniority scoring, decision-maker matrix.

Core insight: the right contact depends on BOTH the role tier AND the company size.

  Small startup (1-50 people):
    Best contact for SWE role = CTO (makes all eng hiring calls)
    Recruiter barely exists; HR = office manager

  Mid-size (51-500):
    Best = Engineering Manager / VP Eng
    Recruiter handles process but EM makes decision

  Large (500+):
    Best = Engineering Manager (direct decision maker)
    VP / Director = budget owner (worth CC'ing)
    Recruiter = gatekeeper (must be engaged, not bypassed)

Role Tier taxonomy (7 tiers, 0 = most senior):
  TIER_0  FOUNDER    CEO, CTO, Co-Founder, Founder
  TIER_1  C_SUITE    Chief*, President, COO, CFO, CMO
  TIER_2  VP         Vice President, SVP, EVP
  TIER_3  DIRECTOR   Director, Head of
  TIER_4  MANAGER    Manager, Lead, Principal (tech lead), Staff (eng)
  TIER_5  RECRUITER  HR, Recruiter, Talent Acquisition, People Ops
  TIER_6  IC         Engineer, Developer, Designer, Analyst, Scientist
  TIER_7  UNKNOWN    Unclassified

Decision-maker probability matrix:
  decision_maker_prob[tier][company_size_bucket] → float (0-1)
  company_size_buckets: "tiny" (<50), "small" (50-200), "mid" (200-1000), "large" (1000+)

Department relevance:
  For a tech job, engineering contacts score higher than marketing.
  Recruiter is always relevant (process) but rarely the decision maker.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Role Tier enum
# ---------------------------------------------------------------------------

class RoleTier(IntEnum):
    FOUNDER   = 0
    C_SUITE   = 1
    VP        = 2
    DIRECTOR  = 3
    MANAGER   = 4
    RECRUITER = 5
    IC        = 6
    UNKNOWN   = 7


# ---------------------------------------------------------------------------
# Decision-maker probability matrix
# decision_maker_prob[tier][size_bucket] = probability (0-1)
# Size buckets: tiny=<50, small=50-200, mid=200-1000, large=1000+
# ---------------------------------------------------------------------------

_DM_MATRIX: Dict[RoleTier, Dict[str, float]] = {
    RoleTier.FOUNDER:   {"tiny": 0.95, "small": 0.85, "mid": 0.50, "large": 0.20},
    RoleTier.C_SUITE:   {"tiny": 0.90, "small": 0.80, "mid": 0.55, "large": 0.25},
    RoleTier.VP:        {"tiny": 0.85, "small": 0.78, "mid": 0.70, "large": 0.50},
    RoleTier.DIRECTOR:  {"tiny": 0.80, "small": 0.75, "mid": 0.72, "large": 0.60},
    RoleTier.MANAGER:   {"tiny": 0.80, "small": 0.82, "mid": 0.85, "large": 0.88},
    RoleTier.RECRUITER: {"tiny": 0.40, "small": 0.50, "mid": 0.55, "large": 0.60},
    RoleTier.IC:        {"tiny": 0.10, "small": 0.08, "mid": 0.05, "large": 0.03},
    RoleTier.UNKNOWN:   {"tiny": 0.30, "small": 0.25, "mid": 0.20, "large": 0.15},
}

# Department relevance for a tech/engineering job (multiplier)
_DEPT_RELEVANCE: Dict[str, float] = {
    "engineering":    1.00,
    "product":        0.85,
    "data":           0.85,
    "ml":             0.85,
    "ai":             0.85,
    "platform":       0.90,
    "infrastructure": 0.90,
    "hr":             0.75,
    "people":         0.75,
    "talent":         0.75,
    "recruiting":     0.75,
    "finance":        0.30,
    "marketing":      0.25,
    "sales":          0.20,
    "legal":          0.15,
}

# Keyword → (tier, department) mappings
_TIER_RULES: List[Tuple[re.Pattern, RoleTier, str]] = [
    # FOUNDER
    (re.compile(r"\b(founder|co-founder|co.founder)\b", re.I), RoleTier.FOUNDER, "executive"),
    # C_SUITE
    (re.compile(r"\bchief\b", re.I),                            RoleTier.C_SUITE, "executive"),
    (re.compile(r"\bcto\b",   re.I),                            RoleTier.C_SUITE, "engineering"),
    (re.compile(r"\bceo\b",   re.I),                            RoleTier.C_SUITE, "executive"),
    (re.compile(r"\bcoo\b",   re.I),                            RoleTier.C_SUITE, "executive"),
    (re.compile(r"\bpresident\b", re.I),                        RoleTier.C_SUITE, "executive"),
    # VP
    (re.compile(r"\bvice\s+president\b|\bsvp\b|\bevp\b|\bvp\b", re.I), RoleTier.VP, ""),
    # DIRECTOR
    (re.compile(r"\bdirector\b|\bhead\s+of\b", re.I),           RoleTier.DIRECTOR, ""),
    # MANAGER / LEAD
    (re.compile(r"\bmanager\b|\bteam\s+lead\b|\blead\b", re.I), RoleTier.MANAGER, ""),
    (re.compile(r"\bstaff\s+(engineer|swe)\b", re.I),           RoleTier.MANAGER, "engineering"),
    (re.compile(r"\bprincipal\b", re.I),                        RoleTier.MANAGER, "engineering"),
    # RECRUITER / HR
    (re.compile(r"\brecruit\w*\b|\btalent\b|\bpeople\s+ops\b|\bhuman\s+resource\b", re.I),
                                                                  RoleTier.RECRUITER, "hr"),
    (re.compile(r"\bhrbp\b|\bhr\s+business\b", re.I),           RoleTier.RECRUITER, "hr"),
    # IC
    (re.compile(r"\bengineer\b|\bdeveloper\b|\bprogrammer\b|\bswe\b", re.I),
                                                                  RoleTier.IC, "engineering"),
    (re.compile(r"\bdata\s+scientist\b|\bml\s+engineer\b", re.I), RoleTier.IC, "data"),
    (re.compile(r"\bdesigner\b|\bux\b", re.I),                   RoleTier.IC, "product"),
    (re.compile(r"\banalyst\b", re.I),                           RoleTier.IC, "data"),
]

# Seniority keywords that shift the tier UP (more senior) within same category
_SENIORITY_BOOST = re.compile(
    r"\b(senior|sr\.?|staff|principal|distinguished|fellow|vp|svp|evp|executive)\b",
    re.I,
)


# ---------------------------------------------------------------------------
# HierarchyScore output
# ---------------------------------------------------------------------------

@dataclass
class HierarchyScore:
    tier:                 RoleTier
    tier_name:            str
    department:           str
    seniority_level:      str              # "junior" | "mid" | "senior" | "executive"
    decision_maker_prob:  float            # 0-1 for this tier × company size
    dept_relevance:       float            # 0-1 department relevance for tech role
    combined_dm_score:    float            # decision_maker_prob × dept_relevance × 100
    decision_path_role:   str              # "direct_decision_maker" | "budget_owner" | etc.
    outreach_notes:       str             # how to approach this person


# ---------------------------------------------------------------------------
# RoleHierarchy
# ---------------------------------------------------------------------------

class RoleHierarchy:
    """
    Classifies a job title into the role hierarchy and computes
    decision-maker probability for a given company size.

    Usage:
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Engineering Manager", company_size=200)
        print(score.combined_dm_score)   # → ~85
        print(score.decision_path_role)  # → "direct_decision_maker"
    """

    def score(
        self,
        title:        str,
        company_size: int   = 100,
        is_tech_role: bool  = True,
    ) -> HierarchyScore:
        """
        Score a contact title for decision-maker probability.

        Args:
            title:        Job title string ("Engineering Manager")
            company_size: Estimated headcount (0 = unknown, defaults to 100)
            is_tech_role: True if the target job is a tech/engineering role
        """
        tier, department = self._classify(title)
        size_bucket      = _size_bucket(company_size)
        dm_prob          = _DM_MATRIX[tier][size_bucket]

        # Department relevance (only for tech roles)
        dept_rel = _DEPT_RELEVANCE.get(department.lower(), 0.50) if is_tech_role else 1.0

        # Seniority level label
        seniority = _seniority_label(title, tier)

        combined = dm_prob * dept_rel * 100

        return HierarchyScore(
            tier                = tier,
            tier_name           = tier.name,
            department          = department,
            seniority_level     = seniority,
            decision_maker_prob = dm_prob,
            dept_relevance      = dept_rel,
            combined_dm_score   = round(combined, 1),
            decision_path_role  = _decision_path_role(tier, company_size),
            outreach_notes      = _outreach_notes(tier, company_size, seniority),
        )

    def classify_department(self, title: str) -> str:
        """Quick department classification from title."""
        _, dept = self._classify(title)
        return dept

    def get_tier(self, title: str) -> RoleTier:
        tier, _ = self._classify(title)
        return tier

    # ── Internal classifier ────────────────────────────────────────────────────

    @staticmethod
    def _classify(title: str) -> Tuple[RoleTier, str]:
        """
        Map a title string to (RoleTier, department).
        Tries rules in order (most specific first → UNKNOWN fallback).
        """
        if not title or not title.strip():
            return RoleTier.UNKNOWN, ""

        for pattern, tier, dept in _TIER_RULES:
            if pattern.search(title):
                # Derive department from title if not in rule
                if not dept:
                    dept = _dept_from_title(title)
                return tier, dept

        # Fallback: all-caps or very short → probably not a real title
        return RoleTier.UNKNOWN, _dept_from_title(title)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _size_bucket(size: int) -> str:
    if size <= 0 or size > 10_000:
        return "mid"     # unknown → assume mid
    if size < 50:
        return "tiny"
    if size < 200:
        return "small"
    if size < 1000:
        return "mid"
    return "large"


def _seniority_label(title: str, tier: RoleTier) -> str:
    if tier in (RoleTier.FOUNDER, RoleTier.C_SUITE):
        return "executive"
    if tier == RoleTier.VP:
        return "executive"
    if tier == RoleTier.DIRECTOR:
        return "senior"
    if _SENIORITY_BOOST.search(title):
        return "senior"
    if tier == RoleTier.MANAGER:
        return "senior"
    if tier == RoleTier.IC:
        return "mid"
    return "mid"


def _dept_from_title(title: str) -> str:
    """Infer department from title keywords."""
    t = title.lower()
    if any(k in t for k in ("engineer", "developer", "software", "backend", "frontend", "fullstack", "platform", "infra", "sre", "devops")):
        return "engineering"
    if any(k in t for k in ("data", "analytics", "scientist", "ml", "machine learning", "ai")):
        return "data"
    if any(k in t for k in ("product", "pm", "program manager")):
        return "product"
    if any(k in t for k in ("recruit", "talent", "hr", "people", "human resource")):
        return "hr"
    if any(k in t for k in ("design", "ux", "ui")):
        return "product"
    if any(k in t for k in ("sales", "account", "business development", "bd")):
        return "sales"
    if any(k in t for k in ("market", "growth", "content", "brand")):
        return "marketing"
    if any(k in t for k in ("finance", "accounting", "cfo", "controller")):
        return "finance"
    return ""


def _decision_path_role(tier: RoleTier, company_size: int) -> str:
    """Return the contact's role in the hiring decision chain."""
    size_b = _size_bucket(company_size)

    if tier == RoleTier.MANAGER:
        return "direct_decision_maker"
    if tier in (RoleTier.FOUNDER, RoleTier.C_SUITE) and size_b in ("tiny", "small"):
        return "direct_decision_maker"
    if tier in (RoleTier.VP, RoleTier.DIRECTOR):
        return "budget_owner"
    if tier == RoleTier.RECRUITER:
        return "process_gatekeeper"
    if tier in (RoleTier.FOUNDER, RoleTier.C_SUITE):
        return "executive_sponsor"
    if tier == RoleTier.IC:
        return "peer_referrer"
    return "unknown"


def _outreach_notes(tier: RoleTier, company_size: int, seniority: str) -> str:
    """Return personalized outreach strategy note."""
    size_b = _size_bucket(company_size)

    if tier == RoleTier.MANAGER:
        return "Lead with technical depth — they care about what you'll build, not just your CV."
    if tier in (RoleTier.FOUNDER, RoleTier.C_SUITE) and size_b == "tiny":
        return "Founders move fast. Lead with impact metrics and mission alignment. Keep it < 100 words."
    if tier in (RoleTier.VP, RoleTier.DIRECTOR):
        return "They own the team roadmap. Lead with how you solve their team's scaling challenges."
    if tier == RoleTier.RECRUITER:
        return "Recruiters want a clean, complete pitch. Follow their process; never bypass ATS entirely."
    if tier == RoleTier.IC:
        return "Peers respond to technical curiosity. Ask about their stack — not about jobs."
    return "Keep it brief. Lead with a genuine reason for reaching out."
