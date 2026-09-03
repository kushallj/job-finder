"""
tests/test_tsenta_auto_apply.py — Comprehensive Unit Test Suite for Tsenta Auto-Apply Engine.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.models import Application, Job, Resume
from src.tsenta.ats_detector import detect_ats, SUPPORTED_ATS_LIST
from src.tsenta.client import TsentaClient
from src.tsenta.models import TsentaConfigRecord, TsentaQuota, TsentaSubmission
from src.tsenta.payload_builder import TsentaPayloadBuilder
from src.tsenta.service import TsentaService


@pytest.fixture
def db_session():
    """In-memory SQLite database session for isolated testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_ats_detection_across_platforms():
    """Test 18+ ATS classifier on URLs and page heuristics."""
    test_cases = [
        ("https://boards.greenhouse.io/anthropic/jobs/4029102", "greenhouse"),
        ("https://jobs.lever.co/openai/8f3a9b", "lever"),
        ("https://nvidia.wd3.myworkdayjobs.com/NVIDIAExternalCareerSite/job/Senior-Engineer", "workday"),
        ("https://jobs.ashbyhq.com/linear/c929a", "ashby"),
        ("https://acme.bamboohr.com/careers/12", "bamboohr"),
        ("https://jobs.smartrecruiters.com/Stripe/123", "smartrecruiters"),
        ("https://jobs.jobvite.com/hulu/job/123", "jobvite"),
        ("https://oracle.taleo.net/careersection/jobdetail.ftl", "taleo"),
        ("https://careers-microsoft.icims.com/jobs/123", "icims"),
        ("https://career4.successfactors.com/careers", "successfactors"),
        ("https://startup.breezy.hr/p/123-engineer", "breezyhr"),
        ("https://customcompany.com/careers/open-role", "custom_ats"),
    ]

    for url, expected_code in test_cases:
        info = detect_ats(url)
        assert info.code == expected_code, f"Expected {expected_code} for {url}, got {info.code}"


@pytest.mark.asyncio
async def test_payload_builder_and_screening_resolution(db_session):
    """Test AI submission packet generation and Answer Bank resolution."""
    from src.answer_bank.models import AnsweredQuestion

    # Pre-seed cache entries to test instant retrieval
    db_session.add(
        AnsweredQuestion(
            question_text="How many years of Python experience do you have?",
            normalized_question="how many years of python experience do you have",
            answer_text="I have over 4 years of production Python and FastAPI experience.",
            source="manual",
            category="ats_screening",
            context="ats_application",
        )
    )
    db_session.add(
        AnsweredQuestion(
            question_text="Are you authorized to work?",
            normalized_question="are you authorized to work",
            answer_text="Yes, I am fully authorized to work.",
            source="manual",
            category="ats_screening",
            context="ats_application",
        )
    )
    db_session.commit()

    job = Job(
        id=101,
        job_id="test-job-101",
        title="Staff Backend Engineer",
        company="Databricks",
        description="We are looking for a Python and FastAPI engineer with experience in PostgreSQL, Redis, and distributed systems.",
        url="https://jobs.lever.co/databricks/101",
    )
    db_session.add(job)
    db_session.commit()

    builder = TsentaPayloadBuilder(db=db_session)
    packet = await builder.build_submission_packet(
        job=job,
        sample_questions=["How many years of Python experience do you have?", "Are you authorized to work?"],
    )

    assert packet["applicant"]["full_name"] == "Kushall Jain"
    assert "Databricks" in packet["job"]["company"]
    assert len(packet["screening_questions"]) == 2
    assert "Python" in packet["screening_questions"][0]["question"]
    assert "experience" in packet["screening_questions"][0]["answer"].lower()
    assert "Databricks" in packet["cover_letter"]



@pytest.mark.asyncio
async def test_tsenta_client_submission_and_receipt(db_session):
    """Test submission dispatch and verifiable cryptographic receipt creation."""
    client = TsentaClient()
    ats_info = detect_ats("https://boards.greenhouse.io/figma/jobs/123")
    
    packet = {
        "job": {"id": 202, "company": "Figma", "title": "Senior Software Engineer"},
        "applicant": {"full_name": "Kushall Jain", "email": "canaby007@gmail.com"},
        "screening_questions": [{"question": "Notice period?", "answer": "Immediate"}],
    }

    result = await client.submit_application(packet, ats_info, dry_run=True)
    assert result["status"] == "submitted"
    assert result["receipt_id"].startswith("TSENTA-GREENHOUSE-")
    assert "https://tsenta.com/receipts/" in result["proof_url"]


@pytest.mark.asyncio
async def test_tsenta_service_review_gate_and_approval(db_session):
    """Test full review gate workflow: review_ready -> approve_and_submit -> submitted."""
    job = Job(
        id=303,
        job_id="test-job-303",
        title="Distributed Systems Lead",
        company="Palantir",
        url="https://boards.greenhouse.io/palantir/jobs/303",
    )
    db_session.add(job)
    db_session.commit()

    service = TsentaService(db=db_session)
    
    # 1. Trigger Auto-Apply (Review Required mode)
    review_res = await service.auto_apply_job(
        job_id=303,
        mode_override="review_required",
        sample_questions=["How many years of Python experience do you have?", "Are you authorized to work?"],
    )
    assert review_res["status"] == "review_ready"
    assert review_res["ats_code"] == "greenhouse"
    submission_id = review_res["submission"]["id"]

    # Verify submission in DB
    sub_record = db_session.query(TsentaSubmission).filter(TsentaSubmission.id == submission_id).first()
    assert sub_record.status == "review_ready"

    # 2. User reviews and approves submission
    approve_res = await service.approve_and_submit(
        submission_id=submission_id,
        custom_cover_letter="Approved custom cover letter.",
    )
    assert approve_res["status"] == "submitted"
    assert approve_res["receipt_id"].startswith("TSENTA-GREENHOUSE-")

    # Verify updated DB state
    db_session.refresh(sub_record)
    assert sub_record.status == "submitted"
    assert sub_record.receipt_id == approve_res["receipt_id"]

    # Verify Application table updated
    app_record = db_session.query(Application).filter(Application.job_id == 303).first()
    assert app_record is not None
    assert app_record.status == "applied"
    assert app_record.ats_detected == "Greenhouse"



@pytest.mark.asyncio
async def test_quota_tracking_and_config(db_session):
    """Test quota management and configuration updates."""
    service = TsentaService(db=db_session)
    
    # Update config
    updated_cfg = service.update_config({
        "mode": "full_auto",
        "min_fit_score": 85,
        "auto_apply_enabled": True,
    })
    assert updated_cfg["mode"] == "full_auto"
    assert updated_cfg["min_fit_score"] == 85

    # Check status
    status = await service.client.get_account_status()
    assert status["engine_status"] == "online"
    assert status["supported_ats_count"] == 18
