"""
agent_25_executive_outreach.py — Agent 25: Autonomous Executive Outbound Pitch Engine.

Generates 3-stage high-conviction Trojan Horse drip campaigns targeting Engineering VPs and CTOs.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent, AgentResult, AgentContext
from src.services.executive_outreach_service import ExecutiveOutreachService

logger = logging.getLogger("nexus.agents.executive_outreach")


class ExecutiveOutreachAgent(BaseAgent):
    """Synthesizes executive Trojan Horse outbound campaigns."""

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(context=context)
        self.service = ExecutiveOutreachService()

    def run(
        self,
        candidate_name: str = "Ujjwal",
        target_company: str = "Databricks",
        executive_name: str = "David (VP of Engineering)",
        executive_title: str = "VP of Engineering",
        pain_point_id: Optional[str] = None,
        custom_proof_of_work_url: Optional[str] = None,
        **kwargs: Any,
    ) -> AgentResult:
        """Runs the executive outreach campaign synthesizer."""
        try:
            result = self.service.generate_campaign(
                candidate_name=candidate_name,
                target_company=target_company,
                executive_name=executive_name,
                executive_title=executive_title,
                pain_point_id=pain_point_id,
                custom_proof_of_work_url=custom_proof_of_work_url,
            )
            return AgentResult(
                agent="executive_outreach",
                ok=True,
                data=result,
                summary=f"Synthesized 3-Stage Executive Drip Campaign for {executive_name} at {target_company} (Pain Point: {result['pain_point']['title']}).",
            )
        except Exception as exc:
            logger.error(f"Executive outreach execution failed: {exc}")
            return AgentResult(
                agent="executive_outreach",
                ok=False,
                error=str(exc),
                data={},
            )
