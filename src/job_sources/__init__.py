"""Job sources: the single entry point for fetching jobs from every API/feed.

    from src.job_sources import fetch_jobs, fetch_and_store

    report = await fetch_jobs("python developer")          # concurrent, deduped, no DB
    stored, report = await fetch_and_store(db, "python developer")

Layout:
  models.py    SearchQuery, JobRecord (canonical job shape), Tier, reports
  base.py      JobSource protocol + CallableSource adapter
  sources.py   every source, wrapped once (official APIs, public feeds, opt-in scrapers)
  registry.py  which sources run (JOB_SOURCES, JOB_SOURCES_ALLOW_SCRAPING, API keys)
  service.py   fetch concurrently -> dedupe -> bulk store

CLI: python -m src.job_sources --list | "<query>" [--location X] [--store]
"""

from src.job_sources.base import CallableSource, JobSource
from src.job_sources.models import FetchReport, JobRecord, SearchQuery, SourceReport, Tier
from src.job_sources.registry import all_sources, describe, enabled_sources
from src.job_sources.service import dedupe, fetch_and_store, fetch_jobs, store_jobs, upsert_jobs

__all__ = [
    "CallableSource", "FetchReport", "JobRecord", "JobSource", "SearchQuery", "SourceReport", "Tier",
    "all_sources", "dedupe", "describe", "enabled_sources", "fetch_and_store", "fetch_jobs", "store_jobs", "upsert_jobs",
]
