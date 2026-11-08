"""Every job source, wrapped once. Add a source here and list it in `registry.SOURCES`.

Official APIs and public feeds reuse the existing clients in `src/job_data_providers.py`
and `src/scrapers/ats_scraper.py`. Scrape-tier sources wrap the legacy scrapers and are
opt-in (JOB_SOURCES_ALLOW_SCRAPING). LinkedIn, X and Google result pages are never
sources (CLAUDE.md section 1), so JobSpy runs without LinkedIn and the Google
`site:` searcher is not registered at all.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

import httpx

from src.config import settings
from src.job_data_providers import (
    AIDevBoardClient,
    ArbeitnowClient,
    CareerjetClient,
    FantasticJobsClient,
    JobDataAPIClient,
    USAJobsClient,
    normalize_job,
)
from src.job_sources.base import CallableSource
from src.job_sources.models import SearchQuery, Tier

Rows = list[Mapping[str, Any]]
HTTP_TIMEOUT = 20.0


# --- official, key-based APIs ------------------------------------------------------

async def _jobdataapi(q: SearchQuery) -> Rows:
    return await JobDataAPIClient().search(query=q.text, location=q.location or None,
                                           max_age=q.max_age_days, page_size=q.limit)


async def _aidevboard(q: SearchQuery) -> Rows:
    return await AIDevBoardClient().search(query=q.text, location=q.location or None, limit=q.limit)


async def _fantastic_jobs(q: SearchQuery) -> Rows:
    return await FantasticJobsClient().search(query=q.text, location=q.location or None, limit=q.limit)


async def _careerjet(q: SearchQuery) -> Rows:
    return await CareerjetClient().search(query=q.text, location=q.location or None, page_size=q.limit)


async def _usajobs(q: SearchQuery) -> Rows:
    return await USAJobsClient().search(query=q.text, location=q.location or None,
                                        results_per_page=q.limit, remote_only=False)


ADZUNA_CURRENCY = {"in": "INR", "gb": "GBP", "us": "USD", "de": "EUR", "ca": "CAD", "au": "AUD", "sg": "SGD"}


async def _adzuna(q: SearchQuery) -> Rows:
    country = (settings.adzuna_country or "in").lower()
    params = {"app_id": settings.adzuna_app_id, "app_key": settings.adzuna_app_key,
              "results_per_page": min(q.limit, 50), "what": q.text, "max_days_old": q.max_age_days}
    if q.location:
        params["where"] = q.location
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(f"https://api.adzuna.com/v1/api/jobs/{country}/search/1", params=params)
        res.raise_for_status()
    rows = []
    for j in res.json().get("results", []):
        item = {
            "id": j.get("id"),
            "title": j.get("title"),
            "company": (j.get("company") or {}).get("display_name"),
            "location": (j.get("location") or {}).get("display_name"),
            "description": j.get("description"),
            "url": j.get("redirect_url"),
            "created_at": j.get("created"),
            "salary_min": j.get("salary_min"),
            "salary_max": j.get("salary_max"),
            "salary_currency": ADZUNA_CURRENCY.get(country) if j.get("salary_min") or j.get("salary_max") else None,
            "tags": [j["category"]["label"]] if (j.get("category") or {}).get("label") else [],
        }
        rows.append(normalize_job(item, "adzuna"))
    return rows


# --- public JSON feeds ----------------------------------------------------------------

async def _arbeitnow(q: SearchQuery) -> Rows:
    return await ArbeitnowClient().search(query=q.text, location=q.location or None, limit=q.limit)


async def _remotive(q: SearchQuery) -> Rows:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get("https://remotive.com/api/remote-jobs",
                               params={"search": q.text, "limit": q.limit})
        res.raise_for_status()
    rows = []
    for j in res.json().get("jobs", []):
        item = {**j, "company": j.get("company_name"), "location": j.get("candidate_required_location") or "Remote",
                "published": j.get("publication_date"), "work_mode": "remote", "remote": True}
        rows.append(normalize_job(item, "remotive"))
    return rows


async def _ats_boards(q: SearchQuery) -> Rows:
    """Public Greenhouse + Lever job-board APIs for the companies in ats_scraper."""
    from src.scrapers.ats_scraper import ATSScraper

    return await ATSScraper().search(query=q.text, location=q.location)


# --- scrape tier (opt-in) ---------------------------------------------------------------

async def _firecrawl(q: SearchQuery) -> Rows:
    from src.scrapers.firecrawl_scraper import FirecrawlCareerScraper

    return await FirecrawlCareerScraper().search(query=q.text, location=q.location, max_results=q.limit)


JOBSPY_SITES = ["indeed", "glassdoor", "naukri"]  # never "linkedin" (CLAUDE.md section 1)


async def _jobspy(q: SearchQuery) -> Rows:
    from src.scrapers.jobspy_scraper import JobSpyScraper

    return await JobSpyScraper().search(q.text, location=q.location or "india", results_wanted=q.limit,
                                        hours_old=q.max_age_days * 24, sites=JOBSPY_SITES)


async def _foorilla(q: SearchQuery) -> Rows:
    import aiohttp

    from src.scrapers.foorilla_scraper import FoorillaScraper

    async with aiohttp.ClientSession() as session:
        postings = await FoorillaScraper(session).search(q.text, q.location)
    return [asdict(p) for p in postings]


def _has(*keys: str):
    return lambda: all(getattr(settings, k, None) for k in keys)


ALL_SOURCES: tuple[CallableSource, ...] = (
    CallableSource("jobdataapi", Tier.OFFICIAL_API, _jobdataapi, _has("jobdata_api_key"), "jobdataapi.com"),
    CallableSource("aidevboard", Tier.OFFICIAL_API, _aidevboard, _has("aidevboard_api_key"), "AI/ML jobs board"),
    CallableSource("fantastic_jobs", Tier.OFFICIAL_API, _fantastic_jobs,
                   lambda: FantasticJobsClient().enabled, "ATS + board aggregator"),
    CallableSource("careerjet", Tier.OFFICIAL_API, _careerjet, _has("careerjet_api_key"), "Careerjet partner API"),
    CallableSource("usajobs", Tier.OFFICIAL_API, _usajobs, _has("usajobs_api_key"), "US federal jobs"),
    CallableSource("adzuna", Tier.OFFICIAL_API, _adzuna, _has("adzuna_app_id", "adzuna_app_key"), "Adzuna search API"),
    CallableSource("arbeitnow", Tier.PUBLIC_FEED, _arbeitnow, description="Arbeitnow public job-board API"),
    CallableSource("remotive", Tier.PUBLIC_FEED, _remotive, description="Remotive public remote-jobs API"),
    CallableSource("ats_boards", Tier.PUBLIC_FEED, _ats_boards, description="Greenhouse + Lever public boards"),
    CallableSource("firecrawl", Tier.SCRAPE, _firecrawl, _has("firecrawl_api_key"), "Startup career pages via Firecrawl"),
    CallableSource("jobspy", Tier.SCRAPE, _jobspy, description="Indeed/Glassdoor/Naukri via JobSpy (no LinkedIn)"),
    CallableSource("foorilla", Tier.SCRAPE, _foorilla, description="Foorilla.com HTML"),
)
