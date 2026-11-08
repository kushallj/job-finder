"""ATS job boards: one source per platform, querying every configured company concurrently.

Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee and Teamtailor publish
documented public job-board APIs/feeds. Rippling and Workday expose the JSON their own
career pages use (undocumented), so they are scrape tier. Companies: ats_boards.yml.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from functools import cache
from pathlib import Path
from typing import Any

import feedparser
import yaml

from src.job_data_providers import normalize_job
from src.job_sources.base import CallableSource
from src.job_sources.models import SearchQuery, Tier
from src.job_sources.sources._http import client, get_json, get_text, html_to_text, matches, request

Rows = list[Mapping[str, Any]]
CompanyFetch = Callable[[str, str, SearchQuery], Awaitable[Rows]]

BOARDS_FILE = Path(__file__).resolve().parent.parent / "ats_boards.yml"
MAX_CONCURRENT_COMPANIES = 10


@cache
def boards() -> dict[str, dict[str, str]]:
    with BOARDS_FILE.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return {platform: dict(companies or {}) for platform, companies in data.items()}


def _per_company(platform: str, fetch_company: CompanyFetch, companies: Callable[[], Mapping[str, str]] | None = None):
    """Fan out over a platform's companies with bounded concurrency; skip companies that fail."""
    async def fetch(q: SearchQuery) -> Rows:
        targets = companies() if companies else boards().get(platform, {})
        sem = asyncio.Semaphore(MAX_CONCURRENT_COMPANIES)

        async def one(slug: str, name: str) -> Rows:
            async with sem:
                return await fetch_company(slug, name, q)

        results = await asyncio.gather(*(one(s, n) for s, n in targets.items()), return_exceptions=True)
        if results and all(isinstance(r, BaseException) for r in results):
            raise next(r for r in results if isinstance(r, BaseException))
        return [row for r in results if not isinstance(r, BaseException) for row in r]
    return fetch


# --- Greenhouse + Lever: reuse the curated lists and parsers in ats_scraper ---------------------

def _ats_scraper_companies(attr: str) -> Callable[[], dict[str, str]]:
    def load() -> dict[str, str]:
        from src.scrapers import ats_scraper
        return dict(getattr(ats_scraper, attr))
    return load


def _ats_scraper_fetch(fn_name: str) -> CompanyFetch:
    async def fetch(slug: str, name: str, q: SearchQuery) -> Rows:
        from src.scrapers import ats_scraper
        async with client() as c:
            return await getattr(ats_scraper, fn_name)(c, slug, name, q.text)
    return fetch


# --- documented public boards ---------------------------------------------------------------------

async def _ashby(slug: str, name: str, q: SearchQuery) -> Rows:
    data = await get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", params={"includeCompensation": "true"})
    rows = []
    for j in data.get("jobs", []):
        text = j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml"))
        if not j.get("isListed", True) or not matches(q.text, j.get("title"), j.get("team"), j.get("department"), text):
            continue
        rows.append(normalize_job({
            "id": j.get("id"), "title": j.get("title"), "company": name, "location": j.get("location"),
            "description": text, "url": j.get("jobUrl"), "published_at": j.get("publishedAt"), "remote": j.get("isRemote"),
            "work_mode": (j.get("workplaceType") or "").lower() or None,
            "tags": [t for t in (j.get("department"), j.get("team"), j.get("employmentType")) if t],
        }, "ashby"))
    return rows


async def _workable(slug: str, name: str, q: SearchQuery) -> Rows:
    data = await get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}", params={"details": "true"})
    return [normalize_job({
        "id": j.get("shortcode"), "title": j.get("title"), "company": name,
        "location": ", ".join(p for p in (j.get("city"), j.get("country")) if p) or ("Remote" if j.get("telecommuting") else ""),
        "description": html_to_text(j.get("description")), "url": j.get("url"), "published": j.get("published_on"),
        "remote": j.get("telecommuting"), "experience_level": j.get("experience") or None,
        "tags": [t for t in (j.get("department"), j.get("function"), j.get("employment_type")) if t],
    }, "workable") for j in data.get("jobs", []) if matches(q.text, j.get("title"), j.get("department"), j.get("function"))]


async def _smartrecruiters(slug: str, name: str, q: SearchQuery) -> Rows:
    data = await get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                          params={"q": q.text, "limit": min(q.limit, 100)})
    rows = []
    for j in data.get("content", []):
        loc = j.get("location") or {}
        rows.append(normalize_job({
            "id": j.get("id"), "title": j.get("name"), "company": (j.get("company") or {}).get("name") or name,
            "location": loc.get("fullLocation") or ", ".join(p for p in (loc.get("city"), (loc.get("country") or "").upper()) if p),
            "url": f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}", "published": j.get("releasedDate"),
            "remote": loc.get("remote"), "experience_level": (j.get("experienceLevel") or {}).get("label"),
            "tags": [t for t in ((j.get("function") or {}).get("label"), (j.get("typeOfEmployment") or {}).get("label")) if t],
        }, "smartrecruiters"))
    return rows


