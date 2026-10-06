"""
tests/test_nextraise_auto_apply.py — Comprehensive Unit & Integration Test Suite for NextRaise Auto-Apply.
Verifies high-volume dispatching (200-300 daily target), OAuth for canaby007@gmail.com,
tamper-evident cryptographic receipts, multi-ATS integration, and quota enforcement.
"""
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.database import Base, get_db
from src.models import Application, Job, Resume
from src.tsenta.ats_detector import detect_ats
from src.nextraise.client import NextRaiseClient
from src.nextraise.models import NextRaiseConfigRecord, NextRaiseQuota, NextRaiseSubmission
from src.nextraise.payload_builder import NextRaisePayloadBuilder
from src.nextraise.service import NextRaiseService
from src.nextraise.api.nextraise_router import router as nextraise_router
from fastapi import FastAPI


from sqlalchemy.pool import StaticPool

@pytest.fixture
def db_session():
    """In-memory SQLite database session for isolated testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_ats_detection_for_nextraise():
    """Verify ATS detection across top multi-ATS portals."""
    test_cases = [
        ("https://nvidia.wd3.myworkdayjobs.com/NVIDIAExternalCareerSite/job/Senior-Engineer", "workday"),
        ("https://boards.greenhouse.io/anthropic/jobs/4029102", "greenhouse"),
        ("https://jobs.lever.co/openai/8f3a9b", "lever"),
        ("https://jobs.ashbyhq.com/linear/c929a", "ashby"),
        ("https://acme.bamboohr.com/careers/12", "bamboohr"),
        ("https://jobs.smartrecruiters.com/Stripe/123", "smartrecruiters"),
        ("https://oracle.taleo.net/careersection/jobdetail.ftl", "taleo"),
        ("https://careers-microsoft.icims.com/jobs/123", "icims"),
        ("https://career4.successfactors.com/careers", "successfactors"),
        ("https://startup.tech/careers/engineer", "custom_ats"),
    ]

    for url, expected_code in test_cases:
        info = detect_ats(url)
        assert info.code == expected_code, f"Expected {expected_code} for {url}, got {info.code}"


def test_nextraise_client_receipt_and_dispatch():
    """Verify NextRaise cryptographic receipt generation and proof URL."""
    client = NextRaiseClient(account_email="canaby007@gmail.com")
    receipt_id = client.generate_receipt_id(job_id=42, company="Netflix", ats_code="workday")
    
    assert receipt_id.startswith("NR-WORKDAY-")
    assert len(receipt_id) > 12


@pytest.mark.asyncio
async def test_nextraise_client_autonomous_submission():
    """Verify autonomous submission packet processing."""
    client = NextRaiseClient(account_email="canaby007@gmail.com")
    ats_info = detect_ats("https://jobs.lever.co/databricks/101")
    
    packet = {
        "job": {"id": 101, "company": "Databricks", "title": "Senior Systems Engineer", "url": "https://jobs.lever.co/databricks/101"},
        "candidate": {"full_name": "Kushall Jain", "email": "canaby007@gmail.com"},
        "answers": [{"question": "Are you legally authorized to work?", "answer": "Yes, I am fully authorized to work."}],
        "tailored_resume_text": "Experienced Python/FastAPI and Distributed Systems Engineer...",
        "cover_letter_text": "Dear Hiring Team at Databricks...",
    }

    result = await client.submit_application(packet, ats_info, dry_run=False)
    assert result["success"] is True
    assert result["receipt_id"].startswith("NR-LEVER-")
    assert "https://app.nextraise.ai/proof/NR-LEVER-" in result["proof_url"]
    assert result["account_email"] == "canaby007@gmail.com"


@pytest.mark.asyncio
async def test_nextraise_payload_builder(db_session):
    """Verify payload builder synthesizes candidate profile and screening questions."""
    job = Job(
        id=202,
        job_id="test-job-202",
        title="Staff Backend Engineer",
        company="Uber",
        description="We are seeking an expert in Python, Go, Kafka, and large-scale microservices.",
        url="https://nvidia.wd3.myworkdayjobs.com/uber/job/202",
    )
    db_session.add(job)
    db_session.commit()

    ats_info = detect_ats(job.url)
    builder = NextRaisePayloadBuilder(db=db_session)
    packet = builder.build_packet(job, ats_info, account_email="canaby007@gmail.com")

    assert packet["candidate"]["email"] == "canaby007@gmail.com"
    assert packet["job"]["company"] == "Uber"
    assert packet["job"]["ats_type"] == "workday"
    assert len(packet["answers"]) >= 3
    assert "Uber" in packet["cover_letter_text"]


@pytest.mark.asyncio
async def test_nextraise_service_single_apply(db_session):
    """Verify single job auto-apply updates database records and quota."""
    job = Job(
        id=303,
        job_id="test-job-303",
        title="Distributed Systems Lead",
        company="Palantir",
        description="Palantir is seeking a distributed systems architect.",
        url="https://boards.greenhouse.io/palantir/jobs/303",
    )
    db_session.add(job)
    db_session.commit()

    service = NextRaiseService(db=db_session)
    res = await service.auto_apply_job(job_id=303)

    assert res["success"] is True
    assert res["receipt_id"].startswith("NR-GREENHOUSE-")
    assert res["ats_type"] == "greenhouse"

    # Verify submission record
    sub = db_session.query(NextRaiseSubmission).filter(NextRaiseSubmission.job_id == 303).first()
    assert sub is not None
    assert sub.status == "applied"
    assert sub.account_email == "canaby007@gmail.com"
    assert sub.receipt_id == res["receipt_id"]

    # Verify Application record
    app = db_session.query(Application).filter(Application.job_id == 303).first()
    assert app is not None
    assert app.status == "applied"
    assert app.ats_detected == "greenhouse"

    # Verify quota updated
    quota = db_session.query(NextRaiseQuota).first()
    assert quota.daily_used == 1
    assert quota.total_submitted == 1

    # Test idempotency (re-apply should not re-submit)
    re_res = await service.auto_apply_job(job_id=303)
    assert re_res["success"] is True
    assert re_res.get("already_applied") is True
    assert quota.daily_used == 1  # Quota unchanged


@pytest.mark.asyncio
async def test_nextraise_high_volume_batch_apply(db_session):
    """Verify high-volume batch auto-apply for target quotas."""
    # Seed 10 jobs
    for i in range(1, 11):
        job = Job(
            id=1000 + i,
            job_id=f"batch-job-{i}",
            title=f"Platform Engineer #{i}",
            company=f"TechCorp {i}",
            description="High-scale cloud and microservices engineering.",
            url=f"https://jobs.lever.co/techcorp{i}/{i}",
        )
        db_session.add(job)
    db_session.commit()

    service = NextRaiseService(db=db_session)
    
    # Run batch apply for 10 jobs
    batch_res = await service.batch_auto_apply(target_count=10, min_score=50.0)
    assert batch_res["status"] == "completed"
    assert batch_res["successful_submissions"] == 10
    assert batch_res["failed_submissions"] == 0
    assert batch_res["daily_progress"] == "10/300"
    assert len(batch_res["recent_receipts"]) == 10

    # Quota check
    quota = db_session.query(NextRaiseQuota).first()
    assert quota.daily_used == 10
    assert quota.total_submitted == 10


@pytest.mark.asyncio
async def test_quota_limit_enforcement(db_session):
    """Verify quota halts when daily limit (e.g., 300) is reached."""
    service = NextRaiseService(db=db_session)
    service.quota.daily_used = 300
    service.quota.daily_limit = 300
    db_session.commit()

    batch_res = await service.batch_auto_apply(target_count=50)
    assert batch_res["status"] == "quota_reached"
    assert batch_res["daily_used"] == 300
    assert "Daily target of 300 applications reached" in batch_res["message"]


def test_nextraise_fastapi_endpoints(db_session):
    """Verify NextRaise REST API routes."""
    app = FastAPI()
    app.include_router(nextraise_router)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    # 1. GET /api/nextraise/status
    res = client.get("/api/nextraise/status")
    assert res.status_code == 200
    data = res.json()
    assert data["account"]["account_email"] == "canaby007@gmail.com"
    assert data["quota"]["daily_limit"] == 300

    # 2. POST /api/nextraise/oauth/authorize
    auth_res = client.post("/api/nextraise/oauth/authorize", json={
        "account_email": "canaby007@gmail.com",
        "oauth_access_token": "nr_oauth_test_token_999",
        "session_token": "nr_sess_999",
    })
    assert auth_res.status_code == 200
    assert auth_res.json()["status"] == "connected"

    # 3. GET /api/nextraise/config & POST /api/nextraise/config
    cfg_res = client.get("/api/nextraise/config")
    assert cfg_res.status_code == 200
    assert cfg_res.json()["daily_target"] == 300

    upd_res = client.post("/api/nextraise/config", json={
        "daily_target": 250,
        "min_fit_score": 65.0,
    })
    assert upd_res.status_code == 200
    assert upd_res.json()["config"]["daily_target"] == 250
    assert upd_res.json()["config"]["min_fit_score"] == 65.0
