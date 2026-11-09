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
        """Compose a neutral outreach draft without asserting unconfigured candidate details."""
        company = contact.get("company", "your startup")
        subject = f"Engineering roles at {company}"
        body_text, body_html = self.compose_interest_outreach(contact.get("name", ""), company)
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
