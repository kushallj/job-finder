"""
agent_18_anti_ghosting_sla.py — Agent 18: Anti-Ghosting SLA & Recruiter Escalation Engine.

Tracks post-interview communication timelines, detects SLA breaches, and generates
calibrated 3-tier escalation follow-up scripts to prevent candidate momentum loss.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent, AgentResult, AgentContext
from src.services.anti_ghosting_service import AntiGhostingService

logger = logging.getLogger("nexus.agents.anti_ghosting_sla")


class AntiGhostingAgent(BaseAgent):
    """Monitors SLA timelines and synthesizes high-leverage recruiter escalation scripts."""

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(context=context)
        self.service = AntiGhostingService()

    def run(
        self,
        company_name: str = "Pine Labs",
        interview_stage: str = "Technical Screen",
        days_elapsed: int = 4,
        recruiter_name: Optional[str] = "Recruiting Team",
        candidate_leverage: Optional[str] = "Has Competing Timelines",
        competing_company: Optional[str] = "Another Tier-1 Tech Firm",
        **kwargs: Any
    ) -> AgentResult:
        """Runs the SLA risk assessment and escalation draft synthesizer."""
        try:
            result = self.service.synthesize_escalations(
                company_name=company_name,
                interview_stage=interview_stage,
                days_elapsed=days_elapsed,
                recruiter_name=recruiter_name,
                candidate_leverage=candidate_leverage,
                competing_company=competing_company,
            )
            return AgentResult(
                agent="anti_ghosting_sla",
                ok=True,
                data=result,
                summary=f"Evaluated {company_name} SLA at {days_elapsed} days elapsed: {result['risk_metrics']['sla_status']} ({result['risk_metrics']['ghosting_risk_percent']}% risk).",
            )
        except Exception as exc:
            logger.error(f"Anti-ghosting evaluation failed: {exc}")
            return AgentResult(
                agent="anti_ghosting_sla",
                ok=False,
                error=str(exc),
                data={},
            )
