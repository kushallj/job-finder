"""
agent_22_web3_bounty_harvester.py — Agent 22: Web3 & Open-Source Bounty Harvester.

Scans open-source hackathons, Gitcoin bounties, and Web3 ecosystem grants ($500–$25,000 USD),
synthesizing formal PR RFC proposals and tracking crypto-to-fiat escrow payouts.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent, AgentResult, AgentContext
from src.services.web3_bounty_harvester import Web3BountyHarvesterService

logger = logging.getLogger("nexus.agents.web3_bounty_harvester")


class Web3BountyHarvesterAgent(BaseAgent):
    """Matches developer capabilities to high-reward Web3/OSS bounties and synthesizes RFC proposals."""

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(context=context)
        self.service = Web3BountyHarvesterService()

    def run(
        self,
        bounty_id: str = "bounty_solana_blinks_01",
        candidate_name: str = "Ujjwal",
        proposed_architecture: Optional[str] = None,
        timeline_days: int = 10,
        github_profile: Optional[str] = None,
        usd_to_inr_rate: float = 86.5,
        **kwargs: Any,
    ) -> AgentResult:
        """Runs proposal generation and reward estimation."""
        try:
            result = self.service.synthesize_proposal(
                bounty_id=bounty_id,
                candidate_name=candidate_name,
                proposed_architecture=proposed_architecture,
                timeline_days=timeline_days,
                github_profile=github_profile,
                usd_to_inr_rate=usd_to_inr_rate,
            )
            reward_usd = result["reward_usd"]
            reward_inr = result["reward_inr_lakhs"]
            org = result["organization"]
            return AgentResult(
                agent="web3_bounty_harvester",
                ok=True,
                data=result,
                summary=f"Synthesized Bounty RFC Proposal for {result['bounty_title']} ({org}) ➔ Reward: ${reward_usd:,} USD (~₹{reward_inr}L INR).",
            )
        except Exception as exc:
            logger.error(f"Web3 bounty harvester execution failed: {exc}")
            return AgentResult(
                agent="web3_bounty_harvester",
                ok=False,
                error=str(exc),
                data={},
            )
