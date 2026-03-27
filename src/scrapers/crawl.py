# =============================================================================
# Cloudflare Browser Rendering — /crawl helper
# Exports: CrawlRequest, cloudflare_crawl
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

    async with httpx.AsyncClient(timeout=60) as client:
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
