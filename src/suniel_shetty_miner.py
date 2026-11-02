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

from src.services.base_company_miner import (
    MAX_OUTREACH_PER_COMPANY,
    ROLE_PATTERNS,
    BaseCompanyMiner,
    get_role_priority,
)
from src.suniel_shetty_startups import SUNIEL_SHETTY_STARTUPS_REGISTRY, SunielShettyStartup

logger = logging.getLogger("suniel_shetty_miner")
logger.setLevel(logging.INFO)


class SunielShettyMiner(BaseCompanyMiner):
    """Autonomous miner for Suniel Shetty show startups, leadership, and engineering openings."""

    def compose_shetty_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose high-converting cold email tailored specifically to Suniel Shetty show startups."""
        first_name = contact["name"].split()[0] if contact.get("name") else "there"
        company = contact.get("company", "your startup")
        source = contact.get("show_or_source", "Bharat Ke Super Founders")
        title = contact.get("title", "Founder")

        subject = f"Engineering & Product Scaling at {company} ({source}) — Kushall Jain"

        body_text = f"""Hi {first_name},

I've been closely following {company}'s journey since your showcase on {source} and the backing from leading Indian venture ecosystem mentors.

I'm a Software Engineer specializing in Python, FastAPI, React, and building resilient, high-speed digital architectures from 0-to-1. Early and growth-stage scaling requires versatile engineers who can take complete ownership of backend APIs, customer-facing workflows, and mission-critical reliability.

Given your leadership as {title}, I wanted to reach out directly to see if you're looking for an agile, high-ownership engineer to accelerate {company}'s product roadmap.

Key Highlights:
• Full-stack development with FastAPI, Python, React & Next.js
• High-concurrency APIs, event-driven data flows, and database optimization (PostgreSQL, Redis)
• Startup velocity: fast shipping speed, clean system design, and production ownership

My LinkedIn: {self.sender_linkedin or ''}

Would you be open to a brief 10-minute chat this week to explore if my skill set could add immediate leverage to {company}?

Best regards,
{self.sender_name}
Software Engineer
{self.sender_linkedin or ''}
"""

        body_html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; line-height: 1.6;">
  <p>Hi {first_name},</p>
  <p>I've been closely following <strong>{company}</strong>'s journey since your showcase on <strong>{source}</strong> and the backing from leading Indian venture ecosystem mentors.</p>
  <p>I'm a Software Engineer specializing in <strong>Python, FastAPI, React</strong>, and building resilient, high-speed digital architectures from 0-to-1. Early and growth-stage scaling requires versatile engineers who can take complete ownership of backend APIs, customer-facing workflows, and mission-critical reliability.</p>
  <p>Given your leadership as <em>{title}</em>, I wanted to reach out directly to see if you're looking for an agile, high-ownership engineer to accelerate {company}'s product roadmap.</p>
  <p><strong>Key Highlights:</strong></p>
  <ul>
    <li>Full-stack development with FastAPI, Python, React & Next.js</li>
    <li>High-concurrency APIs, event-driven data flows, and database optimization (PostgreSQL, Redis)</li>
    <li>Startup velocity: fast shipping speed, clean system design, and production ownership</li>
  </ul>
  <p>Would you be open to a brief 10-minute chat this week to explore if my skill set could add immediate leverage to {company}?</p>
  <p>Best regards,<br>
  <strong>{self.sender_name}</strong><br>
  <span style="color: #64748B;">Software Engineer</span><br>
  <a href="{self.sender_linkedin or '#'}" style="color: #4F46E5;">{self.sender_linkedin or ''}</a>
  </p>
</body>
</html>"""

        return subject, body_text, body_html

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
