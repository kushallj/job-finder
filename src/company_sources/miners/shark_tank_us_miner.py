"""
shark_tank_us_miner.py — Autonomous Job Sourcing & Decision Maker Outreach Engine
for Shark Tank US Startups (Seasons 1-16).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()

from src.company_sources.miners.base_company_miner import (
    MAX_OUTREACH_PER_COMPANY,
    ROLE_PATTERNS,
    BaseCompanyMiner,
    get_role_priority,
)
from src.company_sources.registries.shark_tank_us_startups import SHARK_TANK_US_REGISTRY, SharkTankUSStartup

logger = logging.getLogger("shark_tank_us_miner")
logger.setLevel(logging.INFO)


class SharkTankUSMiner(BaseCompanyMiner):
    """Autonomous miner for Shark Tank US startups, leadership, and engineering openings."""

    def compose_shark_tank_us_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose neutral outreach without unconfigured candidate claims."""
        company = contact.get("company") or "your company"
        body_text, body_html = self.compose_interest_outreach(contact.get("name") or "", company)
        return f"Engineering roles at {company}", body_text, body_html

    async def mine_shark_tank_us_decision_makers(
        self, startup: SharkTankUSStartup, max_results: int = 6
    ) -> List[Dict[str, Any]]:
        """Search and extract founders, CTOs, and technical leaders for Shark Tank US startup."""
        clean_name = startup.name.split("(")[0].strip()
        domain = startup.domain or f"{clean_name.lower().replace(' ', '')}.com"

        contacts = await self.search_linkedin_decision_makers(
            company_name=clean_name,
            domain=domain,
            max_results=max_results,
        )
        for c in contacts:
            c.update({
                "company": startup.name,
                "domain": domain,
                "season": startup.season,
                "sharks": ", ".join(startup.sharks_invested),
            })
        return contacts

    async def mine_and_outreach_startup_us(
        self, startup: SharkTankUSStartup, auto_send: bool = False
    ) -> List[Dict[str, Any]]:
        """Mine decision makers for single Shark Tank US startup and dispatch outreach with strict <= 2 cap."""
        contacts = await self.mine_shark_tank_us_decision_makers(startup, max_results=6)
        if not contacts:
            return []

        return await self.save_and_outreach(
            contacts=contacts,
            company_name=startup.name,
            source_prefix=f"shark_tank_us_s{startup.season}",
            department=startup.category,
            auto_send=auto_send,
            composer=self.compose_shark_tank_us_outreach,
            template_type="shark_tank_us_outreach",
        )


shark_tank_us_miner = SharkTankUSMiner()
