"""
tests/test_inbound_email_sync.py
Comprehensive test suite for Inbound Recruiter Email Sync & Auto-Advancing Pipeline.

Verifies:
1. Recruiter intent classification (INTERVIEW_INVITATION, ASSESSMENT, OFFER, REJECTION, FOLLOW_UP_REQUIRED)
2. InboundEmailSyncService matching and auto-advancement of Kanban cards without manual dragging
3. Amber (3d), Blue (6d), and Red (Overdue) countdown timers and Email Provenance Badges
4. REST API endpoints (/api/mailbox/connect, /api/mailbox/simulate-inbound, /api/mailbox/status, /api/mailbox/messages)
5. Reflection on /api/kanban/board
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
    MailboxAccount,
    InboundRecruiterMessage,
    User,
)
from src.database import get_db
from src.services.inbound_email_classifier import InboundEmailIntentClassifier
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
    """FastAPI TestClient with overridden database session and a seeded test user."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Seed a test user so JWT auth succeeds
    seed_db = TestingSessionLocal()
    test_user = User(
        id=1,
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )
    seed_db.merge(test_user)
    seed_db.commit()
    seed_db.close()

    from src.auth.jwt_handler import create_access_token
    token = create_access_token(data={"sub": "1"})

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        yield client
    app.dependency_overrides.clear()


def test_intent_classifier_interview_invitation():
    """Verify classification of interview invitations -> technical_interview + 3d countdown."""
    classifier = InboundEmailIntentClassifier()
    result = classifier.classify(
        subject="Re: Interview invitation — Senior Frontend Engineer",
        body="Hi Kushal, we would love to schedule an interview with our team. Please choose a time on calendly.com/tessellate",
    )
    assert result.intent == "INTERVIEW_INVITATION"
    assert result.target_stage == "technical_interview"
    assert result.action_title == "Technical Interview"
    assert result.countdown_days == 3
    assert result.confidence >= 0.90


def test_intent_classifier_phone_screen():
    """Verify recruiter screen classification."""
    classifier = InboundEmailIntentClassifier()
    result = classifier.classify(
        subject="Invitation: Quick Phone Screen with Stripe",
        body="We'd like to schedule an introductory phone screen to discuss your background.",
    )
    assert result.intent == "INTERVIEW_INVITATION"
    assert result.target_stage == "recruiter_screen"
    assert result.action_title == "Recruiter Screen"
    assert result.countdown_days == 3


def test_intent_classifier_assessment():
    """Verify classification of coding assessment -> take_home + 6d countdown."""
    classifier = InboundEmailIntentClassifier()
    result = classifier.classify(
        subject="Tessellate Engineering: Take-Home Coding Challenge",
        body="Please complete the following hackerrank technical assessment within 6 days.",
    )
    assert result.intent == "ASSESSMENT"
    assert result.target_stage == "take_home"
    assert result.action_title == "Take-home assessment"
    assert result.countdown_days == 6
    assert result.confidence >= 0.90


def test_intent_classifier_offer():
    """Verify classification of offer -> offer stage."""
    classifier = InboundEmailIntentClassifier()
    result = classifier.classify(
        subject="Formal Offer Letter: Senior Full Stack Engineer at Tessellate",
        body="We are pleased to offer you the position of Senior Full Stack Engineer. Please review the attached employment agreement.",
    )
    assert result.intent == "OFFER"
    assert result.target_stage == "offer"
    assert result.action_title == "Offer Review"
    assert result.countdown_days == 4


def test_intent_classifier_rejection():
    """Verify classification of rejection -> rejected column."""
    classifier = InboundEmailIntentClassifier()
    result = classifier.classify(
        subject="Update regarding your application with Acme Corp",
        body="Thank you for your interest. Unfortunately, we have decided to pursue other candidates whose qualifications more closely align with our needs.",
    )
    assert result.intent == "REJECTION"
    assert result.target_stage == "rejected"
    assert result.countdown_days is None


