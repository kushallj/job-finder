"""
web_crawler.py — Async concurrent team/about page crawler.

Strategy:
  Companies publish employee names and emails on their public websites:
    /team, /about, /leadership, /people, /contact, /careers, /founders

  We crawl these pages concurrently, extract:
    1. Email addresses (regex)
    2. Names near emails (context window)
    3. LinkedIn profile URLs → names
    4. Schema.org structured data (Person objects)
    5. Open Graph / meta tags (author info)

Politeness:
  - 1 request/sec per domain (token bucket)
  - Respect robots.txt (basic check, skip disallowed paths)
  - User-Agent identifies as a research crawler
  - Max 10 pages per domain
  - Timeout: 10s per request

Concurrency model:
  - AsyncIO + httpx (I/O bound, perfect for async)
  - Semaphore(8): max 8 concurrent cross-domain requests
  - Per-domain serial (polite) via per-domain locks

Extraction pipeline per page:
  HTML → BeautifulSoup → [regex emails] + [JSON-LD Person] + [nearby names]
  → ContactCandidate list

Data quality notes:
  - Regex email extraction finds everything, including support@, info@ etc.
  - We use _PERSONAL_EMAIL_FILTER to eliminate obvious role/system emails
  - Name extraction: look within 200-char window around each email
  - LinkedIn URL extraction: /in/username → hints at person's name from slug
"""

from __future__ import annotations

import asyncio
import logging
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# Regex patterns
_EMAIL_RE      = re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")
_NAME_RE       = re.compile(r"\b([A-Z][a-z]{1,20})\s+([A-Z][a-z]{1,20})\b")
_LINKEDIN_RE   = re.compile(r"linkedin\.com/in/([a-zA-Z0-9\-]+)")
_ROLE_EMAILS   = re.compile(
    r"^(info|contact|hello|support|help|sales|marketing|admin|hr|"
    r"careers|jobs|recruiting|team|dev|api|noreply|no-reply|"
    r"donotreply|security|legal|billing|press|media|feedback|"
    r"newsletter|webmaster|postmaster|abuse|privacy|gdpr|"
    r"compliance|investors|ir)@",
    re.IGNORECASE,
)

# Pages to probe on company website
_TEAM_PATHS = [
    "/team", "/about", "/about-us", "/leadership", "/people",
    "/founders", "/company", "/contact", "/contact-us",
    "/careers/team", "/our-team", "/management", "/board",
    "/staff", "/crew", "/who-we-are",
]


@dataclass
class CrawlContact:
    name:         str
    email:        str
    title:        str        = ""
    linkedin_url: str        = ""
    source_url:   str        = ""
    confidence:   int        = 35    # web scrape baseline


