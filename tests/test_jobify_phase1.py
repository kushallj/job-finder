"""Jobify Phase 1: /api/me, /api/me/subscription, /api/jobs, per-user saved/applied."""

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import get_db
from src.models import Application, Base, CandidateProfile, Job, User
from src.services import jobify_jobs as jj


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


def _job(**kw):
    base = dict(job_id=kw.get("title", "j"), title="Backend Engineer", company="Acme", location="Bengaluru, India",
                description="Build APIs.\n- Design REST services\n- Own Postgres schema", tags=json.dumps(["python", "postgres"]),
                fetched_at=datetime.utcnow())
    base.update(kw)
    return Job(**base)


@pytest.fixture
def jobs(db_session):
    rows = [
        _job(title="Senior Python Engineer", tags=json.dumps(["python", "fastapi"]), salary_min=3_000_000, salary_max=4_500_000,
             salary_currency="INR", experience_level="5-8 years", fetched_at=datetime.utcnow() - timedelta(days=3)),
        _job(title="Go Platform Engineer", company="Quarry", location="Remote", has_remote=True, tags=json.dumps(["go", "kubernetes"]),
             salary_min=150_000, salary_max=190_000, salary_currency="USD", fetched_at=datetime.utcnow() - timedelta(days=1)),
        _job(title="Backend Intern", company="Tessellate", location="Pune, India", work_mode="hybrid",
             tags=json.dumps(["python", "django"]), fetched_at=datetime.utcnow()),
    ]
    db_session.add_all(rows)
    db_session.commit()
    return rows


def _auth(clerk_auth, who="a"):
    return clerk_auth.headers(f"user_{who}", f"{who}@example.com")


# --- me / subscription ---------------------------------------------------------

