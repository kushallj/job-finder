"""
crawl_all_startups_and_nifty500.py — Master High-Throughput Job Crawler.

Scrapes live software, backend, fullstack, DevOps, and AI engineering opportunities across:
1. Official NSE Nifty 500 Enterprises (TCS, Infosys, HCL, Persistent, Coforge, Dixon, Zomato, Swiggy, etc.)
2. Y Combinator & Global Accelerator Startups (Zepto, Razorpay, Groww, Postman, SigNoz, Supabase, Cursor, Deel, etc.)
3. Global FinTech Fest Companies (Juspay, Cashfree, Pine Labs, M2P, Yubi, PayU, Stripe, Adyen, etc.)
4. Shark Tank India & US Breakouts (Snitch, Intervue, Stage, Clean Electric, Bombas, Scrub Daddy, Everlywell, etc.)
5. Suniel Shetty Show Startups (Digital Labour Chowk, Regrip, CRASTE, Waayu, Fittr, Rupyz, etc.)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import SessionLocal
from src.models import Job
from src.nifty500_registry import get_all_nifty500_companies
from src.accelerators_registry import get_all_accelerator_startups
from src.fintech_festival_companies import FINTECH_FESTIVAL_REGISTRY
from src.shark_tank_india_startups import get_all_shark_tank_startups
from src.shark_tank_us_startups import get_all_shark_tank_us_startups
from src.suniel_shetty_startups import get_all_suniel_shetty_startups

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("master_crawler")

TECH_TITLE_KEYWORDS = [
    "software", "engineer", "developer", "backend", "frontend", "full stack", "fullstack",
    "devops", "sre", "data engineer", "platform", "cloud", "ai", "machine learning", "ml",
    "python", "react", "golang", "java", "tech lead", "engineering manager", "architect",
    "mobile", "ios", "android", "infrastructure", "systems", "qa", "sdet"
]


def is_tech_job(title: str) -> bool:
    """Return True if title corresponds to a software or tech role."""
    t = title.lower()
    return any(k in t for k in TECH_TITLE_KEYWORDS)


def extract_tech_stack(text: str) -> List[str]:
    """Extract known tech stack tokens."""
    stack = []
    tokens = {
        "Python": r"\bpython\b",
        "FastAPI": r"\bfastapi\b",
        "React": r"\breact(\.js)?\b",
        "Node.js": r"\bnode(\.js)?\b",
        "TypeScript": r"\btypescript\b",
        "Go": r"\b(golang|go)\b",
        "Java": r"\bjava\b",
        "PostgreSQL": r"\bpostgres(ql)?\b",
        "Redis": r"\bredis\b",
        "Kafka": r"\bkafka\b",
        "AWS": r"\baws\b",
        "Kubernetes": r"\b(k8s|kubernetes)\b",
        "Docker": r"\bdocker\b",
        "Next.js": r"\bnext(\.js)?\b",
    }
    for tech, pat in tokens.items():
        if re.search(pat, text, re.I):
            stack.append(tech)
    return stack or ["Python", "FastAPI", "React"]


class MasterJobCrawler:
    """Concurrent multi-source crawler for enterprise and startup tech jobs."""

    def __init__(self):
        self.total_fetched = 0
        self.total_inserted = 0
        self.client = httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers={
            "User-Agent": "JobFinderBot/2.0 (Engineering Outreach & Sourcing Engine)"
        })

    async def crawl_greenhouse_board(self, company_name: str, slug: str, source_tag: str) -> List[Dict[str, Any]]:
        """Scrape live tech jobs from Greenhouse ATS API."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        results = []
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for j in data.get("jobs", []):
                    title = j.get("title", "")
                    if is_tech_job(title):
                        loc = j.get("location", {}).get("name", "Remote / India")
                        j_url = j.get("absolute_url", "")
                        results.append({
                            "title": title,
                            "company": company_name,
                            "location": loc,
                            "url": j_url,
                            "source": source_tag,
                            "tags": ["Engineering", "Greenhouse", source_tag],
                        })
        except Exception as exc:
            logger.debug(f"Greenhouse crawl skip for {slug}: {exc}")
        return results

    async def crawl_lever_board(self, company_name: str, slug: str, source_tag: str) -> List[Dict[str, Any]]:
        """Scrape live tech jobs from Lever ATS API."""
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        results = []
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for j in data:
                    title = j.get("text", "")
                    if is_tech_job(title):
                        loc = j.get("categories", {}).get("location", "Remote / India")
                        j_url = j.get("hostedUrl", "")
                        results.append({
                            "title": title,
                            "company": company_name,
                            "location": loc,
                            "url": j_url,
                            "source": source_tag,
                            "tags": ["Engineering", "Lever", source_tag],
                        })
        except Exception as exc:
            logger.debug(f"Lever crawl skip for {slug}: {exc}")
        return results

    async def crawl_smartrecruiters_board(self, company_name: str, slug: str, source_tag: str) -> List[Dict[str, Any]]:
        """Scrape live tech jobs from SmartRecruiters ATS API."""
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        results = []
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for j in data.get("content", []):
                    title = j.get("name", "")
                    if is_tech_job(title):
                        loc = j.get("location", {}).get("city", "Remote / India")
                        j_url = f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}"
                        results.append({
                            "title": title,
                            "company": company_name,
                            "location": loc,
                            "url": j_url,
                            "source": source_tag,
                            "tags": ["Engineering", "SmartRecruiters", source_tag],
                        })
        except Exception as exc:
            logger.debug(f"SmartRecruiters crawl skip for {slug}: {exc}")
        return results

    def save_jobs_to_db(self, jobs: List[Dict[str, Any]]):
        """Batch upsert discovered tech jobs into SQLite."""
        if not jobs:
            return

        with SessionLocal() as db:
            for j in jobs:
                # Deduplicate by url or company+title
                title = j["title"]
                comp = j["company"]
                existing = db.query(Job).filter(
                    (Job.url == j["url"]) | ((Job.company == comp) & (Job.title == title))
                ).first()

                if not existing:
                    job_id = f"crawl_{abs(hash(comp + title + j['url'])) % 10000000}"
                    tech_stack = extract_tech_stack(title + " " + " ".join(j.get("tags", [])))
                    new_job = Job(
                        job_id=job_id,
                        title=title,
                        company=comp,
                        location=j.get("location", "India / Remote"),
                        url=j.get("url", ""),
                        source=j.get("source", "crawler"),
                        tags=json.dumps(j.get("tags", ["Engineering"])),
                        description=f"Software engineering opening at {comp}. Tech Stack: {', '.join(tech_stack)}.",
                        fetched_at=datetime.now(timezone.utc),
                    )
                    db.add(new_job)
                    self.total_inserted += 1

            db.commit()

    async def run_full_crawler_cycle(self):
        """Execute concurrent multi-source crawler across all catalogs."""
        logger.info("🚀 Starting Master Tech Jobs Crawler...")

        tasks = []

        # 1. Global FinTech Fest Companies
        logger.info(f"Indexing {len(FINTECH_FESTIVAL_REGISTRY)} Global FinTech Fest companies...")
        for comp in FINTECH_FESTIVAL_REGISTRY:
            slug = comp.ats_slug or comp.id
            if comp.ats_platform == "greenhouse":
                tasks.append(self.crawl_greenhouse_board(comp.name, slug, "gff_fintech"))
            elif comp.ats_platform == "lever":
                tasks.append(self.crawl_lever_board(comp.name, slug, "gff_fintech"))
            elif comp.ats_platform == "smartrecruiters":
                tasks.append(self.crawl_smartrecruiters_board(comp.name, slug, "gff_fintech"))

        # 2. Y Combinator & Global Accelerator Startups
        acc_startups = get_all_accelerator_startups()
        logger.info(f"Indexing {len(acc_startups)} YC & Accelerator startups...")
        for s in acc_startups:
            slug = s.ats_slug or s.id
            src_tag = f"accelerator_{s.accelerator.lower().replace(' ', '_')}"
            if s.ats_platform == "greenhouse":
                tasks.append(self.crawl_greenhouse_board(s.name, slug, src_tag))
            elif s.ats_platform == "lever":
                tasks.append(self.crawl_lever_board(s.name, slug, src_tag))

        # 3. Shark Tank India Startups
        st_india = get_all_shark_tank_startups()
        logger.info(f"Indexing {len(st_india)} Shark Tank India startups...")
        for s in st_india:
            slug = s.ats_slug or s.id
            src_tag = f"shark_tank_india_s{s.season}"
            if s.ats_platform == "greenhouse":
                tasks.append(self.crawl_greenhouse_board(s.name, slug, src_tag))
            elif s.ats_platform == "lever":
                tasks.append(self.crawl_lever_board(s.name, slug, src_tag))

        # 4. Shark Tank US Startups
        st_us = get_all_shark_tank_us_startups()
        logger.info(f"Indexing {len(st_us)} Shark Tank US startups...")
        for s in st_us:
            slug = s.ats_slug or s.id
            src_tag = f"shark_tank_us_s{s.season}"
            if s.ats_platform == "greenhouse":
                tasks.append(self.crawl_greenhouse_board(s.name, slug, src_tag))
            elif s.ats_platform == "lever":
                tasks.append(self.crawl_lever_board(s.name, slug, src_tag))

        # 5. Suniel Shetty Startups
        shetty_startups = get_all_suniel_shetty_startups()
        logger.info(f"Indexing {len(shetty_startups)} Suniel Shetty show & portfolio startups...")
        for s in shetty_startups:
            slug = s.id
            src_tag = f"shetty_{s.show_or_source.lower().replace(' ', '_')}"
            tasks.append(self.crawl_lever_board(s.name, slug, src_tag))

        # 6. Official Nifty 500 Enterprises
        nifty500 = get_all_nifty500_companies()
        logger.info(f"Indexing {len(nifty500)} official Nifty 500 companies...")
        for c in nifty500:
            sym_lower = c.symbol.lower()
            src_tag = f"nifty500_{sym_lower}"
            # Check tech enterprises with greenhouse/lever endpoints
            tasks.append(self.crawl_greenhouse_board(c.name, sym_lower, src_tag))
            tasks.append(self.crawl_lever_board(c.name, sym_lower, src_tag))

        logger.info(f"Executing {len(tasks)} concurrent async scraper tasks...")
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            chunk = tasks[i:i + batch_size]
            results = await asyncio.gather(*chunk, return_exceptions=True)
            for r in results:
                if isinstance(r, list) and r:
                    self.total_fetched += len(r)
                    self.save_jobs_to_db(r)
            logger.info(f"Progress: [{min(i + batch_size, len(tasks))}/{len(tasks)}] tasks completed | Jobs Inserted: {self.total_inserted}")

        await self.client.aclose()
        logger.info(f"✅ Master Tech Job Crawl Complete! Total Jobs Fetched: {self.total_fetched} | New Tech Jobs Saved to DB: {self.total_inserted}")
        return {
            "total_fetched": self.total_fetched,
            "total_inserted": self.total_inserted,
        }


if __name__ == "__main__":
    crawler = MasterJobCrawler()
    asyncio.run(crawler.run_full_crawler_cycle())
