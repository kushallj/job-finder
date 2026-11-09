"""Which sources run. One place to read settings, so callers never filter sources themselves.

    JOB_SOURCES=""                      all sources whose keys are configured (non-scrape)
    JOB_SOURCES="adzuna,remotive"       only these (still subject to keys and the scrape gate)
    JOB_SOURCES_ALLOW_SCRAPING=false    scrape-tier sources stay off unless this is true
"""

from __future__ import annotations

from collections.abc import Iterable

from src.config import settings
from src.job_sources.base import JobSource
from src.job_sources.models import Tier
from src.job_sources.sources import ALL_SOURCES


def all_sources() -> tuple[JobSource, ...]:
    return ALL_SOURCES


def _parse(names: str | Iterable[str] | None) -> set[str] | None:
    if names is None:
        return None
    if isinstance(names, str):
        names = names.split(",")
    picked = {n.strip().lower() for n in names if n and n.strip()}
    return picked or None


def enabled_sources(
    names: str | Iterable[str] | None = None,
    *,
    allow_scraping: bool | None = None,
) -> list[JobSource]:
    """Sources that may run now: selected by name, keys present, scrape tier gated."""
    wanted = _parse(names if names is not None else settings.job_sources)
    scraping = settings.job_sources_allow_scraping if allow_scraping is None else allow_scraping
    out = []
    for src in all_sources():
        if wanted is not None and src.name not in wanted:
            continue
        if src.tier is Tier.SCRAPE and not scraping:
            continue
        if src.enabled:
            out.append(src)
    return out


def describe() -> list[dict[str, object]]:
    """Every source with its tier and whether it would run (for the CLI and ops)."""
    active = {s.name for s in enabled_sources()}
    return [
        {"name": s.name, "tier": s.tier.value, "configured": s.enabled, "active": s.name in active,
         "description": getattr(s, "description", "")}
        for s in all_sources()
    ]
