"""
agent_14_interviewer.py — Interviewer Agent (mock interview + STAR feedback).

STRATEGY
--------
This is the direct answer to NxtJob's "Interviewer" agent — structured mock
interviews with STAR-based feedback. Designed stateless-session (frontend
holds the running Q&A array, backend scores one answer at a time) so it
works cleanly behind a plain HTTP API with no server-side session storage.

Two operations:
  1. generate_questions(company, role_title, n) — pulls from
     agent_08_interview_prepper.py's industry-focus heuristics and
     agent_10_challenge_solver.py's identified challenge (if a JD was
     supplied) to build a tailored question set: a mix of behavioral
     ("tell me about a time...") and technical/system-design questions
     that map to what THIS company/industry actually probes for.

  2. score_answer(question, answer, focus_area) — deterministic STAR
     structure check (does the answer contain a Situation, Task, Action,
     Result shape?) plus a specificity heuristic (numbers/proper nouns
     present?). Optionally polished via UnifiedAIService for qualitative
     feedback — falls back to the deterministic rubric if unavailable.

DAG node contract:
    Input:  AgentContext, company: str, role_title: str = "", job_description: str = "",
            num_questions: int = 5
    Output: AgentResult.data = {"questions": [{"id", "text", "type", "focus_area"}]}

    Input:  AgentContext, question: str, answer: str, focus_area: str = ""
    Output: AgentResult.data = {"star_scores": {...}, "feedback": str, "overall": float}
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from .base import AgentContext, AgentResult, BaseAgent
from .agent_08_interview_prepper import _FOCUS_HEURISTICS
from .agent_10_challenge_solver import ChallengeSolverAgent

try:
    from src.ai.unified_ai_service import UnifiedAIService
    _AI_AVAILABLE = True
except Exception:  # noqa: BLE001
    _AI_AVAILABLE = False

_BEHAVIORAL_BANK = [
    "Tell me about a time you found a problem nobody else had noticed and fixed it.",
    "Describe a time you had to make a tradeoff between shipping fast and doing it right.",
    "Tell me about a disagreement with a teammate or manager on a technical decision — how did it resolve?",
    "Describe the most difficult bug you've debugged and how you tracked it down.",
    "Tell me about a time you had to learn something unfamiliar quickly to unblock a project.",
]

_TECHNICAL_BANK_BY_FOCUS = {
    "API security & compliance (BFSI-grade)": "Walk me through how you'd design role-based access control for a multi-tenant fintech platform.",
    "system design for multi-tenant SaaS": "How would you design a system to safely isolate customer data across tenants sharing infrastructure?",
    "data integrity in financial transactions": "How would you ensure exactly-once processing for a payment/transaction pipeline?",
    "credit-scoring/rules-engine design": "How would you design a rules engine that product managers can update without a code deploy?",
    "auth & RBAC": "Walk me through your approach to closing an unauthenticated endpoint you discover in production.",
    "IoT/device-command architecture": "How would you design a reliable command pipeline from cloud to a flaky field device?",
    "event-driven pipeline design (Docker/Lambda/MQTT)": "How would you debug a message that silently disappeared somewhere in an event-driven pipeline?",
    "distributed systems debugging": "Describe your process for debugging an intermittent failure that only happens in production.",
    "hardware-in-the-loop reliability": "How would you design monitoring for a system where the failure mode is physical hardware, not just software?",
}

_STAR_MARKERS = {
    "situation": [r"\bwhen\b", r"\bat (my|the|\w+)\b", r"\bwe (were|had)\b", r"\bsituation\b", r"\bcontext\b"],
    "task": [r"\bneeded to\b", r"\bhad to\b", r"\bmy (job|task|goal)\b", r"\bresponsib", r"\bbefore\b"],
    "action": [r"\bi (did|built|wrote|designed|implemented|debugged|led|fixed|refactored|profiled|added|rewrote|created|analyzed|migrated|optimi[sz]ed)\b"],
    "result": [r"\d", r"\bresult(ed)?\b", r"\bimprove", r"\breduc", r"\bincreas", r"\bcut\b"],
}


class InterviewerAgent(BaseAgent):
    name = "interviewer"

    def generate_questions(self, company: str, role_title: str = "",
                            job_description: str = "", num_questions: int = 5) -> AgentResult:
        return self._timed(self._generate, company, role_title, job_description, num_questions)

    def score_answer(self, question: str, answer: str, focus_area: str = "") -> AgentResult:
        return self._timed(self._score, question, answer, focus_area)

    # -- question generation ------------------------------------------------

    def _generate(self, company: str, role_title: str, job_description: str, num_questions: int) -> AgentResult:
        company_cfg = self.context.company(company) or {}
        industry = company_cfg.get("industry", "")
        focus_areas = _FOCUS_HEURISTICS.get(industry, ["general backend/system design fundamentals"])

        # Pull in the real challenge if we have JD text — makes one question
        # directly about the company's actual stated problem.
        challenge_q = None
        if job_description:
            challenge_result = ChallengeSolverAgent(self.context).run(
                company=company, job_description=job_description
            )
            challenge = challenge_result.data.get("identified_challenge", "")
            if challenge:
                challenge_q = f"{company} has publicly stated they're dealing with: \"{challenge}\". How would you approach that?"

        questions: List[Dict[str, str]] = []
        if challenge_q:
            questions.append({"id": "q0", "text": challenge_q, "type": "company_specific", "focus_area": industry})

        for i, focus in enumerate(focus_areas):
            tq = _TECHNICAL_BANK_BY_FOCUS.get(focus)
            if tq:
                questions.append({"id": f"tech{i}", "text": tq, "type": "technical", "focus_area": focus})

        behavioral_needed = max(0, num_questions - len(questions))
        for i, bq in enumerate(_BEHAVIORAL_BANK[:behavioral_needed]):
            questions.append({"id": f"beh{i}", "text": bq, "type": "behavioral", "focus_area": "behavioral"})

        questions = questions[:num_questions]

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Generated {len(questions)} questions for {company} "
                    f"({'company-specific' if challenge_q else 'industry-generic'} + behavioral).",
            data={"questions": questions},
        )

    # -- STAR scoring ---------------------------------------------------------

    def _score(self, question: str, answer: str, focus_area: str) -> AgentResult:
        star_scores = self._deterministic_star_check(answer)
        specificity = self._specificity_score(answer)
        overall = round((sum(star_scores.values()) / 4 * 70) + (specificity * 30), 1)

        feedback = self._build_deterministic_feedback(star_scores, specificity, answer)
        used_llm = False

        if _AI_AVAILABLE and answer.strip():
            polished = self._try_llm_feedback(question, answer, star_scores, specificity)
            if polished:
                feedback = polished
                used_llm = True

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Scored answer: {overall}/100 ({'LLM-polished' if used_llm else 'deterministic'} feedback).",
            data={
                "star_scores": star_scores,
                "specificity_score": round(specificity * 100, 1),
                "overall": overall,
                "feedback": feedback,
                "used_llm": used_llm,
            },
        )

    @staticmethod
    def _deterministic_star_check(answer: str) -> Dict[str, float]:
        answer_l = answer.lower()
        scores = {}
        for part, patterns in _STAR_MARKERS.items():
            hit = any(re.search(p, answer_l) for p in patterns)
            scores[part] = 1.0 if hit else 0.0
        return scores

    @staticmethod
    def _specificity_score(answer: str) -> float:
        has_number = bool(re.search(r"\d", answer))
        word_count = len(answer.split())
        length_ok = 40 <= word_count <= 300
        return (0.6 if has_number else 0.0) + (0.4 if length_ok else 0.0)

    @staticmethod
    def _build_deterministic_feedback(star_scores: Dict[str, float], specificity: float, answer: str) -> str:
        missing = [part for part, hit in star_scores.items() if hit == 0.0]
        lines = []
        if not answer.strip():
            return "No answer given yet."
        if missing:
            lines.append(f"Missing or unclear: {', '.join(missing).title()}. "
                          f"A strong STAR answer states each part explicitly.")
        else:
            lines.append("Hits all four STAR components (Situation, Task, Action, Result).")
        if specificity < 0.6:
            lines.append("Add a concrete number or metric — vague outcomes are less convincing than measured ones.")
        word_count = len(answer.split())
        if word_count < 40:
            lines.append("Answer is quite short — interviewers usually want more concrete detail.")
        elif word_count > 300:
            lines.append("Answer is long — tighten it to the most relevant 90 seconds of story.")
        return " ".join(lines)

    def _try_llm_feedback(self, question: str, answer: str, star_scores: Dict[str, float],
                           specificity: float) -> Optional[str]:
        try:
            prompt = (
                "You are a strict but constructive interview coach. Give 2-3 sentences of feedback "
                "on this answer using the STAR framework (Situation, Task, Action, Result). "
                "Do not invent facts about the candidate not present in the answer.\n\n"
                f"QUESTION: {question}\n\nANSWER: {answer}\n\n"
                f"Deterministic STAR check found: {star_scores}. Specificity score: {specificity}."
            )
            service = UnifiedAIService()
            try:
                text = asyncio.run(service.generate_text(prompt, max_tokens=200))
            except RuntimeError:
                loop = asyncio.get_event_loop()
                text = loop.run_until_complete(service.generate_text(prompt, max_tokens=200))
            return text.strip() if text else None
        except Exception:  # noqa: BLE001
            self.log.debug("LLM feedback unavailable, using deterministic feedback", exc_info=True)
            return None


if __name__ == "__main__":
    ctx = AgentContext.load()
    agent = InterviewerAgent(ctx)
    q_result = agent.generate_questions(company="Perfios", num_questions=4)
    print(q_result.to_json())
    demo_answer = (
        "At Progfin we had a query that was taking 800ms and slowing down the whole dashboard. "
        "I needed to fix it before the next release. I profiled the query, added the right indexes, "
        "and rewrote a join. As a result response time dropped to 200ms, a 75% improvement."
    )
    s_result = agent.score_answer(q_result.data["questions"][0]["text"], demo_answer)
    print(s_result.to_json())
