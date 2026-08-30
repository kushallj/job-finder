"""
agent_12_influencer.py — Influencer / Visibility Agent.

STRATEGY
--------
This is the ToS-safe version of "run this on LinkedIn/X": it does not log
into any platform, does not scrape feeds, and does not auto-post. Both
LinkedIn and X explicitly prohibit automated posting/engagement outside
their official partner APIs (which require business approval this repo
doesn't have), and account-level automation risks a ban — not a trade-off
worth making for a job search.

What it does instead: drafts short, specific posts built ONLY from real
material — a proof point from config/profile.yml, or a challenge/solution
sketch from agent_10_challenge_solver.py — timed to a target company's
signal (so the post is topical, not generic "excited to share" filler).
You review and post it yourself in one copy-paste, same review gate as
every outreach email in this system.

Why this matters for the job search: recruiters and engineering managers
at your target companies often check a candidate's recent posts before
replying to a cold email. A thin trail of generic "excited to announce"
posts hurts more than no posts at all; a small number of specific,
technical posts that reference real signals (a company's funding round, a
genuine engineering problem) helps.

DAG node contract:
    Input:  AgentContext, angle: str = "proof_point" | "challenge" | "signal_reaction",
            company: Optional[str] = None, challenge_data: Optional[dict] = None
    Output: AgentResult.data = {"platform_drafts": {"linkedin": str, "x": str}}
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import AgentContext, AgentResult, BaseAgent

X_CHAR_LIMIT = 280


class InfluencerAgent(BaseAgent):
    name = "influencer"

    def run(self, angle: str = "proof_point", company: Optional[str] = None,
            challenge_data: Optional[Dict[str, Any]] = None) -> AgentResult:
        return self._timed(self._run, angle, company, challenge_data)

    def _run(self, angle: str, company: Optional[str], challenge_data: Optional[Dict[str, Any]]) -> AgentResult:
        profile = self.context.profile
        narrative = profile.get("narrative", {})
        proof_points = narrative.get("proof_points_by_theme", {})

        if angle == "challenge" and challenge_data and challenge_data.get("identified_challenge"):
            linkedin, x_post = self._draft_challenge_posts(company, challenge_data)
        elif angle == "signal_reaction" and company:
            linkedin, x_post = self._draft_signal_reaction_posts(company)
        else:
            linkedin, x_post = self._draft_proof_point_posts(proof_points)

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Drafted {angle} post pair — review and post manually, nothing here auto-publishes.",
            data={
                "platform_drafts": {"linkedin": linkedin, "x": x_post},
                "reminder": "Copy-paste only. No auto-posting, no scraping — post these yourself.",
            },
        )

    def _draft_proof_point_posts(self, proof_points: Dict[str, str]):
        point = next(iter(proof_points.values()), "")
        linkedin = (
            f"A small technical note from recent work:\n\n{point}\n\n"
            f"The pattern that keeps showing up for me is the same: find the thing nobody's "
            f"watching (access control, a slow query, an unowned edge case), fix it, and measure "
            f"the before/after. Curious what similar patterns others have run into."
        )
        x_post = self._truncate_for_x(f"Recent work note: {point} Small fixes, measured before/after.")
        return linkedin, x_post

    def _draft_challenge_posts(self, company: Optional[str], challenge_data: Dict[str, Any]):
        challenge = challenge_data.get("identified_challenge", "")
        matched = challenge_data.get("matched_proof_points", [])
        anchor = matched[0] if matched else ""
        linkedin = (
            f"Been thinking about a problem a lot of teams in this space run into: {challenge}\n\n"
            f"Worked through something similar before: {anchor}\n\n"
            f"Not naming names, but if you're on an engineering team dealing with this kind of thing, "
            f"happy to swap notes."
        )
        x_post = self._truncate_for_x(f"Problem a lot of eng teams hit: {challenge}. Dealt with something similar: {anchor}")
        return linkedin, x_post

    def _draft_signal_reaction_posts(self, company: str):
        company_cfg = self.context.company(company) or {}
        signals = company_cfg.get("signals", [])
        detail = signals[0].get("detail", "") if signals else f"{company}'s recent growth"
        linkedin = (
            f"Saw that {detail} — congrats to the {company} team.\n\n"
            f"Companies at this stage usually hit the same wall: the platform/security work that was "
            f"'good enough' at 10x smaller scale stops being good enough. That's the kind of problem "
            f"I like working on."
        )
        x_post = self._truncate_for_x(f"Congrats to {company} on {detail}. That stage always surfaces the same platform/security wall.")
        return linkedin, x_post

    @staticmethod
    def _truncate_for_x(text: str) -> str:
        return text if len(text) <= X_CHAR_LIMIT else text[:X_CHAR_LIMIT - 1].rsplit(" ", 1)[0] + "…"


if __name__ == "__main__":
    ctx = AgentContext.load()
    result = InfluencerAgent(ctx).run(angle="signal_reaction", company="SolarSquare")
    print(result.to_json())
