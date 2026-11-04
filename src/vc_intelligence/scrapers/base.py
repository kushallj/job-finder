"""
Base VC Scraper Utility & Helper Functions
Provides resilient HTTP querying, domain normalization, and slug generation.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional
from urllib.parse import urlparse
import httpx

log = logging.getLogger("vc_intelligence.scraper")

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def clean_domain(url: Optional[str]) -> Optional[str]:
    """
    Extract clean normalized domain from URL.
    Examples:
        'https://www.stripe.com/about' -> 'stripe.com'
        'http://sub.domain.co.in/' -> 'sub.domain.co.in'
    """
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc or None
    except Exception:
        return None


def slugify(text: str) -> str:
    """
    Generate an alphanumeric URL-safe slug from a string.
    Example: 'Y Combinator W24!' -> 'y-combinator-w24'
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


async def fetch_html_or_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
) -> Optional[httpx.Response]:
    """
    Resilient async HTTP fetch helper.
    """
    req_headers = DEFAULT_HEADERS.copy()
    if headers:
        req_headers.update(headers)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=req_headers, params=params)
            resp.raise_for_status()
            return resp
    except httpx.HTTPError as exc:
        log.warning(f"HTTP fetch failed for {url}: {exc}")
        return None
    except Exception as exc:
        log.warning(f"Unexpected error fetching {url}: {exc}")
        return None
