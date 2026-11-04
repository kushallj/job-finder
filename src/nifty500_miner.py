"""
nifty500_miner.py — Autonomous Job Sourcing & Tech Leadership Outreach Engine
for Nifty 500 Enterprise Companies (NSE India).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()

from src.nifty500_registry import NIFTY_500_REGISTRY, Nifty500Company
from src.services.base_company_miner import (
    MAX_OUTREACH_PER_COMPANY,
    ROLE_PATTERNS,
    BaseCompanyMiner,
    get_role_priority,
)

logger = logging.getLogger("nifty500_miner")
logger.setLevel(logging.INFO)


class Nifty500Miner(BaseCompanyMiner):
    """Autonomous miner for Nifty 500 enterprises, tech leaders, and engineering opportunities."""

    def compose_nifty500_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose high-converting cold email tailored specifically to Nifty 500 Indian enterprise scale."""
        return self.compose_outreach_email(contact, context_label="Nifty 500")

    async def mine_nifty500_decision_makers(
        self, company: Nifty500Company, max_results: int = 6
    ) -> List[Dict[str, Any]]:
        """Search and extract CTOs, VPs of Engineering, and Tech Directors for Nifty 500 company."""
        contacts = await self.search_linkedin_decision_makers(
            company_name=company.name,
            domain=company.domain,
            max_results=max_results,
        )
        for c in contacts:
            c.update({
                "domain": company.domain,
                "symbol": company.symbol,
                "industry": company.industry,
                "series": company.series,
            })
        return contacts

    async def mine_and_outreach_company(
        self, company: Nifty500Company, auto_send: bool = False
    ) -> List[Dict[str, Any]]:
        """Mine decision makers for single Nifty 500 company and dispatch outreach with strict <= 2 cap."""
        contacts = await self.mine_nifty500_decision_makers(company, max_results=6)
        if not contacts:
            return []

        return await self.save_and_outreach(
            contacts=contacts,
            company_name=company.name,
            source_prefix=f"nifty500_{company.symbol.lower()}",
            department=company.industry,
            auto_send=auto_send,
            composer=self.compose_nifty500_outreach,
            template_type="nifty500_enterprise_outreach",
        )


nifty500_miner = Nifty500Miner()