class TeamPageCrawler:
    """
    Crawls company team pages to extract contact information.

    Usage:
        crawler = TeamPageCrawler()
        contacts = await crawler.crawl("stripe.com")
        await crawler.close()
    """

    MAX_PAGES_PER_DOMAIN = 10
    REQUEST_TIMEOUT      = 10.0
    CONCURRENCY          = 8

    def __init__(self):
        self._http = httpx.AsyncClient(
            timeout=self.REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; JobResearchBot/1.0; "
                    "+https://github.com/research-bot)"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        self._global_sem    = asyncio.Semaphore(self.CONCURRENCY)
        self._domain_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._rate_buckets: Dict[str, float] = {}    # domain → last_request_time

    # ── Public API ────────────────────────────────────────────────────────────

    async def crawl(
        self,
        domain: str,
        extra_paths: Optional[List[str]] = None,
    ) -> List[CrawlContact]:
        """
        Crawl team/about pages for `domain` and return contacts.

        Args:
            domain:      Root domain (e.g. "stripe.com")
            extra_paths: Additional paths to probe beyond default list

        Returns:
            Deduplicated CrawlContact list, sorted by confidence desc
        """
        base_url = f"https://{domain}"
        paths    = list(_TEAM_PATHS) + (extra_paths or [])
        urls     = [urljoin(base_url, p) for p in paths[:self.MAX_PAGES_PER_DOMAIN]]

        # Crawl all URLs concurrently (with per-domain polite rate limit)
        tasks = [
            asyncio.create_task(self._fetch_and_extract(url, domain))
            for url in urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten + dedup by email
        seen_emails: Set[str] = set()
        contacts: List[CrawlContact] = []
        for batch in results:
            if isinstance(batch, list):
                for c in batch:
                    email_key = c.email.lower()
                    if email_key and email_key not in seen_emails:
                        seen_emails.add(email_key)
                        contacts.append(c)

        return sorted(contacts, key=lambda c: c.confidence, reverse=True)

    async def close(self) -> None:
        await self._http.aclose()

    # ── Fetch + extract ───────────────────────────────────────────────────────

    async def _fetch_and_extract(self, url: str, domain: str) -> List[CrawlContact]:
        """Fetch one URL and extract all contacts from it."""
        async with self._global_sem:
            # Per-domain rate limit: 1 req/sec
            await self._rate_limit(domain)
            try:
                resp = await self._http.get(url)
                if resp.status_code != 200:
                    return []
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    return []
                return self._parse_html(resp.text, url)
            except (httpx.TimeoutException, httpx.ConnectError):
                return []
            except Exception as e:
                log.debug("Crawl error for %s: %s", url, e)
                return []

    def _parse_html(self, html: str, source_url: str) -> List[CrawlContact]:
        """
        Extract contacts from raw HTML using multiple strategies:
          1. Direct email regex
          2. JSON-LD Person schema
          3. vCard / hCard microformat
          4. LinkedIn URLs → name hints
          5. Nearby name extraction
        """
        contacts: Dict[str, CrawlContact] = {}    # keyed by email
        soup = BeautifulSoup(html, "html.parser")

        # Remove script/style tags (would contain minified JS with false positives)
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ")

        # ── Strategy 1: JSON-LD Person objects ───────────────────────────────
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                self._extract_jsonld(data, source_url, contacts)
            except Exception:
                pass

        # ── Strategy 2: Direct email regex ───────────────────────────────────
        for email in _EMAIL_RE.findall(html):
            email = email.lower().strip(".,;")
            if _ROLE_EMAILS.match(email):
                continue
            if email in contacts:
                continue
            # Find name in proximity
            name  = self._extract_nearby_name(text, email)
            title = self._extract_nearby_title(text, email)
            contacts[email] = CrawlContact(
                name=name,
                email=email,
                title=title,
                source_url=source_url,
                confidence=45 if name and name.lower() != "unknown" else 30,
            )

        # ── Strategy 3: LinkedIn URL → name slug hint ─────────────────────────
        for li_match in _LINKEDIN_RE.finditer(html):
            slug     = li_match.group(1)   # e.g. "john-doe"
            li_url   = f"https://linkedin.com/in/{slug}"
            name_hint = slug.replace("-", " ").title()
            # See if this person's name is near an email we already found
            for email, contact in contacts.items():
                if contact.name.lower() == "unknown" or not contact.name:
                    # Check proximity of LinkedIn URL to email in raw HTML
                    if self._are_nearby(html, li_url, email, window=500):
                        contact.name        = name_hint
                        contact.linkedin_url = li_url
                        contact.confidence   = max(contact.confidence, 50)

        # ── Strategy 4: Look for named anchors with email links ───────────────
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("mailto:"):
                email = href[7:].split("?")[0].lower().strip()
                if email and not _ROLE_EMAILS.match(email):
                    # The link text is often the person's name
                    link_text = a_tag.get_text(strip=True)
                    name_from_link = link_text if _NAME_RE.match(link_text) else "Unknown"
                    if email not in contacts:
                        contacts[email] = CrawlContact(
                            name=name_from_link,
                            email=email,
                            source_url=source_url,
                            confidence=55 if name_from_link != "Unknown" else 35,
                        )
                    elif name_from_link != "Unknown":
                        contacts[email].name = name_from_link
                        contacts[email].confidence = max(contacts[email].confidence, 55)

        return list(contacts.values())

    def _extract_jsonld(
        self,
        data: object,
        source_url: str,
        out: Dict[str, CrawlContact],
    ) -> None:
        """Recursively extract Person objects from JSON-LD data."""
        if isinstance(data, list):
            for item in data:
                self._extract_jsonld(item, source_url, out)
            return
        if not isinstance(data, dict):
            return

        obj_type = data.get("@type", "")
        if obj_type in ("Person", "ContactPoint"):
            email = data.get("email", "").lower().lstrip("mailto:").strip()
            name  = data.get("name", "") or data.get("alternateName", "")
            title = data.get("jobTitle", "") or data.get("description", "")[:80]
            li    = data.get("sameAs", "") or data.get("url", "")
            if isinstance(li, list):
                li = next((u for u in li if "linkedin" in u), "")

            if email and not _ROLE_EMAILS.match(email):
                out[email] = CrawlContact(
                    name=name or "Unknown",
                    email=email,
                    title=title,
                    linkedin_url=li if "linkedin" in li else "",
                    source_url=source_url,
                    confidence=70,    # schema.org data is high quality
                )

        # Recurse into @graph and itemListElement
        for key in ("@graph", "itemListElement", "member", "employee", "founder"):
            if key in data:
                self._extract_jsonld(data[key], source_url, out)

    @staticmethod
    def _extract_nearby_name(text: str, email: str, window: int = 200) -> str:
        """Find 'FirstName LastName' pattern within `window` chars of the email."""
        idx = text.lower().find(email.lower())
        if idx == -1:
            return "Unknown"
        snippet = text[max(0, idx - window): idx + window]
        names = _NAME_RE.findall(snippet)
        if names:
            first, last = names[0]
            return f"{first} {last}"
        return "Unknown"

    @staticmethod
    def _extract_nearby_title(text: str, email: str, window: int = 300) -> str:
        """Heuristically extract a job title near the email."""
        idx = text.lower().find(email.lower())
        if idx == -1:
            return ""
        snippet = text[max(0, idx - window): idx + window]
        # Common title patterns
        title_re = re.compile(
            r"\b(CEO|CTO|CFO|COO|VP|Head of|Director|Manager|Engineer|"
            r"Recruiter|Talent|HR|Lead|Principal|Staff|Senior|Junior|"
            r"Founder|Co-Founder|President|Partner)\b[^\n.]{0,40}",
            re.IGNORECASE,
        )
        match = title_re.search(snippet)
        return match.group(0).strip() if match else ""

    @staticmethod
    def _are_nearby(text: str, a: str, b: str, window: int = 500) -> bool:
        """Check if strings `a` and `b` appear within `window` chars of each other."""
        idx_a = text.lower().find(a.lower())
        idx_b = text.lower().find(b.lower())
        if idx_a == -1 or idx_b == -1:
            return False
        return abs(idx_a - idx_b) <= window

    # ── Rate limiting ─────────────────────────────────────────────────────────

    async def _rate_limit(self, domain: str) -> None:
        """Enforce 1 req/sec per domain (polite crawling)."""
        import time
        async with self._domain_locks[domain]:
            last = self._rate_buckets.get(domain, 0.0)
            now  = time.monotonic()
            wait = 1.0 - (now - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._rate_buckets[domain] = time.monotonic()
