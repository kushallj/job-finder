"""Fetch from every enabled source at once, dedupe, and store. The only job-fetch entry point.

Time:  sources run concurrently, so a refresh takes as long as the slowest source (capped by
       JOB_SOURCE_TIMEOUT_SECONDS), not the sum. Dedupe is one O(n) pass over two dicts.
Space: records are small frozen slotted dataclasses; storing checks existing ids with one
       IN query per 500 records instead of one SELECT per job.
Errors: one failing or slow source is reported and skipped; it never fails the refresh.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Iterable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.config import settings
from src.job_sources.base import JobSource
from src.job_sources.models import FetchReport, JobRecord, SearchQuery, SourceReport
from src.job_sources.registry import enabled_sources
from src.models import Job

log = logging.getLogger(__name__)

STORE_CHUNK = 500


async def _run_one(source: JobSource, query: SearchQuery, limit_s: float) -> tuple[SourceReport, list[JobRecord]]:
    started = time.perf_counter()
    try:
        records = await asyncio.wait_for(source.fetch(query), timeout=limit_s)
    except TimeoutError:
        report = SourceReport(source.name, source.tier, "timeout", error=f"over {limit_s:.0f}s")
        records = []
    except Exception as exc:  # isolate every source; surfaced in the report
        log.warning("job source %s failed: %s", source.name, exc)
        report = SourceReport(source.name, source.tier, "failed", error=f"{type(exc).__name__}: {exc}"[:300])
        records = []
    else:
        report = SourceReport(source.name, source.tier, "ok" if records else "empty", count=len(records))
    report.seconds = round(time.perf_counter() - started, 2)
    return report, records


def dedupe(records: Iterable[JobRecord]) -> tuple[list[JobRecord], int]:
    """Drop repeats by job_id, then by fingerprint (same role on several boards), keeping
    the most complete copy in the position of its first occurrence."""
    by_print: dict[str, JobRecord] = {}
    seen_ids: set[str] = set()
    total = 0
    for rec in records:
        total += 1
        if rec.job_id in seen_ids:
            continue
        seen_ids.add(rec.job_id)
        kept = by_print.get(rec.fingerprint)
        if kept is None or rec.completeness > kept.completeness:
            by_print[rec.fingerprint] = rec  # dict keeps first-insertion order on overwrite
    unique = list(by_print.values())
    return unique, total - len(unique)


async def fetch_jobs(
    query: SearchQuery | str,
    sources: Sequence[JobSource] | None = None,
    *,
    per_source_timeout: float | None = None,
) -> FetchReport:
    """Query every enabled source concurrently and return unique records plus per-source stats."""
    q = SearchQuery(query) if isinstance(query, str) else query
    active = list(sources) if sources is not None else enabled_sources()
    limit = per_source_timeout if per_source_timeout is not None else settings.job_source_timeout_seconds
    results = await asyncio.gather(*(_run_one(s, q, limit) for s in active))
    reports = [r for r, _ in results]
    unique, dupes = dedupe(rec for _, recs in results for rec in recs)
    report = FetchReport(query=q, records=unique, sources=reports, duplicates=dupes)
    log.info("job fetch %s", report.summary())
    return report


def store_jobs(db: Session, records: Sequence[JobRecord]) -> int:
    """Insert records whose job_id isn't stored yet, with every field the source provided.
    Existing rows are left untouched (first writer wins, as before). Returns rows inserted."""
    stored = 0
    for start in range(0, len(records), STORE_CHUNK):
        chunk = records[start:start + STORE_CHUNK]
        ids = [r.job_id for r in chunk]
        existing = {jid for (jid,) in db.query(Job.job_id).filter(Job.job_id.in_(ids))}
        new = [Job(**r.to_row()) for r in chunk if r.job_id not in existing]
        if not new:
            continue
        db.add_all(new)
        try:
            db.commit()
            stored += len(new)
        except IntegrityError:  # a concurrent refresh inserted some of these: fall back per row
            db.rollback()
            stored += _store_one_by_one(db, [r for r in chunk if r.job_id not in existing])
    return stored


def _store_one_by_one(db: Session, records: Iterable[JobRecord]) -> int:
    stored = 0
    for rec in records:
        db.add(Job(**rec.to_row()))
        try:
            db.commit()
            stored += 1
        except IntegrityError:
            db.rollback()
    return stored


UPSERT_FIELDS = ("title", "company", "location", "description", "url", "posted_date", "provider_id",
                 "company_website", "salary_min", "salary_max", "salary_currency", "has_remote", "work_mode",
                 "experience_level", "tags", "expired_at", "provider_payload")


def upsert_jobs(db: Session, records: Sequence[JobRecord]) -> tuple[int, int]:
    """Insert new records and refresh existing ones (non-empty fields win; `provider_sources`
    accumulates every source that listed the job). Returns (inserted, updated)."""
    inserted = updated = 0
    for start in range(0, len(records), STORE_CHUNK):
        chunk = records[start:start + STORE_CHUNK]
        existing = {j.job_id: j for j in db.query(Job).filter(Job.job_id.in_([r.job_id for r in chunk]))}
        for rec in chunk:
            row = rec.to_row()
            job = existing.get(rec.job_id)
            if job is None:
                db.add(Job(**row, provider_sources=json.dumps([rec.source])))
                inserted += 1
                continue
            for name in UPSERT_FIELDS:
                if row[name] not in (None, ""):
                    setattr(job, name, row[name])
            sources = _json_list(job.provider_sources) or ([job.source] if job.source else [])
            job.provider_sources = json.dumps(list(dict.fromkeys([*sources, rec.source])))
            updated += 1
        db.commit()
    return inserted, updated


def _json_list(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw) if raw else []
    except ValueError:
        return []
    return [str(v) for v in value] if isinstance(value, list) else []


async def fetch_and_store(
    db: Session,
    query: SearchQuery | str,
    sources: Sequence[JobSource] | None = None,
) -> tuple[int, FetchReport]:
    report = await fetch_jobs(query, sources)
    stored = store_jobs(db, report.records)
    log.info("job fetch '%s': stored %d new of %d unique", report.query.text, stored, len(report.records))
    return stored, report
