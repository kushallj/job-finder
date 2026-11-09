"""Opportunity actions: lifecycle "do next", action queue ranking, transitions.

The action queue and transitions are per-user (filtered by Application.user_id), so
these tests sign in with a Clerk test token and create rows owned by that user. They
used to call the API anonymously with ownerless rows, which only worked before the
endpoints were tenant-scoped.
"""

import uuid

from fastapi.testclient import TestClient

from main import app
from src.database import SessionLocal, init_db
from src.models import Application, Job, User


def _signed_in(clerk_auth):
    """Client + auth headers + the auto-provisioned user's id (as in production)."""
    sub = f"user_{uuid.uuid4().hex[:12]}"
    headers = clerk_auth.headers(sub=sub, email=f"{sub}@example.com")
    client = TestClient(app)
    assert client.get("/api/me", headers=headers).status_code == 200
    with SessionLocal() as db:
        user_id = db.query(User.id).filter(User.clerk_user_id == sub).scalar()
    return client, headers, user_id


def _job(db, prefix: str, **kw) -> Job:
    job = Job(job_id=f"{prefix}-{uuid.uuid4().hex}", url="https://example.com/apply", source="test", **kw)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _cleanup(job_ids):
    with SessionLocal() as db:
        db.query(Application).filter(Application.job_id.in_(job_ids)).delete(synchronize_session=False)
        db.query(Job).filter(Job.id.in_(job_ids)).delete(synchronize_session=False)
        db.commit()


def test_lifecycle_transition_offer_to_negotiation_and_accept(clerk_auth):
    init_db()
    client, headers, uid = _signed_in(clerk_auth)
    with SessionLocal() as db:
        job = _job(db, "lifecycle", title="Staff Engineer", company="Lifecycle Co")
        app_row = Application(job_id=job.id, status="offer", user_id=uid)
        db.add(app_row)
        db.commit()
        job_id, app_id = job.id, app_row.id
    try:
        r = client.post(f"/api/opportunities/{job_id}/do-next", headers=headers)
        assert r.status_code == 200 and r.json()["action"] == "negotiate"
        with SessionLocal() as db:
            assert db.get(Application, app_id).status == "negotiation"
        r = client.post(f"/api/opportunities/{job_id}/do-next", headers=headers)
        assert r.status_code == 200 and r.json()["action"] == "accept_offer" and r.json()["requires_confirmation"] is True
        r = client.post(f"/api/applications/{app_id}/transition", json={"status": "accepted"}, headers=headers)
        assert r.status_code == 200 and r.json()["application_status"] == "accepted"
    finally:
        _cleanup([job_id])


def test_action_queue_ranks_and_exposes_lifecycle_action(clerk_auth):
    init_db()
    client, headers, uid = _signed_in(clerk_auth)
    ids = []
    with SessionLocal() as db:
        for idx, status in enumerate(("saved", "offer")):
            job = _job(db, f"queue-{idx}", title=f"Engineer {idx}", company=f"Queue Co {idx}")
            db.add(Application(job_id=job.id, status=status, match_score=60 + idx * 30, user_id=uid))
            db.commit()
            ids.append(job.id)
    try:
        r = client.get("/api/action-queue?limit=1000", headers=headers)
        assert r.status_code == 200
        by_job = {item["job_id"]: item for item in r.json()["actions"] if item["job_id"] in ids}
        assert by_job[ids[0]]["action"]["key"] == "prepare_application"
        assert by_job[ids[1]]["action"]["key"] == "negotiate"
    finally:
        _cleanup(ids)


def test_action_queue_excludes_closed_and_deduplicates_job_state(clerk_auth):
    init_db()
    client, headers, uid = _signed_in(clerk_auth)
    with SessionLocal() as db:
        job = _job(db, "queue-dedupe", title="Platform Engineer", company="Queue Co")
        db.add(Application(job_id=job.id, status="saved", match_score=70, user_id=uid))
        db.commit()
        db.add(Application(job_id=job.id, status="applied", match_score=80, user_id=uid))
        db.commit()
        closed = _job(db, "closed", title="Closed Engineer", company="Closed Co")
        db.add(Application(job_id=closed.id, status="accepted", match_score=99, user_id=uid))
        db.commit()
        job_id, closed_id = job.id, closed.id
    try:
        r = client.get("/api/action-queue?limit=100", headers=headers)
        assert r.status_code == 200
        rows = r.json()["actions"]
        ours = [x for x in rows if x["job_id"] == job_id]
        assert len(ours) == 1 and ours[0]["stage"] == "applied"
        assert not any(x["job_id"] == closed_id for x in rows)
    finally:
        _cleanup([job_id, closed_id])


def test_action_queue_hides_other_users_applications(clerk_auth):
    """Tenant isolation: user B never sees user A's opportunities."""
    init_db()
    _client_a, _headers_a, uid_a = _signed_in(clerk_auth)
    client_b, headers_b, _uid_b = _signed_in(clerk_auth)
    with SessionLocal() as db:
        job = _job(db, "private", title="Private Role", company="A Co")
        db.add(Application(job_id=job.id, status="saved", match_score=90, user_id=uid_a))
        db.commit()
        job_id = job.id
    try:
        rows = client_b.get("/api/action-queue?limit=1000", headers=headers_b).json()["actions"]
        assert not any(x["job_id"] == job_id for x in rows)
    finally:
        _cleanup([job_id])
