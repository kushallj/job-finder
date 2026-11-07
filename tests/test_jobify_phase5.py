"""Jobify Phase 5: portfolio draft, username rules, publish snapshot, public view, regenerate."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.dependencies import is_public_path
from src.database import get_db
from src.models import Base, CandidateExperience, CandidateProfile, CandidateProject, Portfolio, User


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


def _draft(client, h, **identity):
    p = client.get("/api/portfolio", headers=h).json()
    p["identity"].update(identity)
    return p


def _put(client, h, p):
    r = client.put("/api/portfolio", headers=h, json=p)
    assert r.status_code == 200, r.text
    return r.json()


def test_owner_routes_require_auth(client):
    assert client.get("/api/portfolio").status_code == 401
    assert client.put("/api/portfolio", json={}).status_code == 401
    assert client.get("/api/portfolio/username-available", params={"name": "alex"}).status_code == 401
    assert client.post("/api/portfolio/publish", json={"username": "alex"}).status_code == 401
    assert client.delete("/api/portfolio/publish").status_code == 401
    assert client.post("/api/portfolio/regenerate").status_code == 401


def test_public_path_rule():
    assert is_public_path("/api/portfolio/alex", "GET")
    assert not is_public_path("/api/portfolio", "GET")
    assert not is_public_path("/api/portfolio/username-available", "GET")
    assert not is_public_path("/api/portfolio/alex/chat", "POST")         # legacy chat no longer public
    assert not is_public_path("/api/portfolio/alex/github-activity", "GET")
    assert not is_public_path("/api/portfolio/alex", "PUT")


def test_get_creates_draft_with_contract_shape(client, clerk_auth):
    p = client.get("/api/portfolio", headers=_auth(clerk_auth)).json()
    assert p["status"] == "draft" and p["username"] == ""
    assert set(p) >= {"identity", "contact", "projects", "experience", "education", "hacks", "research",
                      "socials", "custom", "sources"}
    assert set(p["identity"]) == {"fullName", "firstName", "jobTitle", "tagline", "bio", "introLabels", "skills"}
    assert p["contact"]["email"] == "a@example.com"
    assert p["sources"] == {"resume": None, "github": None, "snapshot": None}


def test_save_draft_roundtrip_assigns_ids_and_ignores_status(client, clerk_auth):
    h = _auth(clerk_auth)
    p = _draft(client, h, fullName="Alex Example", skills=["React", "react", " Python "])
    p["projects"] = [{"title": "Gridline", "subtitle": "https://x.dev", "description": "grid"}]
    p["status"], p["username"] = "published", "hijack"
    p["contact"]["website"] = "not-a-url-yet"  # drafts are lenient so autosave never drops edits
    out = _put(client, h, p)
    assert out["status"] == "draft" and out["username"] == ""
    assert out["identity"]["skills"] == ["react", "python"]
    assert out["projects"][0]["id"] and out["projects"][0]["title"] == "Gridline"
    assert client.get("/api/portfolio", headers=h).json()["contact"]["website"] == "not-a-url-yet"


def test_draft_limits_enforced(client, clerk_auth):
    h = _auth(clerk_auth)
    p = _draft(client, h, bio="x" * 3001)
    assert client.put("/api/portfolio", headers=h, json=p).status_code == 422


def test_username_rules(client, clerk_auth):
    h = _auth(clerk_auth)
    check = lambda n: client.get("/api/portfolio/username-available", headers=h, params={"name": n}).json()
    assert check("alex-dev") == {"available": True}
    for bad in ("ab", "Has Space", "a" * 25, "under_score"):
        assert check(bad)["available"] is False
    assert check("-alex")["available"] is False
    assert check("admin")["reason"] == "That username is reserved"
    assert check("publish")["available"] is False


def test_publish_snapshot_and_public_view(client, clerk_auth):
    h = _auth(clerk_auth)
    _put(client, h, _draft(client, h, fullName="Alex Example", tagline="v1"))
    r = client.post("/api/portfolio/publish", headers=h, json={"username": "alex"})
    assert r.status_code == 200 and r.json()["status"] == "published" and r.json()["username"] == "alex"

    public = client.get("/api/portfolio/alex")  # no auth header
    assert public.status_code == 200 and public.json()["identity"]["tagline"] == "v1"
    assert "status" not in public.json() and "sources" not in public.json()

    # Draft edits don't leak until the user publishes again
    _put(client, h, _draft(client, h, tagline="v2 draft"))
    assert client.get("/api/portfolio/alex").json()["identity"]["tagline"] == "v1"
    client.post("/api/portfolio/publish", headers=h, json={"username": "alex"})
    assert client.get("/api/portfolio/alex").json()["identity"]["tagline"] == "v2 draft"
    assert client.get("/api/portfolio/ALEX").status_code == 200


def test_publish_validation(client, clerk_auth):
    h = _auth(clerk_auth)
    p = _draft(client, h, fullName="")
    _put(client, h, p)
    r = client.post("/api/portfolio/publish", headers=h, json={"username": "alex"})
    assert r.status_code == 422 and r.json()["error"]["fields"]["fullName"]

    p = _draft(client, h, fullName="Alex")
    p["socials"]["github"] = "javascript:alert(1)"
    _put(client, h, p)
    r = client.post("/api/portfolio/publish", headers=h, json={"username": "alex"})
    assert r.status_code == 422 and "github" in r.json()["error"]["fields"]

    r = client.post("/api/portfolio/publish", headers=h, json={"username": "admin"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "USERNAME_UNAVAILABLE"


def test_username_taken_across_users_and_isolation(client, clerk_auth):
    a, b = _auth(clerk_auth, "a"), _auth(clerk_auth, "b")
    _put(client, a, _draft(client, a, fullName="Alex", tagline="secret draft"))
    client.post("/api/portfolio/publish", headers=a, json={"username": "alex"})

    _put(client, b, _draft(client, b, fullName="Blair"))
    assert client.get("/api/portfolio/username-available", headers=b, params={"name": "alex"}).json() == {
        "available": False, "reason": "That username is taken"}
    assert client.get("/api/portfolio/username-available", headers=a, params={"name": "alex"}).json() == {"available": True}
    r = client.post("/api/portfolio/publish", headers=b, json={"username": "alex"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "USERNAME_UNAVAILABLE"

    # B only ever sees B's own draft
    assert client.get("/api/portfolio", headers=b).json()["identity"]["fullName"] == "Blair"
    assert client.get("/api/portfolio", headers=a).json()["identity"]["tagline"] == "secret draft"


def test_unpublish_hides_public_and_keeps_username(client, clerk_auth, db_session):
    h = _auth(clerk_auth)
    _put(client, h, _draft(client, h, fullName="Alex"))
    client.post("/api/portfolio/publish", headers=h, json={"username": "alex"})
    r = client.delete("/api/portfolio/publish", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "draft" and r.json()["username"] == "alex"
    assert client.get("/api/portfolio/alex").status_code == 404
    assert db_session.query(Portfolio).one().published_content is None
    b = _auth(clerk_auth, "b")
    assert client.get("/api/portfolio/username-available", headers=b, params={"name": "alex"}).json()["available"] is False


def test_public_unknown_is_404(client):
    assert client.get("/api/portfolio/nobody").status_code == 404


def test_regenerate_fills_empty_fields_only(client, clerk_auth, db_session):
    h = _auth(clerk_auth)
    p = _draft(client, h, fullName="Alex Custom", jobTitle="")
    p["experience"] = [{"title": "Engineer", "subtitle": "Acme · 2020 – 2022", "description": "my words"}]
    _put(client, h, p)

    user = db_session.query(User).filter(User.clerk_user_id == "user_a").one()
    profile = CandidateProfile(user_identifier="user_a", full_name="Profile Name", email="a@example.com",
                               current_title="Staff Engineer", bio_summary="From profile", skills=json.dumps(["Go"]),
                               github_url="https://github.com/alex")
    db_session.add(profile)
    db_session.flush()
    db_session.add_all([
        CandidateExperience(profile_id=profile.id, company="Acme", title="Engineer", start_date="2020", end_date="2022",
                            description="profile words"),
        CandidateExperience(profile_id=profile.id, company="Beta", title="Lead", start_date="2023", end_date="Present"),
        CandidateProject(profile_id=profile.id, title="Gridline", demo_url="https://grid.dev", description="grid"),
    ])
    db_session.commit()
    assert user.id

    out = client.post("/api/portfolio/regenerate", headers=h).json()
    assert out["identity"]["fullName"] == "Alex Custom"          # manual edit kept
    assert out["identity"]["jobTitle"] == "Staff Engineer"       # empty field filled
    assert out["identity"]["bio"] == "From profile"
    assert "go" in out["identity"]["skills"]
    assert out["socials"]["github"] == "https://github.com/alex"
    assert [e["title"] for e in out["experience"]] == ["Engineer", "Lead"]   # duplicate not re-added
    assert out["experience"][0]["description"] == "my words"
    assert out["experience"][1]["subtitle"] == "Beta · 2023 – Present"
    assert out["projects"][0]["subtitle"] == "https://grid.dev"
    assert out["sources"]["snapshot"] and out["sources"]["resume"]

    again = client.post("/api/portfolio/regenerate", headers=h).json()
    assert len(again["experience"]) == 2 and len(again["projects"]) == 1   # idempotent


def test_clerk_id_placeholder_name_is_not_prefilled(client, clerk_auth, db_session):
    # Token without a name claim: auto-provisioning stores the Clerk id ("User_A") as full_name.
    h = _auth(clerk_auth, "z")
    client.get("/api/me", headers=h)
    user = db_session.query(User).filter(User.clerk_user_id == "user_z").one()
    user.full_name = "User_Z"
    db_session.commit()
    p = client.get("/api/portfolio", headers=h).json()
    assert p["identity"]["fullName"] == "" and p["identity"]["firstName"] == ""
    assert client.post("/api/portfolio/regenerate", headers=h).json()["identity"]["fullName"] == ""


def test_regenerate_without_profile_adds_nothing_invented(client, clerk_auth):
    h = _auth(clerk_auth)
    out = client.post("/api/portfolio/regenerate", headers=h).json()
    assert out["projects"] == [] and out["experience"] == [] and out["identity"]["jobTitle"] == ""
    assert out["sources"]["snapshot"]
