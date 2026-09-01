"""
fintech_festival_scraper.py — Concurrent ATS Career Scraper for FinTech Festival Sponsors.

Scrapes live engineering postings from sponsors and exhibitors of Global FinTech Fest (GFF)
and Singapore FinTech Festival (SFF) directly from Greenhouse, Lever, SmartRecruiters, and Career feeds.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from src.fintech_festival_companies import FINTECH_FESTIVAL_REGISTRY, FinTechFestivalCompany, get_fintech_festival_company
from src.job_data_providers import normalize_job

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(12.0, connect=6.0)
CONCURRENCY_LIMIT = 20


async def _scrape_greenhouse_fintech(
    client: httpx.AsyncClient,
    company: FinTechFestivalCompany,
    keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if not company.ats_slug:
        return []
    url = f"https://boards-api.greenhouse.io/v1/boards/{company.ats_slug}/jobs?content=true"
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()
        raw_jobs = data.get("jobs", [])
        matched = []
        for j in raw_jobs:
            title = j.get("title", "")
            content = j.get("content", "")
            text = f"{title} {content}".lower()
            if keywords:
                if not any(k.lower() in text for k in keywords):
                    continue
            row = normalize_job({
                "id": f"gh_ft_{company.id}_{j.get('id')}",
                "title": title,
                "company": company.name,
                "location": (j.get("location") or {}).get("name") or "India / Remote",
                "description": content,
                "url": j.get("absolute_url"),
                "published": j.get("updated_at"),
                "tags": ["FinTech-Festival-Sponsor", company.category, company.festival],
            }, "greenhouse_fintech")
            row["festival_info"] = company.to_dict()
            matched.append(row)
        return matched
    except Exception as exc:
        logger.debug("Greenhouse fintech scrape failed for %s: %s", company.name, exc)
        return []


async def _scrape_lever_fintech(
    client: httpx.AsyncClient,
    company: FinTechFestivalCompany,
    keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if not company.ats_slug:
        return []
    url = f"https://api.lever.co/v0/postings/{company.ats_slug}?mode=json"
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        raw_jobs = resp.json()
        if not isinstance(raw_jobs, list):
            return []
        matched = []
        for j in raw_jobs:
            title = j.get("text", "")
            desc = j.get("descriptionPlain") or j.get("description", "")
            text = f"{title} {desc}".lower()
            if keywords:
                if not any(k.lower() in text for k in keywords):
                    continue
            categories = j.get("categories", {}) or {}
            row = normalize_job({
                "id": f"lever_ft_{company.id}_{j.get('id')}",
                "title": title,
                "company": company.name,
                "location": categories.get("location") or "India / Remote",
                "description": desc,
                "url": j.get("hostedUrl") or j.get("applyUrl"),
                "published": j.get("createdAt"),
                "tags": ["FinTech-Festival-Sponsor", company.category, company.festival],
            }, "lever_fintech")
            row["festival_info"] = company.to_dict()
            matched.append(row)
        return matched
    except Exception as exc:
        logger.debug("Lever fintech scrape failed for %s: %s", company.name, exc)
        return []


async def _scrape_smartrecruiters_fintech(
    client: httpx.AsyncClient,
    company: FinTechFestivalCompany,
    keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if not company.ats_slug:
        return []
    url = f"https://api.smartrecruiters.com/v1/companies/{company.ats_slug}/postings"
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()
        raw_jobs = data.get("content", [])
        matched = []
        for j in raw_jobs:
            title = j.get("name", "")
            loc = j.get("location", {}) or {}
            city = loc.get("city", "")
            country = loc.get("country", "")
            loc_str = f"{city}, {country}".strip(", ") or "Global"
            text = title.lower()
            if keywords:
                if not any(k.lower() in text for k in keywords):
                    continue
            row = normalize_job({
                "id": f"sr_ft_{company.id}_{j.get('id')}",
                "title": title,
                "company": company.name,
                "location": loc_str,
                "description": f"Role at {company.name}: {title}",
                "url": f"https://jobs.smartrecruiters.com/{company.ats_slug}/{j.get('id')}",
                "published": j.get("releasedDate"),
                "tags": ["FinTech-Festival-Sponsor", company.category, company.festival],
            }, "smartrecruiters_fintech")
            row["festival_info"] = company.to_dict()
            matched.append(row)
        return matched
    except Exception as exc:
        logger.debug("SmartRecruiters fintech scrape failed for %s: %s", company.name, exc)
        return []


class FinTechFestivalScraper:
    """Orchestrator for scanning career feeds of FinTech Festival sponsors."""

    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.transport = transport

    async def scrape_all_festival_sponsors(
        self,
        keywords: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        festivals: Optional[List[str]] = None,
        company_ids: Optional[List[str]] = None,
        max_jobs: int = 150,
    ) -> List[Dict[str, Any]]:
        """Scrape active engineering opportunities from all festival sponsors."""
        target_list = FINTECH_FESTIVAL_REGISTRY
        if categories:
            cat_set = set(c.lower() for c in categories)
            target_list = [c for c in target_list if c.category.lower() in cat_set]
        if festivals:
            fest_set = set(f.lower() for f in festivals)
            target_list = [c for c in target_list if any(f.lower() in c.festival.lower() for f in fest_set)]
        if company_ids:
            id_set = set(cid.lower() for cid in company_ids)
            target_list = [c for c in target_list if c.id.lower() in id_set]

        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        all_jobs: List[Dict[str, Any]] = []

        async def worker(comp: FinTechFestivalCompany, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
            async with semaphore:
                if comp.ats_platform == "greenhouse":
                    return await _scrape_greenhouse_fintech(client, comp, keywords=keywords)
                elif comp.ats_platform == "lever":
                    return await _scrape_lever_fintech(client, comp, keywords=keywords)
                elif comp.ats_platform == "smartrecruiters":
                    return await _scrape_smartrecruiters_fintech(client, comp, keywords=keywords)
                return []

        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, transport=self.transport) as client:
            tasks = [worker(c, client) for c in target_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    all_jobs.extend(res)

        return all_jobs[:max_jobs]
