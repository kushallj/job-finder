"""
Unit and integration tests for Multi-Tenant Isolation (P0-3).
Verifies that:
- User B cannot view User A's contacts (GET /api/contacts -> empty, GET /api/contacts/{id} -> 404)
- User B cannot update User A's outreach status (PUT /api/outreach/{id}/status -> 404)
- User B cannot view or modify User A's Kanban cards or board (GET /api/kanban/cards -> empty, PATCH /api/kanban/cards/{id}/stage -> 404)
- User B's pipeline stats reflect only User B's data (GET /api/stats -> 0 applications/outreach)
- User A and User B maintain completely isolated application lifecycles
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, User, Job, Application, Contact, OutreachRecord
from src.auth.crypto import hash_password
from src.auth.jwt_handler import create_access_token
from src.database import get_db
from main import app


@pytest.fixture
def multi_tenant_db(monkeypatch):
    """Isolated SQLite in-memory test database fixture with StaticPool for thread safety."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSession()

    import main
    import src.database
    monkeypatch.setattr(main, "SessionLocal", TestingSession)
    monkeypatch.setattr(src.database, "SessionLocal", TestingSession)

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_setup(multi_tenant_db):
    """Seed User A, User B, a shared Job, and User A's initial records."""
    # User A (Tenant 1)
    user_a = User(
        email="tenant_a@example.com",
        hashed_password=hash_password("password_a"),
        full_name="Tenant A",
        subscription_tier="free",
        credits_balance=50,
        is_active=True,
        is_superuser=False,
    )
    # User B (Tenant 2)
    user_b = User(
        email="tenant_b@example.com",
        hashed_password=hash_password("password_b"),
        full_name="Tenant B",
        subscription_tier="free",
        credits_balance=50,
        is_active=True,
        is_superuser=False,
    )
    multi_tenant_db.add_all([user_a, user_b])
    multi_tenant_db.commit()
    multi_tenant_db.refresh(user_a)
    multi_tenant_db.refresh(user_b)

    # Shared Job catalog item
    job = Job(
        job_id="job_tensor_01",
        title="Senior AI Platform Engineer",
        company="TensorWorks AI",
        location="Remote",
        description="Build LLM infra",
    )
    multi_tenant_db.add(job)
    multi_tenant_db.commit()
    multi_tenant_db.refresh(job)

    # User A's Contact
    contact_a = Contact(
        user_id=user_a.id,
        name="Elena Rostova",
        title="Head of Talent",
        email="elena@tensorworks.ai",
        company="TensorWorks AI",
        confidence_score=95,
    )
    multi_tenant_db.add(contact_a)

    # User A's Application
    app_a = Application(
        user_id=user_a.id,
        job_id=job.id,
        status="technical_interview",
        kanban_stage="technical_interview",
        match_score=94.0,
        kanban_order=0,
    )
    multi_tenant_db.add(app_a)

    # User A's Outreach Record
    outreach_a = OutreachRecord(
        user_id=user_a.id,
        contact_id=1,
        job_id=job.id,
        subject="Intro - Senior AI Platform Engineer",
        contact_email="elena@tensorworks.ai",
        contact_name="Elena Rostova",
        email_sent=True,
        status="sent",
        sent_at=datetime.utcnow(),
    )
    multi_tenant_db.add(outreach_a)
    multi_tenant_db.commit()
    multi_tenant_db.refresh(contact_a)
    multi_tenant_db.refresh(app_a)
    multi_tenant_db.refresh(outreach_a)

    token_a = create_access_token({"sub": str(user_a.id), "email": user_a.email})
    token_b = create_access_token({"sub": str(user_b.id), "email": user_b.email})

    return {
        "db": multi_tenant_db,
        "user_a": user_a,
        "user_b": user_b,
        "job": job,
        "contact_a": contact_a,
        "app_a": app_a,
        "outreach_a": outreach_a,
        "token_a": token_a,
        "token_b": token_b,
    }


