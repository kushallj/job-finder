"""
tests/test_workday_autopilot.py — Comprehensive Unit & Integration Test Suite for Workday Autopilot.
Verifies autonomous Workday tenant account provisioning, dynamic resume tailoring,
ATS keyword scoring, ReportLab PDF compilation, 5-step multi-form automation, and FastAPI endpoints.
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.database import Base, get_db
from src.models import Application, Job, Resume
from src.workday.models import (
    WorkdayCandidateProfile,
    WorkdayAccountRecord,
    WorkdayApplicationSubmission,
    WorkdayConfigRecord,
)
from src.workday.client import WorkdayClient, parse_workday_url
from src.workday.resume_tailorer import WorkdayResumeTailorer
from src.workday.service import WorkdayService
from src.workday.api.workday_router import router as workday_router


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


def test_workday_url_parsing():
    """Verify URL parsing across diverse Workday tenant URL formats."""
    test_cases = [
        (
            "https://gartner.wd5.myworkdayjobs.com/Gartner/job/Fort-Myers-Florida/Account-Executive_JR00888",
            ("gartner", "wd5", "Gartner", "JR00888"),
        ),
        (
            "https://nvidia.wd3.myworkdayjobs.com/NVIDIAExternalCareerSite/job/Santa-Clara-CA/Senior-Software-Engineer_JR194821",
            ("nvidia", "wd3", "NVIDIAExternalCareerSite", "JR194821"),
        ),
        (
            "https://flip.myworkdayjobs.com/Careers/job/Remote/Lead-Architect_90210",
            ("flip", "wd1", "Careers", "90210"),
        ),
        (
            "https://target.wd1.myworkdayjobs.com/en-US/targetcareers/job/Minneapolis-MN/Manager_R0001",
            ("target", "wd1", "targetcareers", "R0001"),
        ),
    ]

    for url, expected in test_cases:
        parsed = parse_workday_url(url)
        assert parsed["is_workday"] is True
        assert parsed["tenant"] == expected[0]
        assert parsed["instance"] == expected[1]
        assert parsed["site"] == expected[2]
        assert parsed["job_id"] == expected[3]

    # Non-workday URL test
    invalid_parsed = parse_workday_url("https://boards.greenhouse.io/stripe/jobs/12345")
    assert invalid_parsed["is_workday"] is False


def test_workday_resume_tailorer_and_pdf_generation():
    """Verify AI dynamic resume keyword extraction, ATS scoring, and PDF synthesis."""
    tailorer = WorkdayResumeTailorer()
    
    job_description = """
    We are seeking a Senior Distributed Systems Engineer experienced with Python, FastAPI, Docker,
    PostgreSQL, Redis, Kubernetes, Kafka, and Microservices Architecture.
    You will design scalable cloud systems and optimize high-throughput data pipelines.
    """
    
    candidate_profile = {
        "full_name": "Kushall Jain",
        "email": "canaby007@gmail.com",
        "phone": "+1 (555) 019-2834",
        "city": "San Francisco",
        "state": "CA",
        "headline": "Lead Systems & Backend Engineer",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis", "Kafka", "AWS"],
        "experience": [
            {
                "title": "Lead Backend Engineer",
                "company": "CloudScale AI",
                "dates": "2022 - Present",
                "description": "Architected high-throughput microservices using Python and FastAPI. Scaled Postgres database and Kafka streaming queues."
            }
        ],
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "institution": "University of California",
                "year": "2020"
            }
        ]
    }

    # 1. Preview Tailoring
    tailored = tailorer.tailor_for_workday(job_description, candidate_profile)
    assert tailored["ats_score"] >= 70
    assert len(tailored["matched_keywords"]) >= 4
    assert "Microservices" in tailored["matched_keywords"] or "Python" in tailored["matched_keywords"]
    assert "FastAPI" in tailored["skills"]

    # 2. PDF Synthesis
    pdf_path = tailorer.generate_tailored_pdf(
        job_id=999,
        company_name="Gartner",
        tailored_data=tailored,
        candidate_profile=candidate_profile
    )
    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")
    assert os.path.getsize(pdf_path) > 1000  # PDF generated with valid binary stream


@pytest.mark.asyncio
async def test_workday_client_account_and_submission():
    """Verify autonomous account registration, login, and 5-step form submission."""
    client = WorkdayClient(tenant_domain="gartner.wd5.myworkdayjobs.com")

    # 1. Account registration
    reg_result = await client.register_candidate_account("canaby007@gmail.com", "SecureWorkdayPass123!")
    assert reg_result["success"] is True
    assert reg_result["account_created"] is True
    assert reg_result["tenant"] == "gartner"

    # 2. Account login
    login_result = await client.login_candidate_account("canaby007@gmail.com", "SecureWorkdayPass123!")
    assert login_result["success"] is True
    assert "session_token" in login_result

    # 3. 5-step execution
    submission_packet = {
        "job": {"id": 888, "company": "Gartner", "title": "Senior Solutions Architect", "url": "https://gartner.wd5.myworkdayjobs.com/Gartner/job/888"},
        "candidate": {"full_name": "Kushall Jain", "email": "canaby007@gmail.com"},
        "tailored_resume_path": "/tmp/dummy_resume.pdf",
        "screening_answers": {"legal_authorization": "Yes", "requires_sponsorship": "No"},
        "eeo": {"gender": "Decline to specify", "race_ethnicity": "Asian"}
    }

    sub_result = await client.execute_multi_step_submission(
        session_token=login_result["session_token"],
        job_url=submission_packet["job"]["url"],
        submission_data=submission_packet
    )

    assert sub_result["success"] is True
    assert sub_result["status"] == "submitted"
    assert sub_result["receipt_id"].startswith("WD-GARTNER-")
    assert len(sub_result["steps_completed"]) == 5
    assert "step5_eeo_and_signature" in sub_result["steps_completed"]


@pytest.mark.asyncio
async def test_workday_service_single_apply(db_session):
    """Verify WorkdayService end-to-end auto application for a Workday posting."""
    job = Job(
        id=777,
        job_id="wd-job-777",
        title="Senior Platform Engineer",
        company="NVIDIA",
        description="NVIDIA is hiring a Senior Platform Engineer with Python, Go, Kubernetes, and Cloud Architecture.",
        url="https://nvidia.wd3.myworkdayjobs.com/NVIDIAExternalCareerSite/job/Santa-Clara/Senior-Platform-Engineer_777",
    )
    db_session.add(job)
    db_session.commit()

    service = WorkdayService(db=db_session)
    result = await service.auto_apply_job(job_id=777)

    assert result["success"] is True
    assert result["receipt_id"].startswith("WD-NVIDIA-")
    assert result["tenant"] == "nvidia"
    assert result["ats_score"] >= 60
    assert os.path.exists(result["resume_path"])

    # Verify Account record was provisioned
    acct = db_session.query(WorkdayAccountRecord).filter(WorkdayAccountRecord.tenant_domain == "nvidia.wd3.myworkdayjobs.com").first()
    assert acct is not None
    assert acct.email == "canaby007@gmail.com"
    assert acct.status == "active"

    # Verify Submission record
    sub = db_session.query(WorkdayApplicationSubmission).filter(WorkdayApplicationSubmission.job_id == 777).first()
    assert sub is not None
    assert sub.status == "submitted"
    assert sub.receipt_id == result["receipt_id"]

    # Verify Application table record
    app = db_session.query(Application).filter(Application.job_id == 777).first()
    assert app is not None
    assert app.status == "applied"
    assert app.ats_detected == "workday"

    # Test Idempotency (re-applying should return already_applied without duplicate increment)
    re_result = await service.auto_apply_job(job_id=777)
    assert re_result["success"] is True
    assert re_result.get("already_applied") is True


@pytest.mark.asyncio
async def test_workday_batch_auto_apply(db_session):
    """Verify batch auto-apply against multiple Workday job postings."""
    # Seed 5 Workday jobs
    for i in range(1, 6):
        job = Job(
            id=2000 + i,
            job_id=f"wd-batch-{i}",
            title=f"Cloud Engineer #{i}",
            company=f"TenantCorp{i}",
            description="Python, Kubernetes, Docker, and Microservices.",
            url=f"https://tenant{i}.wd5.myworkdayjobs.com/careers/job/{i}",
        )
        db_session.add(job)
    db_session.commit()

    service = WorkdayService(db=db_session)
    batch_res = await service.batch_auto_apply(target_count=5, min_score=50.0)

    assert batch_res["status"] == "completed"
    assert batch_res["successful_submissions"] == 5
    assert batch_res["failed_submissions"] == 0
    assert len(batch_res["recent_receipts"]) == 5
    assert batch_res["daily_progress"] == "5/100"

    # Quota check
    config = db_session.query(WorkdayConfigRecord).first()
    assert config.daily_used == 5


def test_workday_fastapi_endpoints(db_session):
    """Verify all Workday FastAPI router endpoints."""
    app = FastAPI()
    app.include_router(workday_router)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    # 1. GET /api/workday/status
    res = client.get("/api/workday/status")
    assert res.status_code == 200
    data = res.json()
    assert data["profile"]["email"] == "canaby007@gmail.com"
    assert data["config"]["daily_limit"] == 100

    # 2. GET & POST /api/workday/profile
    prof_res = client.get("/api/workday/profile")
    assert prof_res.status_code == 200
    assert prof_res.json()["full_name"] == "Kushall Jain"

    upd_res = client.post("/api/workday/profile", json={
        "full_name": "Kushall Jain",
        "email": "canaby007@gmail.com",
        "phone": "+1 555-987-6543",
        "city": "San Francisco",
        "state": "CA",
        "postal_code": "94105",
        "headline": "Senior Staff Distributed Systems Architect",
        "linkedin_url": "https://linkedin.com/in/kushalljain",
        "github_url": "https://github.com/canaby007",
        "experience_years": 8,
        "skills": ["Python", "FastAPI", "Go", "Kubernetes", "AWS", "Workday API"],
        "education": [{"degree": "B.S. Computer Science", "school": "UC Berkeley"}],
        "work_history": [{"title": "Staff Architect", "company": "NextGen"}],
        "salary_expectation": 185000,
        "is_authorized_us": True,
        "requires_sponsorship": False,
        "eeo_gender": "Decline to self-identify",
        "eeo_race": "Asian",
        "eeo_veteran": "No",
        "eeo_disability": "No"
    })
    assert upd_res.status_code == 200
    assert upd_res.json()["profile"]["experience_years"] == 8

    # 3. POST /api/workday/preview-tailor
    tailor_res = client.post("/api/workday/preview-tailor", json={
        "job_description": "Seeking Python and FastAPI expert for microservices architecture."
    })
    assert tailor_res.status_code == 200
    assert "tailored_profile" in tailor_res.json()
    assert tailor_res.json()["ats_score"] > 50

    # 4. GET /api/workday/accounts & GET /api/workday/submissions
    accts_res = client.get("/api/workday/accounts")
    assert accts_res.status_code == 200
    assert isinstance(accts_res.json()["accounts"], list)

    subs_res = client.get("/api/workday/submissions")
    assert subs_res.status_code == 200
    assert isinstance(subs_res.json()["submissions"], list)

    # 5. POST /api/workday/config
    cfg_res = client.post("/api/workday/config", json={
        "daily_limit": 150,
        "auto_pilot_enabled": True,
        "min_match_score": 65.0
    })
    assert cfg_res.status_code == 200
    assert cfg_res.json()["config"]["daily_limit"] == 150

    # 6. POST /api/workday/resolve-question (Phase 2 AnswerBank Bridge)
    q_res = client.post("/api/workday/resolve-question", json={
        "question": "What experience do you have with distributed systems and microservices?",
        "job_title": "Senior Backend Architect",
        "company": "Scale Dynamics"
    })
    assert q_res.status_code == 200
    assert "answer" in q_res.json()
    assert len(q_res.json()["answer"]) > 0
    assert q_res.json()["confidence"] >= 0.90

    # 7. POST /api/workday/save-answer (Phase 4 Bi-Directional Learning Loop)
    custom_q = "How many years of experience do you have designing distributed event-driven systems?"
    custom_ans = "I have 8+ years architecting Kafka and microservices handling 50k req/s."
    save_res = client.post("/api/workday/save-answer", json={
        "question": custom_q,
        "answer": custom_ans,
        "category": "years_of_experience",
        "source": "user_edited"
    })
    assert save_res.status_code == 200
    assert save_res.json()["status"] == "saved"
    assert save_res.json()["answer"] == custom_ans
    assert save_res.json()["source"] == "user_edited"
    assert save_res.json()["profile_updated"] is True

    # Check that subsequent resolve-question immediately hits user-edited cached answer
    resolve_cached_res = client.post("/api/workday/resolve-question", json={
        "question": custom_q,
        "job_title": "Senior Backend Architect",
        "company": "Scale Dynamics"
    })
    assert resolve_cached_res.status_code == 200
    assert resolve_cached_res.json()["cached"] is True
    assert resolve_cached_res.json()["answer"] == custom_ans
    assert resolve_cached_res.json()["source"] == "user_edited"

    # 8. POST /api/workday/save-answers-batch
    batch_save_res = client.post("/api/workday/save-answers-batch", json={
        "answers": [
            {
                "question": "What is your notice period?",
                "answer": "Immediately available (0 days)",
                "category": "notice_period",
                "source": "user_edited"
            },
            {
                "question": "Are you open to hybrid roles in San Francisco?",
                "answer": "Yes, open to 3 days on-site in SF.",
                "category": "location_preference",
                "source": "user_edited"
            }
        ]
    })
    assert batch_save_res.status_code == 200
    assert batch_save_res.json()["saved_count"] == 2

    # 9. GET /api/workday/answers
    list_ans_res = client.get("/api/workday/answers?limit=50")
    assert list_ans_res.status_code == 200
    assert list_ans_res.json()["total_count"] >= 3
    found_item = next((a for a in list_ans_res.json()["answers"] if "notice period" in a["question_text"].lower()), None)
    assert found_item is not None
    assert found_item["answer_text"] == "Immediately available (0 days)"

    # 10. DELETE /api/workday/answers/{id}
    del_res = client.delete(f"/api/workday/answers/{found_item['id']}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