def test_intent_classifier_follow_up():
    """Verify classification of follow-up requests -> maintains stage, overdue red alert."""
    classifier = InboundEmailIntentClassifier()
    result = classifier.classify(
        subject="Action required: Additional information needed for Tessellate",
        body="Please provide your updated portfolio link and confirm your notice period.",
    )
    assert result.intent == "FOLLOW_UP_REQUIRED"
    assert result.target_stage is None  # Does not move card
    assert result.action_title == "Follow-up required"
    assert result.countdown_days == -1  # Overdue


def test_auto_advance_pipeline_interview_invitation(test_db_session):
    """
    Test end-to-end inbound recruiter sync auto-advancing a Kanban card
    from 'applied' to 'technical_interview' with amber countdown and email provenance.
    """
    # 1. Seed a Job and Application in 'applied' stage
    job = Job(
        job_id="job_tessellate_101",
        title="Senior Frontend Engineer",
        company="Tessellate",
        location="Bengaluru / Remote",
        description="Looking for expert in React, TypeScript, Vite, LLM Integration.",
    )
    test_db_session.add(job)
    test_db_session.commit()

    app_card = Application(
        job_id=job.id,
        user_id=1,
        status="applied",
        kanban_stage="applied",
        kanban_order=0,
        applied_at=datetime.utcnow() - timedelta(days=2),
    )
    test_db_session.add(app_card)
    test_db_session.commit()

    service = InboundEmailSyncService(test_db_session)

    # 2. Connect candidate mailbox
    mailbox = service.connect_mailbox(
        provider="gmail",
        email_address="candidate@gmail.com",
    )
    assert mailbox.id is not None
    assert mailbox.is_connected is True

    # 3. Process an inbound interview invitation email
    sim_result = service.process_inbound_message(
        sender_email="recruiter@tessellate.io",
        sender_name="Sarah Jenkins",
        subject="Re: Interview invitation — Senior Frontend Engineer",
        body_text="Hi Kushal, we were very impressed by your profile. Let's schedule an interview on calendly.com/tessellate-eng.",
        mailbox_id=mailbox.id,
    )

    # 4. Verify auto-advancement
    assert sim_result.matched is True
    assert sim_result.application_id == app_card.id
    assert sim_result.previous_stage == "applied"
    assert sim_result.new_stage == "technical_interview"
    assert sim_result.classified_intent == "INTERVIEW_INVITATION"
    assert sim_result.provenance_badge == '"Re: Interview invitation — Senior Frontend Engineer" from recruiter@tessellate.io'
    assert sim_result.alert_severity == "amber"
    assert "in 3 days" in sim_result.countdown_label

    # 5. Verify database state
    test_db_session.refresh(app_card)
    assert app_card.kanban_stage == "technical_interview"
    assert app_card.status == "interviewing"
    assert app_card.recruiter_email == "recruiter@tessellate.io"
    assert app_card.recruiter_name == "Sarah Jenkins"
    assert app_card.email_subject == "Re: Interview invitation — Senior Frontend Engineer"
    assert app_card.next_action_title == "Technical Interview"


def test_auto_advance_pipeline_take_home_assessment(test_db_session):
    """Test auto-advancing from 'applied' to 'take_home' with 6-day blue timer."""
    job = Job(
        job_id="job_scaleai_202",
        title="Backend Engineer",
        company="ScaleAI",
        location="San Francisco, CA",
    )
    test_db_session.add(job)
    test_db_session.commit()

    app_card = Application(
        job_id=job.id,
        user_id=1,
        status="applied",
        kanban_stage="applied",
        applied_at=datetime.utcnow() - timedelta(days=1),
    )
    test_db_session.add(app_card)
    test_db_session.commit()

    service = InboundEmailSyncService(test_db_session)
    sim_result = service.process_inbound_message(
        sender_email="hiring@scaleai.com",
        sender_name="Alex Tech",
        subject="ScaleAI: Take-home coding assessment",
        body_text="Please review the instructions and complete this take-home technical challenge.",
    )

    assert sim_result.matched is True
    assert sim_result.new_stage == "take_home"
    assert sim_result.alert_severity == "blue"
    assert "in 6 days" in sim_result.countdown_label

    test_db_session.refresh(app_card)
    assert app_card.kanban_stage == "take_home"
    assert app_card.next_action_title == "Take-home assessment"


