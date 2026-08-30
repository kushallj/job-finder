"""External job intelligence providers: JobDataAPI + AI Dev Jobs.

Both providers are optional. They are queried only from the backend, cached into
our local DB, and treated as discovery/enrichment sources rather than sources of
truth for candidate actions.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from src.config import settings

JOBDATA_BASE = "https://jobdataapi.com/api"
AIDEV_BASE = "https://aidevboard.com/api/v1"


def _dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        return None


def _company_name(company: Any) -> Optional[str]:
    if isinstance(company, dict):
        return company.get("name") or company.get("company_name")
    return str(company) if company else None


def normalize_job(item: Dict[str, Any], provider: str) -> Dict[str, Any]:
    company = item.get("company")
    title = item.get("title") or item.get("name") or "Untitled role"
    description = item.get("description_string") or item.get("description") or item.get("description_md")
    url = item.get("application_url") or item.get("url") or item.get("apply_url")
    posted = _dt(item.get("published") or item.get("posted") or item.get("published_at"))
    salary_min = item.get("salary_min_usd") or item.get("salary_min")
    salary_max = item.get("salary_max_usd") or item.get("salary_max")
    tags = item.get("tags")
    if isinstance(tags, list):
        cleaned_tags = []
        for tag in tags:
            if isinstance(tag, dict):
                cleaned_tags.append(tag.get("name") or tag.get("label") or str(tag))
            else:
                cleaned_tags.append(str(tag))
    else:
        cleaned_tags = []

    ext = item.get("ext_id") or item.get("id")
    provider_id = str(ext) if ext is not None else None
    job_key = f"{provider}:{provider_id or url or title}"

    work_mode = item.get("work_mode")
    if isinstance(work_mode, int):
        work_mode = {1: "hybrid", 2: "remote", 3: "remote_any"}.get(work_mode, str(work_mode))

    return {
        "job_id": job_key,
        "title": title,
        "company": _company_name(company) or item.get("company_name"),
        "location": item.get("location") or item.get("location_string"),
        "description": description,
        "url": url,
        "source": provider,
        "posted_date": posted,
        "provider_id": provider_id,
        "company_website": (company or {}).get("website") if isinstance(company, dict) else item.get("company_website"),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": item.get("salary_currency"),
        "has_remote": item.get("has_remote"),
        "work_mode": work_mode,
        "experience_level": item.get("experience_level") or item.get("level"),
        "tags": cleaned_tags,
        "expired_at": _dt(item.get("expired")),
        "provider_payload": item,
    }


class JobDataAPIClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 20.0, transport=None):
        self.api_key = api_key or settings.jobdata_api_key
        self.timeout = timeout
        self.transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search(self, *, query: Optional[str] = None, location: Optional[str] = None,
                     max_age: int = 30, page_size: int = 50, remote: Optional[bool] = None) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        params: Dict[str, Any] = {
            "page_size": min(max(page_size, 1), 100),
            "max_age": max(1, min(max_age, 999)),
            "description_str": "true",
            "salary_extras": "true",
        }
        if query:
            params["title"] = query
        if location:
            params["location"] = location
        if remote is not None:
            params["has_remote"] = str(remote).lower()
        headers = {"Authorization": f"Api-Key {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(f"{JOBDATA_BASE}/jobs/", params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
        return [normalize_job(item, "jobdataapi") for item in payload.get("results", [])]


class AIDevBoardClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0, transport=None):
        self.api_key = api_key or settings.aidevboard_api_key
        self.timeout = timeout
        self.transport = transport

    @property
    def enabled(self) -> bool:
        return True

    async def search(self, *, query: Optional[str] = None, location: Optional[str] = None,
                     limit: int = 50, workplace: Optional[str] = None, level: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": min(max(limit, 1), 50)}
        if query:
            params["q"] = query
        if location:
            params["location"] = location
        if workplace:
            params["workplace"] = workplace
        if level:
            params["level"] = level
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(f"{AIDEV_BASE}/jobs", params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
        items = payload.get("jobs") or payload.get("results") or []
        return [normalize_job(item, "aidevboard") for item in items]

    async def match(self, *, skills: List[str], salary_min: Optional[int] = None,
                    salary_max: Optional[int] = None, workplace: Optional[str] = None,
                    level: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        body: Dict[str, Any] = {"skills": skills, "limit": min(max(limit, 1), 50)}
        if salary_min is not None:
            body["salary_min"] = salary_min
        if salary_max is not None:
            body["salary_max"] = salary_max
        if workplace:
            body["workplace"] = workplace
        if level:
            body["level"] = level
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.post(f"{AIDEV_BASE}/jobs/match", json=body, headers=headers)
            response.raise_for_status()
            return response.json()

    async def stats(self) -> Dict[str, Any]:
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(f"{AIDEV_BASE}/stats", headers=headers)
            response.raise_for_status()
            return response.json()

    async def salary_trends(self, *, tag: Optional[str] = None, level: Optional[str] = None,
                            location: Optional[str] = None, days: int = 90) -> Dict[str, Any]:
        params: Dict[str, Any] = {"days": min(max(days, 1), 365)}
        if tag: params["tag"] = tag
        if level: params["level"] = level
        if location: params["location"] = location
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(f"{AIDEV_BASE}/salary-trends", params=params, headers=headers)
            response.raise_for_status()
            return response.json()


async def search_all(*, query: str, location: Optional[str] = None,
                     max_age: int = 30, limit: int = 50) -> Dict[str, List[Dict[str, Any]]]:
    """Sequentially query both providers; each provider may independently fail."""
    results: Dict[str, List[Dict[str, Any]]] = {"jobdataapi": [], "aidevboard": []}
    jobdata = JobDataAPIClient()
    aidev = AIDevBoardClient()
    try:
        results["jobdataapi"] = await jobdata.search(query=query, location=location, max_age=max_age, page_size=limit)
    except Exception:
        pass
    try:
        results["aidevboard"] = await aidev.search(query=query, location=location, limit=limit)
    except Exception:
        pass
    return results
