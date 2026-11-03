"""
tests/test_kanban_backend.py
Unit & Integration tests for Kanban Application Tracker with Countdown Timers and Recruiter Email Provenance Badges.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, get_db
from src.models import Job, Application, User
from src.services.kanban_service import KanbanService, KANBAN_COLUMNS
from src.auth.jwt_handler import create_access_token
from main import app


@pytest.fixture(scope="module")
def test_db():
    """Create an in-memory SQLite database for Kanban tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    yield db
    db.close()


def test_calculate_countdown_amber_alert():
    """Verify next action in 1 to 3 days generates a 🟡 Amber alert."""
    now = datetime(2026, 11, 2, 12, 0, 0)
    due_at = now + timedelta(days=3)

    days_rem, label, severity = KanbanService.calculate_countdown(
        next_action_type="technical_interview",
        next_action_title="Technical Interview",
        next_action_due_at=due_at,
        now=now,
    )

    assert severity == "amber"
    assert label == "Next: Technical Interview in 3 days"
    assert round(days_rem) == 3


def test_calculate_countdown_blue_alert():
    """Verify next action in 4 to 7 days generates a 🔵 Blue alert."""
    now = datetime(2026, 11, 2, 12, 0, 0)
    due_at = now + timedelta(days=6)

    days_rem, label, severity = KanbanService.calculate_countdown(
        next_action_type="take_home",
        next_action_title="Take-home assessment",
        next_action_due_at=due_at,
        now=now,
    )

    assert severity == "blue"
    assert label == "Next: Take-home assessment in 6 days"
    assert round(days_rem) == 6


def test_calculate_countdown_red_alert_overdue():
    """Verify overdue deadline (<= 0 days) generates a 🔴 Red alert."""
    now = datetime(2026, 11, 2, 12, 0, 0)
    due_at = now - timedelta(days=1)

    days_rem, label, severity = KanbanService.calculate_countdown(
        next_action_type="follow_up",
        next_action_title="Follow-up required",
        next_action_due_at=due_at,
        now=now,
    )

    assert severity == "red"
    assert label == "Overdue / Follow-up required"
    assert days_rem < 0


def test_calculate_countdown_applied_overdue_fallback():
    """Verify application with no response after 7 days automatically triggers 🔴 Red alert."""
    now = datetime(2026, 11, 10, 12, 0, 0)
    applied_at = datetime(2026, 11, 1, 12, 0, 0)  # 9 days ago

    days_rem, label, severity = KanbanService.calculate_countdown(
        next_action_type=None,
        next_action_title=None,
        next_action_due_at=None,
        applied_at=applied_at,
        now=now,
    )

    assert severity == "red"
    assert label == "Overdue / Follow-up required"


def test_format_email_provenance_badge():
    """Verify exact formatting of recruiter email provenance badge."""
    badge = KanbanService.format_email_provenance(
        email_subject="Re: Interview invitation — Senior Frontend Engineer",
        recruiter_email="recruiter@tessellate.io",
    )
    assert badge == '"Re: Interview invitation — Senior Frontend Engineer" from recruiter@tessellate.io'


