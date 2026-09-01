"""
tier1_career_scraper.py — Concurrent Direct Career Page & ATS Scraper for 60 Tier-1 Tech Companies.

Directly queries Greenhouse, Lever, SmartRecruiters, and Career endpoints to discover
active engineering positions at Rubrik, Stripe, Databricks, Meta, Airbnb, Zepto, Razorpay, CRED, etc.,
bypassing conventional job boards entirely.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.tier1_companies import TIER1_REGISTRY, Tier1Company, get_tier1_company
from src.job_data_providers import normalize_job

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(12.0, connect=6.0)
CONCURRENCY_LIMIT = 15


async def _scrape_greenhouse_company(
    client: httpx.AsyncClient,
    company: Tier1Company,
    keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Scrape Greenhouse public JSON API for a company."""
    if not company.ats_slug:
        return []
    url = f"https://boards-api.greenhouse.io/v1/boards/{company.ats_slug}/jobs?content=true"
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs_raw = data.get("jobs", [])
        matched = []
        for j in jobs_raw:
            title = j.get("title", "")
            content = j.get("content", "")
            text = f"{title} {content}".lower()
            if keywords:
                if not any(k.lower() in text for k in keywords):
                    continue
            normalized = normalize_job({
                "id": f"gh_{j.get('id')}",
                "title": title,
                "company": company.name,
                "location": (j.get("location") or {}).get("name"),
                "description": content,
                "url": j.get("absolute_url"),
                "published": j.get("updated_at"),
                "tags": ["Tier-1", company.likely_level, company.negotiation_target_lakhs],
            }, "greenhouse_direct")
            normalized["compensation_benchmark"] = company.to_dict()
            matched.append(normalized)
        return matched
    except Exception as exc:
        logger.debug("Greenhouse scrape failed for %s: %s", company.name, exc)
        return []


async def _scrape_lever_company(
    client: httpx.AsyncClient,
    company: Tier1Company,
    keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Scrape Lever public JSON API for a company."""
    if not company.ats_slug:
        return []
    url = f"https://api.lever.co/v0/postings/{company.ats_slug}?mode=json"
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        jobs_raw = resp.json()
        if not isinstance(jobs_raw, list):
            return []
        matched = []
        for j in jobs_raw:
            title = j.get("text", "")
            desc = j.get("descriptionPlain") or j.get("description", "")
            text = f"{title} {desc}".lower()
            if keywords:
                if not any(k.lower() in text for k in keywords):
                    continue
            categories = j.get("categories", {}) or {}
            normalized = normalize_job({
                "id": f"lever_{j.get('id')}",
                "title": title,
                "company": company.name,
                "location": categories.get("location"),
                "description": desc,
                "url": j.get("hostedUrl") or j.get("applyUrl"),
                "published": j.get("createdAt"),
                "tags": ["Tier-1", company.likely_level, company.negotiation_target_lakhs],
            }, "lever_direct")
            normalized["compensation_benchmark"] = company.to_dict()
            matched.append(normalized)
        return matched
    except Exception as exc:
        logger.debug("Lever scrape failed for %s: %s", company.name, exc)
        return []


async def _scrape_smartrecruiters_company(
    client: httpx.AsyncClient,
    company: Tier1Company,
    keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Scrape SmartRecruiters public postings API for a company."""
    if not company.ats_slug:
        return []
    url = f"https://api.smartrecruiters.com/v1/companies/{company.ats_slug}/postings"
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs_raw = data.get("content", [])
        matched = []
        for j in jobs_raw:
            title = j.get("name", "")
            loc = j.get("location", {}) or {}
            city = loc.get("city", "")
            country = loc.get("country", "")
            loc_str = f"{city}, {country}".strip(", ")
            text = title.lower()
            if keywords:
                if not any(k.lower() in text for k in keywords):
                    continue
            normalized = normalize_job({
                "id": f"sr_{j.get('id')}",
                "title": title,
                "company": company.name,
                "location": loc_str,
                "description": f"Position at {company.name}: {title}",
                "url": f"https://jobs.smartrecruiters.com/{company.ats_slug}/{j.get('id')}",
                "published": j.get("releasedDate"),
                "tags": ["Tier-1", company.likely_level, company.negotiation_target_lakhs],
            }, "smartrecruiters_direct")
            normalized["compensation_benchmark"] = company.to_dict()
            matched.append(normalized)
        return matched
    except Exception as exc:
        logger.debug("SmartRecruiters scrape failed for %s: %s", company.name, exc)
        return []


class Tier1CareerScraper:
    """Orchestrator for scanning all 60 Tier-1 career portals."""

    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.transport = transport

    async def scrape_all_tier1_careers(
        self,
        keywords: Optional[List[str]] = None,
        companies: Optional[List[str]] = None,
        max_jobs: int = 100,
    ) -> List[Dict[str, Any]]:
        """Scrape active career openings across target companies concurrently."""
        target_companies = TIER1_REGISTRY
        if companies:
            comp_set = set(c.lower() for c in companies)
            target_companies = [c for c in TIER1_REGISTRY if c.name.lower() in comp_set]

        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        all_jobs: List[Dict[str, Any]] = []

        async def worker(comp: Tier1Company, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
            async with semaphore:
                if comp.ats_platform == "greenhouse":
                    return await _scrape_greenhouse_company(client, comp, keywords=keywords)
                elif comp.ats_platform == "lever":
                    return await _scrape_lever_company(client, comp, keywords=keywords)
                elif comp.ats_platform == "smartrecruiters":
                    return await _scrape_smartrecruiters_company(client, comp, keywords=keywords)
                return []

        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, transport=self.transport) as client:
            tasks = [worker(c, client) for c in target_companies]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    all_jobs.extend(res)

        return all_jobs[:max_jobs]
