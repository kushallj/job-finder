"""src/job_sources: one fetch entry point across every job API.

Fake sources only: no network. Covers concurrency + isolation (slow/failing sources),
dedupe, storage of rich fields, registry gating, and the LinkedIn hard rule.
"""

import asyncio
import json
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src import tasks
from src.config import settings
from src.job_sources import (
    CallableSource,
    JobRecord,
    SearchQuery,
    Tier,
    all_sources,
    dedupe,
    enabled_sources,
    fetch_and_store,
    fetch_jobs,
    store_jobs,
)
from src.job_sources import sources as src_mod
from src.models import Base, Job


def _row(i, **kw):
    return {"job_id": f"fake:{i}", "title": f"Engineer {i}", "company": f"Co{i}", "location": "Remote", **kw}


def _source(name, rows=(), *, delay=0.0, error=None, tier=Tier.PUBLIC_FEED, enabled=True):
    async def fetch(_q):
        await asyncio.sleep(delay)
        if error:
            raise error
        return list(rows)
    return CallableSource(name, tier, fetch, lambda: enabled)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


# --- fetch ----------------------------------------------------------------------------

def test_sources_run_concurrently_and_failures_are_isolated():
    srcs = [
        _source("a", [_row(1)], delay=0.3),
        _source("b", [_row(2)], delay=0.3),
        _source("broken", error=RuntimeError("API down")),
        _source("slow", [_row(3)], delay=5),
    ]
    started = time.perf_counter()
    report = asyncio.run(fetch_jobs("engineer", srcs, per_source_timeout=1.0))
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0, "sources must run in parallel, capped by the timeout"
    assert sorted(r.job_id for r in report.records) == ["fake:1", "fake:2"]
    status = {s.name: s.status for s in report.sources}
    assert status == {"a": "ok", "b": "ok", "broken": "failed", "slow": "timeout"}
    assert "API down" in next(s.error for s in report.sources if s.name == "broken")


def test_rows_without_title_or_company_are_dropped():
    report = asyncio.run(fetch_jobs("x", [_source("a", [_row(1), {"title": "No company"}, {"company": "No title"}])]))
    assert [r.job_id for r in report.records] == ["fake:1"]


def test_dedupe_by_id_then_fingerprint_keeps_richest_copy():
    plain = JobRecord.from_dict(_row(1, job_id="board_a:1", title="Backend Engineer", company="Acme"), "board_a")
    rich = JobRecord.from_dict(_row(2, job_id="board_b:9", title="backend  engineer", company="ACME",
                                    salary_min=100000, tags=["python"]), "board_b")
    same_id = JobRecord.from_dict(_row(3, job_id="board_a:1", title="Other"), "board_a")
    other = JobRecord.from_dict(_row(4), "board_c")

    unique, dupes = dedupe([plain, rich, same_id, other])
    assert dupes == 2
    assert [r.job_id for r in unique] == ["board_b:9", "fake:4"]  # rich copy takes plain's slot


def test_legacy_scraper_dict_maps_skills_and_string_dates():
    rec = JobRecord.from_dict({"title": "Dev", "company": "Co", "skills": ["Go", "SQL", "Go", " "],
                               "posted_date": "2026-11-01T10:00:00Z", "url": "https://x"}, "greenhouse")
    assert rec.job_id.startswith("greenhouse:")
    assert rec.tags == ("Go", "SQL")  # order kept, exact duplicates and blanks dropped
    assert rec.posted_date is not None and rec.posted_date.year == 2026


# --- store ------------------------------------------------------------------------------

def test_store_keeps_rich_fields_and_skips_existing(db):
    db.add(Job(job_id="fake:1", title="Old", company="Co1"))
    db.commit()
    records = [JobRecord.from_dict(_row(i, salary_min=50000, salary_max=90000, salary_currency="USD",
                                        work_mode="remote", tags=["python", "aws"],
                                        experience_level="senior"), "fake") for i in (1, 2, 3)]

    assert store_jobs(db, records) == 2
    job = db.query(Job).filter_by(job_id="fake:2").one()
    assert (job.salary_min, job.salary_max, job.salary_currency) == (50000, 90000, "USD")
    assert job.work_mode == "remote" and job.experience_level == "senior"
    assert json.loads(job.tags) == ["python", "aws"]
    assert db.query(Job).filter_by(job_id="fake:1").one().title == "Old"  # first writer wins
    assert store_jobs(db, records) == 0


def test_fetch_and_store_end_to_end(db):
    stored, report = asyncio.run(fetch_and_store(db, SearchQuery("dev"), [_source("a", [_row(1), _row(2)])]))
    assert stored == 2 and len(report.records) == 2
    assert db.query(Job).count() == 2


def test_catalog_task_uses_job_sources(monkeypatch, db):
    async def fake(dbs, query, sources=None):
        return 4, None
    monkeypatch.setattr("src.job_sources.fetch_and_store", fake)
    monkeypatch.setattr("src.database.SessionLocal", lambda: db)
    assert tasks._scrape("python") == 4


# --- registry -----------------------------------------------------------------------------

def test_linkedin_and_google_results_are_never_sources():
    names = {s.name for s in all_sources()}
    assert not any("linkedin" in n or "google" in n for n in names)
    assert "linkedin" not in src_mod.JOBSPY_SITES


def test_scrape_tier_is_off_by_default(monkeypatch):
    monkeypatch.setattr(settings, "job_sources", "")
    monkeypatch.setattr(settings, "job_sources_allow_scraping", False)
    assert all(s.tier is not Tier.SCRAPE for s in enabled_sources())
    with_scraping = {s.name for s in enabled_sources(allow_scraping=True)}
    assert {"jobspy", "foorilla"} <= with_scraping


def test_keyed_sources_need_keys_and_names_filter(monkeypatch):
    for key in ("jobdata_api_key", "careerjet_api_key", "usajobs_api_key", "adzuna_app_id", "adzuna_app_key"):
        monkeypatch.setattr(settings, key, None)
    names = {s.name for s in enabled_sources("")}
    assert names.isdisjoint({"jobdataapi", "careerjet", "usajobs", "adzuna"})
    assert {"arbeitnow", "remotive", "greenhouse", "weworkremotely"} <= names  # public feeds need no key

    monkeypatch.setattr(settings, "adzuna_app_id", "id")
    monkeypatch.setattr(settings, "adzuna_app_key", "key")
    assert [s.name for s in enabled_sources("adzuna, remotive")] == ["adzuna", "remotive"]