def test_kanban_service_crud_and_board(test_db):
    """Verify board generation, stage transitions, next action scheduling, and email provenance attachment."""
    service = KanbanService(test_db)

    # 1. Seed realistic sample cards
    board = service.seed_sample_kanban()
    assert board.status == "success"
    assert board.total_applications >= 3
    assert board.amber_count >= 1
    assert board.blue_count >= 1
    assert board.red_count >= 1

    # Check amber card exists with exact badge and countdown
    amber_cards = [c for c in service.get_cards() if c.alert_severity == "amber"]
    assert len(amber_cards) >= 1
    tessellate_card = next(c for c in amber_cards if "Tessellate" in c.company)
    assert tessellate_card.countdown_label == "Next: Technical Interview in 3 days"
    assert tessellate_card.provenance_badge == '"Re: Interview invitation — Senior Frontend Engineer" from recruiter@tessellate.io'

    # Check blue card exists
    blue_cards = [c for c in service.get_cards() if c.alert_severity == "blue"]
    assert len(blue_cards) >= 1
    vercel_card = next(c for c in blue_cards if "Vercel" in c.company)
    assert vercel_card.countdown_label == "Next: Take-home assessment in 6 days"
    assert "talent@vercel.com" in vercel_card.provenance_badge

    # 2. Stage transition
    updated_card = service.transition_stage(tessellate_card.id, "offer", order=5)
    assert updated_card.kanban_stage == "offer"
    assert updated_card.kanban_order == 5

    # 3. Schedule next action
    new_due = datetime.utcnow() + timedelta(days=2)
    action_card = service.set_next_action(
        tessellate_card.id,
        action_type="offer_decision",
        action_title="Offer Decision Call",
        due_at=new_due,
    )
    assert action_card.next_action_title == "Offer Decision Call"
    assert action_card.alert_severity == "amber"

    # 4. Attach email provenance
    provenance_card = service.set_email_provenance(
        tessellate_card.id,
        recruiter_email="vp.eng@tessellate.io",
        email_subject="Official Offer Letter & Equity Grants",
        recruiter_name="Elena Vance",
    )
    assert provenance_card.provenance_badge == '"Official Offer Letter & Equity Grants" from vp.eng@tessellate.io'
    assert provenance_card.recruiter_name == "Elena Vance"


def test_kanban_api_endpoints():
    """Verify FastAPI /api/kanban endpoints via TestClient — authenticated as test user."""
    from sqlalchemy.pool import StaticPool
    # Build an isolated in-memory DB with a test user so we can generate a real JWT.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    test_user = User(
        email="kanban_test@example.com",
        full_name="Kanban Tester",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    from src.auth.jwt_handler import create_access_token
    token = create_access_token(data={"sub": str(test_user.id)})
    auth_headers = {"Authorization": f"Bearer {token}"}

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    # 1. Seed board
    seed_res = client.post("/api/kanban/seed", headers=auth_headers)
    assert seed_res.status_code == 200
    data = seed_res.json()
    assert data["status"] == "success"
    assert "columns" in data
    assert "applied" in data["columns"]
    assert "technical_interview" in data["columns"]
    assert "take_home" in data["columns"]

    # 2. Get board
    board_res = client.get("/api/kanban/board", headers=auth_headers)
    assert board_res.status_code == 200
    b_data = board_res.json()
    assert b_data["active_countdown_alerts"] >= 3
    assert b_data["amber_count"] >= 1
    assert b_data["blue_count"] >= 1
    assert b_data["red_count"] >= 1

    # 3. Get cards filtered by severity
    cards_res = client.get("/api/kanban/cards?alert_severity=amber", headers=auth_headers)
    assert cards_res.status_code == 200
    amber_list = cards_res.json()
    assert len(amber_list) >= 1
    assert all(c["alert_severity"] == "amber" for c in amber_list)

    # Pick a card for mutation tests
    card_id = amber_list[0]["id"]

    # 4. Update stage via PATCH
    patch_res = client.patch(
        f"/api/kanban/cards/{card_id}/stage",
        json={"stage": "recruiter_screen", "order": 2},
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["kanban_stage"] == "recruiter_screen"

    # 5. Set next action via POST
    action_time = (datetime.utcnow() + timedelta(days=5)).isoformat()
    post_action_res = client.post(
        f"/api/kanban/cards/{card_id}/next-action",
        json={
            "next_action_type": "take_home",
            "next_action_title": "Take-home assessment",
            "next_action_due_at": action_time,
        },
        headers=auth_headers,
    )
    assert post_action_res.status_code == 200
    assert post_action_res.json()["alert_severity"] == "blue"

    # 6. Set email provenance via POST
    prov_res = client.post(
        f"/api/kanban/cards/{card_id}/email-provenance",
        json={
            "recruiter_email": "recruiter@tessellate.io",
            "email_subject": "Re: Interview invitation — Senior Frontend Engineer",
            "recruiter_name": "Sarah Lin",
        },
        headers=auth_headers,
    )
    assert prov_res.status_code == 200
    assert prov_res.json()["provenance_badge"] == '"Re: Interview invitation — Senior Frontend Engineer" from recruiter@tessellate.io'

    # 7. Verify unauthenticated request is correctly rejected
    unauth_res = client.get("/api/kanban/board")
    assert unauth_res.status_code == 401

    app.dependency_overrides.clear()
