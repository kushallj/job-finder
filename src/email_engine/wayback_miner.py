"""
wayback_miner.py — Email discovery via Wayback Machine (archive.org).

Why Wayback Machine?
  Companies often had emails exposed on old /team, /about, /contact pages
  before they cleaned up their sites. The Internet Archive preserves those
  snapshots. Job postings, press kits, and old newsletters also frequently
  leaked hr@, careers@, and personal founder/executive emails that are now
  removed from the live site.

Algorithm:
  Stage 1 — CDX Index Query (no full page downloads)
    GET http://web.archive.org/cdx/search/cdx
        ?url=*.{domain}/*&output=json&fl=original,timestamp
        &filter=statuscode:200&filter=mimetype:text/html
        &collapse=urlkey&limit=500
    → Returns list of (original_url, oldest_timestamp) for every archived
      HTML page under the domain. No snapshot is fetched yet.
    → Filter down to high-value paths: /team, /about, /contact, /careers…

  Stage 2 — Snapshot Fetch (async, rate-limited)
    For each high-value URL fetch TWO snapshots:
      • Oldest   → emails most likely still present / not yet scrubbed
      • ~2015    → sweet spot between enough content and fewer obfuscations
    Snapshots: https://web.archive.org/web/{timestamp}/{url}
    Rate limit: Semaphore(5), 0.5 s between requests (polite to archive.org)

  Stage 3 — Email Extraction
    Regex extract all emails from raw HTML text.
    Keep only @{domain} emails plus role emails (hr@, careers@, etc.) on the
    target domain. Strip mailto: / HTML entities. Deduplicate.
    Extract nearby name using 200-char context window (same as web_crawler).

Confidence baseline: 40 (archived page, lower than live page = 45).
  +10 if a real name was found in context.
  +5  if the snapshot is from before 2018 (higher signal = email was real).
  +5  if found in both oldest and newest snapshot (corroboration).

Integration:
  Called as a Layer 1 source in discovery_engine._layer1_collect.
  Returns List[WaybackContact] → converted to List[DiscoveredEmail] by caller.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import httpx

log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_CDX_API  = "http://web.archive.org/cdx/search/cdx"
_WB_BASE  = "https://web.archive.org/web"

_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")
_NAME_RE  = re.compile(r"\b([A-Z][a-z]{1,20})\s+([A-Z][a-z]{1,20})\b")

# High-value paths — pages most likely to have exposed emails
_HIGH_VALUE_PATHS = {
    "/team", "/about", "/about-us", "/leadership", "/people",
    "/founders", "/company", "/contact", "/contact-us",
    "/careers", "/staff", "/press", "/management", "/board",
    "/who-we-are", "/our-team", "/the-team", "/meet-the-team",
    "/meet-us", "/investors", "/advisors", "/executive",
}

# Role emails worth keeping even though they are not personal
_KEEP_ROLE_RE = re.compile(
    r"^(hr|careers|jobs|recruiting|talent|hiring|founder|ceo|cto|coo|"
    r"hello|hi|info|press|media)@",
    re.IGNORECASE,
)

# Noise emails to always drop
_DROP_RE = re.compile(
    r"(noreply|no-reply|donotreply|unsubscribe|bounce|mailer-daemon|"
    r"postmaster|abuse|security|legal|privacy|gdpr|webmaster|"
    r"support|help|billing|api|dev|admin|newsletter|feedback)@",
    re.IGNORECASE,
)


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class WaybackContact:
    email:       str
    name:        str        = "Unknown"
    title:       str        = ""
    source_url:  str        = ""       # original (non-wayback) URL
    snapshot_ts: str        = ""       # YYYYMMDDhhmmss
    confidence:  int        = 40


# ── Main class ────────────────────────────────────────────────────────────────

class WaybackMiner:
    """
    Discovers emails for a domain by mining archived snapshots on archive.org.

    Usage:
        miner = WaybackMiner()
        contacts = await miner.mine("stripe.com")
        await miner.close()
    """

    # CDX: how many archived URLs to consider per domain
    CDX_LIMIT        = 500
    # Max snapshots to actually download (after path filtering)
    MAX_SNAPSHOTS    = 30
    # Concurrent snapshot downloads
    CONCURRENCY      = 5
    # Seconds between requests to archive.org (politeness)
    REQUEST_DELAY    = 0.5
    REQUEST_TIMEOUT  = 20.0   # per snapshot fetch
    CDX_TIMEOUT      = 60.0   # CDX index query can be slow for large domains

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            timeout=self.REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; ResearchBot/1.0; "
                    "email-discovery-tool)"
                ),
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            },
        )
        self._sem        = asyncio.Semaphore(self.CONCURRENCY)
        self._last_req   = 0.0   # monotonic time of last archive.org request
        self._req_lock   = asyncio.Lock()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def mine(self, domain: str) -> List[WaybackContact]:
        """
        Full pipeline: CDX query → snapshot selection → fetch → extract.

        Args:
            domain: Root domain, e.g. "stripe.com"

        Returns:
            Deduplicated WaybackContact list sorted by confidence desc.
        """
        domain = domain.lower().lstrip("www.")
        log.info("WaybackMiner: starting for domain=%s", domain)

        # Stage 1: query CDX index
        snapshot_pairs = await self._stage1_cdx(domain)
        if not snapshot_pairs:
            log.info("WaybackMiner: no archived URLs found for %s", domain)
            return []

        log.info(
            "WaybackMiner: %d high-value snapshot URLs queued for %s",
            len(snapshot_pairs), domain,
        )

        # Stage 2: fetch snapshots concurrently
        tasks = [
            asyncio.create_task(self._fetch_snapshot(orig_url, ts, domain))
            for orig_url, ts in snapshot_pairs[: self.MAX_SNAPSHOTS]
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Stage 3: flatten + dedup
        seen: Dict[str, WaybackContact] = {}
        for batch in batch_results:
            if not isinstance(batch, list):
                continue
            for contact in batch:
                key = contact.email.lower()
                if key not in seen:
                    seen[key] = contact
                else:
                    # Corroboration bonus: found in multiple snapshots
                    existing = seen[key]
                    existing.confidence = min(90, existing.confidence + 5)
                    if contact.name != "Unknown" and existing.name == "Unknown":
                        existing.name = contact.name

        contacts = sorted(seen.values(), key=lambda c: c.confidence, reverse=True)
        log.info(
            "WaybackMiner: extracted %d unique emails for %s", len(contacts), domain
        )
        return contacts

    async def close(self) -> None:
        await self._http.aclose()

    # ── Stage 1: CDX Index Query ───────────────────────────────────────────────

    async def _stage1_cdx(
        self, domain: str
    ) -> List[Tuple[str, str]]:
        """
        Query the CDX API for archived HTML pages under `domain`.

        Fires one small CDX call per high-value path prefix in parallel
        (e.g. domain/about*, domain/team*, domain/contact*) rather than
        scanning the entire domain index. Keeps each CDX call fast regardless
        of how many total pages the domain has archived.

        Returns list of (original_url, oldest_timestamp) deduplicated.
        """
        # Build prefixes for all scheme+subdomain variants we care about
        prefixes: List[str] = []
        for scheme in ("http", "https"):
            for host in (domain, f"www.{domain}"):
                for path in (
                    "/about", "/team", "/contact",
                    "/leadership", "/people", "/founders",
                    "/careers", "/press", "/staff", "/management",
                ):
                    prefixes.append(f"{scheme}://{host}{path}")

        tasks = [
            asyncio.create_task(self._cdx_prefix(prefix))
            for prefix in prefixes
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls: Set[str] = set()
        pairs: List[Tuple[str, str]] = []
        for batch in results:
            if not isinstance(batch, list):
                continue
            for original_url, timestamp in batch:
                if original_url not in seen_urls:
                    seen_urls.add(original_url)
                    pairs.append((original_url, timestamp))

        return pairs

    async def _cdx_prefix(self, url_prefix: str) -> List[Tuple[str, str]]:
        """
        Single CDX call for one URL prefix.
        Uses matchType=prefix so /about matches /about-us, /about/team, etc.
        Limits to 10 results per prefix — keeps each call sub-second.
        """
        params = [
            ("url",      url_prefix + "*"),
            ("output",   "json"),
            ("fl",       "original,timestamp"),
            ("filter",   "statuscode:200"),
            ("filter",   "mimetype:text/html"),
            ("collapse", "urlkey"),
            ("limit",    "10"),
            ("from",     "20000101"),
        ]
        await self._polite_wait()
        try:
            resp = await self._http.get(
                _CDX_API,
                params=params,
                timeout=self.CDX_TIMEOUT,
            )
            if resp.status_code != 200:
                return []
            rows = resp.json()
        except Exception as exc:
            log.debug("CDX prefix query failed (%s): %s", url_prefix, exc)
            return []

        if not rows:
            return []
        if rows[0] == ["original", "timestamp"]:
            rows = rows[1:]

        return [
            (row[0], row[1])
            for row in rows
            if isinstance(row, list) and len(row) >= 2
        ]

    # ── Stage 2: Snapshot Fetch ────────────────────────────────────────────────

    async def _fetch_snapshot(
        self,
        original_url: str,
        timestamp: str,
        domain: str,
    ) -> List[WaybackContact]:
        """Fetch one Wayback snapshot and extract emails."""
        snapshot_url = f"{_WB_BASE}/{timestamp}/{original_url}"
        async with self._sem:
            await self._polite_wait()
            try:
                resp = await self._http.get(snapshot_url)
                if resp.status_code != 200:
                    return []
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    return []
                return self._extract_emails(resp.text, original_url, timestamp, domain)
            except (httpx.TimeoutException, httpx.ConnectError):
                return []
            except Exception as exc:
                log.debug("WaybackMiner fetch error (%s): %s", snapshot_url, exc)
                return []

    # ── Stage 3: Email Extraction ──────────────────────────────────────────────

    def _extract_emails(
        self,
        html: str,
        source_url: str,
        timestamp: str,
        domain: str,
    ) -> List[WaybackContact]:
        """
        Extract emails from raw HTML snapshot.

        Keeps:
          • Emails ending in @{domain} or @{subdomain}.{domain}
          • Known role emails (hr@, careers@, hello@) on the target domain
        Drops:
          • Noise / system emails (_DROP_RE)
          • Emails from unrelated domains
        """
        # Strip Wayback toolbar injection (first ~3 KB is Wayback UI boilerplate)
        # The actual archived content starts after the </script> following the toolbar
        body = _strip_wayback_toolbar(html)

        # Decode common HTML email obfuscation
        body = body.replace("&#64;", "@").replace(" [at] ", "@").replace("[at]", "@")
        body = body.replace(" [@] ", "@").replace("(at)", "@")
        body = re.sub(r"\s+\[dot\]\s+", ".", body, flags=re.IGNORECASE)

        text = _html_to_text(body)
        contacts: Dict[str, WaybackContact] = {}

        for email in _EMAIL_RE.findall(body):
            email = email.lower().strip(".,;:>\"'")
            if not _is_target_domain(email, domain):
                continue
            if _DROP_RE.search(email):
                if not _KEEP_ROLE_RE.match(email):
                    continue

            if email in contacts:
                continue

            name  = _extract_nearby_name(text, email)
            title = _extract_nearby_title(text, email)
            conf  = _base_confidence(name, timestamp)

            contacts[email] = WaybackContact(
                email=email,
                name=name,
                title=title,
                source_url=source_url,
                snapshot_ts=timestamp,
                confidence=conf,
            )

        return list(contacts.values())

    # ── Rate limiting ──────────────────────────────────────────────────────────

    async def _polite_wait(self) -> None:
        """Enforce REQUEST_DELAY seconds between archive.org requests."""
        async with self._req_lock:
            now  = time.monotonic()
            wait = self.REQUEST_DELAY - (now - self._last_req)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_req = time.monotonic()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _url_path(url: str) -> str:
    """Return the path component of a URL, lowercase, no query string."""
    try:
        from urllib.parse import urlparse
        path = urlparse(url).path.rstrip("/").lower() or "/"
        return path
    except Exception:
        return "/"


def _is_high_value(path: str) -> bool:
    """Return True if path starts with any high-value segment."""
    for segment in _HIGH_VALUE_PATHS:
        if path == segment or path.startswith(segment + "/"):
            return True
    return False


def _is_target_domain(email: str, domain: str) -> bool:
    """True if email belongs to domain or any subdomain of it."""
    if "@" not in email:
        return False
    email_domain = email.split("@", 1)[1]
    return email_domain == domain or email_domain.endswith("." + domain)


def _strip_wayback_toolbar(html: str) -> str:
    """
    Remove the Wayback Machine toolbar injection (~2–4 KB at the top).
    The archive wraps pages in a script block ending with '<!-- END WAYBACK TOOLBAR -->'.
    """
    marker = "<!-- END WAYBACK TOOLBAR -->"
    idx = html.find(marker)
    if idx != -1:
        return html[idx + len(marker):]
    return html


def _html_to_text(html: str) -> str:
    """
    Very lightweight HTML-to-text: strip tags, decode entities.
    Avoids importing BeautifulSoup for performance (Wayback fetches can be large).
    """
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_nearby_name(text: str, email: str, window: int = 200) -> str:
    """Find 'FirstName LastName' within `window` chars of the email in plain text."""
    idx = text.lower().find(email.lower())
    if idx == -1:
        return "Unknown"
    snippet = text[max(0, idx - window): idx + window]
    names = _NAME_RE.findall(snippet)
    if names:
        first, last = names[0]
        return f"{first} {last}"
    return "Unknown"


def _extract_nearby_title(text: str, email: str, window: int = 300) -> str:
    """Heuristically extract a job title near the email."""
    idx = text.lower().find(email.lower())
    if idx == -1:
        return ""
    snippet = text[max(0, idx - window): idx + window]
    title_re = re.compile(
        r"\b(CEO|CTO|CFO|COO|VP|Head of|Director|Manager|Engineer|"
        r"Recruiter|Talent|HR|Lead|Principal|Staff|Senior|Junior|"
        r"Founder|Co-Founder|President|Partner)\b[^\n.]{0,40}",
        re.IGNORECASE,
    )
    m = title_re.search(snippet)
    return m.group(0).strip() if m else ""


def _base_confidence(name: str, timestamp: str) -> int:
    """
    Compute baseline confidence for a Wayback-sourced email.

      40  base (archived page)
      +10 if a real name was found nearby
      +5  if snapshot is from before 2018 (higher signal era)
    """
    conf = 40
    if name and name != "Unknown":
        conf += 10
    try:
        year = int(timestamp[:4])
        if year < 2018:
            conf += 5
    except (ValueError, IndexError):
        pass
    return conf
