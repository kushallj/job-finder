"""
shark_tank_us_miner.py — Autonomous Job Sourcing & Decision Maker Outreach Engine
for Shark Tank US Startups (Seasons 1-16).
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
from src.shark_tank_us_startups import SHARK_TANK_US_REGISTRY, SharkTankUSStartup

logger = logging.getLogger("shark_tank_us_miner")
logger.setLevel(logging.INFO)


class SharkTankUSMiner(BaseCompanyMiner):
    """Autonomous miner for Shark Tank US startups, leadership, and engineering openings."""

    def compose_shark_tank_us_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose high-converting cold email tailored specifically to Shark Tank US portfolio founders."""
        first_name = contact["name"].split()[0] if contact.get("name") else "there"
        company = contact.get("company", "your startup")
        season = contact.get("season", 1)
        sharks = contact.get("sharks", "the Sharks")
        title = contact.get("title", "Founder")

        subject = f"Engineering & Digital Platform Scaling at {company} (Shark Tank Season {season}) — Kushall Jain"

        body_text = f"""Hi {first_name},

I've been following {company}'s growth since your presentation on Shark Tank Season {season} and partnership with {sharks}.

I'm a Software Engineer specializing in Python, FastAPI, React, and building scalable, fault-tolerant distributed web and mobile platforms. Rapid growth following national recognition creates massive engineering demands—from server reliability to fast iterations on consumer-facing features.

Given your leadership as {title}, I wanted to reach out directly to see if {company} is looking for a driven, full-stack software engineer who can build and ship critical features with speed and autonomy.

Key Technical Highlights:
• Full-stack architecture with FastAPI, Python, React & Next.js
• Distributed caching, messaging pipelines, and database optimization (PostgreSQL, Redis, Kafka)
• Cloud infrastructure, microservices design, and automated CI/CD pipelines

My LinkedIn: {self.sender_linkedin or ''}

Would you be open to a brief 10-minute chat this week to explore how my technical background aligns with {company}'s engineering roadmaps?

Best regards,
{self.sender_name}
Software Engineer
{self.sender_linkedin or ''}
"""

        body_html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; line-height: 1.6;">
  <p>Hi {first_name},</p>
  <p>I've been following <strong>{company}</strong>'s growth since your presentation on <strong>Shark Tank Season {season}</strong> and partnership with {sharks}.</p>
  <p>I'm a Software Engineer specializing in <strong>Python, FastAPI, React</strong>, and building scalable, fault-tolerant distributed web and mobile platforms. Rapid growth following national recognition creates massive engineering demands—from server reliability to fast iterations on consumer-facing features.</p>
  <p>Given your leadership as <em>{title}</em>, I wanted to reach out directly to see if {company} is looking for a driven, full-stack software engineer who can build and ship critical features with speed and autonomy.</p>
  <p><strong>Key Technical Highlights:</strong></p>
  <ul>
    <li>Full-stack architecture with FastAPI, Python, React & Next.js</li>
    <li>Distributed caching, messaging pipelines, and database optimization (PostgreSQL, Redis, Kafka)</li>
    <li>Cloud infrastructure, microservices design, and automated CI/CD pipelines</li>
  </ul>
  <p>Would you be open to a brief 10-minute chat this week to explore how my technical background aligns with {company}'s engineering roadmaps?</p>
  <p>Best regards,<br>
  <strong>{self.sender_name}</strong><br>
  <span style="color: #64748B;">Software Engineer</span><br>
  <a href="{self.sender_linkedin or '#'}" style="color: #4F46E5;">{self.sender_linkedin or ''}</a>
  </p>
</body>
</html>"""

        return subject, body_text, body_html

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
