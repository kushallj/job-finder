"""External job intelligence providers: JobDataAPI + AI Dev Jobs + Fantastic Jobs + Arbeitnow + Careerjet.

All providers are optional. They are queried only from the backend, cached into
our local DB, and treated as discovery/enrichment sources rather than sources of
truth for candidate actions.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from src.config import settings

JOBDATA_BASE = "https://jobdataapi.com/api"
AIDEV_BASE = "https://aidevboard.com/api/v1"
FANTASTIC_BASE = "https://data.fantastic.jobs/v1"
ARBEITNOW_BASE = "https://www.arbeitnow.com/api/job-board-api"
CAREERJET_BASE = "https://search.api.careerjet.net/v4/query"
USAJOBS_BASE = "https://data.usajobs.gov/api/search"


def _dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
        except Exception:
            return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(str(value))
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    except Exception:
        pass
    return None


def _company_name(company: Any) -> Optional[str]:
    if isinstance(company, dict):
        return company.get("name") or company.get("company_name") or company.get("organization")
    return str(company) if company else None



def normalize_job(item: Dict[str, Any], provider: str) -> Dict[str, Any]:
    desc = item.get("MatchedObjectDescriptor") if isinstance(item.get("MatchedObjectDescriptor"), dict) else item
    company = (
        desc.get("OrganizationName")
        or desc.get("DepartmentName")
        or item.get("company")
        or item.get("company_name")
        or item.get("organization")
        or item.get("hiring_organization")
    )
    title = (
        desc.get("PositionTitle")
        or item.get("title")
        or item.get("name")
        or item.get("job_title")
        or "Untitled role"
    )

    # Description resolution
    user_area = desc.get("UserArea", {}) if isinstance(desc.get("UserArea"), dict) else {}
    details = user_area.get("Details", {}) if isinstance(user_area.get("Details"), dict) else {}
    description = (
        item.get("description_string")
        or item.get("description")
        or item.get("description_text")
        or item.get("description_md")
        or item.get("description_html")
    )
    if not description and details.get("JobSummary"):
        description = details.get("JobSummary")
        if details.get("MajorDuties"):
            duties = details.get("MajorDuties")
            if isinstance(duties, list):
                description += "\n\nDuties:\n" + "\n".join(f"- {d}" for d in duties)
            elif isinstance(duties, str):
                description += f"\n\nDuties:\n{duties}"

    url = (
        desc.get("PositionURI")
        or (desc.get("ApplyURI") and desc.get("ApplyURI")[0] if isinstance(desc.get("ApplyURI"), list) and desc.get("ApplyURI") else None)
        or item.get("application_url")
        or item.get("url")
        or item.get("apply_url")
    )
    posted = _dt(
        desc.get("PublicationStartDate")
        or item.get("published")
        or item.get("posted")
        or item.get("published_at")
        or item.get("date_created")
        or item.get("date_posted")
        or item.get("created_at")
        or item.get("date")
    )
    salary_min = item.get("salary_min_usd") or item.get("salary_min")
    salary_max = item.get("salary_max_usd") or item.get("salary_max")

    remun = desc.get("PositionRemuneration")
    if isinstance(remun, list) and remun:
        r0 = remun[0]
        if isinstance(r0, dict):
            if not salary_min and r0.get("MinimumRange"):
                try:
                    salary_min = float(str(r0.get("MinimumRange")).replace(",", ""))
                except ValueError:
                    pass
            if not salary_max and r0.get("MaximumRange"):
                try:
                    salary_max = float(str(r0.get("MaximumRange")).replace(",", ""))
                except ValueError:
                    pass

    tags = item.get("tags")
    job_types = item.get("job_types")
    cleaned_tags = []
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict):
                cleaned_tags.append(tag.get("name") or tag.get("label") or str(tag))
            else:
                cleaned_tags.append(str(tag))
    if isinstance(job_types, list):
        for jt in job_types:
            cleaned_tags.append(str(jt))
    if desc.get("JobCategory") and isinstance(desc.get("JobCategory"), list):
        for jc in desc.get("JobCategory"):
            if isinstance(jc, dict) and jc.get("Name"):
                cleaned_tags.append(jc["Name"])
    if details.get("LowGrade") and details.get("HighGrade"):
        cleaned_tags.append(f"GS-{details.get('LowGrade')}/{details.get('HighGrade')}")

    # Location extraction supporting strings, dicts, and structured place lists
    loc = desc.get("PositionLocationDisplay") or item.get("location") or item.get("location_string")
    if not loc and desc.get("PositionLocation") and isinstance(desc.get("PositionLocation"), list):
        loc_names = [pl.get("LocationName") for pl in desc.get("PositionLocation") if isinstance(pl, dict) and pl.get("LocationName")]
        if loc_names:
            loc = "; ".join(loc_names)
    if not loc and isinstance(item.get("locations"), str):
        loc = item.get("locations")
    elif not loc and isinstance(item.get("locations"), list):
        places = []
        for p in item.get("locations"):
            if isinstance(p, dict):
                addr = p.get("address")
                if isinstance(addr, dict):
                    parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
                    cleaned_p = [str(x) for x in parts if x and str(x).lower() != "none"]
                    if cleaned_p:
                        places.append(", ".join(cleaned_p))
                elif isinstance(addr, str) and addr:
                    places.append(addr)
            elif isinstance(p, str) and p:
                places.append(p)
        if places:
            loc = "; ".join(places)

    if not loc and item.get("locations_derived"):
        loc_derived = item.get("locations_derived")
        loc = ", ".join(str(l) for l in loc_derived) if isinstance(loc_derived, list) else str(loc_derived)
    if not loc and item.get("cities_derived"):
        cities = item.get("cities_derived")
        loc = ", ".join(str(c) for c in cities) if isinstance(cities, list) else str(cities)

    if isinstance(loc, list):
        loc = ", ".join(str(x) for x in loc)
    elif isinstance(loc, dict):
        loc = str(loc)

    ext = item.get("MatchedObjectId") or item.get("ext_id") or item.get("id") or item.get("slug")

    provider_id = str(ext) if ext is not None else None
    job_key = f"{provider}:{provider_id or url or title}"

    work_mode = item.get("work_mode")
    if details.get("RemoteIndicator") is True or str(details.get("RemoteIndicator")).lower() == "true":
        work_mode = "remote"
    elif details.get("TeleworkEligible") is True or str(details.get("TeleworkEligible")).lower() == "true":
        work_mode = "remote"
    elif isinstance(work_mode, int):
        work_mode = {1: "hybrid", 2: "remote", 3: "remote_any"}.get(work_mode, str(work_mode))
    elif not work_mode and item.get("remote_derived"):
        work_mode = "remote" if item.get("remote_derived") else "onsite"
    elif not work_mode and item.get("remote") is not None:
        work_mode = "remote" if item.get("remote") else "onsite"

    has_remote = item.get("has_remote")
    if has_remote is None:
        has_remote = (
            item.get("remote")
            or (work_mode in ("remote", "remote_any", "hybrid"))
            or (details.get("RemoteIndicator") is True or str(details.get("RemoteIndicator")).lower() == "true")
        )

    org_url = None
    if isinstance(company, dict):
        org_url = company.get("website") or company.get("url") or company.get("organization_url")
    else:
        org_url = item.get("organization_url") or item.get("company_website")

    salary_curr = item.get("salary_currency") or item.get("salary_currency_code") or ("USD" if provider == "usajobs" else None)

    return {
        "job_id": job_key,
        "title": title,
        "company": _company_name(company) or item.get("company_name") or item.get("organization"),
        "location": loc,
        "description": description,
        "url": url,
        "source": provider,
        "posted_date": posted,
        "provider_id": provider_id,
        "company_website": org_url,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": salary_curr,
        "has_remote": has_remote,
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


class FantasticJobsClient:
    """Client for Fantastic.jobs high-volume ATS & Job Board API (v1)."""
    def __init__(self, api_key: Optional[str] = None, timeout: float = 20.0, transport=None):
        self.api_key = (
            api_key
            or getattr(settings, "fantastic_jobs_api_key", None)
            or getattr(settings, "fantasticjobs_api_key", None)
        )
        self.timeout = timeout
        self.transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search_ats(
        self,
        *,
        query: Optional[str] = None,
        location: Optional[str] = None,
        time_frame: str = "24h",
        limit: int = 50,
        offset: int = 0,
        include_org_details: bool = True,
    ) -> List[Dict[str, Any]]:
        """Query active ATS jobs directly from company career sites."""
        if not self.enabled:
            return []
        params: Dict[str, Any] = {
            "time_frame": time_frame,
            "limit": min(max(limit, 1), 100),
            "offset": max(0, offset),
        }
        if query:
            params["title"] = query
        if location:
            params["location"] = location
        if include_org_details:
            params["include_basic_organization_details"] = "true"

        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(f"{FANTASTIC_BASE}/active-ats", params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
        items = payload if isinstance(payload, list) else (payload.get("jobs") or payload.get("results") or [])
        return [normalize_job(item, "fantastic_jobs") for item in items]

    async def search_job_boards(
        self,
        *,
        query: Optional[str] = None,
        location: Optional[str] = None,
        time_frame: str = "24h",
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query active job listings aggregated across job boards."""
        if not self.enabled:
            return []
        params: Dict[str, Any] = {
            "time_frame": time_frame,
            "limit": min(max(limit, 1), 100),
            "offset": max(0, offset),
        }
        if query:
            params["title"] = query
        if location:
            params["location"] = location

        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(f"{FANTASTIC_BASE}/active-jb", params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
        items = payload if isinstance(payload, list) else (payload.get("jobs") or payload.get("results") or [])
        return [normalize_job(item, "fantastic_jobs") for item in items]

    async def search(
        self,
        *,
        query: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50,
        time_frame: str = "24h",
    ) -> List[Dict[str, Any]]:
        """Search ATS jobs (primary source)."""
        return await self.search_ats(query=query, location=location, limit=limit, time_frame=time_frame)

    async def count_ats(
        self,
        *,
        query: Optional[str] = None,
        location: Optional[str] = None,
        time_frame: str = "24h",
    ) -> int:
        """Get live ATS job count for query filters."""
        if not self.enabled:
            return 0
        params: Dict[str, Any] = {"time_frame": time_frame}
        if query:
            params["title"] = query
        if location:
            params["location"] = location
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(f"{FANTASTIC_BASE}/active-ats-count", params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("count", 0) if isinstance(data, dict) else int(data)


class ArbeitnowClient:
    """Client for Arbeitnow Job Board API (free public open access)."""
    def __init__(self, timeout: float = 20.0, transport=None):
        self.timeout = timeout
        self.transport = transport

    @property
    def enabled(self) -> bool:
        return True

    async def search(
        self,
        *,
        query: Optional[str] = None,
        location: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch jobs from Arbeitnow API and apply query & location filtering."""
        params: Dict[str, Any] = {"page": max(1, page)}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(ARBEITNOW_BASE, params=params)
            response.raise_for_status()
            payload = response.json()

        raw_items = payload.get("data", []) if isinstance(payload, dict) else (payload if isinstance(payload, list) else [])
        normalized = [normalize_job(item, "arbeitnow") for item in raw_items]

        if not query and not location:
            return normalized[:limit]

        query_lower = query.lower() if query else None
        loc_lower = location.lower() if location else None

        filtered = []
        for job in normalized:
            if query_lower:
                text_to_search = f"{job.get('title', '')} {job.get('company', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
                if query_lower not in text_to_search:
                    continue
            if loc_lower:
                job_loc = (job.get("location") or "").lower()
                if loc_lower not in job_loc and not (loc_lower in ("remote", "any") and job.get("has_remote")):
                    continue
            filtered.append(job)
            if len(filtered) >= limit:
                break
        return filtered


class CareerjetClient:
    """Client for Careerjet Job Search API (v4)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        locale_code: Optional[str] = None,
        timeout: float = 20.0,
        transport=None,
    ) -> None:
        self.api_key = api_key or getattr(settings, "careerjet_api_key", None)
        self.locale_code = locale_code or getattr(settings, "careerjet_locale_code", "en_US")
        self.timeout = timeout
        self.transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        *,
        query: Optional[str] = None,
        location: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        locale_code: Optional[str] = None,
        sort: str = "date",
        contract_type: Optional[str] = None,
        work_hours: Optional[str] = None,
        fragment_size: int = 500,
        user_ip: str = "161.248.229.81",
        user_agent: str = "JobFinder/2.1 (Python/FastAPI; +https://github.com/kushallj/job-finder)",
    ) -> List[Dict[str, Any]]:
        """Search jobs using Careerjet API v4 with Basic authentication."""
        if not self.enabled:
            return []

        params: Dict[str, Any] = {
            "locale_code": locale_code or self.locale_code or "en_US",
            "page": max(1, min(page, 10)),
            "page_size": max(1, min(page_size, 100)),
            "sort": sort,
            "fragment_size": fragment_size,
            "user_ip": user_ip,
            "user_agent": user_agent,
        }

        if query:
            params["keywords"] = query
        if location:
            params["location"] = location
        if contract_type:
            params["contract_type"] = contract_type
        if work_hours:
            params["work_hours"] = work_hours

        auth_str = base64.b64encode(f"{self.api_key}:".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_str}",
            "Referer": "https://github.com/kushallj/job-finder",
            "User-Agent": user_agent,
        }

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(CAREERJET_BASE, params=params, headers=headers)

            response.raise_for_status()
            payload = response.json()

        resp_type = payload.get("type")
        if resp_type == "JOBS":
            items = payload.get("jobs", [])
            return [normalize_job(item, "careerjet") for item in items]
        elif resp_type == "LOCATIONS":
            return []
        return []