def test_contact_tenant_isolation(test_setup):
    """Verify User B cannot view User A's contacts in list or by ID."""
    db = test_setup["db"]
    token_a = test_setup["token_a"]
    token_b = test_setup["token_b"]
    contact_a = test_setup["contact_a"]

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    # User A fetches contacts -> Sees 1 contact
    res_a = client.get("/api/contacts", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert len(res_a.json()["contacts"]) == 1
    assert res_a.json()["contacts"][0]["id"] == contact_a.id

    # User B fetches contacts -> Sees 0 contacts
    res_b = client.get("/api/contacts", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert len(res_b.json()["contacts"]) == 0

    # User A fetches contact by ID -> 200 OK
    res_get_a = client.get(f"/api/contacts/{contact_a.id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_get_a.status_code == 200

    # User B fetches User A's contact by ID -> 404 Not Found
    res_get_b = client.get(f"/api/contacts/{contact_a.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_get_b.status_code == 404

    app.dependency_overrides.clear()


def test_outreach_record_tenant_isolation(test_setup):
    """Verify User B cannot update User A's outreach record status."""
    db = test_setup["db"]
    token_a = test_setup["token_a"]
    token_b = test_setup["token_b"]
    outreach_a = test_setup["outreach_a"]

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    # User B attempts to mark User A's outreach as replied -> 404 Not Found
    res_b = client.put(
        f"/api/outreach/{outreach_a.id}/status",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"status": "replied"},
    )
    assert res_b.status_code == 404

    # User A updates their outreach record -> 200 OK
    res_a = client.put(
        f"/api/outreach/{outreach_a.id}/status",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"status": "replied"},
    )
    assert res_a.status_code == 200
    assert res_a.json()["new_status"] == "replied"

    app.dependency_overrides.clear()


def test_kanban_board_and_card_isolation(test_setup):
    """Verify User B cannot view User A's cards or transition stages."""
    db = test_setup["db"]
    token_a = test_setup["token_a"]
    token_b = test_setup["token_b"]
    app_a = test_setup["app_a"]

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    # User A fetches board -> Sees 1 application
    res_board_a = client.get("/api/kanban/board", headers={"Authorization": f"Bearer {token_a}"})
    assert res_board_a.status_code == 200
    assert res_board_a.json()["total_applications"] == 1

    # User B fetches board -> Sees 0 applications
    res_board_b = client.get("/api/kanban/board", headers={"Authorization": f"Bearer {token_b}"})
    assert res_board_b.status_code == 200
    assert res_board_b.json()["total_applications"] == 0

    # User B fetches cards -> 0 cards
    res_cards_b = client.get("/api/kanban/cards", headers={"Authorization": f"Bearer {token_b}"})
    assert res_cards_b.status_code == 200
    assert len(res_cards_b.json()) == 0

    # User B attempts to transition User A's card stage -> 404 Not Found
    res_transition_b = client.patch(
        f"/api/kanban/cards/{app_a.id}/stage",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"stage": "offer", "order": 0},
    )
    assert res_transition_b.status_code == 404

    # User A transitions card stage -> 200 OK
    res_transition_a = client.patch(
        f"/api/kanban/cards/{app_a.id}/stage",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"stage": "offer", "order": 0},
    )
    assert res_transition_a.status_code == 200
    assert res_transition_a.json()["kanban_stage"] == "offer"

    app.dependency_overrides.clear()


def test_pipeline_stats_tenant_isolation(test_setup):
    """Verify pipeline stats strictly count per tenant."""
    db = test_setup["db"]
    token_a = test_setup["token_a"]
    token_b = test_setup["token_b"]

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    # User A stats: 1 app, 1 contact, 1 outreach
    res_a = client.get("/api/stats", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    stats_a = res_a.json()["stats"]
    assert stats_a["total_applications"] == 1
    assert stats_a["total_contacts"] == 1
    assert stats_a["total_outreach_attempts"] == 1
    assert len(res_a.json()["recent_outreach"]) == 1

    # User B stats: 0 apps, 0 contacts, 0 outreach
    res_b = client.get("/api/stats", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    stats_b = res_b.json()["stats"]
    assert stats_b["total_applications"] == 0
    assert stats_b["total_contacts"] == 0
    assert stats_b["total_outreach_attempts"] == 0
    assert len(res_b.json()["recent_outreach"]) == 0

    app.dependency_overrides.clear()


def test_application_mutation_and_action_queue_isolation(test_setup):
    """Verify User B creating an application on the same job does not affect User A."""
    db = test_setup["db"]
    token_a = test_setup["token_a"]
    token_b = test_setup["token_b"]
    job = test_setup["job"]
    app_a = test_setup["app_a"]

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    # User B saves the job -> Creates User B's own application
    res_save_b = client.put(
        f"/api/jobs/{job.id}/application",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"status": "saved"},
    )
    assert res_save_b.status_code == 200
    b_app_id = res_save_b.json()["application_id"]
    assert b_app_id != app_a.id

    # Verify User A's application status is untouched ("technical_interview")
    db.refresh(app_a)
    assert app_a.status == "technical_interview"

    # Action queue for User A vs User B
    res_queue_a = client.get("/api/action-queue", headers={"Authorization": f"Bearer {token_a}"})
    assert res_queue_a.status_code == 200

    res_queue_b = client.get("/api/action-queue", headers={"Authorization": f"Bearer {token_b}"})
    assert res_queue_b.status_code == 200

    app.dependency_overrides.clear()


def test_candidate_profile_tenant_isolation(test_setup):
    """Verify CandidateProfile updates for User B do not overwrite User A's profile."""
    db = test_setup["db"]
    token_a = test_setup["token_a"]
    token_b = test_setup["token_b"]

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    # User A updates profile headline
    res_a = client.post(
        "/api/profile/current",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"full_name": "Alice Wonderland", "skills": ["Python", "PyTorch"]},
    )
    assert res_a.status_code == 200
    assert res_a.json()["profile"]["full_name"] == "Alice Wonderland"

    # User B updates profile headline
    res_b = client.post(
        "/api/profile/current",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"full_name": "Bob Builder", "skills": ["Go", "Kubernetes"]},
    )
    assert res_b.status_code == 200
    assert res_b.json()["profile"]["full_name"] == "Bob Builder"

    # Verify User A still sees Alice Wonderland
    get_a = client.get("/api/profile/current", headers={"Authorization": f"Bearer {token_a}"})
    assert get_a.status_code == 200
    assert get_a.json()["profile"]["full_name"] == "Alice Wonderland"
    assert "PyTorch" in get_a.json()["profile"]["skills"]

    # Verify User B sees Bob Builder
    get_b = client.get("/api/profile/current", headers={"Authorization": f"Bearer {token_b}"})
    assert get_b.status_code == 200
    assert get_b.json()["profile"]["full_name"] == "Bob Builder"
    assert "Kubernetes" in get_b.json()["profile"]["skills"]

    app.dependency_overrides.clear()

