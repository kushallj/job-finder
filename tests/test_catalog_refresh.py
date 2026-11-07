"""Scheduled job-catalog refresh (src/tasks.py) and the no-auto-send guarantee.

Nothing here talks to Redis or a job source: Celery primitives and the scraper are
monkeypatched, and tasks are called directly (synchronous execution).
"""

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src import tasks
from src.config import settings
from src.models import Base, CatalogRefreshRun, User
from src.services import catalog_runs


@pytest.fixture(autouse=True)
def run_db(monkeypatch):
    """Tasks open src.database.SessionLocal themselves; point it at in-memory SQLite."""
    import src.database

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(src.database, "SessionLocal", factory)
    yield factory
    engine.dispose()

SENDING_TASKS = {"src.tasks.send_outreach", "src.tasks.run_full_pipeline"}


def test_beat_never_schedules_sending_or_the_single_user_pipeline():
    scheduled = {e["task"] for e in tasks.app.conf.beat_schedule.values()}
    assert not scheduled & SENDING_TASKS, scheduled
    assert "src.tasks.refresh_job_catalog" in scheduled


def test_catalog_refresh_runs_twice_daily_at_default_ist_times():
    entry = next(e for e in tasks.app.conf.beat_schedule.values()
                 if e["task"] == "src.tasks.refresh_job_catalog")
    sched = entry["schedule"]
    assert sched.hour == {2, 14}   # UTC = 08:00 and 20:00 IST
    assert sched.minute == {30}


def test_full_pipeline_chain_has_no_outreach_step(monkeypatch):
    captured = []

    class _Result:
        id = "root"

    class _Workflow:
        def apply_async(self):
            return _Result()

    def fake_chain(*steps):
        captured.extend(steps)
        return _Workflow()

    monkeypatch.setattr(tasks, "chain", fake_chain)
    tasks.run_full_pipeline()
    names = []
    for step in captured:
        names.extend(s.task for s in getattr(step, "tasks", [step]))
    assert "src.tasks.send_outreach" not in names
    assert names[-1] == "src.tasks.regenerate_tracker"


@pytest.mark.parametrize("raw, expected", [
    (" Node.js Developer, Python Developer,,node.js developer ", ["Node.js Developer", "Python Developer"]),
    ("", tasks.SCRAPE_QUERIES),
    (" , ", tasks.SCRAPE_QUERIES),
])
def test_catalog_queries_from_settings(monkeypatch, raw, expected):
    monkeypatch.setattr(settings, "catalog_queries", raw)
    assert tasks.catalog_queries() == list(expected)


def test_refresh_dispatches_one_scrape_per_query(monkeypatch, run_db):
    monkeypatch.setattr(settings, "catalog_queries", "A,B,C")
    seen = {}

    class _Result:
        id = "chord-id"

    def fake_chord(header):
        seen["header"] = list(header)
        return lambda callback: seen.setdefault("callback", callback) and _Result()

    monkeypatch.setattr(tasks, "chord", fake_chord)
    assert tasks.refresh_job_catalog() == "chord-id"
    assert [s.task for s in seen["header"]] == ["src.tasks.scrape_catalog_query"] * 3
    assert [s.args[0] for s in seen["header"]] == ["A", "B", "C"]
    assert seen["callback"].task == "src.tasks.catalog_refresh_done"

    with run_db() as db:
        run = db.query(CatalogRefreshRun).one()
        assert (run.status, run.queries, run.task_id) == ("running", 3, "chord-id")
        assert seen["callback"].kwargs == {"run_id": run.id}


def test_catalog_query_failure_is_reported_not_raised(monkeypatch):
    def boom(_q):
        raise RuntimeError("source down")

    monkeypatch.setattr(tasks, "_scrape", boom)
    out = tasks.scrape_catalog_query("Backend")
    assert out == {"query": "Backend", "stored": 0, "error": "RuntimeError: source down"}

    monkeypatch.setattr(tasks, "_scrape", lambda _q: 7)
    assert tasks.scrape_catalog_query("Python")["stored"] == 7


def test_refresh_summary_counts_jobs_and_failures():
    summary = tasks.catalog_refresh_done([
        {"query": "A", "stored": 4, "error": None},
        {"query": "B", "stored": 0, "error": "Timeout"},
        {"query": "C", "stored": 3, "error": None},
    ])
    assert summary == {"queries": 3, "new_jobs": 7, "failed": [{"query": "B", "error": "Timeout"}],
                       "status": None}  # no run_id -> nothing recorded


