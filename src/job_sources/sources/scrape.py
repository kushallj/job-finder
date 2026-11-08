"""Scrape-tier sources: HTML scraping or crawlers. Off unless JOB_SOURCES_ALLOW_SCRAPING=true.

Kept opt-in because site terms and anti-bot rules apply (CLAUDE.md section 7, legal review
pending). LinkedIn, X and Google result pages are never sources: JobSpy runs without
LinkedIn, and the old Google `site:` searcher was deleted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from src.config import settings
from src.job_sources.base import CallableSource
from src.job_sources.models import SearchQuery, Tier

Rows = list[Mapping[str, Any]]

JOBSPY_SITES = ["indeed", "glassdoor", "naukri"]  # never "linkedin" (CLAUDE.md section 1)


async def _firecrawl(q: SearchQuery) -> Rows:
    from src.scrapers.firecrawl_scraper import FirecrawlCareerScraper

    return await FirecrawlCareerScraper().search(query=q.text, location=q.location, max_results=q.limit)


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


async def _tier1_careers(q: SearchQuery) -> Rows:
    from src.scrapers.tier1_career_scraper import Tier1CareerScraper

    return await Tier1CareerScraper().scrape_all_tier1_careers(keywords=[q.text], max_jobs=q.limit)


async def _indian_app_startups(q: SearchQuery) -> Rows:
    from src.scrapers.indian_app_startups_scraper import IndianAppStartupsScraper

    return await IndianAppStartupsScraper().scrape_all_startups(keywords=[q.text], max_jobs=q.limit)


async def _fintech_festival(q: SearchQuery) -> Rows:
    from src.scrapers.fintech_festival_scraper import FinTechFestivalScraper

    return await FinTechFestivalScraper().scrape_all_festival_sponsors(keywords=[q.text], max_jobs=q.limit)


SOURCES: tuple[CallableSource, ...] = (
    CallableSource("firecrawl", Tier.SCRAPE, _firecrawl, lambda: bool(settings.firecrawl_api_key),
                   "Startup career pages via Firecrawl"),
    CallableSource("jobspy", Tier.SCRAPE, _jobspy, description="Indeed/Glassdoor/Naukri via JobSpy (no LinkedIn)"),
    CallableSource("foorilla", Tier.SCRAPE, _foorilla, description="Foorilla.com HTML"),
    CallableSource("tier1_careers", Tier.SCRAPE, _tier1_careers, description="~60 Tier-1 tech career sites"),
    CallableSource("indian_app_startups", Tier.SCRAPE, _indian_app_startups, description="~100 Indian app startups' career pages"),
    CallableSource("fintech_festival", Tier.SCRAPE, _fintech_festival, description="FinTech Festival sponsors' career pages"),
)