def test_inbound_follow_up_maintains_stage_and_triggers_red_alert(test_db_session):
    """Test that FOLLOW_UP_REQUIRED maintains the current stage and sets a Red alert."""
    job = Job(
        job_id="job_deepmind_303",
        title="Staff AI Engineer",
        company="DeepMind",
        location="London / Remote",
    )
    test_db_session.add(job)
    test_db_session.commit()

    app_card = Application(
        job_id=job.id,
        user_id=1,
        status="interviewing",
        kanban_stage="technical_interview",
        applied_at=datetime.utcnow() - timedelta(days=5),
    )
    test_db_session.add(app_card)
    test_db_session.commit()

    service = InboundEmailSyncService(test_db_session)
    sim_result = service.process_inbound_message(
        sender_email="talent@deepmind.com",
        subject="Action required: Additional information needed for DeepMind role",
        body_text="Please provide your latest publication list by tomorrow.",
    )

    assert sim_result.matched is True
    assert sim_result.previous_stage == "technical_interview"
    assert sim_result.new_stage == "technical_interview"  # Unchanged!
    assert sim_result.alert_severity == "red"
    assert sim_result.countdown_label == "Overdue / Follow-up required"

    test_db_session.refresh(app_card)
    assert app_card.kanban_stage == "technical_interview"
    assert app_card.next_action_title == "Follow-up required"


def test_mailbox_fastapi_endpoints(test_client, test_engine):
    """Test the complete REST API workflow for mailbox connection and inbound simulation."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()

    # 1. Connect mailbox
    connect_resp = test_client.post(
        "/api/mailbox/connect",
        json={
            "provider": "gmail",
            "email_address": "kushal@example.com",
            "auto_advance_pipeline": True,
        },
    )
    assert connect_resp.status_code == 200
    account_data = connect_resp.json()
    assert account_data["email_address"] == "kushal@example.com"
    assert account_data["is_connected"] is True

    # 2. Check status endpoint
    status_resp = test_client.get("/api/mailbox/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["email_address"] == "kushal@example.com"

    # 3. Seed an application
    job = Job(
        job_id="job_tessellate_fastapi_1",
        title="Senior Frontend Engineer",
        company="Tessellate",
        location="Remote",
    )
    db.add(job)
    db.commit()

    app_card = Application(
        job_id=job.id,
        user_id=1,
        status="applied",
        kanban_stage="applied",
    )
    db.add(app_card)
    db.commit()
    db.close()

    # 4. Simulate inbound recruiter email
    sim_resp = test_client.post(
        "/api/mailbox/simulate-inbound",
        json={
            "sender_email": "recruiter@tessellate.io",
            "sender_name": "Sarah Recruiter",
            "subject": "Re: Interview invitation — Senior Frontend Engineer",
            "body_text": "We would love to schedule a technical interview with our frontend team. Please pick a slot on calendly.com/tessellate-eng",
        },
    )
    assert sim_resp.status_code == 200
    adv_data = sim_resp.json()
    assert adv_data["matched"] is True
    assert adv_data["new_stage"] == "technical_interview"
    assert adv_data["alert_severity"] == "amber"
    assert "in 3 days" in adv_data["countdown_label"]
    assert adv_data["provenance_badge"] == '"Re: Interview invitation — Senior Frontend Engineer" from recruiter@tessellate.io'

    # 5. Check Kanban Board reflection
    board_resp = test_client.get("/api/kanban/board")
    assert board_resp.status_code == 200
    board_data = board_resp.json()
    interview_cards = board_data["columns"]["technical_interview"]
    assert len(interview_cards) == 1
    card = interview_cards[0]
    assert card["company"] == "Tessellate"
    assert card["provenance_badge"] == '"Re: Interview invitation — Senior Frontend Engineer" from recruiter@tessellate.io'
    assert card["alert_severity"] == "amber"
    assert "in 3 days" in card["countdown_label"]

    # 6. Check messages audit trail endpoint
    msg_resp = test_client.get("/api/mailbox/messages")
    assert msg_resp.status_code == 200
    messages = msg_resp.json()
    assert len(messages) >= 1
    assert messages[0]["classified_intent"] == "INTERVIEW_INVITATION"
    assert messages[0]["new_kanban_stage"] == "technical_interview"
