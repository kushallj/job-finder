"""
Unit tests for ProfileService, CandidateProfile, TargetCompanyRecord, and Conversion Funnel.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, CandidateProfile, TargetCompanyRecord, OutreachFunnelEvent
from src.services.profile_service import ProfileService

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

def test_profile_extraction_from_raw_text(db_session):
    service = ProfileService(db=db_session)
    sample_resume = """
    Aarav Sharma
    aarav.sharma@example.com | +91 9876543210
    https://linkedin.com/in/aarav-sharma | https://github.com/aaravsharma
    
    Summary:
    Full stack software engineer with 4 years of experience building Python and React applications.
    
    Technical Skills:
    Languages & Frameworks: Python, FastAPI, React, TypeScript, Docker, Kubernetes, PostgreSQL, Redis
    """
    extracted = service.extract_profile_from_text(sample_resume)
    assert extracted["full_name"] == "Aarav Sharma"
    assert extracted["email"] == "aarav.sharma@example.com"
    assert extracted["phone"] == "+91 9876543210"
    assert "linkedin.com/in/aarav-sharma" in extracted["linkedin_url"]
    assert "github.com/aaravsharma" in extracted["github_url"]
    assert "Python" in extracted["skills"]
    assert "FastAPI" in extracted["skills"]
    assert "React" in extracted["skills"]
    assert extracted["years_of_experience"] == 4.0

def test_profile_crud_and_target_companies(db_session):
    service = ProfileService(db=db_session)
    profile = service.get_or_create_profile("user_123")
    assert profile is not None
    assert profile.user_identifier == "user_123"

    updated = service.update_profile("user_123", {
        "full_name": "Dev Tester",
        "email": "dev@test.com",
        "skills": ["Go", "Kubernetes", "gRPC"],
        "years_of_experience": 5.5,
    })
    assert updated.full_name == "Dev Tester"
    assert updated.years_of_experience == 5.5
    assert "Go" in updated.skills

    # Add Target Company
    company = service.add_target_company("user_123", {
        "name": "Stripe",
        "domain": "stripe.com",
        "tier": "tier1",
        "industry": "FinTech / Payments",
        "signal_score": 95.0,
    })
    assert company.name == "Stripe"
    assert company.signal_score == 95.0

    companies = service.get_target_companies("user_123")
    assert len(companies) >= 1
    assert any(c.name == "Stripe" for c in companies)

def test_funnel_metrics_and_event_logging(db_session):
    service = ProfileService(db=db_session)
    # Log outreach events
    service.log_funnel_event(event_type="email_sent", company="Palantir", user_id="test_user")
    service.log_funnel_event(event_type="email_sent", company="Databricks", user_id="test_user")
    service.log_funnel_event(event_type="email_sent", company="Ramp", user_id="test_user")
    service.log_funnel_event(event_type="email_sent", company="Brex", user_id="test_user")
    service.log_funnel_event(event_type="reply_received", company="Ramp", notes="Recruiter asked for calendar", user_id="test_user")
    service.log_funnel_event(event_type="interview_scheduled", company="Ramp", role_title="Senior Backend", user_id="test_user")

    metrics = service.get_funnel_metrics("test_user")
    assert metrics["total_sent"] == 4
    assert metrics["replies"] == 1
    assert metrics["interviews"] == 1
    assert metrics["reply_rate_pct"] == 25.0
    assert metrics["interview_rate_pct"] == 25.0
    assert len(metrics["recent_events"]) == 6
