"""
startups_gallery_miner.py — Autonomous Founder Discovery & Decision Maker Mining Engine
for 1,369 High-Growth Startups featured on startups.gallery.

Features:
1. Executive & Founder Extraction (Founders, Co-Founders, CEO, CTO, Founding Engineers).
2. Deep Multi-Network Profile Discovery:
   - LinkedIn Profile URL
   - X (Twitter) Profile URL
   - Synthesized / Verified Corporate Email ID
3. Database State Synchronization & Repeatable Batch Mining:
   - Tracks mined status per startup so re-running seamlessly processes the next 100 companies.
4. Export helpers for CSV and JSON generation.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from src.database import SessionLocal
from src.models import Contact, OutreachRecord, StartupsGalleryCompanyRecord
from src.services.base_company_miner import (
    MAX_OUTREACH_PER_COMPANY,
    ROLE_PATTERNS,
    BaseCompanyMiner,
    get_role_priority,
)
from src.startups_gallery_registry import (
    STARTUPS_GALLERY_REGISTRY,
    StartupsGalleryCompany,
    get_all_startups_gallery_companies,
    get_company_by_slug,
)

logger = logging.getLogger("startups_gallery_miner")
logger.setLevel(logging.INFO)

TWITTER_REGEX = re.compile(
    r"https?://(?:www\.)?(?:twitter\.com|x\.com)/([A-Za-z0-9_]{1,25})/?(?:\?[^\s\"'>]*)?",
    re.I,
)


class StartupsGalleryMiner(BaseCompanyMiner):
    """
    Autonomous engine for mining Founders, Co-Founders, and CTOs from startups.gallery
    with persistent state tracking across sequential batch runs.
    """

    def __init__(self):
        super().__init__()
        self._ensure_database_seeded()

    def _ensure_database_seeded(self):
        """Seed all 1,369 startups.gallery companies into the tracking table if empty."""
        try:
            with SessionLocal() as db:
                count = db.query(StartupsGalleryCompanyRecord).count()
                if count < len(STARTUPS_GALLERY_REGISTRY):
                    existing_slugs = {
                        r[0] for r in db.query(StartupsGalleryCompanyRecord.slug).all()
                    }
                    new_records = [
                        StartupsGalleryCompanyRecord(
                            slug=c.slug,
                            name=c.name,
                            domain=c.domain,
                            category=c.category,
                            funding=c.funding,
                            location=c.location,
                            founded_year=c.founded_year,
                            description=c.description,
                            mined=False,
                            founders_count=0,
                        )
                        for c in STARTUPS_GALLERY_REGISTRY
                        if c.slug not in existing_slugs
                    ]
                    if new_records:
                        db.add_all(new_records)
                        db.commit()
                        logger.info("Seeded %d startups.gallery companies into database", len(new_records))
        except Exception as exc:
            logger.warning("Could not auto-seed startups_gallery_companies: %s", exc)

    async def search_twitter_handle(self, person_name: str, company_name: str) -> Optional[str]:
        """Search Google via SerpApi for a person's X / Twitter profile."""
        if not self.serpapi_key or not person_name:
            return None

        clean_name = re.sub(r"[^a-zA-Z\s]", "", person_name).strip()
        query = f'"{clean_name}" "{company_name}" (site:x.com OR site:twitter.com)'
        url = (
            f"https://serpapi.com/search.json?engine=google&q={urllib.parse.quote(query)}"
            f"&api_key={self.serpapi_key}&num=3"
        )

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JobFinder/2.0"})
            loop = asyncio.get_event_loop()
            resp_bytes = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=10).read())
            data = json.loads(resp_bytes.decode())
            results = data.get("organic_results", [])
            for r in results:
                link = r.get("link", "")
                m = TWITTER_REGEX.search(link)
                if m:
                    handle = m.group(1).lower()
                    if handle not in ["search", "explore", "home", "intent", "i", "settings"]:
                        return f"https://x.com/{m.group(1)}"
        except Exception:
            pass
        return None

    async def mine_startup_founders(
        self,
        company: StartupsGalleryCompany,
        max_results: int = 4,
        extract_twitter: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Extract Founders, Co-Founders, and technical executives for a given startup.
        Extracts: Name, Title, LinkedIn URL, X (Twitter) URL, and Corporate Email.
        """
        clean_name = company.name.split("(")[0].strip()
        domain = company.domain or f"{company.slug.replace('-', '')}.com"

        contacts = await self.search_linkedin_decision_makers(
            company_name=clean_name,
            domain=domain,
            max_results=max_results,
        )

        for c in contacts:
            c.update({
                "company": company.name,
                "domain": domain,
                "category": company.category,
                "funding": company.funding,
                "location": company.location,
                "founded_year": company.founded_year,
                "twitter_url": None,
            })

            # Fetch X / Twitter profile if requested
            if extract_twitter:
                c["twitter_url"] = await self.search_twitter_handle(c["name"], clean_name)

        return contacts

    def compose_startups_gallery_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose tailored cold email referencing company's recent funding and trajectory."""
        first_name = contact["name"].split()[0] if contact.get("name") else "there"
        company = contact.get("company", "your startup")
        funding = contact.get("funding", "recent venture backing")
        category = contact.get("category", "high-growth tech")
        title = contact.get("title", "Founder")

        subject = f"Engineering & Product Velocity at {company} — Kushall Jain"

        body_text = f"""Hi {first_name},

I've been tracking {company}'s notable growth in {category} (congratulations on {funding}).

I'm a Software Engineer specializing in Python, FastAPI, React, and building resilient, high-speed distributed systems. Fast-scaling startups with strong investor momentum need versatile engineers who can execute across 0-to-1 core features, scalable backends, and low-latency APIs.

Given your leadership as {title}, I wanted to reach out directly to see if {company} is looking for a self-directed engineer to accelerate upcoming technical milestones.

Key Highlights:
• Full-stack architecture with FastAPI, Python, React & Next.js
• Distributed caching, messaging pipelines, and database optimization (PostgreSQL, Redis, Kafka)
• Startup velocity: high ownership, clean system design, and production reliability

My LinkedIn: {self.sender_linkedin or ''}

Would you be open to a brief 10-minute chat this week to see how my technical background aligns with {company}'s roadmaps?

Best regards,
{self.sender_name}
Software Engineer
{self.sender_linkedin or ''}
"""

        body_html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; line-height: 1.6;">
  <p>Hi {first_name},</p>
  <p>I've been tracking <strong>{company}</strong>'s notable growth in <em>{category}</em> (congratulations on <strong>{funding}</strong>).</p>
  <p>I'm a Software Engineer specializing in <strong>Python, FastAPI, React</strong>, and building resilient, high-speed distributed systems. Fast-scaling startups with strong investor momentum need versatile engineers who can execute across 0-to-1 core features, scalable backends, and low-latency APIs.</p>
  <p>Given your leadership as <em>{title}</em>, I wanted to reach out directly to see if {company} is looking for a self-directed engineer to accelerate upcoming technical milestones.</p>
  <p><strong>Key Highlights:</strong></p>
  <ul>
    <li>Full-stack architecture with FastAPI, Python, React & Next.js</li>
    <li>Distributed caching, messaging pipelines, and database optimization (PostgreSQL, Redis, Kafka)</li>
    <li>Startup velocity: high ownership, clean system design, and production reliability</li>
  </ul>
  <p>Would you be open to a brief 10-minute chat this week to see how my technical background aligns with {company}'s roadmaps?</p>
  <p>Best regards,<br>
  <strong>{self.sender_name}</strong><br>
  <span style="color: #64748B;">Software Engineer</span><br>
  <a href="{self.sender_linkedin or '#'}" style="color: #4F46E5;">{self.sender_linkedin or ''}</a>
  </p>
</body>
</html>"""

        return subject, body_text, body_html

    async def mine_and_store_startup(
        self,
        company: StartupsGalleryCompany,
        auto_send: bool = False,
        extract_twitter: bool = True,
    ) -> List[Dict[str, Any]]:
        """Mine decision makers for single startups.gallery company, persist to DB, and mark mined."""
        contacts = await self.mine_startup_founders(
            company=company,
            max_results=4,
            extract_twitter=extract_twitter,
        )

        with SessionLocal() as db:
            for dm in contacts:
                existing = db.query(Contact).filter(Contact.email == dm["email"]).first()
                if not existing:
                    new_c = Contact(
                        name=dm["name"],
                        title=dm["title"],
                        company=dm["company"],
                        email=dm["email"],
                        linkedin_url=dm.get("linkedin_url"),
                        twitter_url=dm.get("twitter_url"),
                        confidence_score=92 if dm.get("email") else 85,
                        source="startups_gallery",
                        department=company.category,
                    )
                    db.add(new_c)
                    self.total_mined += 1
                else:
                    if dm.get("twitter_url") and not existing.twitter_url:
                        existing.twitter_url = dm.get("twitter_url")

            # Update company record status
            rec = db.query(StartupsGalleryCompanyRecord).filter(
                StartupsGalleryCompanyRecord.slug == company.slug
            ).first()
            if rec:
                rec.mined = True
                rec.mined_at = datetime.now(timezone.utc)
                rec.founders_count = len(contacts)
            db.commit()

        # Optional outreach execution within MAX_OUTREACH_PER_COMPANY rate limit
        if auto_send and contacts:
            await self.save_and_outreach(
                contacts=contacts,
                company_name=company.name,
                source_prefix="startups_gallery",
                department=company.category,
                auto_send=True,
                composer=self.compose_startups_gallery_outreach,
                template_type="startups_gallery_founder_outreach",
            )

        return contacts

    async def batch_mine(
        self,
        batch_size: int = 100,
        category: Optional[str] = None,
        offset: Optional[int] = None,
        auto_send: bool = False,
        extract_twitter: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes a batch mining run of unmined companies.
        Subsequent runs automatically pick up the next unmined companies.
        """
        self._ensure_database_seeded()

        with SessionLocal() as db:
            query = db.query(StartupsGalleryCompanyRecord)
            if offset is not None:
                query = query.offset(offset)
            else:
                # Default: fetch unmined companies first
                query = query.filter(StartupsGalleryCompanyRecord.mined == False)

            if category:
                query = query.filter(
                    StartupsGalleryCompanyRecord.category.ilike(f"%{category}%")
                )

            records = query.limit(batch_size).all()
            target_slugs = [r.slug for r in records]

        if not target_slugs:
            return {
                "batch_size": batch_size,
                "companies_processed": 0,
                "founders_mined": 0,
                "contacts": [],
                "message": "All companies in the selected criteria have already been mined!",
            }

        companies = [get_company_by_slug(s) for s in target_slugs if get_company_by_slug(s)]
        all_contacts: List[Dict[str, Any]] = []

        for c in companies:
            contacts = await self.mine_and_store_startup(
                company=c,
                auto_send=auto_send,
                extract_twitter=extract_twitter,
            )
            all_contacts.extend(contacts)
            await asyncio.sleep(0.5)

        return {
            "batch_size": batch_size,
            "companies_processed": len(companies),
            "founders_mined": len(all_contacts),
            "contacts": all_contacts,
            "message": f"Successfully processed {len(companies)} companies and discovered {len(all_contacts)} founders.",
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns mining status and progress across all 1,369 startups.gallery companies."""
        self._ensure_database_seeded()
        with SessionLocal() as db:
            total_companies = db.query(StartupsGalleryCompanyRecord).count()
            mined_companies = db.query(StartupsGalleryCompanyRecord).filter(
                StartupsGalleryCompanyRecord.mined == True
            ).count()
            pending_companies = total_companies - mined_companies
            total_founders = db.query(Contact).filter(
                Contact.source == "startups_gallery"
            ).count()

            founders_with_linkedin = db.query(Contact).filter(
                Contact.source == "startups_gallery",
                Contact.linkedin_url.isnot(None),
            ).count()

            founders_with_twitter = db.query(Contact).filter(
                Contact.source == "startups_gallery",
                Contact.twitter_url.isnot(None),
            ).count()

            founders_with_email = db.query(Contact).filter(
                Contact.source == "startups_gallery",
                Contact.email.isnot(None),
            ).count()

        return {
            "total_companies": total_companies,
            "mined_companies": mined_companies,
            "pending_companies": pending_companies,
            "completion_percentage": round((mined_companies / total_companies * 100), 2) if total_companies else 0.0,
            "total_founders_mined": total_founders,
            "founders_with_linkedin": founders_with_linkedin,
            "founders_with_twitter": founders_with_twitter,
            "founders_with_email": founders_with_email,
        }


startups_gallery_miner = StartupsGalleryMiner()
