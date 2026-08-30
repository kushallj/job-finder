import uuid
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from main import app
from src.database import SessionLocal, init_db
from src.models import Job, Application, Contact, OutreachRecord


def test_lifecycle_transition_offer_to_negotiation_and_accept():
    init_db(); db = SessionLocal()
    jid = f"lifecycle-{uuid.uuid4().hex}"
    job = Job(job_id=jid, title="Staff Engineer", company="Lifecycle Co", url="https://example.com/apply", source="test")
    db.add(job); db.commit(); db.refresh(job)
    app_row = Application(job_id=job.id, status="offer")
    db.add(app_row); db.commit(); db.refresh(app_row); job_id = job.id; app_id = app_row.id; db.close()
    try:
        client = TestClient(app)
        r = client.post(f"/api/opportunities/{job_id}/do-next")
        assert r.status_code == 200 and r.json()["action"] == "negotiate"
        db = SessionLocal(); current = db.query(Application).filter(Application.id == app_id).first(); assert current and current.status == "negotiation"; db.close()
        r = client.post(f"/api/opportunities/{job_id}/do-next")
        assert r.status_code == 200 and r.json()["action"] == "accept_offer" and r.json()["requires_confirmation"] is True
        r = client.post(f"/api/applications/{app_id}/transition", json={"status": "accepted"})
        assert r.status_code == 200 and r.json()["application_status"] == "accepted"
    finally:
        db = SessionLocal(); db.query(Application).filter(Application.job_id == job_id).delete(synchronize_session=False); db.query(Job).filter(Job.id == job_id).delete(synchronize_session=False); db.commit(); db.close()


def test_action_queue_ranks_and_exposes_lifecycle_action():
    init_db(); db = SessionLocal()
    ids = []
    for idx, status in enumerate(("saved", "offer")):
        jid = f"queue-{idx}-{uuid.uuid4().hex}"
        job = Job(job_id=jid, title=f"Engineer {idx}", company=f"Queue Co {idx}", url="https://example.com/apply", source="test")
        db.add(job); db.commit(); db.refresh(job)
        app_row = Application(job_id=job.id, status=status, match_score=60 + idx * 30)
        db.add(app_row); db.commit(); ids.append((job.id, app_row.id))
    db.close()
    try:
        client = TestClient(app)
        r = client.get('/api/action-queue?limit=1000')
        assert r.status_code == 200
        payload = r.json()
        by_job = {item['job_id']: item for item in payload['actions'] if item['job_id'] in {x[0] for x in ids}}
        assert by_job[ids[0][0]]['action']['key'] == 'prepare_application'
        assert by_job[ids[1][0]]['action']['key'] == 'negotiate'
    finally:
        db = SessionLocal()
        for job_id, _ in ids:
            db.query(Application).filter(Application.job_id == job_id).delete(synchronize_session=False)
            db.query(Job).filter(Job.id == job_id).delete(synchronize_session=False)
        db.commit(); db.close()


def test_action_queue_excludes_closed_and_deduplicates_job_state():
    init_db(); db = SessionLocal()
    jid = f"queue-dedupe-{uuid.uuid4().hex}"
    job = Job(job_id=jid, title="Platform Engineer", company="Queue Co", url="https://example.com", source="test")
    db.add(job); db.commit(); db.refresh(job)
    db.add(Application(job_id=job.id, status="saved", match_score=70))
    db.commit()
    db.add(Application(job_id=job.id, status="applied", match_score=80))
    db.commit()
    closed_job = Job(job_id=f"closed-{uuid.uuid4().hex}", title="Closed Engineer", company="Closed Co", url="https://example.com", source="test")
    db.add(closed_job); db.commit(); db.refresh(closed_job)
    db.add(Application(job_id=closed_job.id, status="accepted", match_score=99)); db.commit()
    ids = [job.id, closed_job.id]
    db.close()
    try:
        client = TestClient(app)
        r = client.get('/api/action-queue?limit=100')
        assert r.status_code == 200
        rows = r.json()['actions']
        ours = [x for x in rows if x['job_id'] in ids]
        assert len([x for x in ours if x['job_id'] == job.id]) == 1
        assert not any(x['job_id'] == closed_job.id for x in rows)
        assert next(x for x in ours if x['job_id'] == job.id)['stage'] == 'applied'
    finally:
        db = SessionLocal()
        db.query(Application).filter(Application.job_id.in_(ids)).delete(synchronize_session=False)
        db.query(Job).filter(Job.id.in_(ids)).delete(synchronize_session=False)
        db.commit(); db.close()