@pytest.mark.parametrize("errors, expected", [
    ([None, None], "ok"),
    ([None, "Timeout"], "partial"),
    (["Timeout", "403"], "failed"),
    ([], "failed"),
])
def test_refresh_done_records_run_outcome(run_db, errors, expected):
    with run_db() as db:
        run_id = catalog_runs.start_run(db, ["q"] * max(len(errors), 1))
    results = [{"query": f"q{i}", "stored": 2, "error": e} for i, e in enumerate(errors)]
    assert tasks.catalog_refresh_done(results, run_id=run_id)["status"] == expected
    with run_db() as db:
        run = db.get(CatalogRefreshRun, run_id)
        assert run.status == expected and run.finished_at is not None
        assert run.new_jobs == 2 * len(errors)
        assert json.loads(run.results) == results


def test_tracking_failure_never_breaks_the_refresh(monkeypatch):
    import src.database

    def broken():
        raise RuntimeError("db down")

    monkeypatch.setattr(src.database, "SessionLocal", broken)
    monkeypatch.setattr(tasks, "chord", lambda header: (lambda cb: type("R", (), {"id": "x"})()))
    assert tasks.refresh_job_catalog() == "x"
    assert tasks.catalog_refresh_done([{"query": "a", "stored": 1, "error": None}], run_id=5)["new_jobs"] == 1


def _run(db, status, started_ago_h, finished_ago_h=None, results=None):
    now = datetime.utcnow()
    r = CatalogRefreshRun(status=status, queries=1, started_at=now - timedelta(hours=started_ago_h),
                          finished_at=None if finished_ago_h is None else now - timedelta(hours=finished_ago_h),
                          results=json.dumps(results) if results else None)
    db.add(r)
    db.commit()
    return r


def test_status_flags_stale_and_stuck(run_db):
    with run_db() as db:
        assert catalog_runs.catalog_status(db)["stale"] is True  # never ran
        _run(db, "ok", 30, 29.5)
        out = catalog_runs.catalog_status(db)
        assert out["stale"] is True and out["lastSuccessAt"]
        _run(db, "partial", 11, 10.8, [{"query": "B", "stored": 0, "error": "Timeout"}])
        _run(db, "failed", 1, 0.9)
        _run(db, "running", 3)
        out = catalog_runs.catalog_status(db)
        assert out["stale"] is False  # the partial run 10.8h ago counts as a success
        assert [r["status"] for r in out["runs"]] == ["failed", "running", "partial", "ok"]
        assert next(r for r in out["runs"] if r["status"] == "running")["stuck"] is True
        assert out["runs"][2]["failures"] == [{"query": "B", "error": "Timeout"}]


def test_admin_endpoint_requires_superuser(run_db, clerk_auth):
    from fastapi.testclient import TestClient
    from main import app
    from src.database import get_db

    db = run_db()
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        assert client.get("/api/admin/catalog-runs").status_code == 401
        h = clerk_auth.headers("user_ops", "ops@example.com")
        assert client.get("/api/admin/catalog-runs", headers=h).status_code == 403
        db.query(User).filter(User.email == "ops@example.com").update({"is_superuser": True})
        db.commit()
        _run(db, "ok", 2, 1.9)
        r = client.get("/api/admin/catalog-runs", headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["stale"] is False and r.json()["runs"][0]["status"] == "ok"
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()


@pytest.mark.parametrize("flag", [False, True])
def test_send_outreach_follows_auto_send_setting(monkeypatch, flag):
    import src.job_processor as jp

    seen = {}

    class _Metrics:
        emails_sent = emails_failed = jobs_processed = 0

    class FakeProcessor:
        def __init__(self, config):
            seen["auto_send"] = config.auto_send_emails
            self.metrics = _Metrics()

        async def process_all_jobs(self, **_kw):
            return None

        async def close(self):
            return None

    monkeypatch.setattr(jp, "JobProcessor", FakeProcessor)
    monkeypatch.setattr(settings, "auto_send_emails", flag)
    tasks.send_outreach()
    assert seen["auto_send"] is flag
