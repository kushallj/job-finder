"""
shark_tank_miner.py — Autonomous Job Sourcing & Decision Maker Outreach Engine
for Shark Tank India Startups (Seasons 1-5).
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
from src.company_sources.registries.shark_tank_india_startups import SHARK_TANK_INDIA_REGISTRY, SharkTankStartup

logger = logging.getLogger("shark_tank_miner")
logger.setLevel(logging.INFO)


class SharkTankMiner(BaseCompanyMiner):
    """Autonomous miner for Shark Tank India startups, founders, and career openings."""

    def compose_shark_tank_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose high-converting cold email tailored specifically to Shark Tank India alumni."""
        first_name = contact["name"].split()[0] if contact.get("name") else "there"
        company = contact.get("company", "your startup")
        season = contact.get("season", 1)
        sharks = contact.get("sharks", "the Sharks")
        title = contact.get("title", "Founder")

        subject = f"Engineering & Platform Scaling at {company} (Shark Tank India S{season}) — Kushall Jain"

        body_text = f"""Hi {first_name},

I've been following {company}'s impressive growth trajectory since your pitch on Shark Tank India (Season {season}) and backing from {sharks}.

I'm a Software Engineer specializing in Python, FastAPI, React, and building scalable, high-throughput digital platforms and backends. Post-Shark Tank scaling brings immense traffic spikes, real-time inventory and payment demands, and a need for rapid feature deployment.

Given your leadership as {title}, I wanted to reach out directly to see if you're looking for an agile, high-ownership engineer to strengthen your backend architecture and build core customer-facing features.

Key Highlights:
• Full-stack development with FastAPI, Python, React & Next.js
• Low-latency APIs, resilient payment integrations, and async data processing (PostgreSQL, Redis)
• Product mindset: fast iteration, clean architecture, and 0-to-1 build speed

My LinkedIn: {self.sender_linkedin or ''}

Would you be open to a brief 10-minute chat this week to explore how I could contribute to {company}'s next phase of growth?

Best regards,
{self.sender_name}
Software Engineer
{self.sender_linkedin or ''}
"""

        body_html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; line-height: 1.6;">
  <p>Hi {first_name},</p>
  <p>I've been following <strong>{company}</strong>'s impressive growth trajectory since your pitch on <strong>Shark Tank India (Season {season})</strong> and backing from {sharks}.</p>
  <p>I'm a Software Engineer specializing in <strong>Python, FastAPI, React</strong>, and building scalable, high-throughput digital platforms and backends. Post-Shark Tank scaling brings immense traffic surges, real-time payment demands, and a need for rapid feature deployment.</p>
  <p>Given your leadership as <em>{title}</em>, I wanted to reach out directly to see if you're looking for an agile, high-ownership engineer to strengthen your backend architecture and build core customer-facing features.</p>
  <p><strong>Key Highlights:</strong></p>
  <ul>
    <li>Full-stack development with FastAPI, Python, React & Next.js</li>
    <li>Low-latency APIs, resilient payment integrations, and async data processing (PostgreSQL, Redis)</li>
    <li>Product mindset: fast iteration, clean architecture, and 0-to-1 build speed</li>
  </ul>
  <p>Would you be open to a brief 10-minute chat this week to explore how I could contribute to {company}'s next phase of growth?</p>
  <p>Best regards,<br>
  <strong>{self.sender_name}</strong><br>
  <span style="color: #64748B;">Software Engineer</span><br>
  <a href="{self.sender_linkedin or '#'}" style="color: #4F46E5;">{self.sender_linkedin or ''}</a>
  </p>
</body>
</html>"""

        return subject, body_text, body_html

    async def mine_shark_tank_decision_makers(
        self, startup: SharkTankStartup, max_results: int = 6
    ) -> List[Dict[str, Any]]:
        """Search and extract founders, CTOs, and technical leaders for Shark Tank startup."""
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
                "season": startup.season,
                "sharks": ", ".join(startup.sharks_invested),
            })
        return contacts

    async def mine_and_outreach_startup(
        self, startup: SharkTankStartup, auto_send: bool = False
    ) -> List[Dict[str, Any]]:
        """Mine decision makers for single Shark Tank startup and dispatch outreach with strict <= 2 cap."""
        contacts = await self.mine_shark_tank_decision_makers(startup, max_results=6)
        if not contacts:
            return []

        return await self.save_and_outreach(
            contacts=contacts,
            company_name=startup.name,
            source_prefix=f"shark_tank_s{startup.season}",
            department=startup.category,
            auto_send=auto_send,
            composer=self.compose_shark_tank_outreach,
            template_type="shark_tank_outreach",
        )


shark_tank_miner = SharkTankMiner()
