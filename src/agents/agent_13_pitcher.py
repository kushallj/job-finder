"""
agent_13_pitcher.py — Pitcher Agent (WIN narrative one-pager).

STRATEGY
--------
NxtJob.ai's "Pitcher" agent packages a candidate's positioning into what
they call a WIN deck: a Well-researched problem, an Insightful solution,
and a Narrative connecting the two. This agent builds the same artifact
using material this repo already produces for real, evidenced reasons —
it does not generate a new pitch from scratch:

    W (Well-researched problem) <- agent_10_challenge_solver.py's
                                    `identified_challenge` + `evidence`
    I (Insightful solution)     <- agent_10's `matched_proof_points` +
                                    agent_04_resume_tailor.py's ordered
                                    bullets for the same company/JD
    N (Narrative)                <- config/profile.yml `narrative.one_liner`
                                    + `positioning.headline`, tying W and I
                                    together into a single paragraph

Output is a markdown one-pager suitable for a leave-behind after a first
call, or as prep material immediately before an interview (hand it to
agent_08_interview_prepper.py's dossier as a companion document).

DAG node contract:
    Input:  AgentContext, company: str, job_description: str = ""
    Output: AgentResult.data = {
        "win_markdown": str,
        "problem": str, "solution_points": [...], "narrative": str,
    }
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import AgentContext, AgentResult, BaseAgent
from .agent_04_resume_tailor import ResumeTailorAgent
from .agent_10_challenge_solver import ChallengeSolverAgent


class PitcherAgent(BaseAgent):
    name = "pitcher"

    def run(self, company: str, job_description: str = "") -> AgentResult:
        return self._timed(self._run, company, job_description)

    def _run(self, company: str, job_description: str) -> AgentResult:
        challenge_result = ChallengeSolverAgent(self.context).run(
            company=company, job_description=job_description
        )
        tailor_result = ResumeTailorAgent(self.context).run(
            company=company, job_description=job_description, use_llm=False
        )

        problem = challenge_result.data.get("identified_challenge", "")
        evidence = challenge_result.data.get("evidence", [])
        solution_points = challenge_result.data.get("matched_proof_points", []) or \
            tailor_result.data.get("ordered_bullets", [])[:3]

        positioning = self.context.profile.get("positioning", {})
        narrative_cfg = self.context.profile.get("narrative", {})
        candidate_name = self.context.profile.get("candidate", {}).get("name", "")

        narrative = self._build_narrative(
            company, problem, solution_points, positioning, narrative_cfg
        )

        win_markdown = self._render(
            candidate_name, company, problem, evidence, solution_points, narrative,
            tailor_result.data.get("headline", positioning.get("headline", "")),
        )

        warnings = []
        if not problem:
            warnings.append(
                "No specific challenge found — paste the real job description for a much stronger pitch. "
                "Falling back to generic positioning."
            )

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Built WIN one-pager for {company}"
                    f"{' (evidence-backed)' if problem else ' (generic — needs JD)'}.",
            data={
                "win_markdown": win_markdown,
                "problem": problem,
                "solution_points": solution_points,
                "narrative": narrative,
            },
            warnings=warnings,
        )

    @staticmethod
    def _build_narrative(company: str, problem: str, solution_points,
                          positioning: Dict[str, Any], narrative_cfg: Dict[str, Any]) -> str:
        headline = positioning.get("headline", "")
        one_liner = narrative_cfg.get("one_liner", "")
        if problem:
            return (
                f"{company} is dealing with {problem}. {headline} "
                f"{one_liner} That combination is why this role is a fit, not just an "
                f"application — I'd be solving a problem I already have direct evidence "
                f"of solving, not learning it for the first time on the job."
            )
        return f"{headline} {one_liner}"

    @staticmethod
    def _render(name, company, problem, evidence, solution_points, narrative, headline) -> str:
        lines = [f"# WIN Pitch — {name} for {company}", "", f"*{headline}*", ""]

        lines.append("## W — Well-researched problem")
        lines.append(problem or "_No specific problem identified yet — provide the real JD to strengthen this._")
        if evidence:
            lines.append("")
            lines.append("Evidence:")
            for e in evidence:
                lines.append(f"- {e}")

        lines.append("")
        lines.append("## I — Insightful solution (from actual work, not invented)")
        for p in solution_points:
            lines.append(f"- {p}")

        lines.append("")
        lines.append("## N — Narrative")
        lines.append(narrative)

        lines.append("")
        lines.append("---")
        lines.append("*Generated from config/profile.yml and config/target_companies.yml — "
                      "every claim here traces back to real resume evidence.*")
        return "\n".join(lines)


if __name__ == "__main__":
    ctx = AgentContext.load()
    result = PitcherAgent(ctx).run(
        company="Perfios",
        job_description="Scale our microservices and improve API reliability while maintaining "
                         "strict compliance and audit trails as we expand internationally.",
    )
    print(result.data["win_markdown"])
