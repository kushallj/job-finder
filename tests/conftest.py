"""Shared test fixtures for the job-finder test suite."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Job, Application, Resume, Contact, OutreachRecord, ProcessingResult, PipelineMetric
from src.database import init_db

try:
    from hypothesis import settings, HealthCheck
    settings.register_profile(
        "fast",
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    settings.load_profile("fast")
except ImportError:
    pass



@pytest.fixture
def test_db():
    """Create an in-memory SQLite DB with all tables, yield a session, then tear down."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def sample_job():
    """Return a Job instance for testing."""
    return Job(
        job_id="test_123",
        title="Senior Python Dev",
        company="Stripe",
        location="Remote",
        description="Looking for senior Python developer with Django, FastAPI, PostgreSQL. 5+ years.",
        url="https://stripe.com/jobs/123",
        source="adzuna",
    )


@pytest.fixture
def sample_contact():
    """Return a Contact instance for testing."""
    return Contact(
        name="John Doe",
        title="Engineering Manager",
        email="john.doe@stripe.com",
        company="Stripe",
        department="Engineering",
        confidence_score=85,
    )


@pytest.fixture
def sample_resume_text():
    """Return a sample resume string with relevant skills."""
    return """
    KUSHAL JAIN
    Senior Software Engineer

    SKILLS:
    - Python (7 years)
    - Django (5 years)
    - FastAPI (3 years)
    - React (4 years)
    - PostgreSQL (5 years)
    - Docker (4 years)
    - AWS (4 years)

    EXPERIENCE:
    Senior Software Engineer | TechCorp | 2019 - Present
    - Built scalable REST APIs using Django and FastAPI
    - Managed PostgreSQL databases serving 1M+ daily requests
    - Deployed microservices on AWS using Docker and ECS
    - Led frontend development with React and TypeScript

    Software Engineer | StartupXYZ | 2017 - 2019
    - Developed full-stack features using Python/Django and React
    - Implemented CI/CD pipelines with Docker and AWS
    - Optimized database queries reducing latency by 40%

    EDUCATION:
    B.S. Computer Science | University of Technology | 2017
    """


@pytest.fixture
def sample_jd_text():
    """Return a sample job description requiring specific skills."""
    return """
    Senior Python Developer - Stripe

    We are looking for an experienced Python developer to join our payments team.

    Requirements:
    - 5+ years of professional Python development
    - Strong experience with Django and/or FastAPI
    - Deep knowledge of PostgreSQL and database optimization
    - Experience building RESTful APIs at scale
    - Familiarity with microservices architecture

    Nice to have:
    - Experience with Docker and container orchestration
    - AWS or cloud platform experience
    - Frontend experience (React preferred)

    What you'll do:
    - Design and implement backend services for our payments platform
    - Optimize database performance for high-throughput transactions
    - Collaborate with cross-functional teams on API design
    - Mentor junior engineers and review code
    """
