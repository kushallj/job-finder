"""
tests/test_telegram_connector.py
Comprehensive test suite for Telegram Instant Push Notification Bot Connector.

Verifies:
1. One-click Telegram bot pairing deep link generation (https://t.me/<bot>?start=pair_<token>)
2. Webhook activation via /start pair_<token>
3. High-match job push alerts (>=90%) with 1-click action buttons ([⚡ Apply Now], [📝 Draft Pitch])
4. Inbound recruiter interview request alerts with Amber countdown timers
5. Interactive 1-click callback query processing (apply_job, pitch_job, draft_reply_app)
6. Integration with Inbound Email Sync auto-dispatching Telegram alerts
7. RESTful API endpoints via FastAPI TestClient
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.models import (
    Base,
    Job,
    Application,
    TelegramConnector,
    TelegramPushAlertLog,
    MailboxAccount,
)
from src.database import get_db
from src.services.telegram_push_service import TelegramPushService
from src.services.inbound_email_sync_service import InboundEmailSyncService
from main import app


@pytest.fixture
def test_engine():
    """Create isolated in-memory engine with StaticPool and thread sharing enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_db_session(test_engine):
    """Create fresh database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client(test_engine):
    """FastAPI TestClient with overridden database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_telegram_pairing_deep_link_generation(test_db_session):
    """Verify one-click deep link generation with unique token."""
    service = TelegramPushService(test_db_session)
    pairing = service.generate_pairing_details(user_identifier="kushal")

    assert pairing.status == "success"
    assert pairing.is_connected is False
    assert pairing.pairing_code.startswith("pair_")
    assert "https://t.me/" in pairing.pairing_url
    assert pairing.pairing_code in pairing.pairing_url
    assert "Start" in pairing.instructions


def test_telegram_webhook_pairing_activation(test_db_session):
    """Verify webhook activates connector when candidate sends /start pair_<token>."""
    service = TelegramPushService(test_db_session)
    pairing = service.generate_pairing_details(user_identifier="kushal")

    # Complete pairing via webhook simulation
    conn = service.complete_pairing(
        pairing_code=pairing.pairing_code,
        chat_id="987654321",
        telegram_username="exampleuser",
        first_name="Kushal",
    )

    assert conn is not None
    assert conn.is_connected is True
    assert conn.telegram_chat_id == "987654321"
    assert conn.telegram_username == "exampleuser"
    assert conn.paired_at is not None


def test_high_match_job_push_alert(test_db_session):
    """Verify high-match job alert (>=90%) formatting and 1-click action buttons."""
    service = TelegramPushService(test_db_session)
    conn = service.complete_pairing(
        pairing_code="pair_test_101",
        chat_id="987654321",
        telegram_username="kushal",
    )

    job = Job(
        job_id="job_tessellate_tg_001",
        title="Senior Frontend Engineer",
        company="Tessellate",
        location="Bengaluru / Remote",
        salary_min=180000,
        salary_max=220000,
        salary_currency="USD",
        url="https://jobfinder.io/jobs/tessellate-frontend",
    )
    test_db_session.add(job)
    test_db_session.commit()

    alert = service.push_high_match_job_alert(
        job=job,
        match_score=94.0,
        matched_skills=["React", "TypeScript", "Vite", "LLM Integration"],
        reasons=[
            "Matches 3 of your top verified skills: React, TypeScript, Vite",
            "Seniority: Matches your 4+ years frontend experience",
            "Location: Remote / Bengaluru hybrid as preferred",
        ],
        connector=conn,
    )

    assert alert.status == "success"
    assert alert.alert_type == "high_match_job"
    assert "94% Match" in alert.message
    assert "Tessellate" in alert.message
    assert "$180,000 - $220,000 USD" in alert.message
    assert "[Apply Now]" in alert.action_buttons
    assert "[Draft Pitch]" in alert.action_buttons
    assert "[View Job Posting]" in alert.action_buttons

    # Verify audit log in database
    log_entry = test_db_session.query(TelegramPushAlertLog).filter(TelegramPushAlertLog.id == alert.alert_id).first()
    assert log_entry is not None
    assert log_entry.job_id == job.id


def test_interview_request_push_alert(test_db_session):
    """Verify inbound interview invitation push alert with Amber countdown timer."""
    service = TelegramPushService(test_db_session)
    conn = service.complete_pairing(
        pairing_code="pair_test_202",
        chat_id="987654321",
    )

    job = Job(
        job_id="job_tessellate_tg_002",
        title="Senior Frontend Engineer",
        company="Tessellate",
        location="Remote",
    )
    test_db_session.add(job)
    test_db_session.commit()

    app_card = Application(
        job_id=job.id,
        user_id=1,
        status="interviewing",
        kanban_stage="technical_interview",
        recruiter_name="Sarah Jenkins",
        recruiter_email="recruiter@tessellate.io",
        email_subject="Re: Interview invitation — Senior Frontend Engineer",
        next_action_title="Technical Interview",
    )
    test_db_session.add(app_card)
    test_db_session.commit()

    alert = service.push_interview_alert(application=app_card, connector=conn)

    assert alert.status == "success"
    assert alert.alert_type == "interview_request"
    assert "INTERVIEW INVITATION RECEIVED" in alert.message
    assert "Sarah Jenkins" in alert.message
    assert "Technical Interview in 3 days" in alert.message
    assert "Amber Alert" in alert.message
    assert "[Draft Reply]" in alert.action_buttons
    assert "[View Kanban Card]" in alert.action_buttons


