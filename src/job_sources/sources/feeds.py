"""Public JSON job APIs that need no key. Each is documented by its provider for programmatic use."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from src.job_data_providers import ArbeitnowClient, normalize_job
from src.job_sources.base import CallableSource
from src.job_sources.models import SearchQuery, Tier
from src.job_sources.sources._http import get_json, html_to_text, matches

Rows = list[Mapping[str, Any]]


def _epoch(ts: Any) -> str | None:
    try:
        return datetime.fromtimestamp(float(ts), tz=UTC).isoformat() if ts else None
    except (TypeError, ValueError, OSError):
        return None


async def _arbeitnow(q: SearchQuery) -> Rows:
    return await ArbeitnowClient().search(query=q.text, location=q.location or None, limit=q.limit)


async def _remotive(q: SearchQuery) -> Rows:
    data = await get_json("https://remotive.com/api/remote-jobs", params={"search": q.text, "limit": q.limit})
    return [normalize_job({**j, "company": j.get("company_name"), "description": html_to_text(j.get("description")),
                           "location": j.get("candidate_required_location") or "Remote",
                           "published": j.get("publication_date"), "work_mode": "remote", "remote": True}, "remotive")
            for j in data.get("jobs", [])]


async def _remoteok(q: SearchQuery) -> Rows:
    """remoteok.com/api. Terms: link back to Remote OK (the stored url is the Remote OK page)."""
    data = await get_json("https://remoteok.com/api")
    rows = []
    for j in data:
        if not isinstance(j, dict) or not j.get("position"):
            continue  # first element is the legal notice
        text = html_to_text(j.get("description"))
        if not matches(q.text, j.get("position"), " ".join(j.get("tags") or []), text):
            continue
        rows.append(normalize_job({
            "id": j.get("id"), "title": j.get("position"), "company": j.get("company"),
            "location": j.get("location") or "Remote", "description": text, "url": j.get("url"),
            "date": j.get("date"), "tags": j.get("tags") or [], "work_mode": "remote", "remote": True,
            "salary_min": j.get("salary_min") or None, "salary_max": j.get("salary_max") or None,
            "salary_currency": "USD" if j.get("salary_min") else None,
        }, "remoteok"))
    return rows[: q.limit]


async def _jobicy(q: SearchQuery) -> Rows:
    tag = q.text.split()[0] if q.text else ""
    data = await get_json("https://jobicy.com/api/v2/remote-jobs", params={"count": min(q.limit, 50), "tag": tag})
    return [normalize_job({
        "id": j.get("id"), "title": j.get("jobTitle"), "company": j.get("companyName"),
        "location": j.get("jobGeo") or "Remote", "description": html_to_text(j.get("jobDescription")),
        "url": j.get("url"), "published": j.get("pubDate"), "experience_level": j.get("jobLevel"),
        "tags": (j.get("jobIndustry") or []) + (j.get("jobType") or []), "work_mode": "remote", "remote": True,
        "salary_min": j.get("annualSalaryMin"), "salary_max": j.get("annualSalaryMax"),
        "salary_currency": j.get("salaryCurrency"),
    }, "jobicy") for j in data.get("jobs", [])]


async def _himalayas(q: SearchQuery) -> Rows:
    data = await get_json("https://himalayas.app/jobs/api/search", params={"q": q.text, "limit": min(q.limit, 50)})
    return [normalize_job({
        "id": j.get("guid"), "title": j.get("title"), "company": j.get("companyName"),
        "location": ", ".join(j.get("locationRestrictions") or []) or "Remote",
        "description": html_to_text(j.get("description")), "url": j.get("applicationLink") or j.get("guid"),
        "published": _epoch(j.get("pubDate")), "expired": _epoch(j.get("expiryDate")),
        "salary_min": j.get("minSalary"), "salary_max": j.get("maxSalary"), "salary_currency": j.get("currency"),
        "experience_level": ", ".join(j.get("seniority") or []) or None, "tags": j.get("categories") or [],
        "work_mode": "remote", "remote": True,
    }, "himalayas") for j in data.get("jobs", [])]


async def _workingnomads(q: SearchQuery) -> Rows:
    data = await get_json("https://www.workingnomads.com/api/exposed_jobs/")
    rows = []
    for j in data:
        text = html_to_text(j.get("description"))
        if matches(q.text, j.get("title"), j.get("tags"), text):
            rows.append(normalize_job({
                "url": j.get("url"), "title": j.get("title"), "company": j.get("company_name"),
                "location": j.get("location") or "Remote", "description": text, "posted": j.get("pub_date"),
                "tags": (j.get("tags") or "").split(","), "work_mode": "remote", "remote": True,
            }, "workingnomads"))
    return rows[: q.limit]


_LANDING_COMPANY = re.compile(r"landing\.jobs/at/([^/]+)/")


async def _landingjobs(q: SearchQuery) -> Rows:
    data = await get_json("https://landing.jobs/api/v1/jobs", params={"limit": 50})
    rows = []
    for j in data:
        m = _LANDING_COMPANY.search(j.get("url") or "")
        text = html_to_text((j.get("role_description") or "") + (j.get("main_requirements") or ""))
        if not m or not matches(q.text, j.get("title"), " ".join(j.get("tags") or []), text):
            continue
        locs = j.get("locations") or []
        rows.append(normalize_job({
            "id": j.get("id"), "title": j.get("title"), "company": m.group(1).replace("-", " ").title(),
            "location": ", ".join(f"{loc.get('city')}, {loc.get('country_code')}" for loc in locs) or ("Remote" if j.get("remote") else ""),
            "description": text, "url": j.get("url"), "published_at": j.get("published_at"),
            "expired": j.get("expires_at"), "tags": j.get("tags") or [], "remote": j.get("remote"),
            "salary_min": j.get("gross_salary_low"), "salary_max": j.get("gross_salary_high"),
            "salary_currency": j.get("currency_code"),
        }, "landingjobs"))
    return rows[: q.limit]


_HN_COMPANY = re.compile(r"^(.+?)\s+(?:\(YC [^)]*\)\s+)?(?:is|are)\s+hiring", re.IGNORECASE)


async def _hn_jobs(q: SearchQuery) -> Rows:
    """YC-company job posts on Hacker News (official Algolia HN API)."""
    data = await get_json("https://hn.algolia.com/api/v1/search_by_date",
                          params={"tags": "job", "hitsPerPage": 100, "query": q.text})
    rows = []
    for h in data.get("hits", []):
        m = _HN_COMPANY.match(h.get("title") or "")
        if m:
            rows.append(normalize_job({
                "id": h.get("objectID"), "title": h.get("title"), "company": m.group(1).strip(),
                "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                "created_at": h.get("created_at"), "description": html_to_text(h.get("story_text")),
            }, "hn_jobs"))
    return rows[: q.limit]


async def _hn_whoishiring(q: SearchQuery) -> Rows:
    """Top-level comments of the latest 'Ask HN: Who is hiring?' thread ("Company | Role | Location | ...")."""
    stories = await get_json("https://hn.algolia.com/api/v1/search_by_date",
                             params={"tags": "story,author_whoishiring", "hitsPerPage": 5})
    story = next((s for s in stories.get("hits", []) if "who is hiring" in (s.get("title") or "").lower()), None)
    if story is None:
        return []
    sid = story["objectID"]
    data = await get_json("https://hn.algolia.com/api/v1/search",
                          params={"tags": f"comment,story_{sid}", "query": q.text, "hitsPerPage": 200})
    rows = []
    for c in data.get("hits", []):
        if str(c.get("parent_id")) != str(sid):
            continue
        text = html_to_text(c.get("comment_text"))
        parts = [p.strip() for p in text.split("\n", 1)[0].split("|")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            continue
        rows.append(normalize_job({
            "id": c.get("objectID"), "company": parts[0][:200], "title": parts[1][:200],
            "location": parts[2][:200] if len(parts) > 2 else "", "description": text,
            "url": f"https://news.ycombinator.com/item?id={c.get('objectID')}", "created_at": c.get("created_at"),
            "remote": True if "remote" in text.split("\n", 1)[0].lower() else None,
        }, "hn_whoishiring"))
    return rows[: q.limit]


async def _jobtech_se(q: SearchQuery) -> Rows:
    """Arbetsförmedlingen (Swedish public employment service) JobTech API."""
    params: dict[str, Any] = {"q": f"{q.text} {q.location}".strip(), "limit": min(q.limit, 100)}
    data = await get_json("https://jobsearch.api.jobtechdev.se/search", params=params)
    rows = []
    for j in data.get("hits", []):
        addr = j.get("workplace_address") or {}
        rows.append(normalize_job({
            "id": j.get("id"), "title": j.get("headline"), "company": (j.get("employer") or {}).get("name"),
            "location": ", ".join(p for p in (addr.get("municipality"), addr.get("region"), addr.get("country")) if p),
            "description": (j.get("description") or {}).get("text"), "url": j.get("webpage_url"),
            "published": j.get("publication_date"), "expired": j.get("application_deadline"),
        }, "jobtech_se"))
    return rows


async def _getonboard(q: SearchQuery) -> Rows:
    """Get on Board (LatAm tech jobs) public API."""
    data = await get_json("https://www.getonbrd.com/api/v0/search/jobs",
                          params={"query": q.text, "per_page": min(q.limit, 100), "expand": '["company"]'})
    rows = []
    for j in data.get("data", []):
        a = j.get("attributes") or {}
        company = ((a.get("company") or {}).get("data") or {}).get("attributes") or {}
        rows.append(normalize_job({
            "id": j.get("id"), "title": a.get("title"), "company": company.get("name"),
            "location": ", ".join(filter(None, [a.get("city"), a.get("country")])) or ("Remote" if a.get("remote") else ""),
            "description": html_to_text((a.get("description") or "") + (a.get("functions") or "")),
            "url": (j.get("links") or {}).get("public_url"), "published": _epoch(a.get("published_at")),
            "remote": a.get("remote"), "salary_min": a.get("min_salary"), "salary_max": a.get("max_salary"),
            "salary_currency": "USD" if a.get("min_salary") else None,
        }, "getonboard"))
    return rows


async def _jobscollider(q: SearchQuery) -> Rows:
    data = await get_json("https://jobscollider.com/api/search-jobs", params={"title": q.text})
    return [normalize_job({
        "id": j.get("id"), "title": j.get("title"), "company": j.get("company_name"),
        "location": ", ".join(j.get("locations") or []) or "Remote", "description": html_to_text(j.get("description")),
        "url": j.get("url"), "published_at": j.get("published_at"), "experience_level": j.get("seniority"),
        "tags": [j["category"]] if j.get("category") else [], "work_mode": "remote", "remote": True,
        "salary_min": j.get("salary_min") or None, "salary_max": j.get("salary_max") or None,
    }, "jobscollider") for j in data.get("jobs", [])[: q.limit]]


SOURCES: tuple[CallableSource, ...] = (
    CallableSource("arbeitnow", Tier.PUBLIC_FEED, _arbeitnow, description="Arbeitnow (EU)"),
    CallableSource("remotive", Tier.PUBLIC_FEED, _remotive, description="Remotive remote jobs"),
    CallableSource("remoteok", Tier.PUBLIC_FEED, _remoteok, description="Remote OK"),
    CallableSource("jobicy", Tier.PUBLIC_FEED, _jobicy, description="Jobicy remote jobs"),
    CallableSource("himalayas", Tier.PUBLIC_FEED, _himalayas, description="Himalayas remote jobs"),
    CallableSource("workingnomads", Tier.PUBLIC_FEED, _workingnomads, description="Working Nomads"),
    CallableSource("landingjobs", Tier.PUBLIC_FEED, _landingjobs, description="Landing.jobs (EU tech)"),
    CallableSource("hn_jobs", Tier.PUBLIC_FEED, _hn_jobs, description="Hacker News YC job posts"),
    CallableSource("hn_whoishiring", Tier.PUBLIC_FEED, _hn_whoishiring, description="HN 'Who is hiring?' thread"),
    CallableSource("jobtech_se", Tier.PUBLIC_FEED, _jobtech_se, description="JobTech / Arbetsförmedlingen (SE)"),
    CallableSource("getonboard", Tier.PUBLIC_FEED, _getonboard, description="Get on Board (LatAm tech)"),
    CallableSource("jobscollider", Tier.PUBLIC_FEED, _jobscollider, description="JobsCollider remote jobs"),
)
