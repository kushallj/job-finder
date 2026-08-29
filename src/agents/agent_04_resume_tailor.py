"""
agent_04_resume_tailor.py — Resume Tailoring Agent.

STRATEGY
--------
Your labor-market positioning analysis found a specific, fixable mismatch:
the resume headline leads with Node.js while every production backend
artifact is Django REST Framework / FastAPI. This agent re-orders and
re-weights resume bullets per target role so the headline and top bullets
match what that company's ATS keyword search and human reviewer expect —
without inventing anything not already in data/resume.txt (hard rule).

Two tiers, cheapest-first:
  Tier 1 (always runs) — deterministic reordering: pulls the
    `differentiators` list from config/profile.yml and ranks them by
    keyword overlap with the job description, then emits a suggested
    bullet order + a rewritten headline using ONLY existing profile text.
  Tier 2 (optional, LLM) — if src/ai/unified_ai_service is importable and
    a provider is healthy, ask it to smooth phrasing of the Tier-1 output
    into natural sentences. Never asked to add facts — only rephrase.

DAG node contract:
    Input:  AgentContext, company: str, job_description: str
    Output: AgentResult.data = {
        "headline": str, "ordered_bullets": [...], "used_llm": bool
    }
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .base import AgentContext, AgentResult, BaseAgent

try:
    from src.ai.unified_ai_service import UnifiedAIService
    _AI_AVAILABLE = True
except Exception:  # noqa: BLE001 - repo may not have AI deps/env configured
    _AI_AVAILABLE = False


class ResumeTailorAgent(BaseAgent):
    name = "resume_tailor"

    def run(self, company: str, job_description: str = "", use_llm: bool = True) -> AgentResult:
        return self._timed(self._run, company, job_description, use_llm)

    def _run(self, company: str, job_description: str, use_llm: bool) -> AgentResult:
        profile = self.context.profile
        positioning = profile.get("positioning", {})
        differentiators: List[str] = positioning.get("differentiators", [])
        lead_with: List[str] = positioning.get("lead_with", [])

        jd_l = job_description.lower()
        ranked = sorted(
            differentiators,
            key=lambda bullet: self._overlap_score(bullet, jd_l),
            reverse=True,
        )

        headline = self._build_headline(positioning, jd_l, lead_with)

        used_llm = False
        if use_llm and _AI_AVAILABLE and job_description:
            polished = self._try_llm_polish(headline, ranked, job_description)
            if polished:
                headline, ranked = polished
                used_llm = True

        company_cfg = self.context.company(company) or {}
        note = company_cfg.get("why_target_now", "")

        return AgentResult(
            agent=self.name,
            ok=True,
            summary=f"Tailored resume framing for {company} ({'LLM-polished' if used_llm else 'template'}).",
            data={
                "company": company,
                "headline": headline,
                "ordered_bullets": ranked,
                "used_llm": used_llm,
                "targeting_note": note,
            },
        )

    @staticmethod
    def _overlap_score(bullet: str, jd_l: str) -> int:
        bullet_l = bullet.lower()
        keywords = [w for w in bullet_l.replace(",", " ").replace("(", " ").split() if len(w) > 3]
        return sum(1 for k in keywords if k in jd_l)

    @staticmethod
    def _build_headline(positioning: Dict[str, Any], jd_l: str, lead_with: List[str]) -> str:
        base = positioning.get("headline", "")
        # If JD is security-flavored, foreground the security differentiator language.
        if any(w in jd_l for w in ["security", "auth", "access control", "rbac", "compliance"]):
            return base.replace(
                "specializing in API access-control hardening",
                "with hands-on API access-control and auth hardening experience",
            )
        return base

    def _try_llm_polish(self, headline: str, bullets: List[str], job_description: str):
        """Best-effort LLM smoothing. Returns None on any failure — caller
        keeps the deterministic Tier-1 output, which is always valid."""
        try:
            prompt = (
                "Rephrase (do not add facts) the following resume headline and bullets "
                "so they read naturally for this job description. Keep every number and "
                "proper noun EXACTLY as given. Return the headline on the first line, "
                "then each bullet on its own line prefixed with '- '.\n\n"
                f"JOB DESCRIPTION:\n{job_description[:2000]}\n\n"
                f"HEADLINE:\n{headline}\n\nBULLETS:\n" + "\n".join(f"- {b}" for b in bullets)
            )
            service = UnifiedAIService()
            text = asyncio.get_event_loop().run_until_complete(
                service.generate_text(prompt, max_tokens=400)
            ) if not asyncio.get_event_loop().is_running() else asyncio.run(
                service.generate_text(prompt, max_tokens=400)
            )
            if not text:
                return None
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if not lines:
                return None
            new_headline = lines[0]
            new_bullets = [l.lstrip("- ").strip() for l in lines[1:] if l.startswith("-")]
            return new_headline, (new_bullets or bullets)
        except Exception:  # noqa: BLE001
            self.log.debug("LLM polish unavailable, using template output", exc_info=True)
            return None


if __name__ == "__main__":
    ctx = AgentContext.load()
    result = ResumeTailorAgent(ctx).run(
        company="Perfios",
        job_description="Backend engineer, Django REST Framework, PostgreSQL, RBAC, JWT auth, BFSI SaaS",
        use_llm=False,
    )
    print(result.to_json())
