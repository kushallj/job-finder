"""
agent_08_interview_prepper.py — Interview Prep Agent.

STRATEGY
--------
Triggered when a role moves to "Interview" status in data/applications.md
(see CLAUDE.md status list), not as part of the daily outreach pipeline —
company research is comparatively expensive (network calls, LLM tokens),
so it only runs for companies that have actually responded.

Combines three sources into one dossier:
  1. config/target_companies.yml   — the funding/hiring signal + why_target_now
     rationale you can reference directly ("I saw the Series C news...")
  2. src/personalization/company_researcher.py — live GitHub org / blog /
     HN-mention research (async, cached 7 days)
  3. config/profile.yml            — your own differentiators, so the
     dossier also suggests which of YOUR proof points map to what this
     company will likely probe for in interviews

DAG node contract:
    Input:  AgentContext, company: str, role_title: str = ""
    Output: AgentResult.data = {"dossier_markdown": str, "likely_focus_areas": [...]}
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from .base import AgentContext, AgentResult, BaseAgent

try:
    from src.personalization.company_researcher import CompanyResearcher
    _RESEARCHER_AVAILABLE = True
except Exception:  # noqa: BLE001
    _RESEARCHER_AVAILABLE = False

# Keyword -> likely interview focus area heuristics, informed by the
# recurring patterns from the resume positioning analysis (security,
# performance, distributed systems, ownership).
_FOCUS_HEURISTICS = {
    "credit-infra-saas": ["API security & compliance (BFSI-grade)", "system design for multi-tenant SaaS"],
    "fintech-lending": ["data integrity in financial transactions", "credit-scoring/rules-engine design", "auth & RBAC"],
    "cleantech-solar": ["IoT/device-command architecture", "event-driven pipeline design (Docker/Lambda/MQTT)"],
    "industrial-iot": ["distributed systems debugging", "hardware-in-the-loop reliability"],
}


class InterviewPrepAgent(BaseAgent):
    name = "interview_prepper"

    def run(self, company: str, role_title: str = "") -> AgentResult:
        return self._timed(self._run, company, role_title)

    def _run(self, company: str, role_title: str) -> AgentResult:
        company_cfg = self.context.company(company) or {}
        domain = company_cfg.get("domain", "")
        industry = company_cfg.get("industry", "")

        live_profile = None
        if _RESEARCHER_AVAILABLE and domain:
            try:
                live_profile = self._research(domain, company)
            except Exception:  # noqa: BLE001
                self.log.debug("Live company research failed, continuing with static config only", exc_info=True)

        focus_areas = _FOCUS_HEURISTICS.get(industry, ["general backend/system design fundamentals"])
        proof_points = self.context.profile.get("narrative", {}).get("proof_points_by_theme", {})

        dossier = self._build_dossier(company, role_title, company_cfg, live_profile, focus_areas, proof_points)

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Built interview dossier for {company}"
                    f"{' (with live research)' if live_profile and live_profile.is_rich else ' (static config only)'}.",
            data={"dossier_markdown": dossier, "likely_focus_areas": focus_areas},
        )

    @staticmethod
    def _research(domain: str, company: str):
        try:
            return asyncio.run(CompanyResearcher().research(domain, company))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(CompanyResearcher().research(domain, company))

    @staticmethod
    def _build_dossier(company, role_title, company_cfg, live_profile, focus_areas, proof_points) -> str:
        lines = [f"# Interview Dossier — {company}" + (f" ({role_title})" if role_title else "")]

        lines.append("\n## Why this company is on the target list")
        lines.append(company_cfg.get("why_target_now", "Not in target_companies.yml — verify manually."))

        lines.append("\n## Signals to reference naturally in conversation")
        for sig in company_cfg.get("signals", []):
            lines.append(f"- ({sig.get('date', '?')}) {sig.get('detail', '')} — {sig.get('source', '')}")

        if live_profile is not None:
            lines.append("\n## Live research (GitHub / blog / HN)")
            if live_profile.tech_stack:
                lines.append(f"- Tech stack signals: {', '.join(live_profile.tech_stack)}")
            if live_profile.recent_repos:
                lines.append(f"- Recent public repos: {', '.join(live_profile.recent_repos[:5])}")
            if live_profile.hn_mentions:
                lines.append(f"- Hacker News mentions: {', '.join(live_profile.hn_mentions[:3])}")
            if not live_profile.is_rich:
                lines.append("- No rich public signal found — lean on the funding/hiring signals above instead.")

        lines.append("\n## Likely interview focus areas (industry-informed heuristic)")
        for f in focus_areas:
            lines.append(f"- {f}")

        lines.append("\n## Your proof points mapped to likely focus areas")
        for theme, point in proof_points.items():
            lines.append(f"- **{theme}**: {point}")

        lines.append(
            "\n## Reminder\nNever invent metrics not in data/resume.txt / config/profile.yml "
            "when answering behavioral questions — use the proof points above verbatim."
        )
        return "\n".join(lines)


if __name__ == "__main__":
    ctx = AgentContext.load()
    result = InterviewPrepAgent(ctx).run(company="Perfios", role_title="Backend Software Engineer")
    print(result.data["dossier_markdown"])
