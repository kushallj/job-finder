"""
ats_scraper.py — Direct Greenhouse & Lever ATS API integration.

Both platforms expose public, unauthenticated REST APIs for all open job
postings. This bypasses every job board entirely: no Naukri, no LinkedIn,
no bot detection, no rate limits — just clean JSON straight from the company.

Greenhouse: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
Lever:      https://api.lever.co/v0/postings/{slug}?mode=json

How it works:
  1. Query all known companies concurrently (asyncio.gather, max 30 concurrent)
  2. Filter by keyword match against title (high weight) + description (low weight)
  3. Normalize to the same dict format every other scraper in this project uses
  4. 404 / connection errors are silently skipped — the list self-heals

Adding more companies: just append to GREENHOUSE_COMPANIES or LEVER_COMPANIES.
Find the slug from the company's careers URL:
  https://boards.greenhouse.io/{slug}  or  https://jobs.lever.co/{slug}
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import httpx

log = logging.getLogger(__name__)

# ── Concurrency cap — stay friendly to both ATS platforms ────────────────────
_MAX_CONCURRENT = 30
_TIMEOUT        = httpx.Timeout(15.0, connect=8.0)

# ─────────────────────────────────────────────────────────────────────────────
# Company registry
# Format: (slug, display_name)
# ─────────────────────────────────────────────────────────────────────────────

GREENHOUSE_COMPANIES: List[Tuple[str, str]] = [
    # ── India — Fintech ───────────────────────────────────────────────────────
    ("razorpay",        "Razorpay"),
    ("cred",            "CRED"),
    ("groww",           "Groww"),
    ("slice",           "Slice"),
    ("jupiter",         "Jupiter"),
    ("smallcase",       "Smallcase"),
    ("cashfree",        "Cashfree Payments"),
    ("setu",            "Setu"),
    ("ofbusiness",      "OfBusiness"),
    ("creditbook",      "CreditBook"),
    ("freo",            "Freo"),
    ("zeta-tech",       "Zeta"),
    ("coinswitch",      "CoinSwitch"),
    ("wazirx",          "WazirX"),
    ("unocoin",         "Unocoin"),

    # ── India — SaaS / DevTools ───────────────────────────────────────────────
    ("freshworks",      "Freshworks"),
    ("chargebee",       "Chargebee"),
    ("browserstack",    "BrowserStack"),
    ("postman",         "Postman"),
    ("clevertap",       "CleverTap"),
    ("moengage",        "MoEngage"),
    ("exotel",          "Exotel"),
    ("khatabook",       "Khatabook"),
    ("zoho",            "Zoho"),
    ("hasura",          "Hasura"),
    ("rudderstack",     "RudderStack"),
    ("highlight",       "Highlight"),
    ("sprinklr",        "Sprinklr"),
    ("capillarytech",   "Capillary Technologies"),
    ("unicommerce",     "Unicommerce"),
    ("shipbob",         "ShipBob"),

    # ── India — E-commerce / Logistics ───────────────────────────────────────
    ("meesho",          "Meesho"),
    ("shiprocket",      "Shiprocket"),
    ("delhivery",       "Delhivery"),
    ("shadowfax",       "Shadowfax"),
    ("ecomexpress",     "Ecom Express"),
    ("moglix",          "Moglix"),
    ("udaan",           "Udaan"),

    # ── India — Ed-Tech / Health ──────────────────────────────────────────────
    ("vedantu",         "Vedantu"),
    ("unacademy",       "Unacademy"),
    ("practo",          "Practo"),
    ("portea",          "Portea Medical"),
    ("healthifyme",     "HealthifyMe"),
    ("mfine",           "mFine"),

    # ── Global — Cloud / Infra ────────────────────────────────────────────────
    ("cloudflare",      "Cloudflare"),
    ("hashicorp",       "HashiCorp"),
    ("mongodb",         "MongoDB"),
    ("elastic",         "Elastic"),
    ("datadog",         "Datadog"),
    ("snowflake",       "Snowflake"),
    ("databricks",      "Databricks"),
    ("confluent",       "Confluent"),
    ("cockroachlabs",   "CockroachDB"),
    ("planetscale",     "PlanetScale"),
    ("supabase",        "Supabase"),
    ("neon",            "Neon"),
    ("turso",           "Turso"),
    ("render",          "Render"),
    ("railway",         "Railway"),
    ("fly",             "Fly.io"),
    ("digitalocean",    "DigitalOcean"),
    ("linode",          "Linode / Akamai"),

    # ── Global — Developer Tools ──────────────────────────────────────────────
    ("github",          "GitHub"),
    ("gitlab",          "GitLab"),
    ("linear",          "Linear"),
    ("notion",          "Notion"),
    ("figma",           "Figma"),
    ("vercel",          "Vercel"),
    ("netlify",         "Netlify"),
    ("prisma",          "Prisma"),
    ("retool",          "Retool"),
    ("airtable",        "Airtable"),
    ("zapier",          "Zapier"),
    ("segment",         "Segment"),
    ("mixpanel",        "Mixpanel"),
    ("amplitude",       "Amplitude"),
    ("posthog",         "PostHog"),

    # ── Global — AI / ML ─────────────────────────────────────────────────────
    ("anthropic",       "Anthropic"),
    ("openai",          "OpenAI"),
    ("huggingface",     "Hugging Face"),
    ("cohere",          "Cohere"),
    ("mistralai",       "Mistral AI"),
    ("scale-ai",        "Scale AI"),
    ("weights-biases",  "Weights & Biases"),
    ("langchain",       "LangChain"),
    ("qdrant",          "Qdrant"),
    ("weaviate",        "Weaviate"),

    # ── Global — Fintech ──────────────────────────────────────────────────────
    ("stripe",          "Stripe"),
    ("brex",            "Brex"),
    ("ramp",            "Ramp"),
    ("mercury",         "Mercury"),
    ("modern-treasury", "Modern Treasury"),
    ("plaid",           "Plaid"),
    ("marqeta",         "Marqeta"),

    # ── Global — Remote-first / High-growth ──────────────────────────────────
    ("remote",          "Remote.com"),
    ("deel",            "Deel"),
    ("rippling",        "Rippling"),
    ("lattice",         "Lattice"),
    ("leapsome",        "Leapsome"),
    ("dbt-labs",        "dbt Labs"),
    ("airbyte",         "Airbyte"),
    ("meltano",         "Meltano"),
    ("prefect",         "Prefect"),
    ("dagster",         "Dagster"),
]

LEVER_COMPANIES: List[Tuple[str, str]] = [
    # ── India ─────────────────────────────────────────────────────────────────
    ("meesho",          "Meesho"),

    # ── Global — Fintech ──────────────────────────────────────────────────────
    ("plaid",           "Plaid"),

    # ── Global — Sales / Revenue Intelligence ─────────────────────────────────
    ("outreach",        "Outreach"),
    ("clari",           "Clari"),
    ("highspot",        "Highspot"),
    ("mindtickle",      "MindTickle"),

    # ── Global — HR / People ─────────────────────────────────────────────────
    ("15five",          "15Five"),

    # ── Global — Health / Consumer ───────────────────────────────────────────
    ("whoop",           "WHOOP"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Keyword filtering
# ─────────────────────────────────────────────────────────────────────────────

def _matches_query(title: str, description: str, query: str) -> bool:
    """Return True if the job is relevant to the search query."""
    query_words = [w.lower() for w in re.split(r'\W+', query) if len(w) > 2]
    if not query_words:
        return True

    title_lower = title.lower()
    desc_lower  = description.lower()[:1000]   # only check first 1000 chars of description

    # Title match → immediate accept
    if any(w in title_lower for w in query_words):
        return True

    # Description: require at least 2 query words
    desc_hits = sum(1 for w in query_words if w in desc_lower)
    return desc_hits >= min(2, len(query_words))


# ─────────────────────────────────────────────────────────────────────────────
# Greenhouse
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_greenhouse(
    client:       httpx.AsyncClient,
    slug:         str,
    display_name: str,
    query:        str,
) -> List[Dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        resp = await client.get(url)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.debug("[Greenhouse] %s (%s): %s", slug, type(exc).__name__, exc)
        return []

    jobs = []
    for j in data.get("jobs", []):
        title       = j.get("title", "").strip()
        description = re.sub(r"<[^>]+>", " ", j.get("content") or "")
        location    = (j.get("location") or {}).get("name", "")

        if not title:
            continue
        if query and not _matches_query(title, description, query):
            continue

        # Parse updated_at
        posted = ""
        raw_date = j.get("updated_at", "")
        if raw_date:
            try:
                posted = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except ValueError:
                posted = raw_date[:10]

        jobs.append({
            "title":       title,
            "company":     display_name,
            "location":    location,
            "url":         j.get("absolute_url", ""),
            "description": description.strip()[:3000],
            "posted_date": posted,
            "salary":      None,
            "job_type":    None,
            "source":      "greenhouse",
            "skills":      [],
        })

    if jobs:
        log.info("[Greenhouse] %-20s → %d matching jobs", slug, len(jobs))
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Lever
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_lever(
    client:       httpx.AsyncClient,
    slug:         str,
    display_name: str,
    query:        str,
) -> List[Dict]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = await client.get(url)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        postings = resp.json()
        if not isinstance(postings, list):
            postings = postings.get("postings", [])
    except Exception as exc:
        log.debug("[Lever] %s (%s): %s", slug, type(exc).__name__, exc)
        return []

    jobs = []
    for p in postings:
        title       = p.get("text", "").strip()
        description = (p.get("descriptionPlain") or
                       re.sub(r"<[^>]+>", " ", p.get("description") or ""))
        categories  = p.get("categories") or {}
        location    = categories.get("location") or categories.get("allLocations", [""])[0] \
                      if isinstance(categories.get("allLocations"), list) else ""

        if not title:
            continue
        if query and not _matches_query(title, description, query):
            continue

        # createdAt is unix ms
        posted = ""
        raw_ts = p.get("createdAt")
        if raw_ts:
            try:
                posted = datetime.fromtimestamp(raw_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                pass

        jobs.append({
            "title":       title,
            "company":     display_name,
            "location":    str(location),
            "url":         p.get("hostedUrl", ""),
            "description": description.strip()[:3000],
            "posted_date": posted,
            "salary":      None,
            "job_type":    None,
            "source":      "lever",
            "skills":      [],
        })

    if jobs:
        log.info("[Lever]      %-20s → %d matching jobs", slug, len(jobs))
    return jobs


# ─────────────────────────────────────────────────────────────────────────────
# Public scraper class
# ─────────────────────────────────────────────────────────────────────────────

class ATSScraper:
    """
    Queries Greenhouse and Lever ATS APIs directly.

    Usage:
        scraper = ATSScraper()
        jobs = await scraper.search("javascript engineer")
    """

    async def search(
        self,
        query:    str = "",
        location: str = "",          # noqa: ARG002 — ATS APIs don't filter by location
        timeout:  float = 30.0,
    ) -> List[Dict]:
        """
        Fetch all matching jobs from all registered companies.

        Args:
            query:    Search term. Empty string returns everything.
            location: Informational only — used as a hint for logging.
            timeout:  Hard wall-clock timeout for the entire operation.

        Returns:
            List of normalized job dicts.
        """
        log.info("[ATS] Searching %d Greenhouse + %d Lever companies for '%s'",
                 len(GREENHOUSE_COMPANIES), len(LEVER_COMPANIES), query)

        sem    = asyncio.Semaphore(_MAX_CONCURRENT)
        client = httpx.AsyncClient(timeout=_TIMEOUT, http2=False,
                                   headers={"User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)"})

        async def _gh(slug: str, name: str) -> List[Dict]:
            async with sem:
                return await _fetch_greenhouse(client, slug, name, query)

        async def _lv(slug: str, name: str) -> List[Dict]:
            async with sem:
                return await _fetch_lever(client, slug, name, query)

        tasks = (
            [_gh(slug, name) for slug, name in GREENHOUSE_COMPANIES] +
            [_lv(slug, name) for slug, name in LEVER_COMPANIES]
        )

        try:
            async with client:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout,
                )
        except asyncio.TimeoutError:
            log.warning("[ATS] Timed out after %.0fs", timeout)
            return []

        jobs: List[Dict] = []
        errors = 0
        for r in results:
            if isinstance(r, list):
                jobs.extend(r)
            elif isinstance(r, Exception):
                errors += 1

        log.info("[ATS] Done — %d jobs from ATS APIs (%d errors ignored)", len(jobs), errors)
        return jobs
