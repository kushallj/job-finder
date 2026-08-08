"""
firecrawl_scraper.py — Firecrawl-powered career page scraper for top Indian startups.

Unlike ats_scraper.py (which only works for companies on Greenhouse/Lever's public
APIs), this scraper works on *any* career page regardless of what it's built with —
Workday, Darwinbox, a custom Next.js page, whatever. Firecrawl renders the page
(handles JS-heavy SPAs) and returns clean content we can extract structured job
data from.

Strategy, same "cascade with graceful degradation" pattern used elsewhere in this
repo (see ContactFinder in src/contact_finder.py):

  1. Scrape the known/guessed careers URL for each company using Firecrawl's
     structured `json` extraction (schema-guided — asks Firecrawl's own LLM step
     to pull out job listings as structured JSON).
  2. If that returns nothing (page moved, guess was wrong, extraction failed),
     fall back to Firecrawl's `/v1/search` to find the real careers URL and
     retry once.
  3. If still nothing, skip the company and move on — one dead link never
     blocks the other 99 companies (asyncio.gather + semaphore, not a for-loop).

No new SDK dependency: calls the Firecrawl REST API directly over httpx, the same
way ats_scraper.py, contact_finder.py etc. talk to their APIs in this repo.

Setup:
  1. Get a key: https://www.firecrawl.dev/app/api-keys
  2. Add to .env:  FIRECRAWL_API_KEY=fc-...
  3. python -m src.cli firecrawl-scan          # scan all 100 companies
     python -m src.cli firecrawl-scan --query "backend engineer"
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from src.scrapers.base import BaseScraper

log = logging.getLogger(__name__)

FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"
_MAX_CONCURRENT = 8          # be polite — this hits both Firecrawl's API and 100 target sites
_SCRAPE_TIMEOUT = 45.0
_SEARCH_TIMEOUT = 20.0

# ─────────────────────────────────────────────────────────────────────────────
# Top ~100 Indian startups — (display_name, best-guess careers URL)
#
# These URLs are best-effort guesses based on common company career-page
# conventions. Startups change ATS platforms and URL structures often, so a
# guess going stale here is expected, not a bug — that's exactly why every
# entry falls through to the Firecrawl search-based rediscovery step below
# rather than being treated as ground truth.
# ─────────────────────────────────────────────────────────────────────────────

TOP_INDIAN_STARTUPS: List[Tuple[str, str]] = [
    # ── Fintech ────────────────────────────────────────────────────────────
    ("PhonePe",              "https://www.phonepe.com/careers/"),
    ("Paytm",                "https://paytm.com/careers"),
    ("CRED",                 "https://careers.cred.club/"),
    ("Razorpay",             "https://razorpay.com/jobs/"),
    ("Groww",                "https://groww.in/careers"),
    ("Zerodha",              "https://zerodha.com/careers/"),
    ("BharatPe",             "https://bharatpe.com/careers/"),
    ("Slice",                "https://sliceit.com/careers"),
    ("Jupiter",              "https://jupiter.money/careers/"),
    ("Smallcase",            "https://smallcase.com/careers"),
    ("Cashfree Payments",    "https://www.cashfree.com/careers/"),
    ("Setu",                 "https://setu.co/careers/"),
    ("OfBusiness",           "https://www.ofbusiness.com/careers"),
    ("Acko",                 "https://www.acko.com/careers/"),
    ("Digit Insurance",      "https://www.godigit.com/careers"),
    ("PolicyBazaar",         "https://www.policybazaar.com/careers/"),
    ("Vyapar",               "https://vyaparapp.in/careers"),
    ("Open Financial Tech",  "https://open.money/careers"),
    ("KreditBee",            "https://www.kreditbee.in/careers"),
    ("Freo",                 "https://freo.money/careers"),

    # ── Foodtech / Quick Commerce ──────────────────────────────────────────
    ("Zomato",                "https://www.zomato.com/careers"),
    ("Swiggy",                "https://careers.swiggy.com/"),
    ("Zepto",                 "https://www.zeptonow.com/careers"),
    ("Blinkit",               "https://blinkit.com/careers"),
    ("Rebel Foods",           "https://www.rebelfoods.com/careers"),
    ("Licious",               "https://www.licious.in/careers"),
    ("BigBasket",             "https://www.bigbasket.com/careers/"),

    # ── Edtech ─────────────────────────────────────────────────────────────
    ("BYJU'S",                "https://byjus.com/careers/"),
    ("Unacademy",             "https://unacademy.com/careers"),
    ("upGrad",                "https://www.upgrad.com/careers/"),
    ("Vedantu",               "https://www.vedantu.com/careers"),
    ("Toppr",                 "https://www.toppr.com/careers/"),
    ("PhysicsWallah",         "https://www.pw.live/careers"),
    ("Simplilearn",           "https://www.simplilearn.com/careers"),
    ("Testbook",              "https://testbook.com/careers"),
    ("Scaler",                "https://www.scaler.com/careers/"),

    # ── Healthtech ─────────────────────────────────────────────────────────
    ("Practo",                "https://www.practo.com/company/careers"),
    ("PharmEasy",             "https://pharmeasy.in/careers/"),
    ("Tata 1mg",              "https://www.1mg.com/careers"),
    ("Cult.fit",              "https://www.cult.fit/careers"),
    ("HealthifyMe",           "https://www.healthifyme.com/careers/"),
    ("Pristyn Care",          "https://www.pristyncare.com/careers"),
    ("Innovaccer",            "https://innovaccer.com/careers"),

    # ── SaaS / DevTools / B2B ──────────────────────────────────────────────
    ("Freshworks",            "https://www.freshworks.com/company/careers/"),
    ("Chargebee",             "https://www.chargebee.com/careers/"),
    ("BrowserStack",          "https://www.browserstack.com/careers"),
    ("Postman",               "https://www.postman.com/careers/"),
    ("CleverTap",             "https://clevertap.com/careers/"),
    ("MoEngage",              "https://www.moengage.com/careers/"),
    ("Exotel",                "https://exotel.com/careers/"),
    ("Khatabook",             "https://khatabook.com/careers/"),
    ("Zoho",                  "https://www.zoho.com/careers.html"),
    ("Hasura",                "https://hasura.io/careers/"),
    ("RudderStack",           "https://www.rudderstack.com/careers/"),
    ("Sprinklr",              "https://www.sprinklr.com/careers/"),
    ("Capillary Technologies","https://www.capillarytech.com/careers/"),
    ("Unicommerce",           "https://unicommerce.com/careers/"),
    ("Darwinbox",             "https://darwinbox.com/careers"),
    ("Whatfix",               "https://whatfix.com/careers/"),
    ("Zenoti",                "https://www.zenoti.com/careers"),
    ("Netradyne",             "https://netradyne.com/careers/"),
    ("Uniphore",              "https://uniphore.com/careers/"),
    ("Yellow.ai",             "https://yellow.ai/careers/"),
    ("Observe.AI",            "https://www.observe.ai/careers"),
    ("Fractal Analytics",     "https://fractal.ai/careers/"),
    ("Druva",                 "https://www.druva.com/careers/"),
    ("Icertis",               "https://www.icertis.com/careers/"),
    ("SirionLabs",            "https://www.sirion.ai/careers/"),
    ("LeadSquared",           "https://www.leadsquared.com/careers/"),
    ("Wingify",               "https://wingify.com/careers"),
    ("Zoho Corp",             "https://www.zoho.com/careers.html"),

    # ── Gaming ─────────────────────────────────────────────────────────────
    ("Games24x7",             "https://games24x7.com/careers/"),
    ("Dream11",               "https://www.dream11.com/about-us/careers"),
    ("Mobile Premier League", "https://www.mpl.live/careers"),
    ("Nazara Technologies",   "https://www.nazara.com/careers"),
    ("WinZO",                 "https://winzogames.com/careers"),

    # ── Ecommerce / D2C ────────────────────────────────────────────────────
    ("Flipkart",              "https://www.flipkart.com/careers"),
    ("Meesho",                "https://careers.meesho.com/"),
    ("Nykaa",                 "https://www.nykaa.com/careers"),
    ("Lenskart",              "https://www.lenskart.com/careers"),
    ("boAt (Imagine Marketing)","https://www.boat-lifestyle.com/pages/careers"),
    ("Cars24",                "https://www.cars24.com/careers/"),
    ("Urban Company",         "https://www.urbancompany.com/careers"),
    ("FirstCry",              "https://www.firstcry.com/careers"),
    ("Mensa Brands",          "https://mensabrands.com/careers"),
    ("GlobalBees",            "https://globalbees.com/careers"),
    ("Wakefit",               "https://www.wakefit.co/careers"),
    ("Mamaearth (Honasa)",    "https://www.mamaearth.in/careers"),
    ("Sugar Cosmetics",       "https://in.sugarcosmetics.com/pages/careers"),
    ("Purplle",               "https://www.purplle.com/careers"),

    # ── Mobility / Logistics / EV ──────────────────────────────────────────
    ("Ola",                   "https://www.olacabs.com/careers"),
    ("Ola Electric",          "https://www.olaelectric.com/careers"),
    ("Ather Energy",          "https://www.atherenergy.com/careers"),
    ("Rapido",                "https://rapido.bike/careers"),
    ("Porter",                "https://porter.in/careers"),
    ("Delhivery",             "https://www.delhivery.com/careers/"),
    ("Shiprocket",            "https://www.shiprocket.in/careers/"),
    ("Zetwerk",               "https://www.zetwerk.com/careers"),
    ("ElasticRun",            "https://elastic.run/careers/"),
    ("Udaan",                 "https://udaan.com/careers"),
    ("Infra.Market",          "https://infra.market/careers"),

    # ── Media / Misc ───────────────────────────────────────────────────────
    ("Dunzo",                 "https://www.dunzo.com/careers"),
    ("InMobi",                "https://www.inmobi.com/company/careers"),
    ("ShareChat",             "https://sharechat.com/careers"),
    ("Dailyhunt",             "https://careers.dailyhunt.in/"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Firecrawl API client
# ─────────────────────────────────────────────────────────────────────────────

# Schema Firecrawl's extraction step is asked to fill in for each page.
_JOB_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "jobs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "location": {"type": "string"},
                    "department": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["title"],
            },
        }
    },
    "required": ["jobs"],
}

_EXTRACTION_PROMPT = (
    "Extract every open job listing on this careers page. For each job return "
    "its title, location (if shown), department/team (if shown), and the direct "
    "URL to the job posting if there is a link. Ignore navigation links, "
    "footer content, and anything that isn't an actual open role."
)

# Loose heuristics used only when structured extraction comes back empty —
# looks for markdown links whose text reads like a job title.
_JOB_LINK_RE = re.compile(
    r"\[([^\]]{4,120})\]\((https?://[^\s)]+)\)"
)
_TITLE_HINT_RE = re.compile(
    r"\b(engineer|developer|manager|analyst|designer|lead|intern|associate|"
    r"specialist|scientist|architect|director|head of|vp\b|product|sales|"
    r"marketing|recruiter|hr\b)",
    re.IGNORECASE,
)


class FirecrawlCareerScraper(BaseScraper):
    """
    Scrapes career pages for the top Indian startups using Firecrawl.

    Usage:
        scraper = FirecrawlCareerScraper(api_key=settings.firecrawl_api_key)
        jobs = await scraper.search(query="backend engineer")
        await scraper.close()
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("firecrawl_careers")
        self.api_key = api_key
        self._http = httpx.AsyncClient(
            base_url=FIRECRAWL_BASE_URL,
            timeout=httpx.Timeout(_SCRAPE_TIMEOUT, connect=10.0),
            headers=self._headers(),
        )

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    # ── Public API ────────────────────────────────────────────────────────

    async def fetch_jobs(self, **kwargs) -> List[Dict]:
        """BaseScraper-compatible alias for search()."""
        return await self.search(**kwargs)

    async def search(
        self,
        query: str = "",
        location: str = "",
        max_results: int = 1000,
        companies: Optional[List[Tuple[str, str]]] = None,
    ) -> List[Dict]:
        """
        Scrape every company's career page concurrently and return normalized
        job dicts. `query` is an optional keyword filter applied to the title
        (empty string returns everything found).

        Matches the UnifiedScraperInterface.search() signature used by
        src/scrapers/orchestrator.py so this can be registered there directly.
        """
        if not self.api_key:
            log.warning(
                "[Firecrawl] No API key configured (FIRECRAWL_API_KEY) — skipping"
            )
            return []

        registry = companies or TOP_INDIAN_STARTUPS
        log.info("[Firecrawl] Scanning %d company career pages", len(registry))

        sem = asyncio.Semaphore(_MAX_CONCURRENT)

        async def _bounded(name: str, url: str) -> List[Dict]:
            async with sem:
                return await self._scrape_one_company(name, url, query, location)

        results = await asyncio.gather(
            *[_bounded(name, url) for name, url in registry],
            return_exceptions=True,
        )

        all_jobs: List[Dict] = []
        errors = 0
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)
            elif isinstance(r, Exception):
                errors += 1
                log.debug("[Firecrawl] Company scrape failed: %s", r)

        log.info(
            "[Firecrawl] Done — %d jobs from %d companies (%d companies errored)",
            len(all_jobs), len(registry), errors,
        )
        return all_jobs[:max_results]

    # ── Per-company scrape ───────────────────────────────────────────────

    async def _scrape_one_company(
        self, company: str, url: str, query: str, location: str
    ) -> List[Dict]:
        jobs = await self._scrape_url(company, url)

        if not jobs:
            # Guessed URL was wrong or page had no extractable jobs —
            # try to rediscover the real careers page via Firecrawl search.
            discovered_url = await self._discover_careers_url(company)
            if discovered_url and discovered_url != url:
                jobs = await self._scrape_url(company, discovered_url)

        if not jobs:
            return []

        if query:
            q = query.lower()
            jobs = [j for j in jobs if q in j["title"].lower()]

        if location:
            loc = location.lower()
            jobs = [
                j for j in jobs
                if not j.get("location") or loc in j["location"].lower()
            ]

        return jobs

    async def _scrape_url(self, company: str, url: str) -> List[Dict]:
        """Call Firecrawl /v1/scrape with structured extraction, with a
        markdown-heuristic fallback if extraction comes back empty."""
        payload = {
            "url": url,
            "formats": ["json", "markdown"],
            "onlyMainContent": True,
            "json": {
                "schema": _JOB_EXTRACTION_SCHEMA,
                "prompt": _EXTRACTION_PROMPT,
            },
            "timeout": int(_SCRAPE_TIMEOUT * 1000),
        }
        try:
            resp = await self._http.post("/scrape", json=payload)
        except httpx.HTTPError as exc:
            log.debug("[Firecrawl] Request failed for %s (%s): %s", company, url, exc)
            return []

        if resp.status_code != 200:
            log.debug(
                "[Firecrawl] %s → HTTP %d for %s", company, resp.status_code, url
            )
            return []

        try:
            body = resp.json()
        except ValueError:
            return []

        data = body.get("data", body)

        # Preferred path: structured extraction worked.
        extracted = (data.get("json") or {}).get("jobs") if isinstance(data.get("json"), dict) else None
        raw_jobs = extracted or []

        if not raw_jobs:
            # Fallback: heuristically parse job-looking links out of markdown.
            markdown = data.get("markdown") or ""
            raw_jobs = self._extract_jobs_from_markdown(markdown)

        return [
            self._normalize(company, url, job)
            for job in raw_jobs
            if job.get("title")
        ]

    @staticmethod
    def _extract_jobs_from_markdown(markdown: str) -> List[Dict]:
        """Last-resort extraction: find markdown links whose text reads like
        a job title. Cheap, no extra API call, good enough as a fallback."""
        found = []
        for text, link in _JOB_LINK_RE.findall(markdown):
            if _TITLE_HINT_RE.search(text):
                found.append({"title": text.strip(), "url": link})
        return found

    def _normalize(self, company: str, source_url: str, job: Dict) -> Dict:
        job_url = job.get("url") or source_url
        # Firecrawl sometimes returns relative links from markdown parsing.
        if job_url.startswith("/"):
            root = re.match(r"(https?://[^/]+)", source_url)
            job_url = f"{root.group(1)}{job_url}" if root else job_url

        normalized = {
            "title": str(job.get("title", "")).strip()[:200],
            "company": company,
            "location": str(job.get("location") or "India").strip()[:200],
            "url": job_url,
            "description": str(job.get("department") or "").strip(),
            "posted_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "salary": None,
            "job_type": None,
            "source": self.source_name,
            "skills": [],
        }
        return self.normalize_job(normalized)

    async def _discover_careers_url(self, company: str) -> Optional[str]:
        """Use Firecrawl's search endpoint to relocate a company's careers
        page when our guessed URL turns out to be stale or wrong."""
        payload = {"query": f"{company} careers open positions", "limit": 3}
        try:
            resp = await self._http.post(
                "/search", json=payload, timeout=_SEARCH_TIMEOUT
            )
        except httpx.HTTPError:
            return None

        if resp.status_code != 200:
            return None

        try:
            body = resp.json()
        except ValueError:
            return None

        results = body.get("data") or []
        for r in results:
            url = r.get("url", "")
            if "career" in url.lower() or "job" in url.lower():
                return url
        return results[0].get("url") if results else None

    # ── Cleanup ──────────────────────────────────────────────────────────

    async def close(self):
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False
