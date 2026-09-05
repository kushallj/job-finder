"""
agent_23_executive_decision_memo.py — Agent 23: Executive Decision Memo Closer.

Reverse-engineers hiring team economics and synthesizes 1-click executive debrief memos
for hiring managers to justify top-of-band offers to engineering leadership.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent, AgentResult, AgentContext
from src.services.executive_decision_memo import ExecutiveDecisionMemoService

logger = logging.getLogger("nexus.agents.executive_decision_memo")


class ExecutiveDecisionMemoAgent(BaseAgent):
    """Synthesizes executive debrief memos to de-risk hiring managers and secure top-of-band comp."""

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(context=context)
        self.service = ExecutiveDecisionMemoService()

    def run(
        self,
        candidate_name: str = "Candidate",
        company_name: str = "Pine Labs",
        role_title: str = "Senior Software Engineer",
        interview_stage: str = "Final Architecture Debrief",
        key_technical_topics: Optional[List[str]] = None,
        p99_impact_metric: Optional[str] = None,
        competing_offer_anchor: Optional[str] = None,
        target_compensation_lpa: Optional[float] = 38.0,
        **kwargs: Any
    ) -> AgentResult:
        """Runs the executive decision memo synthesizer."""
        try:
            result = self.service.synthesize_memo(
                candidate_name=candidate_name,
                company_name=company_name,
                role_title=role_title,
                interview_stage=interview_stage,
                key_technical_topics=key_technical_topics,
                p99_impact_metric=p99_impact_metric,
                competing_offer_anchor=competing_offer_anchor,
                target_compensation_lpa=target_compensation_lpa,
            )
            return AgentResult(
                agent="executive_decision_memo",
                ok=True,
                data=result,
                summary=f"Synthesized Executive Decision Memo for {company_name} (Target Comp: ₹{target_compensation_lpa} LPA, Sunk Hiring Cost Saved: ₹{result['cost_analysis']['total_hiring_investment_inr_lakhs']}L).",
            )
        except Exception as exc:
            logger.error(f"Executive decision memo synthesis failed: {exc}")
            return AgentResult(
                agent="executive_decision_memo",
                ok=False,
                error=str(exc),
                data={},
            )
