"""
catalog_runs.py: run history for the scheduled job-catalog refresh.

src/tasks.refresh_job_catalog calls start_run() before dispatching its chord, and the
chord callback calls finish_run() with the per-query results. catalog_status() is what
GET /api/admin/catalog-runs returns, so a silent failure is visible:

  status  ok       every query succeeded
          partial  some queries failed
          failed   every query failed, or no queries ran
          running  dispatched, callback not yet received
  stuck   a "running" row older than STUCK_AFTER: the callback never fired
  stale   no ok/partial run finished within CATALOG_STALE_AFTER_HOURS (default 26h,
          i.e. two missed twice-daily runs)

Tracking is best effort: callers wrap these in try/except so a database hiccup never
stops the scrape itself.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.api.contract import iso_utc
from src.config import settings
from src.models import CatalogRefreshRun

STUCK_AFTER = timedelta(hours=2)


def start_run(db: Session, queries: List[str], task_id: Optional[str] = None) -> int:
    run = CatalogRefreshRun(status="running", queries=len(queries), task_id=task_id,
                            started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    return run.id


def set_task_id(db: Session, run_id: int, task_id: str) -> None:
    run = db.get(CatalogRefreshRun, run_id)
    if run:
        run.task_id = task_id
        db.commit()


def finish_run(db: Session, run_id: Optional[int], results: List[Dict[str, Any]]) -> Optional[str]:
    """Record the outcome. Returns the stored status, or None if the row is missing."""
    run = db.get(CatalogRefreshRun, run_id) if run_id else None
    if not run:
        return None
    failed = sum(1 for r in results if r.get("error"))
    run.status = "failed" if not results or failed == len(results) else ("partial" if failed else "ok")
    run.finished_at = datetime.utcnow()
    run.queries = len(results)
    run.new_jobs = sum(int(r.get("stored") or 0) for r in results)
    run.results = json.dumps(results)
    db.commit()
    return run.status


def _out(run: CatalogRefreshRun, now: datetime) -> Dict[str, Any]:
    results = json.loads(run.results) if run.results else []
    return {
        "id": run.id,
        "taskId": run.task_id,
        "status": run.status,
        "stuck": run.status == "running" and now - run.started_at > STUCK_AFTER,
        "startedAt": iso_utc(run.started_at),
        "finishedAt": iso_utc(run.finished_at),
        "queries": run.queries,
        "newJobs": run.new_jobs,
        "failures": [{"query": r.get("query"), "error": r.get("error")} for r in results if r.get("error")],
    }


def catalog_status(db: Session, limit: int = 20) -> Dict[str, Any]:
    now = datetime.utcnow()
    runs = (db.query(CatalogRefreshRun).order_by(CatalogRefreshRun.started_at.desc(),
                                                 CatalogRefreshRun.id.desc())
            .limit(limit).all())
    last_ok = (db.query(CatalogRefreshRun)
               .filter(CatalogRefreshRun.status.in_(["ok", "partial"]))
               .order_by(CatalogRefreshRun.finished_at.desc()).first())
    stale_after = timedelta(hours=settings.catalog_stale_after_hours)
    return {
        "lastSuccessAt": iso_utc(last_ok.finished_at) if last_ok else None,
        "stale": last_ok is None or now - last_ok.finished_at > stale_after,
        "staleAfterHours": settings.catalog_stale_after_hours,
        "runs": [_out(r, now) for r in runs],
    }
