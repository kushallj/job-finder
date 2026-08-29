"""
agent_03_fit_scorer.py — Fit Scoring Agent.

STRATEGY
--------
Implements the exact evaluation rubric already defined in CLAUDE.md so
scores are consistent whether a human runs `/nexus pipeline`, Claude Code
evaluates a pasted JD, or this agent scores a batch of ATS-Hunter results.

    | # | Dimension              | Weight |
    |---|------------------------|--------|
    | 1 | Role match (skills/JD) | 25%    |
    | 2 | Career level fit       | 15%    |
    | 3 | Tech stack overlap     | 20%    |
    | 4 | Remote / location      | 10%    |
    | 5 | Company stage fit      | 10%    |
    | 6 | Growth potential       | 10%    |
    | 7 | Compensation vs target | 10%    |

Threshold for "worth applying": >= 65%. NEVER recommend applying below 50%
(hard rule from CLAUDE.md, enforced here too).

This agent is a *deterministic, explainable* scorer — no LLM call required,
so it's cheap enough to run against every ATS-Hunter result. Use
agent_04_resume_tailor.py's LLM-backed positioning only on roles that clear
this bar, to keep API costs down.

DAG node contract:
    Input:  AgentContext, roles: List[{company, title, description?, location, url}]
    Output: AgentResult.data = {"scored": [...] sorted desc, "worth_applying": [...]}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import AgentContext, AgentResult, BaseAgent

WEIGHTS = {
    "role_match": 0.25,
    "career_level": 0.15,
    "tech_stack": 0.20,
    "location": 0.10,
    "company_stage": 0.10,
    "growth_potential": 0.10,
    "compensation": 0.10,
}
APPLY_THRESHOLD = 65
FLOOR_THRESHOLD = 50  # CLAUDE.md: never recommend applying below this


@dataclass
class ScoredRole:
    company: str
    title: str
    url: str
    score: float
    dimension_scores: Dict[str, float]
    matched_skills: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    recommendation: str = "Skip"


class FitScorerAgent(BaseAgent):
    name = "fit_scorer"

    def run(self, roles: List[Dict[str, Any]]) -> AgentResult:
        return self._timed(self._run, roles)

    def _run(self, roles: List[Dict[str, Any]]) -> AgentResult:
        profile = self.context.profile
        lead_with = [s.lower() for s in profile.get("positioning", {}).get("lead_with", [])]
        target = profile.get("target", {})
        target_roles = [r.lower() for r in target.get("roles", [])]
        target_locations = [l.lower() for l in target.get("locations", [])]
        min_size, max_size = (target.get("company_size_employees") or [0, 10_000])
        comp_range = profile.get("compensation", {})

        scored: List[ScoredRole] = []
        for role in roles:
            company_cfg = self.context.company(role.get("company", "")) or {}
            dims = {}

            dims["role_match"] = self._score_role_match(role.get("title", ""), target_roles)
            dims["career_level"] = self._score_career_level(role.get("title", ""), profile)
            dims["tech_stack"], matched, gaps = self._score_tech_stack(
                role.get("description", "") or role.get("title", ""), lead_with
            )
            dims["location"] = self._score_location(role.get("location", ""), target_locations)
            dims["company_stage"] = self._score_company_stage(company_cfg)
            dims["growth_potential"] = self._score_growth_potential(company_cfg)
            dims["compensation"] = self._score_compensation(company_cfg, comp_range)

            total = sum(dims[k] * WEIGHTS[k] for k in WEIGHTS)
            recommendation = (
                "Apply" if total >= APPLY_THRESHOLD else
                "Consider" if total >= FLOOR_THRESHOLD else
                "Skip"
            )

            scored.append(ScoredRole(
                company=role.get("company", "unknown"),
                title=role.get("title", ""),
                url=role.get("url", ""),
                score=round(total, 1),
                dimension_scores={k: round(v, 1) for k, v in dims.items()},
                matched_skills=matched,
                gaps=gaps,
                recommendation=recommendation,
            ))

        scored.sort(key=lambda r: r.score, reverse=True)
        worth_applying = [r for r in scored if r.score >= APPLY_THRESHOLD]

        return AgentResult(
            agent=self.name,
            ok=True,
            summary=f"Scored {len(scored)} roles; {len(worth_applying)} clear the {APPLY_THRESHOLD}% apply threshold.",
            data={
                "scored": [r.__dict__ for r in scored],
                "worth_applying": [r.__dict__ for r in worth_applying],
            },
        )

    # -- dimension scorers (0-100 each) --------------------------------

    @staticmethod
    def _score_role_match(title: str, target_roles: List[str]) -> float:
        title_l = title.lower()
        if any(tr in title_l for tr in target_roles):
            return 100.0
        # partial credit for generic "software engineer" / "developer"
        if any(w in title_l for w in ["engineer", "developer", "sde"]):
            return 60.0
        return 20.0

    @staticmethod
    def _score_career_level(title: str, profile: Dict[str, Any]) -> float:
        title_l = title.lower()
        seniority = profile.get("positioning", {}).get("seniority", "")
        if any(w in title_l for w in ["staff", "principal", "lead", "head of", "director"]):
            return 30.0  # likely a stretch given resume-evidenced seniority
        if any(w in title_l for w in ["senior", "sde ii", "sde-2", "sde2", "ii"]):
            return 85.0 if "senior" in seniority.lower() or "sde ii" in seniority.lower() else 65.0
        if any(w in title_l for w in ["junior", "intern", "sde i", "sde-1", "associate"]):
            return 50.0  # likely underleveled
        return 75.0  # unspecified level — assume mid

    @staticmethod
    def _score_tech_stack(text: str, lead_with: List[str]):
        text_l = text.lower()
        matched = [t for t in lead_with if t.lower() in text_l]
        gaps = [t for t in lead_with if t.lower() not in text_l]
        if not lead_with:
            return 50.0, matched, gaps
        pct = len(matched) / len(lead_with)
        return round(pct * 100, 1), matched, gaps

    @staticmethod
    def _score_location(location: str, target_locations: List[str]) -> float:
        loc_l = (location or "").lower()
        if not loc_l:
            return 50.0  # unknown, don't penalize hard
        if "remote" in loc_l:
            return 100.0
        if any(tl in loc_l for tl in target_locations):
            return 100.0
        return 40.0

    @staticmethod
    def _score_company_stage(company_cfg: Dict[str, Any]) -> float:
        tier = company_cfg.get("tier")
        if tier == 1:
            return 90.0
        if tier == 2:
            return 70.0
        if tier == 3:
            return 45.0
        return 55.0  # not in target list at all

    @staticmethod
    def _score_growth_potential(company_cfg: Dict[str, Any]) -> float:
        prob = (company_cfg.get("hiring_probability") or "").lower()
        mapping = {
            "high": 95.0, "medium-high": 75.0, "medium": 55.0,
            "low-medium": 35.0, "low": 15.0,
        }
        return mapping.get(prob, 50.0)

    @staticmethod
    def _score_compensation(company_cfg: Dict[str, Any], comp_range: Dict[str, Any]) -> float:
        bench = company_cfg.get("comp_benchmark_inr_lpa") or {}
        median = bench.get("median")
        target_min = comp_range.get("target_ctc_lakhs_min")
        target_max = comp_range.get("target_ctc_lakhs_max")
        if median is None or target_min is None or target_max is None:
            return 50.0  # unknown — neutral score, don't penalize
        if target_min <= median <= target_max:
            return 100.0
        if median < target_min:
            # below target — scale down proportionally, floor at 20
            return max(20.0, 100.0 - (target_min - median) * 5)
        # above target range is still fine (upside), slight cap
        return 90.0


if __name__ == "__main__":
    ctx = AgentContext.load()
    demo_roles = [{
        "company": "Yubi", "title": "Backend Software Engineer (Python)",
        "description": "Django REST Framework, FastAPI, PostgreSQL, JWT auth",
        "location": "Bangalore, India", "url": "https://example.com/job/1",
    }]
    result = FitScorerAgent(ctx).run(demo_roles)
    print(result.to_json())
