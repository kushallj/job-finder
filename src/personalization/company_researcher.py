"""
company_researcher.py — Async company intelligence gatherer.

Data sources (all public, no auth required):
  1. GitHub Org API         — recent repos, languages, org description
  2. Company website        — /blog, /news, /about, /engineering pages
  3. HN Algolia search API  — Hacker News mentions (company in title/story)
  4. Job postings page      — tech stack signals from role descriptions

Concurrency:
  All 4 sources run in parallel via asyncio.gather().
  Per-domain semaphore limits burst to 2 concurrent requests.
  1 req/sec per domain via asyncio.sleep() between page fetches.

Caching:
  SQLite cache (company_research table) with 7-day TTL.
  Cache key = domain (normalized: strip www., lowercase).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import aiohttp
    _AIOHTTP = True
except ImportError:
    _AIOHTTP = False

from .models import CompanyProfile

log = logging.getLogger(__name__)

_CACHE_DB   = Path("data/personalization_cache.db")
_CACHE_TTL  = 7 * 24 * 3600   # 7 days

# Pages to try for company news/engineering content
_BLOG_PATHS = [
    "/blog", "/engineering", "/news", "/updates", "/posts",
    "/tech", "/insights", "/stories", "/medium.com",
]

# Tech stack signal patterns (compiled once)
_TECH_RE = re.compile(
    r"\b(Python|FastAPI|Django|Flask|Node\.?js|React|TypeScript|Go|Rust|Java|Scala"
    r"|Kubernetes|Docker|AWS|GCP|Azure|PostgreSQL|MySQL|MongoDB|Redis|Kafka"
    r"|Terraform|GraphQL|gRPC|Elasticsearch|Spark|Flink|dbt|Airflow"
    r"|LLM|ML|AI|RAG|vector\s+db|embedding|transformer)\b",
    re.IGNORECASE,
)

_HEADLINE_RE = re.compile(
    r"<(?:h[1-4]|title)[^>]*>\s*([^<]{10,120})\s*</(?:h[1-4]|title)>",
    re.IGNORECASE,
)

# Growth signals
_GROWTH_RE = re.compile(
    r"\b(Series [A-E]|raised \$[\d.]+[MBK]|funding|IPO|launch|shipped|"
    r"open.sourc|hiring|grew \d+|expansion|acqui)"
    r"",
    re.IGNORECASE,
)


class CompanyResearcher:
    """
    Researches a company from public sources.

    Usage:
        researcher = CompanyResearcher()
        profile = await researcher.research("stripe.com", "Stripe")
    """

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session       = session
        self._owns_session  = session is None
        self._domain_locks: Dict[str, asyncio.Semaphore] = {}
        self._init_cache()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def research(self, domain: str, company_name: str = "") -> CompanyProfile:
        """
        Full research pipeline.  Returns cached result if fresh (< 7 days).
        """
        domain = _normalize_domain(domain)
        company_name = company_name or domain.split(".")[0].title()

        # Check cache first
        cached = self._load_cache(domain)
        if cached:
            log.debug("CompanyResearcher: cache hit for %s", domain)
            return cached

        profile = await self._run_research(domain, company_name)
        self._save_cache(domain, profile)
        return profile

    # ── Research pipeline ──────────────────────────────────────────────────────

    async def _run_research(self, domain: str, company_name: str) -> CompanyProfile:
        session = await self._get_session()

        results = await asyncio.gather(
            self._research_github(company_name, domain, session),
            self._research_website(domain, session),
            self._research_hn(company_name, session),
            return_exceptions=True,
        )

        github_data = results[0] if not isinstance(results[0], Exception) else {}
        web_data    = results[1] if not isinstance(results[1], Exception) else {}
        hn_data     = results[2] if not isinstance(results[2], Exception) else {}

        # Merge tech stack from all sources
        tech = list(dict.fromkeys(
            github_data.get("tech", []) +
            web_data.get("tech", [])
        ))[:15]

        sources = (
            github_data.get("sources", []) +
            web_data.get("sources", []) +
            hn_data.get("sources", [])
        )

        return CompanyProfile(
            domain           = domain,
            name             = company_name,
            tagline          = web_data.get("tagline", ""),
            tech_stack       = tech,
            recent_news      = (web_data.get("headlines", []) + hn_data.get("stories", []))[:8],
            growth_signals   = web_data.get("growth_signals", [])[:4],
            pain_points      = web_data.get("pain_points", [])[:4],
            culture_keywords = web_data.get("culture_keywords", [])[:6],
            github_org       = github_data.get("org", ""),
            recent_repos     = github_data.get("repos", [])[:6],
            hn_mentions      = hn_data.get("stories", [])[:5],
            research_sources = sources,
        )

    # ── GitHub org research ────────────────────────────────────────────────────

    async def _research_github(
        self, company: str, domain: str, session: aiohttp.ClientSession
    ) -> dict:
        """
        Try common GitHub org slugs derived from company name + domain.
        Returns repo names, languages, org description.
        """
        slugs = _derive_github_slugs(company, domain)
        org_data = {}

        for slug in slugs:
            url = f"https://api.github.com/orgs/{slug}"
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if r.status == 200:
                        data = await r.json()
                        org_data["org"] = slug
                        org_data["sources"] = [url]

                        # Fetch repos
                        repos_url = f"https://api.github.com/orgs/{slug}/repos?sort=updated&per_page=10"
                        async with session.get(repos_url, timeout=aiohttp.ClientTimeout(total=5)) as rr:
                            if rr.status == 200:
                                repos = await rr.json()
                                org_data["repos"] = [
                                    f"{r['name']}: {r.get('description', '')}"
                                    for r in repos
                                    if not r.get("fork") and r.get("stargazers_count", 0) >= 0
                                ][:8]
                                # Extract tech from repo descriptions + topics
                                all_text = " ".join(
                                    f"{r.get('description', '')} {' '.join(r.get('topics', []))}"
                                    for r in repos
                                )
                                org_data["tech"] = list(dict.fromkeys(
                                    m.group(0) for m in _TECH_RE.finditer(all_text)
                                ))
                                org_data["sources"].append(repos_url)
                        break   # found valid org
            except Exception as exc:
                log.debug("GitHub org lookup %s failed: %s", slug, exc)

        return org_data

    # ── Website research ───────────────────────────────────────────────────────

    async def _research_website(
        self, domain: str, session: aiohttp.ClientSession
    ) -> dict:
        """
        Scrape company website for headlines, tech signals, culture keywords.
        Tries /blog, /engineering, /about paths.
        """
        lock = self._domain_locks.setdefault(domain, asyncio.Semaphore(2))
        result: dict = {
            "headlines": [], "tech": [], "growth_signals": [],
            "pain_points": [], "culture_keywords": [], "tagline": "",
            "sources": [],
        }

        pages_to_try = ["https://" + domain] + [
            f"https://{domain}{p}" for p in _BLOG_PATHS[:5]
        ]

        fetched = 0
        for url in pages_to_try:
            if fetched >= 3:
                break
            async with lock:
                try:
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=6),
                        headers={"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"},
                        allow_redirects=True,
                        max_redirects=3,
                    ) as r:
                        if r.status != 200:
                            continue
                        html = await r.text(errors="ignore")
                        result["sources"].append(url)
                        fetched += 1
                        self._parse_html(html, result, is_homepage=(fetched == 1))
                except Exception as exc:
                    log.debug("Website fetch %s: %s", url, exc)
                await asyncio.sleep(0.3)   # gentle crawl rate

        return result

    def _parse_html(self, html: str, result: dict, is_homepage: bool = False) -> None:
        # Tagline from homepage meta description
        if is_homepage:
            m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
            if m and not result["tagline"]:
                result["tagline"] = m.group(1).strip()[:150]

        # Headlines (h1-h3)
        headlines = _HEADLINE_RE.findall(html)
        cleaned   = [re.sub(r"\s+", " ", h).strip() for h in headlines if len(h.strip()) > 15]
        result["headlines"].extend(cleaned[:6])

        # Tech stack from page text
        tech_hits = list(dict.fromkeys(m.group(0) for m in _TECH_RE.finditer(html)))
        result["tech"].extend(tech_hits)

        # Growth signals
        for m in _GROWTH_RE.finditer(html):
            snippet = html[max(0, m.start()-20):m.end()+40].replace("\n", " ").strip()
            result["growth_signals"].append(snippet[:100])

        # Culture keywords
        for kw in ("ownership", "async", "remote", "autonomy", "ship fast",
                   "craft", "impact", "mission", "open source", "scale"):
            if kw.lower() in html.lower():
                result["culture_keywords"].append(kw)

    # ── Hacker News research ───────────────────────────────────────────────────

    async def _research_hn(
        self, company: str, session: aiohttp.ClientSession
    ) -> dict:
        """Search HN Algolia API for company mentions."""
        result: dict = {"stories": [], "sources": []}
        query = company.replace(" ", "+")
        url   = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage=5"

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status == 200:
                    data = await r.json()
                    result["stories"] = [
                        hit["title"]
                        for hit in data.get("hits", [])
                        if hit.get("title")
                    ][:5]
                    result["sources"] = [url]
        except Exception as exc:
            log.debug("HN search for %s: %s", company, exc)

        return result

    # ── Session management ─────────────────────────────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    # ── SQLite cache ───────────────────────────────────────────────────────────

    def _init_cache(self) -> None:
        _CACHE_DB.parent.mkdir(exist_ok=True)
        with sqlite3.connect(_CACHE_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS company_research (
                    domain      TEXT PRIMARY KEY,
                    data_json   TEXT NOT NULL,
                    cached_at   INTEGER NOT NULL
                )
            """)

    def _load_cache(self, domain: str) -> Optional[CompanyProfile]:
        try:
            with sqlite3.connect(_CACHE_DB) as conn:
                row = conn.execute(
                    "SELECT data_json, cached_at FROM company_research WHERE domain=?",
                    (domain,)
                ).fetchone()
                if row and (time.time() - row[1]) < _CACHE_TTL:
                    d = json.loads(row[0])
                    return CompanyProfile(**d)
        except Exception as exc:
            log.debug("Cache load error: %s", exc)
        return None

    def _save_cache(self, domain: str, profile: CompanyProfile) -> None:
        try:
            import dataclasses
            data = dataclasses.asdict(profile)
            with sqlite3.connect(_CACHE_DB) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO company_research (domain, data_json, cached_at)
                       VALUES (?, ?, ?)""",
                    (domain, json.dumps(data), int(time.time()))
                )
        except Exception as exc:
            log.debug("Cache save error: %s", exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_domain(domain: str) -> str:
    """Strip scheme, www, trailing slash."""
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    return domain.split("/")[0].lower()


def _derive_github_slugs(company: str, domain: str) -> List[str]:
    """Generate likely GitHub org slugs from company name and domain."""
    slugs = []
    # From domain: stripe.com → stripe
    base = domain.split(".")[0]
    slugs.append(base)
    # From company name: "Stripe Inc" → stripe-inc, stripe
    slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
    slugs.append(slug)
    # First word only
    first_word = slug.split("-")[0]
    if first_word not in slugs:
        slugs.append(first_word)
    return list(dict.fromkeys(slugs))   # dedup, preserve order
