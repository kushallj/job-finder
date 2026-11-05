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

# ---------------------------------------------------------------------------
# Clerk auth for tests: real RS256 tokens verified against a stub JWKS client.
# Usage: def test_x(clerk_auth): headers = clerk_auth.headers("user_a", "a@x.com")
# ---------------------------------------------------------------------------

class _StubSigningKey:
    def __init__(self, key):
        self.key = key


class _StubJWKClient:
    def __init__(self, public_pem):
        self._public_pem = public_pem

    def get_signing_key_from_jwt(self, token):
        return _StubSigningKey(self._public_pem)


class ClerkTestAuth:
    ISSUER = "https://test-clerk.example.com"

    def __init__(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.private_pem = key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
        self.public_pem = key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def token(self, sub="user_test", email="test@example.com", azp="http://localhost:3000", ttl=300, **claims):
        import time
        import jwt

        now = int(time.time())
        payload = {"sub": sub, "email": email, "iss": self.ISSUER, "iat": now, "nbf": now - 5, "exp": now + ttl}
        if azp:
            payload["azp"] = azp
        payload.update(claims)
        return jwt.encode(payload, self.private_pem, algorithm="RS256")

    def headers(self, sub="user_test", email="test@example.com", **kw):
        return {"Authorization": f"Bearer {self.token(sub, email, **kw)}"}


@pytest.fixture
def clerk_auth(monkeypatch):
    from src.auth.dependencies import set_clerk_jwks_client
    from src.config import settings

    auth = ClerkTestAuth()
    monkeypatch.setattr(settings, "clerk_issuer", auth.ISSUER)
    monkeypatch.setattr(settings, "clerk_authorized_parties", "http://localhost:3000")
    monkeypatch.setattr(settings, "multi_tenant_enabled", True)
    set_clerk_jwks_client(_StubJWKClient(auth.public_pem))
    yield auth
    set_clerk_jwks_client(None)

@pytest.fixture(autouse=True)
def _legacy_single_tenant_auth(request, monkeypatch):
    """Legacy endpoint tests predate global auth and call the API without a token.

    Run them in the backend's single-tenant dev mode (anonymous -> first user), which is
    the documented local-dev behaviour. Tests that use `clerk_auth` or are marked
    `@pytest.mark.multi_tenant` keep strict auth. New Jobify-facing tests must use
    `clerk_auth` and send real tokens.
    """
    if "clerk_auth" in request.fixturenames or request.node.get_closest_marker("multi_tenant"):
        return
    from src.config import settings

    monkeypatch.setattr(settings, "multi_tenant_enabled", False)
    monkeypatch.setattr(settings, "env", "development")
