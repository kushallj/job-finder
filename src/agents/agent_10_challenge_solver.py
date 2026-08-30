"""
agent_10_challenge_solver.py — Challenge Solver Agent ("real Networker").

STRATEGY
--------
This is the direct answer to "fix a real challenge for the company" instead
of generic networking. The insight: outreach that opens with "I noticed
you're hiring" is forgettable. Outreach that opens with "I noticed your
job description calls out {specific pain point}, and here's the exact
approach I used to solve the same problem at {my company}" gets forwarded
internally and remembered.

This agent does NOT invent a challenge — it only surfaces challenges that
are already stated in public signal:
  1. JD pain points     — src/resume_engine/jd_analyzer.py already extracts
                           these from the actual job description text
                           ("scaling microservices", "improving API
                           reliability", etc.) via rule-based parsing.
  2. Company signals     — config/target_companies.yml (funding stage,
                           expansion, product launches — these imply
                           specific operational challenges, e.g. "just
                           raised for overseas expansion" implies
                           multi-region/compliance challenges).
  3. Public research     — src/personalization/company_researcher.py
                           (GitHub repos, HN mentions, tech stack) as
                           supporting evidence, when available.

Then it maps ONLY the differentiators already in config/profile.yml against
that challenge — never inventing a new claimed achievement — and drafts a
short, concrete "here's how I'd approach this" solution sketch usable as:
  - the opening hook in agent_06's outreach email
  - a leave-behind one-pager after a first call
  - a talking point in interview prep (agent_08)

DAG node contract:
    Input:  AgentContext, company: str, job_description: str = ""
    Output: AgentResult.data = {
        "identified_challenge": str,
        "evidence": [...],
        "matched_proof_points": [...],
        "solution_sketch": str,
    }
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .base import AgentContext, AgentResult, BaseAgent

try:
    from src.resume_engine.jd_analyzer import JDAnalyzer
    _JD_AVAILABLE = True
except Exception:  # noqa: BLE001
    _JD_AVAILABLE = False

# Signal-type -> implied operational challenge, used only when no JD text
# is available yet (e.g. before you've found the actual posting).
_SIGNAL_TYPE_CHALLENGES = {
    "funding": "scaling engineering/infra fast enough to deploy new capital without breaking reliability",
    "ipo_filing": "hardening systems (auditability, uptime, security) to survive public-market/regulatory scrutiny",
    "expansion": "building multi-region/compliance-ready infrastructure for new markets",
    "leadership": "a new leadership team typically re-architects or re-prioritizes the platform roadmap",
    "product": "integrating a newly-launched product into existing systems without regressions",
    "acquisition": "integrating two codebases/data models post-acquisition",
    "financials": "sustaining growth-rate performance without a proportional cost/ops blowup",
}


class ChallengeSolverAgent(BaseAgent):
    name = "challenge_solver"

    def run(self, company: str, job_description: str = "") -> AgentResult:
        return self._timed(self._run, company, job_description)

    def _run(self, company: str, job_description: str) -> AgentResult:
        company_cfg = self.context.company(company) or {}
        differentiators = self.context.profile.get("positioning", {}).get("differentiators", [])
        proof_points = self.context.profile.get("narrative", {}).get("proof_points_by_theme", {})

        evidence: List[str] = []
        challenge = ""

        # Tier 1: real JD text, if we have it — strongest signal.
        if job_description and _JD_AVAILABLE:
            jd_points = self._extract_jd_pain_points(job_description)
            if jd_points:
                challenge = jd_points[0]
                evidence.append(f"Job description states: \"{challenge}\"")
                evidence.extend(f"Also mentioned: \"{p}\"" for p in jd_points[1:3])

        # Tier 2: fall back to signal-type inference from target_companies.yml
        if not challenge:
            for sig in company_cfg.get("signals", []):
                implied = _SIGNAL_TYPE_CHALLENGES.get(sig.get("type"))
                if implied:
                    challenge = implied
                    evidence.append(f"({sig.get('date', '?')}) {sig.get('detail', '')} — {sig.get('source', '')}")
                    break

        if not challenge:
            return AgentResult(
                agent=self.name, ok=True,
                summary=f"No specific challenge signal found for {company} — "
                        f"paste the actual JD text for a much stronger result.",
                data={"identified_challenge": "", "evidence": [], "matched_proof_points": [], "solution_sketch": ""},
                warnings=["Falling back to generic — this agent is only as good as the JD/signal text you feed it."],
            )

        matched = self._match_proof_points(challenge, differentiators, proof_points)
        sketch = self._draft_sketch(company, challenge, matched)

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Identified a concrete challenge for {company} and matched {len(matched)} real proof point(s).",
            data={
                "identified_challenge": challenge,
                "evidence": evidence,
                "matched_proof_points": matched,
                "solution_sketch": sketch,
            },
        )

    @staticmethod
    def _extract_jd_pain_points(job_description: str) -> List[str]:
        try:
            analyzer = JDAnalyzer()
            try:
                result = asyncio.run(analyzer.analyze(job_description))
            except RuntimeError:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(analyzer.analyze(job_description))
            return list(getattr(result, "pain_points", []) or [])
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _match_proof_points(challenge: str, differentiators: List[str],
                             proof_points: Dict[str, str]) -> List[str]:
        challenge_l = challenge.lower()
        matched = []
        keyword_theme_map = {
            "security": ["security", "auth", "compliance", "access", "audit"],
            "performance": ["scal", "performance", "latency", "reliab", "cost", "throughput"],
            "ownership": ["ownership", "roadmap", "architect", "integrat"],
            "scale": ["scal", "growth", "volume", "region"],
        }
        for theme, keywords in keyword_theme_map.items():
            if any(k in challenge_l for k in keywords) and theme in proof_points:
                matched.append(proof_points[theme])
        # Always include at least one differentiator as a fallback anchor.
        if not matched and differentiators:
            matched.append(differentiators[0])
        return matched

    @staticmethod
    def _draft_sketch(company: str, challenge: str, matched: List[str]) -> str:
        lines = [f"Challenge at {company}: {challenge}", ""]
        lines.append("Relevant proof (from my actual work — nothing invented here):")
        for m in matched:
            lines.append(f"  - {m}")
        lines.append("")
        lines.append(
            f"Suggested opener for outreach/interview: \"I noticed {company} is dealing with "
            f"{challenge} — at my current/previous role I dealt with a similar problem: "
            f"{matched[0].lower() if matched else '[fill from proof points above]'} Happy to walk through "
            f"how that approach might translate here.\""
        )
        return "\n".join(lines)


if __name__ == "__main__":
    ctx = AgentContext.load()
    result = ChallengeSolverAgent(ctx).run(
        company="Perfios",
        job_description="We need to scale our microservices and improve API reliability while maintaining "
                         "strict compliance and audit trails for BFSI customers as we expand internationally.",
    )
    print(result.to_json())
