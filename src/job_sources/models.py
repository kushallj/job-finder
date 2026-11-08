"""Value types shared by every job source: the query, the canonical job record, run reports."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields
from datetime import datetime
from enum import StrEnum
from typing import Any

from src.job_data_providers import _dt as parse_datetime


class Tier(StrEnum):
    """How a source gets its data. Decides whether it may run by default (CLAUDE.md section 1)."""

    OFFICIAL_API = "official_api"  # documented, key-based API
    PUBLIC_FEED = "public_feed"    # public JSON endpoint meant for programmatic use
    SCRAPE = "scrape"              # HTML scraping: opt-in only (legal review pending)


@dataclass(frozen=True, slots=True)
class SearchQuery:
    text: str
    location: str = ""
    limit: int = 50          # per source
    max_age_days: int = 30


_WS = re.compile(r"\s+")


def _norm(text: str | None) -> str:
    return _WS.sub(" ", (text or "").strip().lower())


def _str_list(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            value = re.split(r"[,;|]", value)
    if not isinstance(value, Iterable):
        return ()
    return tuple(dict.fromkeys(s for s in (str(v).strip() for v in value) if s))


def _float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class JobRecord:
    """One job posting in the shape of the `jobs` table. Every source maps into this."""

    job_id: str
    title: str
    company: str
    source: str
    location: str = ""
    description: str = ""
    url: str = ""
    posted_date: datetime | None = None
    provider_id: str | None = None
    company_website: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    has_remote: bool | None = None
    work_mode: str | None = None
    experience_level: str | None = None
    tags: tuple[str, ...] = ()
    expired_at: datetime | None = None
    provider_payload: Mapping[str, Any] | None = field(default=None, compare=False, repr=False)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any], source: str) -> JobRecord | None:
        """Build from a provider dict: `job_data_providers.normalize_job` output or a legacy
        scraper dict (`skills`, string dates). Returns None without a title and company."""
        title = str(d.get("title") or "").strip()[:500]
        company = str(d.get("company") or d.get("company_name") or "").strip()[:500]
        if not title or not company:
            return None
        src = str(d.get("source") or source)
        url = str(d.get("url") or "").strip()
        job_id = str(d.get("job_id") or "") or f"{src}:{_digest(title, company, url)}"
        payload = d.get("provider_payload")
        return cls(
            job_id=job_id[:255],
            title=title,
            company=company,
            source=src[:100],
            location=str(d.get("location") or "").strip()[:500],
            description=str(d.get("description") or "").strip(),
            url=url,
            posted_date=parse_datetime(d.get("posted_date") or d.get("publication_date")),
            provider_id=d.get("provider_id"),
            company_website=d.get("company_website"),
            salary_min=_float(d.get("salary_min")),
            salary_max=_float(d.get("salary_max")),
            salary_currency=d.get("salary_currency"),
            has_remote=d.get("has_remote"),
            work_mode=d.get("work_mode"),
            experience_level=d.get("experience_level") or d.get("experience"),
            tags=_str_list(d.get("tags") or d.get("skills")),
            expired_at=parse_datetime(d.get("expired_at")),
            provider_payload=payload if isinstance(payload, Mapping) else None,
        )

    @property
    def fingerprint(self) -> str:
        """Same role posted on several boards: normalized title + company + location."""
        return _digest(_norm(self.title), _norm(self.company), _norm(self.location))

    @property
    def completeness(self) -> int:
        """How many optional fields are filled; the richer copy wins a cross-source dedupe."""
        return sum(1 for f in fields(self) if f.name not in _REQUIRED and getattr(self, f.name) not in (None, "", ()))

    def to_row(self) -> dict[str, Any]:
        """Keyword arguments for `src.models.Job` (tags/payload are JSON text columns)."""
        row = {f.name: getattr(self, f.name) for f in fields(self)}
        row["tags"] = json.dumps(list(self.tags)) if self.tags else None
        row["provider_payload"] = json.dumps(self.provider_payload, default=str) if self.provider_payload else None
        return row


_REQUIRED = frozenset({"job_id", "title", "company", "source", "provider_payload"})


def _digest(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8"), usedforsecurity=False).hexdigest()[:16]


@dataclass(slots=True)
class SourceReport:
    name: str
    tier: Tier
    status: str  # ok | empty | failed | timeout
    count: int = 0
    seconds: float = 0.0
    error: str | None = None


@dataclass(slots=True)
class FetchReport:
    query: SearchQuery
    records: list[JobRecord]
    sources: list[SourceReport]
    duplicates: int = 0

    def summary(self) -> str:
        per = ", ".join(f"{s.name}={s.count if s.status in ('ok', 'empty') else s.status}" for s in self.sources)
        return f"'{self.query.text}': {len(self.records)} unique ({self.duplicates} duplicates) [{per}]"