def test_me_requires_auth(client):
    res = client.get("/api/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_me_and_default_subscription(client, clerk_auth):
    me = client.get("/api/me", headers=_auth(clerk_auth)).json()
    assert {k: me[k] for k in ("id", "email", "avatar", "source")} == {"id": "user_a", "email": "a@example.com", "avatar": None, "source": "clerk"}
    assert me["name"]  # full_name from provisioning, else email
    sub = client.get("/api/me/subscription", headers=_auth(clerk_auth)).json()
    assert sub["plan"] is None and sub["status"] == "none"
    assert sub["creditsRemaining"] == 50  # default_signup_credits


def test_subscription_maps_paid_tier(client, clerk_auth, db_session):
    client.get("/api/me", headers=_auth(clerk_auth))
    user = db_session.query(User).filter(User.clerk_user_id == "user_a").one()
    user.subscription_tier, user.subscription_status = "pro", "active"
    user.current_period_end = datetime(2026, 12, 5)
    db_session.commit()
    sub = client.get("/api/me/subscription", headers=_auth(clerk_auth)).json()
    assert (sub["plan"], sub["status"], sub["renewsAt"]) == ("pro", "active", "2026-12-05T00:00:00")


# --- jobs list / detail -----------------------------------------------------------

def test_job_shape(client, clerk_auth, jobs):
    body = client.get("/api/jobs", headers=_auth(clerk_auth), params={"sort": "recent"}).json()
    assert set(body) == {"items", "total", "page", "pageSize"} and body["total"] == 3
    intern, remote, senior = body["items"]
    assert intern["type"] == "Internship" and intern["workMode"] == "Hybrid" and intern["country"] == "India"
    assert remote["workMode"] == "Remote" and remote["salary"] == "$150K–$190K"
    assert senior["salary"] == "₹30L–₹45L" and senior["experience"] == "5-8 years"
    assert senior["responsibilities"] == ["Design REST services", "Own Postgres schema"]
    assert isinstance(senior["id"], str) and senior["skills"] == ["python", "fastapi"]
    assert all(j["match"] == 0 for j in body["items"])  # no CandidateProfile yet


def test_filters(client, clerk_auth, jobs):
    h = _auth(clerk_auth)
    get = lambda **p: [j["title"] for j in client.get("/api/jobs", headers=h, params=p).json()["items"]]
    assert get(workModes=["Remote"]) == ["Go Platform Engineer"]
    assert get(types=["Internship"]) == ["Backend Intern"]
    assert sorted(get(countries=["India"])) == ["Backend Intern", "Senior Python Engineer"]
    assert get(skills=["fastapi"]) == ["Senior Python Engineer"]
    assert get(minSalaryUsd=100000) == ["Go Platform Engineer"]  # INR 45L ≈ $54K
    assert "Senior Python Engineer" not in get(maxYears=2)
    assert get(q="quarry") == ["Go Platform Engineer"]
    assert get(sort="salary")[0] == "Go Platform Engineer"


def test_pagination(client, clerk_auth, jobs):
    body = client.get("/api/jobs", headers=_auth(clerk_auth), params={"page": 2, "pageSize": 2, "sort": "title"}).json()
    assert (body["total"], body["page"], body["pageSize"], len(body["items"])) == (3, 2, 2, 1)


def test_match_uses_profile_and_match_only(client, clerk_auth, db_session, jobs):
    db_session.add(CandidateProfile(user_identifier="user_a", full_name="A", email="a@example.com", username="a", skills=json.dumps(["python", "fastapi", "postgres"]),
                                    target_roles=json.dumps(["python engineer"]), years_of_experience=6,
                                    target_locations=json.dumps(["india"])))
    db_session.commit()
    body = client.get("/api/jobs", headers=_auth(clerk_auth), params={"sort": "match"}).json()
    top = body["items"][0]
    assert top["title"] == "Senior Python Engineer" and top["match"] == 100
    only = client.get("/api/jobs", headers=_auth(clerk_auth), params={"matchOnly": "true"}).json()
    assert [j["title"] for j in only["items"]] == ["Senior Python Engineer"]


def test_job_detail_and_404(client, clerk_auth, jobs):
    h = _auth(clerk_auth)
    assert client.get(f"/api/jobs/{jobs[0].id}", headers=h).json()["title"] == "Senior Python Engineer"
    res = client.get("/api/jobs/99999", headers=h)
    assert res.status_code == 404 and res.json()["error"]["code"] == "NOT_FOUND"


# --- saved / applied ----------------------------------------------------------------

def test_saved_toggle_and_explicit(client, clerk_auth, jobs):
    h, jid = _auth(clerk_auth), jobs[0].id
    assert client.put(f"/api/me/jobs/{jid}/saved", headers=h).json()["saved"] == [str(jid)]
    assert client.put(f"/api/me/jobs/{jid}/saved", headers=h).json()["saved"] == []
    assert client.put(f"/api/me/jobs/{jid}/saved", headers=h, json={"saved": True}).json()["saved"] == [str(jid)]
    assert client.put(f"/api/me/jobs/{jid}/saved", headers=h, json={"saved": True}).json()["saved"] == [str(jid)]


def test_applied_is_idempotent_and_creates_no_application(client, clerk_auth, db_session, jobs):
    h, jid = _auth(clerk_auth), jobs[0].id
    assert client.post(f"/api/me/jobs/{jid}/applied", headers=h).json()["applied"] == [str(jid)]
    assert client.post(f"/api/me/jobs/{jid}/applied", headers=h).json()["applied"] == [str(jid)]
    # JobsPage.apply() creates the card via POST /applications (Phase 2); no duplicate here.
    assert db_session.query(Application).count() == 0


def test_unknown_job_state_404(client, clerk_auth, jobs):
    assert client.put("/api/me/jobs/99999/saved", headers=_auth(clerk_auth)).status_code == 404


def test_user_state_is_isolated(client, clerk_auth, db_session, jobs):
    a, b, jid = _auth(clerk_auth, "a"), _auth(clerk_auth, "b"), jobs[0].id
    client.put(f"/api/me/jobs/{jid}/saved", headers=a)
    client.post(f"/api/me/jobs/{jid}/applied", headers=a)
    assert client.get("/api/me/jobs/state", headers=b).json() == {"saved": [], "applied": []}
    assert client.get("/api/me/jobs/state", headers=a).json() == {"saved": [str(jid)], "applied": [str(jid)]}


# --- mapper units ---------------------------------------------------------------------

@pytest.mark.parametrize("loc,expected", [("Remote", "Remote"), ("San Francisco, CA", "USA"),
                                          ("Gurugram", "India"), ("Berlin, Germany", "Germany"), ("", "Remote")])
def test_country(loc, expected):
    assert jj.job_country(Job(location=loc)) == expected


def test_sparse_job_degrades_gracefully():
    ui = jj.to_ui_job(Job(id=7, title="Engineer"))
    assert (ui["salary"], ui["experience"], ui["workMode"], ui["skills"], ui["postedDaysAgo"]) == \
        ("Not disclosed", "Not specified", "Onsite", [], 0)

# --- matching profile ----------------------------------------------------------------

def test_profile_empty_then_saved_drives_match(client, clerk_auth, jobs):
    h = _auth(clerk_auth)
    assert client.get("/api/me/profile", headers=h).json() == {
        "skills": [], "targetRoles": [], "yearsOfExperience": None, "locations": [], "complete": False}
    saved = client.put("/api/me/profile", headers=h, json={
        "skills": [" Python ", "python", "FastAPI"], "targetRoles": ["Python Engineer"],
        "yearsOfExperience": 6, "locations": ["India"]}).json()
    assert saved["skills"] == ["Python", "FastAPI"] and saved["complete"] is True
    assert client.get("/api/me/profile", headers=h).json() == saved
    top = client.get("/api/jobs", headers=h, params={"sort": "match"}).json()["items"][0]
    assert top["title"] == "Senior Python Engineer" and top["match"] > 80


def test_profile_validation(client, clerk_auth):
    h = _auth(clerk_auth)
    res = client.put("/api/me/profile", headers=h, json={"skills": ["x"], "yearsOfExperience": -1})
    assert res.status_code == 422 and res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.put("/api/me/profile", headers=h, json={"skills": ["s"] * 51}).status_code == 422


def test_profile_is_per_user(client, clerk_auth):
    client.put("/api/me/profile", headers=_auth(clerk_auth, "a"), json={"skills": ["go"]})
    assert client.get("/api/me/profile", headers=_auth(clerk_auth, "b")).json()["skills"] == []
