# =============================================================================
# Cloudflare Browser Rendering helpers
# Exports: CrawlRequest, cloudflare_crawl, cloudflare_render_page
#
# Two distinct APIs:
#   /content  — single-page render, synchronous, returns HTML immediately.
#               Use for job-board search pages (Naukri, Hirist, Indeed).
#   /crawl    — multi-page async crawl with polling.
#               Use for company career sites (already implemented below).
# =============================================================================

import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, validator

from src.config import settings

log = logging.getLogger("main")


class CrawlRequest(BaseModel):
    url: str
    limit: int = 20
    depth: int = 3
    include_patterns: list[str] = ["**/careers/**", "**/jobs/**", "**/positions/**"]
    exclude_patterns: list[str] = ["**/blog/**", "**/press/**", "**/legal/**", "**/login/**"]
    company_name: Optional[str] = None      # explicit company name; falls back to domain if omitted
    feed_pipeline: bool = True
    query: Optional[str] = None            # post-crawl keyword filter; not sent to Cloudflare

    @validator("url")
    def valid_url(cls, v):
        p = urlparse(v)
        if p.scheme not in ("http", "https") or not p.netloc:
            raise ValueError("url must be a full http/https URL")
        return v

    @validator("limit")
    def cap_limit(cls, v):
        if not 1 <= v <= 100:
            raise ValueError("limit must be 1–100")
        return v

    @validator("depth")
    def cap_depth(cls, v):
        if not 1 <= v <= 10:
            raise ValueError("depth must be 1–10")
        return v


async def cloudflare_crawl(
    url: str,
    limit: int = 20,
    depth: int = 3,
    include_patterns: list[str] = None,
    exclude_patterns: list[str] = None,
) -> list[dict]:
    """
    Cloudflare Browser Rendering /crawl endpoint (async two-step).

    Step 1 — POST  → returns a job_id immediately.
    Step 2 — GET   → poll until status != "running", then collect records.

    Returns a list of page dicts: {url, title, text}.
    """
    account_id = settings.cloudflare_account_id
    api_token  = settings.cloudflare_api_token

    cf_url = (
        f"https://api.cloudflare.com/client/v4/accounts"
        f"/{account_id}/browser-rendering/crawl"
    )
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "limit": limit,
        "depth": depth,
        "render": True,
        "source": "links",                       # "all" | "sitemaps" | "links"
        "formats": ["markdown"],                 # cleaner text than html for job parsing
        "rejectResourceTypes": ["image", "media", "font", "stylesheet"],
        "options": {
            "includePatterns": include_patterns or ["**/careers/**", "**/jobs/**"],
            "excludePatterns": exclude_patterns or ["**/blog/**", "**/legal/**"],
            "includeSubdomains": False,
            "includeExternalLinks": False,
        },
    }

    # Configure connection pooling with httpx limits
    limits = httpx.Limits(
        max_connections=10,
        max_keepalive_connections=5,
    )
    async with httpx.AsyncClient(timeout=60, limits=limits) as client:
        # ── Step 1: Start crawl job ──────────────────────────────────────────
        resp = await client.post(cf_url, headers=headers, json=payload)
        if resp.status_code != 200:
            log.error("CF crawl start error %d: %s", resp.status_code, resp.text[:500])
            raise HTTPException(
                status_code=502,
                detail=f"Cloudflare crawl start error {resp.status_code}: {resp.text[:200]}",
            )

        job_id = resp.json()["result"]           # CF returns just the job ID string
        log.info("CF crawl job started: %s", job_id)

        # ── Step 2: Poll until complete ──────────────────────────────────────
        poll_url = f"{cf_url}/{job_id}"
        data: dict = {}
        for attempt in range(72):                # max ~6 min (72 × 5 s)
            await asyncio.sleep(5)
            poll = await client.get(
                poll_url,
                headers=headers,
                params={"limit": 500},
            )
            if poll.status_code != 200:
                log.warning("CF poll error %d (attempt %d)", poll.status_code, attempt)
                continue
            data = poll.json().get("result", {})
            status = data.get("status", "running")
            log.debug("CF crawl status=%s finished=%s/%s",
                      status, data.get("finished"), data.get("total"))
            if status != "running":
                break

    # ── Step 3: Parse records ────────────────────────────────────────────────
    pages = []
    for record in data.get("records", []):
        if record.get("status") != "completed":
            continue
        meta = record.get("metadata", {})
        pages.append({
            "url":   record.get("url", ""),
            "title": meta.get("title", ""),
            "text":  record.get("markdown") or record.get("html", ""),
        })

    log.info("CF crawl %s done — %d/%d pages usable",
             job_id, len(pages), data.get("total", 0))
    return pages


async def cloudflare_render_page(
    url:              str,
    wait_selector:    Optional[str] = None,
    wait_ms:          int           = 2000,
    timeout_ms:       int           = 30000,
) -> Optional[str]:
    """
    Cloudflare Browser Rendering /content — single-page synchronous render.

    Renders a URL in a real Chromium instance at Cloudflare's edge and returns
    the fully-rendered HTML. Bypasses bot detection without needing a local browser.

    Perfect for job-board search pages (Naukri, Hirist, Indeed) that block
    direct HTTP requests or TLS impersonation.

    Args:
        url:           Page to render.
        wait_selector: Optional CSS selector to wait for before returning HTML.
        wait_ms:       Additional ms to wait after page load (default 2s).
        timeout_ms:    Max render time in ms (default 30s).

    Returns:
        Rendered HTML string, or None on failure.
    """
    account_id = settings.cloudflare_account_id
    api_token  = settings.cloudflare_api_token

    if not account_id or not api_token:
        log.warning("cloudflare_render_page: missing CF credentials — skipping")
        return None

    cf_url  = (
        f"https://api.cloudflare.com/client/v4/accounts"
        f"/{account_id}/browser-rendering/content"
    )
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type":  "application/json",
    }
    payload: dict = {
        "url": url,
        # Skip heavy assets — faster render, same HTML content
        "rejectResourceTypes": ["image", "media", "font", "stylesheet"],
        # networkidle2: wait until no more than 2 in-flight network requests for 500ms
        # This ensures SPA frameworks (React/Next.js) finish fetching data before snapshot
        "gotoOptions": {"waitUntil": "networkidle2", "timeout": timeout_ms},
    }
    if wait_selector:
        payload["waitForSelector"] = {"selector": wait_selector, "timeout": timeout_ms}
    elif wait_ms:
        payload["waitForTimeout"] = wait_ms

    try:
        # Configure connection pooling with httpx limits
        limits = httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
        )
        async with httpx.AsyncClient(
            timeout=timeout_ms / 1000 + 10,
            limits=limits,
        ) as client:
            resp = await client.post(cf_url, headers=headers, json=payload)

        if resp.status_code != 200:
            log.warning("CF /content error %d for %s: %s",
                        resp.status_code, url, resp.text[:200])
            return None

        data = resp.json()
        # Response shape: {"success": true, "result": "<html>..."}
        html = data.get("result") or data.get("html") or ""
        if not html:
            log.warning("CF /content returned empty body for %s", url)
            return None

        log.info("CF /content OK — %d chars for %s", len(html), url)
        return html

    except Exception as exc:
        log.warning("CF /content exception for %s: %s", url, exc)
        return None
