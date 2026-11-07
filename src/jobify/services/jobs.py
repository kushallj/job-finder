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
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional

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


@dataclass(frozen=True, slots=True)
class MatchProfile:
    """A CandidateProfile parsed once per request.

    The profile columns are JSON text; parsing them for every job row made list scoring
    O(rows x profile size). Build this once with `MatchProfile.of(profile)` and reuse it.
    """

    skills: frozenset[str]
    roles: tuple[str, ...]
    role_words: tuple[str, ...]
    targets: tuple[str, ...]
    years: Optional[float]

    @classmethod
    def of(cls, profile: "CandidateProfile | MatchProfile | None") -> Optional["MatchProfile"]:
        if profile is None or isinstance(profile, MatchProfile):
            return profile
        roles = tuple(r.lower() for r in _json_list(profile.target_roles))
        return cls(
            skills=frozenset(s.lower() for s in _json_list(profile.skills)),
            roles=roles,
            role_words=tuple(w for r in roles for w in r.split() if len(w) > 3),
            targets=tuple(t.lower() for t in _json_list(profile.target_locations)),
            years=profile.years_of_experience,
        )


def _score(job: Job, mp: MatchProfile, want: List[str], need: Optional[int], mode: str, country: str) -> int:
    """Weighted match from precomputed job facts (see module docstring for the weights)."""
    if want:
        skills = len(mp.skills.intersection(want)) / len(want)
    elif mp.skills:
        # No structured tags: fall back to profile-skill mentions in the posting text.
        haystack = f"{job.title or ''} {job.description or ''}".lower()
        skills = min(1.0, sum(1 for s in mp.skills if s in haystack) / max(3, min(len(mp.skills), 8)))
    else:
        skills = 0.0

    title = (job.title or "").lower()
    if any(r in title or title in r for r in mp.roles):
        role = 1.0
    elif any(w in title for w in mp.role_words):
        role = 0.5
    else:
        role = 0.0

    if need is None or mp.years is None:
        years = 0.5
    else:
        years = 1.0 if mp.years >= need else max(0.0, 1 - (need - mp.years) / 4)

    if not mp.targets:
        loc = 0.5
    else:
        where = f"{job.location or ''} {country}".lower()
        remote_ok = mode == "Remote" and any("remote" in t for t in mp.targets)
        loc = 1.0 if remote_ok or any(t in where for t in mp.targets) else 0.0

    return round(100 * (0.60 * skills + 0.20 * role + 0.10 * years + 0.10 * loc))


def match_score(job: Job, profile: "CandidateProfile | MatchProfile | None") -> int:
    mp = MatchProfile.of(profile)
    if mp is None:
        return 0
    return _score(job, mp, job_skills(job), job_min_years(job), job_work_mode(job), job_country(job))


def to_ui_job(job: Job, profile: "CandidateProfile | MatchProfile | None" = None) -> Dict[str, Any]:
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

@dataclass(slots=True)
class _Candidate:
    """Cheap per-row facts used to filter and sort. The full UI card (description,
    responsibilities regex, salary text) is only built for rows on the requested page."""

    job: Job
    match: int
    salary_usd: float
    posted_days: int


SORTERS: Dict[str, Callable[[_Candidate], Any]] = {
    "match": lambda c: -c.match,
    "recent": lambda c: c.posted_days,
    "salary": lambda c: -c.salary_usd,
    "title": lambda c: (c.job.title or "").lower(),
}


def _candidates(
    rows: Iterable[Job],
    profile: "CandidateProfile | MatchProfile | None",
    *,
    work_modes: List[str],
    types: List[str],
    countries: List[str],
    skills: List[str],
    match_only: bool,
    min_salary_usd: float,
    max_years: Optional[int],
    sort: str,
) -> List[_Candidate]:
    """Filter + sort rows on derived facts, cheapest checks first. One pass, O(rows)."""
    mp = MatchProfile.of(profile)
    want_skills = [s.lower() for s in skills]
    now = datetime.utcnow()
    out: List[_Candidate] = []
    for job in rows:
        mode = job_work_mode(job)
        if work_modes and mode not in work_modes:
            continue
        if types and job_type(job) not in types:
            continue
        country = job_country(job)
        if countries and country not in countries:
            continue
        tags = job_skills(job)
        if want_skills and not all(s in tags for s in want_skills):
            continue
        salary_usd = job_salary_usd(job)
        if min_salary_usd and salary_usd < min_salary_usd:
            continue
        need = job_min_years(job)
        if max_years is not None and need is not None and need > max_years:
            continue
        match = _score(job, mp, tags, need, mode, country) if mp else 0
        if match_only and match < MATCH_ONLY_THRESHOLD:
            continue
        out.append(_Candidate(job, match, salary_usd, job_posted_days_ago(job, now)))
    out.sort(key=SORTERS.get(sort, SORTERS["match"]))  # stable: ties keep newest-first order
    return out


def filter_and_sort(rows: Iterable[Job], profile: "CandidateProfile | MatchProfile | None", **filters: Any) -> List[Dict[str, Any]]:
    """Every matching job as a UI card (kept for callers that need the full list)."""
    mp = MatchProfile.of(profile)
    return [to_ui_job(c.job, mp) for c in _candidates(rows, mp, **filters)]


def list_page(
    rows: Iterable[Job],
    profile: "CandidateProfile | MatchProfile | None",
    *,
    page: int,
    page_size: int,
    **filters: Any,
) -> Dict[str, Any]:
    """Paginated `{items,total,page,pageSize}`; builds UI cards only for the page slice."""
    mp = MatchProfile.of(profile)
    matched = _candidates(rows, mp, **filters)
    start = (page - 1) * page_size
    items = [to_ui_job(c.job, mp) for c in matched[start:start + page_size]]
    return {"items": items, "total": len(matched), "page": page, "pageSize": page_size}
