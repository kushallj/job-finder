"""Jobify Phase 2: Applications board CRUD (/api/applications) + ghosted sweep."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import get_db
from src.models import Application, Base, InboundRecruiterMessage, Job, User
from src.services.jobify_applications import sweep_ghosted

CARD_KEYS = {"id", "company", "position", "stage", "subject", "sender", "date", "messages", "notes", "events", "offer", "source"}


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(db_session, clerk_auth):
    from main import app

    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def _auth(clerk_auth, who="a"):
    return clerk_auth.headers(f"user_{who}", f"{who}@example.com")


def _create(client, h, **kw):
    body = {"company": "Acme", "position": "Backend Engineer", **kw}
    res = client.post("/api/applications", headers=h, json=body)
    assert res.status_code == 201, res.text
    return res.json()


def test_requires_auth(client):
    assert client.get("/api/applications").status_code == 401


def test_empty_board_for_new_user(client, clerk_auth):
    assert client.get("/api/applications", headers=_auth(clerk_auth)).json() == {"items": [], "total": 0, "page": 1, "pageSize": 0}


def test_create_manual_card_shape(client, clerk_auth):
    card = _create(client, _auth(clerk_auth), stage="interview", notes="Referral from Priya")
    assert set(card) == CARD_KEYS
    assert (card["company"], card["position"], card["stage"], card["notes"]) == ("Acme", "Backend Engineer", "interview", "Referral from Priya")
    assert (card["subject"], card["sender"], card["messages"], card["events"], card["offer"], card["source"]) == \
        ("Added manually", "", 1, [], None, "manual")
    assert isinstance(card["id"], str) and datetime.fromisoformat(card["date"])
    assert card["date"].endswith("Z")  # UTC marker, else browsers show it in local time


def test_create_from_jobs_page_payload(client, clerk_auth):
    # Exactly what JobsPage.apply() sends.
    card = _create(client, _auth(clerk_auth), subject="Marked as applied in Jobify", sender="", source="job")
    assert (card["stage"], card["subject"], card["source"]) == ("applied", "Marked as applied in Jobify", "job")


def test_create_validation(client, clerk_auth):
    h = _auth(clerk_auth)
    for bad in ({"company": "", "position": "X"}, {"company": "A", "position": "B", "stage": "hired"},
                {"company": "A", "position": "B", "notes": "x" * 5001}, {"position": "B"}):
        res = client.post("/api/applications", headers=h, json=bad)
        assert res.status_code == 422 and res.json()["error"]["code"] == "VALIDATION_ERROR", bad
    assert client.post("/api/applications", headers=h, json={"company": "A", "position": "B", "jobId": 999}).status_code == 404


def test_list_newest_first(client, clerk_auth):
    h = _auth(clerk_auth)
    _create(client, h, company="First")
    _create(client, h, company="Second")
    assert [c["company"] for c in client.get("/api/applications", headers=h).json()["items"]] == ["Second", "First"]


def test_patch_shapes_the_board_sends(client, clerk_auth):
    h = _auth(clerk_auth)
    cid = _create(client, h)["id"]
    patch = lambda body: client.patch(f"/api/applications/{cid}", headers=h, json=body)

    assert patch({"stage": "offer"}).json()["stage"] == "offer"                      # drag/drop + status select
    assert patch({"notes": "Call Friday"}).json()["notes"] == "Call Friday"           # notes onBlur
    events = [{"id": "ev_1", "title": "Tech round", "at": "2026-11-12T10:00"}]
    assert patch({"events": events}).json()["events"] == events                       # add interview event
    card = patch({"offer": {"salary": "₹40L", "deadline": "2026-11-20"}}).json()      # offer fields onBlur
    assert card["offer"] == {"salary": "₹40L", "deadline": "2026-11-20"}
    # Edit form posts the whole card (incl. id and unknown keys): extra fields are ignored.
    card = patch({"id": cid, "company": "Acme Corp", "position": "Staff Engineer", "stage": "interview",
                  "notes": "Updated", "whatever": 1}).json()
    assert (card["company"], card["position"], card["stage"], card["notes"]) == ("Acme Corp", "Staff Engineer", "interview", "Updated")
    assert card["events"] == events and card["offer"]["salary"] == "₹40L"            # untouched fields persist
    assert patch({"offer": None}).json()["offer"] is None


def test_patch_validation_and_404(client, clerk_auth):
    h = _auth(clerk_auth)
    cid = _create(client, h)["id"]
    assert client.patch(f"/api/applications/{cid}", headers=h, json={"stage": "hired"}).status_code == 422
    assert client.patch(f"/api/applications/{cid}", headers=h, json={"events": [{"id": "x"}]}).status_code == 422
    res = client.patch("/api/applications/99999", headers=h, json={"notes": "x"})
    assert res.status_code == 404 and res.json()["error"]["code"] == "NOT_FOUND"


def test_delete(client, clerk_auth):
    h = _auth(clerk_auth)
    cid = _create(client, h)["id"]
    assert client.delete(f"/api/applications/{cid}", headers=h).status_code == 204
    assert client.get("/api/applications", headers=h).json()["total"] == 0
    assert client.delete(f"/api/applications/{cid}", headers=h).status_code == 404


def test_users_cannot_see_or_touch_each_others_cards(client, clerk_auth):
    a, b = _auth(clerk_auth, "a"), _auth(clerk_auth, "b")
    cid = _create(client, a, company="Secret Co")["id"]
    assert client.get("/api/applications", headers=b).json()["total"] == 0
    assert client.patch(f"/api/applications/{cid}", headers=b, json={"stage": "rejected"}).status_code == 404
    assert client.delete(f"/api/applications/{cid}", headers=b).status_code == 404
    card = client.get("/api/applications", headers=a).json()["items"][0]
    assert (card["company"], card["stage"]) == ("Secret Co", "applied")


def test_job_linked_card_and_message_count(client, clerk_auth, db_session):
    h = _auth(clerk_auth)
    job = Job(job_id="j1", title="Platform Engineer", company="Quarry", url="https://x")
    db_session.add(job)
    db_session.commit()
    card = _create(client, h, jobId=job.id, source="job")
    db_session.add_all([InboundRecruiterMessage(application_id=int(card["id"]), subject="Hi", sender_email="r@q.com", classified_intent="interview")
                        for _ in range(2)])
    db_session.commit()
    listed = client.get("/api/applications", headers=h).json()["items"][0]
    assert listed["messages"] == 3


def test_legacy_rows_fall_back_to_job_fields(client, clerk_auth, db_session):
    h = _auth(clerk_auth)
    client.get("/api/me", headers=h)
    user = db_session.query(User).filter(User.clerk_user_id == "user_a").one()
    job = Job(job_id="j2", title="SRE", company="Neelam", url="https://x")
    db_session.add(job)
    db_session.commit()
    db_session.add(Application(user_id=user.id, job_id=job.id, kanban_stage="pending", status="pending"))
    db_session.commit()
    card = client.get("/api/applications", headers=h).json()["items"][0]
    assert (card["company"], card["position"], card["stage"], card["source"]) == ("Neelam", "SRE", "applied", "job")


def test_sweep_ghosted(db_session):
    now = datetime(2026, 11, 5)
    user = User(email="u@example.com", credits_balance=0)
    db_session.add(user)
    db_session.commit()
    old = Application(user_id=user.id, kanban_stage="applied", applied_at=now - timedelta(days=31), created_at=now - timedelta(days=31))
    recent_mail = Application(user_id=user.id, kanban_stage="applied", applied_at=now - timedelta(days=60),
                              last_email_received_at=now - timedelta(days=5), created_at=now - timedelta(days=60))
    fresh = Application(user_id=user.id, kanban_stage="applied", applied_at=now - timedelta(days=3), created_at=now - timedelta(days=3))
    interview = Application(user_id=user.id, kanban_stage="interview", applied_at=now - timedelta(days=90), created_at=now - timedelta(days=90))
    db_session.add_all([old, recent_mail, fresh, interview])
    db_session.commit()
    assert sweep_ghosted(db_session, now=now) == 1
    assert [a.kanban_stage for a in (old, recent_mail, fresh, interview)] == ["ghosted", "applied", "applied", "interview"]
