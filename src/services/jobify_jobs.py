"""
jobify_jobs.py — Job rows -> the Jobify `Job` shape, plus per-user match scoring.

Contract (jobify/docs/INTEGRATION.md, jobify/src/services/jobService.js):
  Job = { id, title, company, location, country, experience, salary, skills[], match,
          workMode: "Remote"|"Hybrid"|"Onsite", type: "Full-time"|"Internship",
          postedDaysAgo, description, responsibilities[] }

Scraped rows are often sparse (no salary / work_mode / experience_level), so every
derived field degrades to an honest placeholder instead of guessing.

Match % (0-100, deterministic, one place): computed from the user's CandidateProfile.
  skills overlap 60 · title vs target roles 20 · years fit 10 · location / remote fit 10
No profile -> 0 (the frontend has no onboarding yet; see CLAUDE.md §9 Phase 1).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from src.models import CandidateProfile, Job, User

INDIA_HINTS = ("india", "bengaluru", "bangalore", "mumbai", "delhi", "hyderabad", "pune", "chennai",
               "noida", "gurgaon", "gurugram", "kolkata", "ahmedabad")
USA_HINTS = ("usa", "u.s.", "united states", "san francisco", "new york", "seattle", "austin", "boston")
COUNTRY_ALIASES = {"us": "USA", "usa": "USA", "united states": "USA", "uk": "UK", "united kingdom": "UK"}

# Rough display/filter conversion to USD; the frontend uses the same ballpark rates.
USD_PER = {"USD": 1.0, "INR": 1 / 83, "GBP": 1.25, "EUR": 1.08, "SGD": 0.74, "CAD": 0.73, "AUD": 0.66}
SYMBOL = {"USD": "$", "INR": "₹", "GBP": "£", "EUR": "€"}

_BULLET = re.compile(r"^\s*(?:[-*•▪◦]|\d+[.)])\s+(.{8,240})$")


def _json_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [str(v).strip() for v in val if str(v).strip()]
    except (ValueError, TypeError):
        pass
    return [p.strip() for p in re.split(r"[,;|]", raw) if p.strip()]


def job_skills(job: Job) -> List[str]:
    return list(dict.fromkeys(s.lower() for s in _json_list(job.tags)))


def job_country(job: Job) -> str:
    loc = (job.location or "").strip()
    low = loc.lower()
    if any(h in low for h in INDIA_HINTS):
        return "India"
    if any(h in low for h in USA_HINTS):
        return "USA"
    last = loc.split(",")[-1].strip() if loc else ""
    if not last or last.lower() in ("remote", "anywhere", "worldwide"):
        return "Remote"
    return COUNTRY_ALIASES.get(last.lower(), last)


def job_work_mode(job: Job) -> str:
    mode = (job.work_mode or "").lower()
    if "hybrid" in mode:
        return "Hybrid"
    if job.has_remote or "remote" in mode or "remote" in (job.location or "").lower():
        return "Remote"
    return "Onsite"


def job_type(job: Job) -> str:
    return "Internship" if "intern" in (job.title or "").lower() else "Full-time"


def job_min_years(job: Job) -> Optional[int]:
    """Lower bound of required years, or None when unknown."""
    text = f"{job.experience_level or ''} {job.title or ''}".lower()
    m = re.search(r"(\d+)\s*(?:\+|–|-|to)?\s*\d*\s*(?:years|yrs|yoe)", text)
    if m:
        return int(m.group(1))
    if "intern" in text:
        return 0
    if any(k in text for k in ("junior", "entry", "associate")):
        return 0
    if "senior" in text or "sr." in text:
        return 5
    if any(k in text for k in ("staff", "principal", "lead")):
        return 8
    return None


def job_experience(job: Job) -> str:
    if job_type(job) == "Internship":
        return "Internship"
    if job.experience_level:
        return job.experience_level
    years = job_min_years(job)
    return f"{years}+ years" if years else "Not specified"


def job_salary_usd(job: Job) -> float:
    """Best-known annual salary in USD (max of the range), 0 when unknown."""
    amount = job.salary_max or job.salary_min
    if not amount:
        return 0.0
    return float(amount) * USD_PER.get((job.salary_currency or "USD").upper(), 1.0)


def _fmt_money(amount: float, currency: str) -> str:
    sym = SYMBOL.get(currency, f"{currency} ")
    if currency == "INR":
        return f"{sym}{amount / 100000:.1f}L".replace(".0L", "L")
    return f"{sym}{amount / 1000:.0f}K"


def job_salary(job: Job) -> str:
    cur = (job.salary_currency or "USD").upper()
    lo, hi = job.salary_min, job.salary_max
    if lo and hi and lo != hi:
        return f"{_fmt_money(lo, cur)}–{_fmt_money(hi, cur)}"
    if lo or hi:
        return _fmt_money(lo or hi, cur)
    return "Not disclosed"


def job_posted_days_ago(job: Job, now: Optional[datetime] = None) -> int:
    ref = job.posted_date or job.fetched_at
    if not ref:
        return 0
    now = now or datetime.utcnow()
    return max(0, (now - ref.replace(tzinfo=None)).days)


def job_responsibilities(job: Job, limit: int = 6) -> List[str]:
    out = []
    for line in (job.description or "").splitlines():
        m = _BULLET.match(line)
        if m:
            out.append(m.group(1).strip())
            if len(out) >= limit:
                break
    return out


# --- match -------------------------------------------------------------------

def profile_for(db, user: User) -> Optional[CandidateProfile]:
    """Same linkage convention as auth_router (clerk id, or user_<id>)."""
    keys = [k for k in (user.clerk_user_id, f"user_{user.id}") if k]
    return db.query(CandidateProfile).filter(CandidateProfile.user_identifier.in_(keys)).first()


def match_score(job: Job, profile: Optional[CandidateProfile]) -> int:
    if profile is None:
        return 0
    have = {s.lower() for s in _json_list(profile.skills)}
    want = job_skills(job)
    haystack = f"{job.title or ''} {job.description or ''}".lower()
    if want:
        skills = len(have & set(want)) / len(want)
    elif have:
        # No structured tags: fall back to profile-skill mentions in the posting text.
        skills = min(1.0, sum(1 for s in have if s in haystack) / max(3, min(len(have), 8)))
    else:
        skills = 0.0

    roles = [r.lower() for r in _json_list(profile.target_roles)]
    title = (job.title or "").lower()
    role = 1.0 if any(r in title or title in r for r in roles) else (
        0.5 if any(w in title for r in roles for w in r.split() if len(w) > 3) else 0.0)

    need = job_min_years(job)
    have_years = profile.years_of_experience
    if need is None or have_years is None:
        years = 0.5
    else:
        years = 1.0 if have_years >= need else max(0.0, 1 - (need - have_years) / 4)

    targets = [t.lower() for t in _json_list(profile.target_locations)]
    if not targets:
        loc = 0.5
    else:
        jl = f"{job.location or ''} {job_country(job)}".lower()
        loc = 1.0 if (job_work_mode(job) == "Remote" and any("remote" in t for t in targets)) or any(t in jl for t in targets) else 0.0

    return round(100 * (0.60 * skills + 0.20 * role + 0.10 * years + 0.10 * loc))


def to_ui_job(job: Job, profile: Optional[CandidateProfile] = None) -> Dict[str, Any]:
    return {
        "id": str(job.id),
        "title": job.title or "",
        "company": job.company or "",
        "location": job.location or "",
        "country": job_country(job),
        "experience": job_experience(job),
        "salary": job_salary(job),
        "skills": job_skills(job),
        "match": match_score(job, profile),
        "workMode": job_work_mode(job),
        "type": job_type(job),
        "postedDaysAgo": job_posted_days_ago(job),
        "description": job.description or "",
        "responsibilities": job_responsibilities(job),
        "url": job.url or "",
    }


# --- list filtering (mirrors jobService.list in the mock) --------------------------

MATCH_ONLY_THRESHOLD = 80  # jobService.js: matchOnly keeps match >= 80

SORTERS = {
    "match": lambda j: (-j["match"],),
    "recent": lambda j: (j["postedDaysAgo"],),
    "salary": lambda j: (-j["_salary_usd"],),
    "title": lambda j: (j["title"].lower(),),
}


def filter_and_sort(
    rows: Iterable[Job],
    profile: Optional[CandidateProfile],
    *,
    work_modes: List[str],
    types: List[str],
    countries: List[str],
    skills: List[str],
    match_only: bool,
    min_salary_usd: float,
    max_years: Optional[int],
    sort: str,
) -> List[Dict[str, Any]]:
    want_skills = [s.lower() for s in skills]
    out = []
    for job in rows:
        ui = to_ui_job(job, profile)
        if work_modes and ui["workMode"] not in work_modes:
            continue
        if types and ui["type"] not in types:
            continue
        if countries and ui["country"] not in countries:
            continue
        if want_skills and not all(s in ui["skills"] for s in want_skills):
            continue
        if match_only and ui["match"] < MATCH_ONLY_THRESHOLD:
            continue
        salary_usd = job_salary_usd(job)
        if min_salary_usd and salary_usd < min_salary_usd:
            continue
        need = job_min_years(job)
        if max_years is not None and need is not None and need > max_years:
            continue
        ui["_salary_usd"] = salary_usd
        out.append(ui)
    out.sort(key=SORTERS.get(sort, SORTERS["match"]))
    for ui in out:
        ui.pop("_salary_usd", None)
    return out
