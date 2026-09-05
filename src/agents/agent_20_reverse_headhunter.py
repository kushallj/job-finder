"""
agent_20_reverse_headhunter.py — Agent 20: Reverse Headhunter Bounty Network.

Monetizes warm candidate introductions and internal referrals ($1k–$5k USD / ₹1L–₹5L bounties),
with automated pitch packs, candidate dossiers, and escrow commission tracking.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent, AgentResult, AgentContext
from src.services.reverse_headhunter_service import ReverseHeadhunterService

logger = logging.getLogger("nexus.agents.reverse_headhunter")


class ReverseHeadhunterAgent(BaseAgent):
    """Generates high-conviction referral pitch packs and tracks bounty escrow milestones."""

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(context=context)
        self.service = ReverseHeadhunterService()

    def run(
        self,
        candidate_name: str = "Ujjwal",
        target_company: str = "Stripe",
        role_title: str = "Staff Distributed Systems Engineer",
        referrer_name: str = "Alex / Senior Peer Referrer",
        key_strengths: Optional[List[str]] = None,
        years_experience: int = 6,
        github_portfolio: Optional[str] = None,
        usd_to_inr_rate: float = 86.5,
        **kwargs: Any,
    ) -> AgentResult:
        """Runs pitch pack generation and escrow calculation."""
        try:
            result = self.service.generate_pitch_pack(
                candidate_name=candidate_name,
                target_company=target_company,
                role_title=role_title,
                referrer_name=referrer_name,
                key_strengths=key_strengths,
                years_experience=years_experience,
                github_portfolio=github_portfolio,
                usd_to_inr_rate=usd_to_inr_rate,
            )
            bounty_usd = result["bounty_financials"]["total_bounty_usd"]
            bounty_inr = result["bounty_financials"]["total_bounty_inr_lakhs"]
            return AgentResult(
                agent="reverse_headhunter",
                ok=True,
                data=result,
                summary=f"Generated Referral Pitch Pack for {candidate_name} ➔ {target_company} (Bounty: ${bounty_usd:,} USD / ₹{bounty_inr}L).",
            )
        except Exception as exc:
            logger.error(f"Reverse headhunter execution failed: {exc}")
            return AgentResult(
                agent="reverse_headhunter",
                ok=False,
                error=str(exc),
                data={},
            )
