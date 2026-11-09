"""Official, key-based job APIs. Each runs only when its key(s) are set in the environment.

Field mapping follows each provider's documented response; rows go through
`job_data_providers.normalize_job` so salary/remote/tags land in the same columns.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from src.config import settings
from src.job_data_providers import (
    AIDevBoardClient,
    CareerjetClient,
    FantasticJobsClient,
    JobDataAPIClient,
    USAJobsClient,
    normalize_job,
)
from src.job_sources.base import CallableSource
from src.job_sources.models import SearchQuery, Tier
from src.job_sources.sources._http import get_json, html_to_text, request

Rows = list[Mapping[str, Any]]


def _has(*keys: str):
    return lambda: all(getattr(settings, k, None) for k in keys)


# --- existing clients (src/job_data_providers.py) -----------------------------------------

async def _jobdataapi(q: SearchQuery) -> Rows:
    return await JobDataAPIClient().search(query=q.text, location=q.location or None,
                                           max_age=q.max_age_days, page_size=q.limit)


async def _aidevboard(q: SearchQuery) -> Rows:
    return await AIDevBoardClient().search(query=q.text, location=q.location or None, limit=q.limit)


async def _fantastic_jobs(q: SearchQuery) -> Rows:
    return await FantasticJobsClient().search(query=q.text, location=q.location or None, limit=q.limit)


async def _careerjet(q: SearchQuery) -> Rows:
    return await CareerjetClient().search(query=q.text, location=q.location or None, page_size=q.limit)


async def _usajobs(q: SearchQuery) -> Rows:
    return await USAJobsClient().search(query=q.text, location=q.location or None,
                                        results_per_page=q.limit, remote_only=False)


# --- Adzuna (developer.adzuna.com) -------------------------------------------------------------

ADZUNA_CURRENCY = {"in": "INR", "gb": "GBP", "us": "USD", "de": "EUR", "ca": "CAD", "au": "AUD", "sg": "SGD"}


async def _adzuna(q: SearchQuery) -> Rows:
    country = (settings.adzuna_country or "in").lower()
    params: dict[str, Any] = {"app_id": settings.adzuna_app_id, "app_key": settings.adzuna_app_key,
                              "results_per_page": min(q.limit, 50), "what": q.text, "max_days_old": q.max_age_days}
    if q.location:
        params["where"] = q.location
    data = await get_json(f"https://api.adzuna.com/v1/api/jobs/{country}/search/1", params=params)
    currency = ADZUNA_CURRENCY.get(country)
    return [normalize_job({
        "id": j.get("id"), "title": j.get("title"),
        "company": (j.get("company") or {}).get("display_name"),
        "location": (j.get("location") or {}).get("display_name"),
        "description": j.get("description"), "url": j.get("redirect_url"), "created_at": j.get("created"),
        "salary_min": j.get("salary_min"), "salary_max": j.get("salary_max"),
        "salary_currency": currency if j.get("salary_min") or j.get("salary_max") else None,
        "tags": [j["category"]["label"]] if (j.get("category") or {}).get("label") else [],
    }, "adzuna") for j in data.get("results", [])]


# --- Reed (reed.co.uk/developers) : HTTP Basic, key as username -------------------------------

async def _reed(q: SearchQuery) -> Rows:
    params: dict[str, Any] = {"keywords": q.text, "resultsToTake": min(q.limit, 100)}
    if q.location:
        params["locationName"] = q.location
    res = await request("GET", "https://www.reed.co.uk/api/1.0/search", params=params,
                        auth=(settings.reed_api_key or "", ""))
    rows = []
    for j in res.json().get("results", []):
        posted = j.get("date")  # dd/mm/yyyy
        if posted and posted.count("/") == 2:
            d, m, y = posted.split("/")
            posted = f"{y}-{m}-{d}"
        rows.append(normalize_job({
            "id": j.get("jobId"), "title": j.get("jobTitle"), "company": j.get("employerName"),
            "location": j.get("locationName"), "description": j.get("jobDescription"), "url": j.get("jobUrl"),
            "posted": posted, "salary_min": j.get("minimumSalary"), "salary_max": j.get("maximumSalary"),
            "salary_currency": j.get("currency") or ("GBP" if j.get("minimumSalary") else None),
        }, "reed"))
    return rows


# --- Jooble (jooble.org/api/about) : key in the path ---------------------------------------------

async def _jooble(q: SearchQuery) -> Rows:
    body = {"keywords": q.text, "location": q.location, "page": "1", "ResultOnPage": str(min(q.limit, 50))}
    res = await request("POST", f"https://{settings.jooble_host}/api/{settings.jooble_api_key}", json=body)
    return [normalize_job({
        "id": j.get("id"), "title": j.get("title"), "company": j.get("company"), "location": j.get("location"),
        "description": html_to_text(j.get("snippet")), "url": j.get("link"), "posted": j.get("updated"),
        "tags": [j["type"]] if j.get("type") else [],
    }, "jooble") for j in res.json().get("jobs", [])]


# --- Findwork (findwork.dev/developers) : Token auth ------------------------------------------------

async def _findwork(q: SearchQuery) -> Rows:
    params: dict[str, Any] = {"search": q.text, "sort_by": "date"}
    if q.location:
        params["location"] = q.location
    data = await get_json("https://findwork.dev/api/jobs/", params=params,
                          headers={"Authorization": f"Token {settings.findwork_api_key}"})
    return [normalize_job({
        "id": j.get("id"), "title": j.get("role"), "company": j.get("company_name"), "location": j.get("location"),
        "description": html_to_text(j.get("text")), "url": j.get("url"), "posted": j.get("date_posted"),
        "remote": j.get("remote"), "tags": j.get("keywords") or [],
    }, "findwork") for j in data.get("results", [])[: q.limit]]


# --- CareerOneStop (US Dept. of Labor) : user id + bearer token -------------------------------------

async def _careeronestop(q: SearchQuery) -> Rows:
    from urllib.parse import quote

    loc = quote(q.location or "US")
    url = (f"https://api.careeronestop.org/v2/jobsearch/{settings.careeronestop_user_id}/{quote(q.text)}/"
           f"{loc}/50/accquisitiondate/DESC/0/{min(q.limit, 100)}/{q.max_age_days}")
    data = await get_json(url, headers={"Authorization": f"Bearer {settings.careeronestop_api_token}"})
    return [normalize_job({
        "id": j.get("JvId"), "title": j.get("JobTitle"), "company": j.get("Company"), "location": j.get("Location"),
        "url": j.get("URL"), "posted": j.get("AccquisitionDate"), "description": j.get("Description") or "",
    }, "careeronestop") for j in data.get("Jobs", []) or []]


# --- JSearch on RapidAPI (rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) ----------------------------

async def _jsearch(q: SearchQuery) -> Rows:
    query = f"{q.text} in {q.location}" if q.location else q.text
    days = "today" if q.max_age_days <= 1 else "3days" if q.max_age_days <= 3 else "week" if q.max_age_days <= 7 else "month"
    data = await get_json("https://jsearch.p.rapidapi.com/search",
                          params={"query": query, "page": 1, "num_pages": 1, "date_posted": days},
                          headers={"X-RapidAPI-Key": settings.rapidapi_key or "",
                                   "X-RapidAPI-Host": "jsearch.p.rapidapi.com"})
    return [normalize_job({
        "id": j.get("job_id"), "title": j.get("job_title"), "company": j.get("employer_name"),
        "location": ", ".join(p for p in (j.get("job_city"), j.get("job_state"), j.get("job_country")) if p),
        "description": j.get("job_description"), "url": j.get("job_apply_link"),
        "posted": j.get("job_posted_at_datetime_utc"), "remote": j.get("job_is_remote"),
        "salary_min": j.get("job_min_salary"), "salary_max": j.get("job_max_salary"),
        "salary_currency": j.get("job_salary_currency"), "company_website": j.get("employer_website"),
    }, "jsearch") for j in data.get("data", [])[: q.limit]]


# --- TheirStack (theirstack.com) : bearer; every returned job costs a credit ----------------------

async def _theirstack(q: SearchQuery) -> Rows:
    body: dict[str, Any] = {"job_title_or": [q.text], "posted_at_max_age_days": q.max_age_days,
                            "limit": min(q.limit, settings.theirstack_max_results), "page": 0}
    if q.location:
        body["job_location_pattern_or"] = [q.location]
    res = await request("POST", "https://api.theirstack.com/v1/jobs/search", json=body,
                        headers={"Authorization": f"Bearer {settings.theirstack_api_key}"})
    return [normalize_job({
        "id": j.get("id"), "title": j.get("job_title"),
        "company": (j.get("company_object") or {}).get("name") or j.get("company"),
        "location": j.get("location") or j.get("short_location"), "description": j.get("description"),
        "url": j.get("url") or j.get("final_url"), "posted": j.get("date_posted"), "remote": j.get("remote"),
        "salary_min": j.get("min_annual_salary_usd"), "salary_max": j.get("max_annual_salary_usd"),
        "salary_currency": "USD" if j.get("min_annual_salary_usd") else None,
        "experience_level": j.get("seniority"),
    }, "theirstack") for j in res.json().get("data", [])]


# --- France Travail (francetravail.io) : OAuth2 client credentials ---------------------------------

_FT_TOKEN: dict[str, Any] = {"value": None, "expires": 0.0}


async def _france_travail_token() -> str:
    if _FT_TOKEN["value"] and time.monotonic() < _FT_TOKEN["expires"]:
        return _FT_TOKEN["value"]
    res = await request("POST", "https://entreprise.francetravail.fr/connexion/oauth2/access_token",
                        params={"realm": "/partenaire"},
                        data={"grant_type": "client_credentials", "client_id": settings.france_travail_client_id,
                              "client_secret": settings.france_travail_client_secret,
                              "scope": "api_offresdemploiv2 o2dsoffre"})
    payload = res.json()
    _FT_TOKEN.update(value=payload["access_token"], expires=time.monotonic() + int(payload.get("expires_in", 1200)) - 60)
    return payload["access_token"]


async def _france_travail(q: SearchQuery) -> Rows:
    token = await _france_travail_token()
    res = await request("GET", "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search",
                        params={"motsCles": q.text, "range": f"0-{min(q.limit, 150) - 1}"},
                        headers={"Authorization": f"Bearer {token}"})
    if res.status_code == 204:
        return []
    return [normalize_job({
        "id": j.get("id"), "title": j.get("intitule"), "company": (j.get("entreprise") or {}).get("nom"),
        "location": (j.get("lieuTravail") or {}).get("libelle"), "description": j.get("description"),
        "url": (j.get("origineOffre") or {}).get("urlOrigine"), "posted": j.get("dateCreation"),
        "tags": [j["typeContratLibelle"]] if j.get("typeContratLibelle") else [],
    }, "france_travail") for j in res.json().get("resultats", [])]


SOURCES: tuple[CallableSource, ...] = (
    CallableSource("jobdataapi", Tier.OFFICIAL_API, _jobdataapi, _has("jobdata_api_key"), "jobdataapi.com"),
    CallableSource("aidevboard", Tier.OFFICIAL_API, _aidevboard, _has("aidevboard_api_key"), "AI/ML jobs board"),
    CallableSource("fantastic_jobs", Tier.OFFICIAL_API, _fantastic_jobs,
                   lambda: FantasticJobsClient().enabled, "ATS + board aggregator"),
    CallableSource("careerjet", Tier.OFFICIAL_API, _careerjet, _has("careerjet_api_key"), "Careerjet partner API"),
    CallableSource("usajobs", Tier.OFFICIAL_API, _usajobs, _has("usajobs_api_key"), "US federal jobs"),
    CallableSource("adzuna", Tier.OFFICIAL_API, _adzuna, _has("adzuna_app_id", "adzuna_app_key"), "Adzuna (16 countries)"),
    CallableSource("reed", Tier.OFFICIAL_API, _reed, _has("reed_api_key"), "Reed.co.uk (UK)"),
    CallableSource("jooble", Tier.OFFICIAL_API, _jooble, _has("jooble_api_key"), "Jooble aggregator (70 countries)"),
    CallableSource("findwork", Tier.OFFICIAL_API, _findwork, _has("findwork_api_key"), "Findwork.dev tech jobs"),
    CallableSource("careeronestop", Tier.OFFICIAL_API, _careeronestop,
                   _has("careeronestop_user_id", "careeronestop_api_token"), "CareerOneStop (US DOL)"),
    CallableSource("jsearch", Tier.OFFICIAL_API, _jsearch, _has("rapidapi_key"), "JSearch via RapidAPI"),
    CallableSource("theirstack", Tier.OFFICIAL_API, _theirstack, _has("theirstack_api_key"),
                   "TheirStack (credit per job; capped by THEIRSTACK_MAX_RESULTS)"),
    CallableSource("france_travail", Tier.OFFICIAL_API, _france_travail,
                   _has("france_travail_client_id", "france_travail_client_secret"), "France Travail (FR)"),
)
