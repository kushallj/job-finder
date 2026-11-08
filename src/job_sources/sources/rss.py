"""RSS/Atom job feeds (published for syndication). Parsed with feedparser.

Every board puts the company somewhere different, so each feed has a tiny `split`
function: entry -> (role, company, location). Entries without a company are dropped
rather than guessed (CLAUDE.md: never invent company facts).
"""

from __future__ import annotations

import asyncio
import html
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import feedparser

from src.job_data_providers import normalize_job
from src.job_sources.base import CallableSource
from src.job_sources.models import SearchQuery, Tier
from src.job_sources.sources._http import get_text, html_to_text, matches

Entry = Mapping[str, Any]
Split = Callable[[Entry], tuple[str, str, str]]


def _clean(text: str | None) -> str:
    return " ".join(html.unescape(text or "").replace("\xa0", " ").split())


def _sep(sep: str, *, company_first: bool = False, last: bool = True) -> Split:
    """'Role <sep> Company' (or 'Company <sep> Role')."""
    def split(e: Entry) -> tuple[str, str, str]:
        title = _clean(e.get("title"))
        if sep not in title:
            return title, "", ""
        a, b = title.rsplit(sep, 1) if last else title.split(sep, 1)
        role, company = (b, a) if company_first else (a, b)
        return role.strip(), company.strip(), _clean(e.get("location") or e.get("region"))
    return split


def _author_company(e: Entry) -> tuple[str, str, str]:
    role = _clean(e.get("title"))
    role = re.sub(r"\s+at\s+" + re.escape(_clean(e.get("author"))) + r"$", "", role) if e.get("author") else role
    return role, _clean(e.get("author")), ""


def _jobspresso(e: Entry) -> tuple[str, str, str]:
    company, _, location = (e.get("author") or "").partition("<br>")
    return _clean(e.get("title")), _clean(company), _clean(re.sub(r"<[^>]+>|⚲", "", location))


_DRIBBBLE = re.compile(r"^(?P<company>.+?) is hiring for a position of (?P<role>.+?)(?: in (?P<loc>.+))?$")


def _dribbble(e: Entry) -> tuple[str, str, str]:
    m = _DRIBBBLE.match(_clean(e.get("title")))
    return (m["role"], m["company"], m["loc"] or "") if m else ("", "", "")


_EMPLOYER = re.compile(r"<strong>Employer:</strong>\s*([^<]+)")


def _vuejobs(e: Entry) -> tuple[str, str, str]:
    m = _EMPLOYER.search(e.get("summary") or "")
    title = _clean(e.get("title"))
    parts = [p.strip() for p in title.split("|")]
    return parts[0], _clean(m.group(1)) if m else "", parts[-1] if len(parts) > 2 else ""


def _larajobs(e: Entry) -> tuple[str, str, str]:
    return _clean(e.get("title")), _clean(e.get("job_company")), _clean(e.get("job_location"))


@dataclass(frozen=True, slots=True)
class Feed:
    name: str
    urls: tuple[str, ...]
    split: Split
    description: str
    remote: bool = False


FEEDS: tuple[Feed, ...] = (
    Feed("weworkremotely", (
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "https://weworkremotely.com/remote-jobs.rss",
    ), _sep(": ", company_first=True, last=False), "We Work Remotely", remote=True),
    Feed("hasjob", ("https://hasjob.co/feed",), _sep(" at "), "Hasjob (India)"),
    Feed("python_org", ("https://www.python.org/jobs/feed/rss/",), _sep(", "), "Python.org job board"),
    Feed("jobspresso", ("https://jobspresso.co/feed/?post_type=job_listing",), _jobspresso, "Jobspresso remote", remote=True),
    Feed("realworkfromanywhere", ("https://www.realworkfromanywhere.com/rss.xml",), _author_company,
         "Real Work From Anywhere", remote=True),
    Feed("vuejobs", ("https://vuejobs.com/feed",), _vuejobs, "VueJobs"),
    Feed("dribbble", ("https://dribbble.com/jobs.rss",), _dribbble, "Dribbble design jobs"),
    Feed("remotefirstjobs", ("https://remotefirstjobs.com/rss/jobs.rss",), _sep(" at "), "Remote First Jobs", remote=True),
    Feed("berlinstartupjobs", ("https://berlinstartupjobs.com/feed/",), _sep(" // "), "Berlin Startup Jobs"),
    Feed("golangprojects", ("https://www.golangprojects.com/rss.xml",), _sep(" @ "), "Golang Projects"),
    Feed("larajobs", ("https://larajobs.com/feed",), _larajobs, "LaraJobs (PHP/Laravel)"),
    Feed("remotepython", ("https://www.remotepython.com/latest/jobs/feed/",), _sep(" at "), "Remote Python", remote=True),
)


def _fetcher(feed: Feed):
    async def fetch(q: SearchQuery) -> list[Mapping[str, Any]]:
        texts = await asyncio.gather(*(get_text(u) for u in feed.urls), return_exceptions=True)
        if all(isinstance(t, BaseException) for t in texts):
            raise next(t for t in texts if isinstance(t, BaseException))
        rows, seen = [], set()
        for text in texts:
            if isinstance(text, BaseException):
                continue
            for e in feedparser.parse(text).entries:
                link = e.get("link") or e.get("id")
                if not link or link in seen:
                    continue
                seen.add(link)
                role, company, location = feed.split(e)
                body = html_to_text(e.get("summary") or "")
                if not role or not company or not matches(q.text, role, body):
                    continue
                rows.append(normalize_job({
                    "id": e.get("id") or link, "title": role, "company": company,
                    "location": location or ("Remote" if feed.remote else ""), "description": body, "url": link,
                    "published": e.get("published") or e.get("updated"),
                    "tags": [t.get("term") for t in e.get("tags") or [] if t.get("term")],
                    **({"work_mode": "remote", "remote": True} if feed.remote else {}),
                }, feed.name))
                if len(rows) >= q.limit:
                    return rows
        return rows
    return fetch


SOURCES: tuple[CallableSource, ...] = tuple(
    CallableSource(f.name, Tier.PUBLIC_FEED, _fetcher(f), description=f"{f.description} (RSS)") for f in FEEDS
)
