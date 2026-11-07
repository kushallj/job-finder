"""Scheduled job-catalog refresh (src/tasks.py) and the no-auto-send guarantee.

Nothing here talks to Redis or a job source: Celery primitives and the scraper are
monkeypatched, and tasks are called directly (synchronous execution).
"""

import pytest

from src import tasks
from src.config import settings

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


def test_refresh_dispatches_one_scrape_per_query(monkeypatch):
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
    assert summary == {"queries": 3, "new_jobs": 7, "failed": [{"query": "B", "error": "Timeout"}]}


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