def test_interactive_1click_callbacks(test_db_session):
    """Verify 1-click [Apply Now], [Draft Pitch], and [Draft Reply] button actions."""
    service = TelegramPushService(test_db_session)
    conn = service.complete_pairing(
        pairing_code="pair_test_303",
        chat_id="987654321",
    )

    job = Job(
        job_id="job_scale_tg_003",
        title="Staff AI Engineer",
        company="ScaleAI",
        location="San Francisco, CA",
    )
    test_db_session.add(job)
    test_db_session.commit()

    # 1. Test [⚡ Apply Now] callback
    reply_msg, action = service.handle_callback_query(f"apply_job_{job.id}", chat_id="987654321")
    assert action == "apply_now"
    assert "Application Recorded" in reply_msg
    # Verify Application created in DB
    created_app = test_db_session.query(Application).filter(Application.job_id == job.id).first()
    assert created_app is not None
    assert created_app.kanban_stage == "applied"
    assert created_app.status == "applied"

    # 2. Test [📝 Draft Pitch] callback
    pitch_msg, action_pitch = service.handle_callback_query(f"pitch_job_{job.id}", chat_id="987654321")
    assert action_pitch == "draft_pitch"
    assert "Ready-to-Send Recruiter Pitch for ScaleAI" in pitch_msg
    assert "Staff AI Engineer" in pitch_msg

    # 3. Test [💬 Draft Reply] callback
    reply_draft, action_reply = service.handle_callback_query(f"draft_reply_app_{created_app.id}", chat_id="987654321")
    assert action_reply == "draft_reply"
    assert "Interview Confirmation Response" in reply_draft


def test_inbound_email_sync_auto_triggers_telegram(test_db_session):
    """Verify that InboundEmailSyncService automatically dispatches Telegram alerts on interview emails."""
    # 1. Connect candidate Telegram
    tg_service = TelegramPushService(test_db_session)
    tg_service.complete_pairing(
        pairing_code="pair_sync_404",
        chat_id="987654321",
    )

    # 2. Seed job & application
    job = Job(
        job_id="job_vercel_tg_004",
        title="Senior Frontend Engineer",
        company="Vercel",
        location="Remote",
    )
    test_db_session.add(job)
    test_db_session.commit()

    app_card = Application(
        job_id=job.id,
        user_id=1,
        status="applied",
        kanban_stage="applied",
    )
    test_db_session.add(app_card)
    test_db_session.commit()

    # 3. Inbound recruiter interview email arrives
    sync_service = InboundEmailSyncService(test_db_session)
    sim_result = sync_service.process_inbound_message(
        sender_email="recruiter@vercel.com",
        sender_name="Guillermo",
        subject="Re: Interview invitation — Senior Frontend Engineer",
        body_text="Hi Kushal, we would love to schedule an interview with our Edge team.",
    )

    assert sim_result.matched is True
    assert sim_result.new_stage == "technical_interview"

    # 4. Check Telegram push alert log
    tg_logs = test_db_session.query(TelegramPushAlertLog).filter(TelegramPushAlertLog.application_id == app_card.id).all()
    assert len(tg_logs) >= 1
    assert tg_logs[0].alert_type == "interview_request"


def test_telegram_fastapi_endpoints(test_client, test_engine):
    """Verify all REST API endpoints for Telegram pairing and test alerts."""
    # 1. GET /api/connectors/telegram/pairing
    pairing_res = test_client.get("/api/connectors/telegram/pairing")
    assert pairing_res.status_code == 200
    p_data = pairing_res.json()
    assert p_data["status"] == "success"
    assert p_data["pairing_code"].startswith("pair_")

    # 2. POST /api/connectors/telegram/pair (manual connect)
    pair_res = test_client.post(
        "/api/connectors/telegram/pair",
        json={
            "pairing_code": p_data["pairing_code"],
            "chat_id": "88889999",
            "telegram_username": "kushal_dev",
            "first_name": "Kushal",
        },
    )
    assert pair_res.status_code == 200
    assert pair_res.json()["is_connected"] is True
    assert pair_res.json()["paired_chat_id"] == "88889999"

    # 3. GET /api/connectors/telegram/status
    status_res = test_client.get("/api/connectors/telegram/status")
    assert status_res.status_code == 200
    assert status_res.json()["is_connected"] is True

    # 4. PATCH /api/connectors/telegram/preferences
    pref_res = test_client.patch(
        "/api/connectors/telegram/preferences",
        json={
            "min_match_score": 92.0,
            "notify_high_match_jobs": True,
            "notify_interview_requests": True,
        },
    )
    assert pref_res.status_code == 200
    assert pref_res.json()["min_match_score"] == 92.0

    # 5. POST /api/connectors/telegram/test-alert
    test_alert_res = test_client.post(
        "/api/connectors/telegram/test-alert",
        json={"alert_type": "high_match_job", "match_score": 95.0},
    )
    assert test_alert_res.status_code == 200
    alert_data = test_alert_res.json()
    assert alert_data["status"] == "success"
    assert "[Apply Now]" in alert_data["action_buttons"]

    # 6. POST /api/connectors/telegram/webhook (simulate inline button click)
    webhook_res = test_client.post(
        "/api/connectors/telegram/webhook",
        json={
            "callback_query": {
                "data": "pitch_job_1",
                "message": {"chat": {"id": 88889999}, "message_id": 101},
            }
        },
    )
    assert webhook_res.status_code == 200
    assert webhook_res.json()["action"] == "draft_pitch"

    # 7. DELETE /api/connectors/telegram/pair
    del_res = test_client.delete("/api/connectors/telegram/pair")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"
