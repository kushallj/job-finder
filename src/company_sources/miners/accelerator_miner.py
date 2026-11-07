"""
accelerator_miner.py — Autonomous Job Sourcing & Decision Maker Outreach Engine
for Y Combinator, Surge by Peak XV, Accel Atoms, Antler, and Techstars Startups.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

import httpx
from dotenv import load_dotenv

load_dotenv()

from src.company_sources.registries.accelerators_registry import ACCELERATORS_REGISTRY, AcceleratorStartup
from src.database import SessionLocal
from src.models import Job
from src.company_sources.miners.base_company_miner import (
    MAX_OUTREACH_PER_COMPANY,
    ROLE_PATTERNS,
    BaseCompanyMiner,
    get_role_priority,
)

logger = logging.getLogger("accelerator_miner")
logger.setLevel(logging.INFO)


class AcceleratorMiner(BaseCompanyMiner):
    """
    Autonomous engine for sourcing jobs and decision makers across top global accelerators.
    """

    def __init__(self):
        super().__init__()
        self.total_jobs_sourced = 0
        self.total_leaders_mined = 0
        self.total_emails_dispatched = 0

    async def scrape_startup_jobs(self, startup: AcceleratorStartup, max_jobs: int = 15) -> List[Dict[str, Any]]:
        """Scrape live open engineering positions from company ATS portal."""
        jobs: List[Dict[str, Any]] = []
        if not startup.ats_slug:
            return []

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                if startup.ats_platform == "greenhouse":
                    url = f"https://boards-api.greenhouse.io/v1/boards/{startup.ats_slug}/jobs"
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("jobs", [])[:max_jobs]:
                            jobs.append({
                                "title": item.get("title", ""),
                                "company": startup.name,
                                "location": item.get("location", {}).get("name", "Remote / Global"),
                                "url": item.get("absolute_url", startup.careers_url or ""),
                                "source": f"accelerator_{startup.accelerator.lower().replace(' ', '_')}",
                                "tags": ["Startup", startup.accelerator, startup.stage, "Engineering"],
                            })

                elif startup.ats_platform == "lever":
                    url = f"https://api.lever.co/v0/postings/{startup.ats_slug}?mode=json"
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data[:max_jobs]:
                            jobs.append({
                                "title": item.get("text", ""),
                                "company": startup.name,
                                "location": item.get("categories", {}).get("location", "Remote / India"),
                                "url": item.get("hostedUrl", startup.careers_url or ""),
                                "source": f"accelerator_{startup.accelerator.lower().replace(' ', '_')}",
                                "tags": ["Startup", startup.accelerator, startup.stage, "Engineering"],
                            })

            # Upsert into DB
            if jobs:
                with SessionLocal() as db:
                    for j in jobs:
                        job_id = f"acc_{startup.id}_{hash(j['title']) % 1000000}"
                        existing = db.query(Job).filter(Job.job_id == job_id).first()
                        if not existing:
                            new_job = Job(
                                job_id=job_id,
                                title=j["title"],
                                company=j["company"],
                                location=j["location"],
                                url=j["url"],
                                source=j["source"],
                                tags=json.dumps(j["tags"]),
                                description=f"Live opening at {startup.name} ({startup.accelerator} - {startup.batch}). Stage: {startup.stage}.",
                                fetched_at=datetime.utcnow(),
                            )
                            db.add(new_job)
                            self.total_jobs_sourced += 1
                    db.commit()

        except Exception as exc:
            logger.warning(f"Error sourcing jobs for {startup.name}: {exc}")

        return jobs

    async def mine_startup_decision_makers(
        self, startup: AcceleratorStartup, max_results: int = 6
    ) -> List[Dict[str, Any]]:
        """Search and extract founders, CTOs, and technical leaders for startup."""
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
                "accelerator": startup.accelerator,
                "batch": startup.batch,
            })
        return contacts

    def compose_accelerator_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose high-converting cold email tailored specifically to accelerator & startup culture."""
        first_name = contact["name"].split()[0] if contact.get("name") else "there"
        company = contact.get("company", "your startup")
        accelerator = contact.get("accelerator", "top accelerator")
        batch = contact.get("batch", "")
        title = contact.get("title", "Founder")

        subject = f"Building & Scaling Engineering at {company} ({accelerator}) — Kushall Jain"

        body_text = f"""Hi {first_name},

I've been closely following {company}'s rapid scaling trajectory since your {accelerator} ({batch}) journey.

I'm a Software Engineer specializing in Python, FastAPI, React, and building robust, high-performance distributed backends from 0-to-1 and 1-to-10. I thrive in fast-paced startup environments where engineering speed, clean system design, and high autonomy matter.

Given your leadership as {title}, I wanted to reach out directly to see if you're looking for a versatile engineer who can take full ownership of core product features and scale your backend architecture.

Key Highlights:
• End-to-end full-stack development with FastAPI, Python, React & Next.js
• Built low-latency APIs and event-driven data pipelines (PostgreSQL, Redis, Kafka)
• Startup mindset: high velocity, rapid prototyping, and production-grade reliability

My LinkedIn: {self.sender_linkedin or ''}

Would you be open to a brief 10-minute chat this week to see if my skill set could add immediate leverage to {company}?

Best regards,
{self.sender_name}
Software Engineer
{self.sender_linkedin or ''}
"""

        body_html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; line-height: 1.6;">
  <p>Hi {first_name},</p>
  <p>I've been closely following <strong>{company}</strong>'s rapid scaling trajectory since your <strong>{accelerator}</strong> ({batch}) journey.</p>
  <p>I'm a Software Engineer specializing in <strong>Python, FastAPI, React</strong>, and building robust, high-performance distributed backends from 0-to-1 and 1-to-10. I thrive in fast-paced startup environments where engineering speed, clean system design, and high autonomy matter.</p>
  <p>Given your leadership as <em>{title}</em>, I wanted to reach out directly to see if you're looking for a versatile engineer who can take full ownership of core product features and scale your backend architecture.</p>
  <p><strong>Key Highlights:</strong></p>
  <ul>
    <li>End-to-end full-stack development with FastAPI, Python, React & Next.js</li>
    <li>Built low-latency APIs and event-driven data pipelines (PostgreSQL, Redis, Kafka)</li>
    <li>Startup mindset: high velocity, rapid prototyping, and production-grade reliability</li>
  </ul>
  <p>Would you be open to a brief 10-minute chat this week to see if my skill set could add immediate leverage to {company}?</p>
  <p>Best regards,<br>
  <strong>{self.sender_name}</strong><br>
  <span style="color: #64748B;">Software Engineer</span><br>
  <a href="{self.sender_linkedin or '#'}" style="color: #4F46E5;">{self.sender_linkedin or ''}</a>
  </p>
</body>
</html>"""

        return subject, body_text, body_html

    async def mine_and_outreach_startup(
        self, startup: AcceleratorStartup, auto_send: bool = False
    ) -> List[Dict[str, Any]]:
        """Mine decision makers for single accelerator startup and dispatch outreach with strict <= 2 cap."""
        contacts = await self.mine_startup_decision_makers(startup, max_results=6)
        if not contacts:
            return []

        res = await self.save_and_outreach(
            contacts=contacts,
            company_name=startup.name,
            source_prefix=f"accelerator_{startup.accelerator.lower().replace(' ', '_')}",
            department=startup.category,
            auto_send=auto_send,
            composer=self.compose_accelerator_outreach,
            template_type="accelerator_founder_outreach",
        )
        self.total_leaders_mined += self.total_mined
        self.total_emails_dispatched += self.total_emailed
        return res


accelerator_miner = AcceleratorMiner()