class USAJobsClient:
    """Client for USAJOBS Job Search API (https://data.usajobs.gov/api/search)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        timeout: float = 20.0,
        transport=None,
    ) -> None:
        self.api_key = api_key or getattr(settings, "usajobs_api_key", None)
        self.email = email or getattr(settings, "usajobs_email", None) or "kushall.jain07@gmail.com"
        self.timeout = timeout
        self.transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        *,
        query: Optional[str] = None,
        position_title: Optional[str] = None,
        location: Optional[str] = None,
        remote_only: bool = True,
        job_category_code: Optional[str] = None,
        who_may_apply: str = "public",
        hiring_path: Optional[str] = "public",

        page: int = 1,
        results_per_page: int = 25,
        min_salary: Optional[float] = None,
        max_salary: Optional[float] = None,
        sort_field: str = "opendate",
        sort_direction: str = "desc",
    ) -> List[Dict[str, Any]]:
        """Search federal jobs using USAJOBS API with Authorization-Key and User-Agent headers."""
        if not self.enabled:
            return []

        params: Dict[str, Any] = {
            "Page": max(1, page),
            "ResultsPerPage": max(1, min(results_per_page, 500)),
            "SortField": sort_field,
            "SortDirection": sort_direction,
            "Fields": "full",
        }
        if query:
            params["Keyword"] = query
        if position_title:
            params["PositionTitle"] = position_title
        if location:
            params["LocationName"] = location
        if remote_only:
            params["RemoteIndicator"] = "True"
        if job_category_code:
            params["JobCategoryCode"] = job_category_code
        if who_may_apply:
            params["WhoMayApply"] = who_may_apply
        if hiring_path:
            params["HiringPath"] = hiring_path
        if min_salary:
            params["RemunerationMinimumAmount"] = int(min_salary)
        if max_salary:
            params["RemunerationMaximumAmount"] = int(max_salary)

        headers = {
            "Authorization-Key": self.api_key,
            "User-Agent": self.email,
            "Host": "data.usajobs.gov",
        }

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(USAJOBS_BASE, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()

        search_result = payload.get("SearchResult", {})
        raw_items = search_result.get("SearchResultItems", [])
        return [normalize_job(item, "usajobs") for item in raw_items]


async def search_all(*, query: str, location: Optional[str] = None,
                     max_age: int = 30, limit: int = 50) -> Dict[str, List[Dict[str, Any]]]:
    """Sequentially query all providers; each provider may independently fail."""
    results: Dict[str, List[Dict[str, Any]]] = {
        "jobdataapi": [],
        "aidevboard": [],
        "fantastic_jobs": [],
        "arbeitnow": [],
        "careerjet": [],
        "usajobs": [],
    }
    jobdata = JobDataAPIClient()
    aidev = AIDevBoardClient()
    fantastic = FantasticJobsClient()
    arbeitnow = ArbeitnowClient()
    careerjet = CareerjetClient()
    usajobs = USAJobsClient()

    try:
        results["jobdataapi"] = await jobdata.search(query=query, location=location, max_age=max_age, page_size=limit)
    except Exception:
        pass
    try:
        results["aidevboard"] = await aidev.search(query=query, location=location, limit=limit)
    except Exception:
        pass
    try:
        results["fantastic_jobs"] = await fantastic.search(query=query, location=location, limit=limit)
    except Exception:
        pass
    try:
        results["arbeitnow"] = await arbeitnow.search(query=query, location=location, limit=limit)
    except Exception:
        pass
    try:
        results["careerjet"] = await careerjet.search(query=query, location=location, page_size=limit)
    except Exception:
        pass
    try:
        results["usajobs"] = await usajobs.search(query=query, location=location, results_per_page=limit, remote_only=True)
    except Exception:
        pass
    return results




