"""
sp500_miner.py — Autonomous Job Sourcing & Tech Leadership Outreach Engine
for S&P 500 Enterprise Giants (US Market Leaders).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()

from src.services.base_company_miner import (
    MAX_OUTREACH_PER_COMPANY,
    ROLE_PATTERNS,
    BaseCompanyMiner,
    get_role_priority,
)
from src.sp500_registry import SP500_REGISTRY, SP500Company

logger = logging.getLogger("sp500_miner")
logger.setLevel(logging.INFO)


class SP500Miner(BaseCompanyMiner):
    """Autonomous miner for S&P 500 corporations, tech leadership, and engineering openings."""

    def compose_sp500_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose high-converting cold email tailored specifically to S&P 500 global platform scale."""
        return self.compose_outreach_email(contact, context_label="S&P 500")

    async def mine_sp500_decision_makers(
        self, company: SP500Company, max_results: int = 6
    ) -> List[Dict[str, Any]]:
        """Search and extract CTOs, VPs of Engineering, and Tech Directors for S&P 500 company."""
        contacts = await self.search_linkedin_decision_makers(
            company_name=company.name,
            domain=company.domain,
            max_results=max_results,
        )
        for c in contacts:
            c.update({
                "domain": company.domain,
                "symbol": company.symbol,
                "sector": company.sector,
                "sub_industry": company.sub_industry,
            })
        return contacts

    async def mine_and_outreach_company(
        self, company: SP500Company, auto_send: bool = False
    ) -> List[Dict[str, Any]]:
        """Mine decision makers for single S&P 500 company and dispatch outreach with strict <= 2 cap."""
        contacts = await self.mine_sp500_decision_makers(company, max_results=6)
        if not contacts:
            return []

        return await self.save_and_outreach(
            contacts=contacts,
            company_name=company.name,
            source_prefix=f"sp500_{company.symbol.lower()}",
            department=company.sector,
            auto_send=auto_send,
            composer=self.compose_sp500_outreach,
            template_type="sp500_enterprise_outreach",
        )


sp500_miner = SP500Miner()