async def _recruitee(slug: str, name: str, q: SearchQuery) -> Rows:
    data = await get_json(f"https://{slug}.recruitee.com/api/offers/")
    rows = []
    for j in data.get("offers", []):
        text = html_to_text((j.get("description") or "") + (j.get("requirements") or ""))
        if not matches(q.text, j.get("title"), j.get("department"), text):
            continue
        sal = j.get("salary") or {}
        rows.append(normalize_job({
            "id": j.get("id"), "title": j.get("title"), "company": name,
            "location": ", ".join(p for p in (j.get("city"), j.get("country")) if p) or ("Remote" if j.get("remote") else ""),
            "description": text, "url": j.get("careers_url") or j.get("careers_apply_url"),
            "published": j.get("published_at"), "remote": j.get("remote"),
            "work_mode": "hybrid" if j.get("hybrid") else None,
            "salary_min": sal.get("min"), "salary_max": sal.get("max"), "salary_currency": sal.get("currency"),
            "tags": [t for t in (j.get("department"), j.get("employment_type_code")) if t],
        }, "recruitee"))
    return rows


async def _teamtailor(slug: str, name: str, q: SearchQuery) -> Rows:
    feed = feedparser.parse(await get_text(f"https://{slug}.teamtailor.com/jobs.rss"))
    rows = []
    for e in feed.entries:
        body = html_to_text(e.get("summary"))
        if matches(q.text, e.get("title"), body):
            rows.append(normalize_job({
                "id": e.get("id") or e.get("link"), "title": e.get("title"), "company": name,
                "location": e.get("tt_location") or e.get("location") or "", "description": body,
                "url": e.get("link"), "published": e.get("published"),
            }, "teamtailor"))
    return rows


# --- scrape tier: undocumented career-site JSON ----------------------------------------------------

async def _rippling(slug: str, name: str, q: SearchQuery) -> Rows:
    data = await get_json(f"https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs")
    return [normalize_job({
        "id": j.get("uuid"), "title": j.get("name"), "company": name,
        "location": (j.get("workLocation") or {}).get("label"), "url": j.get("url"),
        "tags": [(j.get("department") or {}).get("label")] if (j.get("department") or {}).get("label") else [],
    }, "rippling") for j in data if matches(q.text, j.get("name"), (j.get("department") or {}).get("label"))]


async def _workday(key: str, name: str, q: SearchQuery) -> Rows:
    host, _, site = key.partition("|")
    tenant = host.split(".")[0]
    base = f"https://{host}.myworkdayjobs.com"
    res = await request("POST", f"{base}/wday/cxs/{tenant}/{site}/jobs",
                        json={"limit": 20, "offset": 0, "searchText": q.text, "appliedFacets": {}})
    return [normalize_job({
        "id": j.get("externalPath"), "title": j.get("title"), "company": name, "location": j.get("locationsText"),
        "url": f"{base}/en-US/{site}{j.get('externalPath', '')}",
        "tags": [b for b in j.get("bulletFields") or [] if isinstance(b, str)],
    }, "workday") for j in res.json().get("jobPostings", [])]


SOURCES: tuple[CallableSource, ...] = (
    CallableSource("greenhouse", Tier.PUBLIC_FEED,
                   _per_company("greenhouse", _ats_scraper_fetch("_fetch_greenhouse"), _ats_scraper_companies("GREENHOUSE_COMPANIES")),
                   description="Greenhouse boards (~100 companies, src/scrapers/ats_scraper.py)"),
    CallableSource("lever", Tier.PUBLIC_FEED,
                   _per_company("lever", _ats_scraper_fetch("_fetch_lever"), _ats_scraper_companies("LEVER_COMPANIES")),
                   description="Lever boards"),
    CallableSource("ashby", Tier.PUBLIC_FEED, _per_company("ashby", _ashby), description="Ashby boards (ats_boards.yml)"),
    CallableSource("workable", Tier.PUBLIC_FEED, _per_company("workable", _workable), description="Workable boards"),
    CallableSource("smartrecruiters", Tier.PUBLIC_FEED, _per_company("smartrecruiters", _smartrecruiters),
                   description="SmartRecruiters boards"),
    CallableSource("recruitee", Tier.PUBLIC_FEED, _per_company("recruitee", _recruitee), description="Recruitee boards"),
    CallableSource("teamtailor", Tier.PUBLIC_FEED, _per_company("teamtailor", _teamtailor), description="Teamtailor boards (RSS)"),
    CallableSource("rippling", Tier.SCRAPE, _per_company("rippling", _rippling), description="Rippling boards (undocumented JSON)"),
    CallableSource("workday", Tier.SCRAPE, _per_company("workday", _workday), description="Workday career sites (undocumented JSON)"),
)
