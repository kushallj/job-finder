"""Shared HTTP + parsing helpers for sources (one user agent, retries, HTML -> text)."""

from __future__ import annotations

import re
import ssl
from functools import cache
from typing import Any

import httpx
from bs4 import BeautifulSoup
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

# Identify honestly; no personal contact details (CLAUDE.md section 1).
USER_AGENT = "JobifyBot/1.0 (+https://github.com/kushallj/job-finder)"
TIMEOUT = 25.0

# Tests swap this for httpx.MockTransport; production leaves it None.
TRANSPORT: httpx.AsyncBaseTransport | None = None


@cache
def ssl_context() -> ssl.SSLContext:
    """One shared TLS context. Building one loads the CA bundle (~0.3 s of blocking CPU);
    per-client contexts were 75% of a full fetch's wall time across ~230 clients."""
    import certifi

    return ssl.create_default_context(cafile=certifi.where())


def client(**kwargs: Any) -> httpx.AsyncClient:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, application/rss+xml, application/xml;q=0.9, */*;q=0.8",
               **kwargs.pop("headers", {})}
    return httpx.AsyncClient(timeout=kwargs.pop("timeout", TIMEOUT), follow_redirects=True, headers=headers,
                             transport=TRANSPORT, verify=ssl_context(), **kwargs)


def _transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


async def request(method: str, url: str, **kwargs: Any) -> httpx.Response:
    """One HTTP call with up to 3 attempts on 429/5xx/network errors (exponential backoff)."""
    headers = kwargs.pop("headers", {})
    async with client(headers=headers) as c:
        async for attempt in AsyncRetrying(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8),
                                           retry=retry_if_exception(_transient), reraise=True):
            with attempt:
                res = await c.request(method, url, **kwargs)
                res.raise_for_status()
    return res


async def get_json(url: str, **kwargs: Any) -> Any:
    return (await request("GET", url, **kwargs)).json()


async def get_text(url: str, **kwargs: Any) -> str:
    return (await request("GET", url, **kwargs)).text


_BLANKS = re.compile(r"\n\s*\n+")


def html_to_text(html: str | None) -> str:
    """Readable plain text; list items become "- " bullets (Jobify parses those as responsibilities)."""
    if not html:
        return ""
    if "<" not in html:
        return html.strip()
    soup = BeautifulSoup(html, "lxml")
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    for br in soup.find_all(["br", "p", "div", "h1", "h2", "h3", "h4", "ul", "ol"]):
        br.insert_after("\n")
    return _BLANKS.sub("\n\n", soup.get_text()).strip()


GENERIC_WORDS = frozenset({
    "developer", "developers", "engineer", "engineers", "engineering", "dev", "programmer", "senior", "junior",
    "lead", "staff", "principal", "sr", "jr", "remote", "job", "jobs", "role", "roles", "position", "hiring",
})


def matches(query: str, *texts: str | None) -> bool:
    """Client-side filter for feeds without server-side search.

    Specific words ("python", "react") must all appear; generic role words ("developer",
    "senior") are optional when a specific word is present, so "python developer" also
    finds "Python Engineer". A query of only generic words needs any one of them.
    """
    words = {w for w in re.findall(r"[a-z0-9+#.]+", query.lower()) if len(w) > 1}
    if not words:
        return True
    hay = " ".join(t for t in texts if t).lower()
    specific = words - GENERIC_WORDS
    if specific:
        return all(w in hay for w in specific)
    return any(w in hay for w in words)
