"""
suniel_shetty_miner.py — Autonomous Job Sourcing & Decision Maker Outreach Engine
for Startups featured on Suniel Shetty's Shows ("Bharat Ke Super Founders", "Horses Stable")
and his High-Growth Portfolio.
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
from src.company_sources.registries.suniel_shetty_startups import SUNIEL_SHETTY_STARTUPS_REGISTRY, SunielShettyStartup

logger = logging.getLogger("suniel_shetty_miner")
logger.setLevel(logging.INFO)


class SunielShettyMiner(BaseCompanyMiner):
    """Autonomous miner for Suniel Shetty show startups, leadership, and engineering openings."""

    def compose_shetty_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose neutral outreach without unconfigured candidate claims."""
        company = contact.get("company") or "your company"
        body_text, body_html = self.compose_interest_outreach(contact.get("name") or "", company)
        return f"Engineering roles at {company}", body_text, body_html

    async def mine_shetty_decision_makers(
        self, startup: SunielShettyStartup, max_results: int = 6
    ) -> List[Dict[str, Any]]:
        """Search and extract founders, CTOs, and technical leaders for Suniel Shetty startup."""
        clean_name = startup.name.split("(")[0].strip()
        domain = startup.domain or f"{clean_name.lower().replace(' ', '')}.in"

        contacts = await self.search_linkedin_decision_makers(
            company_name=clean_name,
            domain=domain,
            max_results=max_results,
        )
        for c in contacts:
            c.update({
                "company": startup.name,
                "domain": domain,
                "show_or_source": startup.show_or_source,
                "category": startup.category,
            })
        return contacts

    async def mine_and_outreach_startup(
        self, startup: SunielShettyStartup, auto_send: bool = False
    ) -> List[Dict[str, Any]]:
        """Mine decision makers for single Suniel Shetty startup and dispatch outreach with strict <= 2 cap."""
        contacts = await self.mine_shetty_decision_makers(startup, max_results=6)
        if not contacts:
            return []

        clean_source = startup.show_or_source.lower().replace(" ", "_")
        return await self.save_and_outreach(
            contacts=contacts,
            company_name=startup.name,
            source_prefix=f"shetty_{clean_source}",
            department=startup.category,
            auto_send=auto_send,
            composer=self.compose_shetty_outreach,
            template_type="shetty_startup_outreach",
        )


suniel_shetty_miner = SunielShettyMiner()
