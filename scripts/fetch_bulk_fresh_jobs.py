#!/usr/bin/env python3
"""
fetch_bulk_fresh_jobs.py — Multi-Source Live Job Harvester.
Fetches fresh live tech jobs across multiple open APIs, categories, and pagination:
- Arbeitnow Multi-Page API (Remote, Germany, EU, Global Tech)
- Remotive Multi-Category API (Software Dev, DevOps, Data, JavaScript, React)
- Target Company Scrapers
Deduplicates against existing SQLite database, computes semantic fit, and stores fresh jobs.
"""
from __future__ import annotations

import sys
import os
import time
import uuid
import json
import httpx
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.database import SessionLocal, init_db
from src.models import Job
from src.autonomous_job_crawler import extract_tech_tags_and_seniority

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("job_harvester")


async def fetch_arbeitnow_jobs(max_pages: int = 5) -> List[Dict[str, Any]]:
    """Fetches real live tech jobs across multiple pages of Arbeitnow public board API."""
    jobs = []
    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            url = f"https://www.arbeitnow.com/api/job-board-api?page={page}"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    if not data:
                        break
                    for item in data:
                        title = item.get("title", "")
                        company = item.get("company_name", "")
                        location = item.get("location", "Remote")
                        description = item.get("description", "")
                        job_url = item.get("url", "")
                        tags = item.get("tags", [])
                        
                        jobs.append({
                            "title": title,
                            "company": company,
                            "location": location,
                            "description": description or " ".join(tags),
                            "url": job_url,
                            "source": "arbeitnow_live",
                            "has_remote": item.get("remote", True),
                            "tags": tags,
                        })
                else:
                    break
            except Exception as e:
                logger.warning(f"Arbeitnow page {page} fetch failed: {e}")
                break
    return jobs


async def fetch_remotive_jobs() -> List[Dict[str, Any]]:
    """Fetches real live remote software jobs across multiple categories from Remotive API."""
    jobs = []
    categories = ["software-dev", "devops", "data", "qa"]
    searches = ["javascript", "typescript", "react", "fullstack", "python", "backend"]
    
    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        for cat in categories:
            url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=100"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json().get("jobs", [])
                    for item in data:
                        jobs.append({
                            "title": item.get("title", ""),
                            "company": item.get("company_name", ""),
                            "location": item.get("candidate_required_location", "Remote / Worldwide"),
                            "description": item.get("description", "")[:2500],
                            "url": item.get("url", ""),
                            "source": "remotive_live",
                            "has_remote": True,
                            "tags": item.get("tags", []),
                        })
            except Exception as e:
                logger.warning(f"Remotive category {cat} failed: {e}")

        for s in searches:
            url = f"https://remotive.com/api/remote-jobs?search={s}&limit=50"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json().get("jobs", [])
                    for item in data:
                        jobs.append({
                            "title": item.get("title", ""),
                            "company": item.get("company_name", ""),
                            "location": item.get("candidate_required_location", "Remote / Worldwide"),
                            "description": item.get("description", "")[:2500],
                            "url": item.get("url", ""),
                            "source": "remotive_live",
                            "has_remote": True,
                            "tags": item.get("tags", []),
                        })
            except Exception as e:
                logger.warning(f"Remotive search {s} failed: {e}")

    return jobs


async def main():
    print("=" * 70)
    print("  🚀 MULTI-SOURCE LIVE JOB HARVESTER (Arbeitnow + Remotive + Global)")
    print("=" * 70)

    init_db()
    session = SessionLocal()
    initial_count = session.query(Job).count()
    print(f"📊 Initial Job Count in DB: {initial_count}")

    print("\n🌐 Fetching from Arbeitnow API (Multi-Page)...")
    arbeitnow_jobs = await fetch_arbeitnow_jobs(max_pages=5)
    print(f"  [✓] Retrieved {len(arbeitnow_jobs)} listings from Arbeitnow")

    print("\n🌐 Fetching from Remotive API (Multi-Category & Search)...")
    remotive_jobs = await fetch_remotive_jobs()
    print(f"  [✓] Retrieved {len(remotive_jobs)} listings from Remotive")

    all_harvested = arbeitnow_jobs + remotive_jobs
    print(f"\n📦 Total Raw Listings Collected: {len(all_harvested)}")

    newly_added = 0
    skipped_duplicates = 0

    for job_data in all_harvested:
        url = job_data.get("url", "").strip()
        title = job_data.get("title", "").strip()
        company = job_data.get("company", "").strip()

        if not url or not title:
            continue

        # Check existing by URL or (company + title) or job_id
        exists = session.query(Job).filter(
            (Job.url == url) | ((Job.company == company) & (Job.title == title))
        ).first()

        if exists:
            skipped_duplicates += 1
            continue

        tags, seniority = extract_tech_tags_and_seniority(title, job_data.get("description", ""))
        unique_job_id = f"{job_data.get('source', 'harvester')}_{abs(hash(url))}_{int(time.time() * 1000) % 1000000}"

        new_job = Job(
            job_id=unique_job_id,
            title=title,
            company=company,
            location=job_data.get("location", "Remote"),
            description=job_data.get("description", ""),
            url=url,
            source=job_data.get("source", "live_harvester"),
            has_remote=job_data.get("has_remote", True),
            experience_level=seniority,
            tags=json.dumps(tags or job_data.get("tags", [])),
            fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(new_job)
        newly_added += 1

    session.commit()
    final_count = session.query(Job).count()

    # JS/TS count
    js_count = session.query(Job).filter(
        Job.title.ilike('%javascript%') | Job.title.ilike('%typescript%') | 
        Job.title.ilike('%react%') | Job.title.ilike('%node%') | 
        Job.title.ilike('%frontend%') | Job.title.ilike('%full%') |
        Job.description.ilike('%javascript%') | Job.description.ilike('%typescript%')
    ).count()

    session.close()

    print("\n" + "=" * 70)
    print(f"  🎉 HARVESTING COMPLETE!")
    print(f"  • Newly Ingested Jobs: +{newly_added}")
    print(f"  • Duplicates Filtered: {skipped_duplicates}")
    print(f"  • Total Active Jobs in Database: {final_count} (JS/TS Specific: {js_count})")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
