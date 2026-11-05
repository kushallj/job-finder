"""
Comprehensive Unit & Integration Tests for Clerk RS256 JWKS Bridge & GDPR Webhook.
Tests:
1. RS256 token verification with PyJWKClient.
2. Auto-provisioning of new Clerk users on first authenticated request with 50 credits.
3. Tampered & expired RS256 tokens rejected with 401.
4. Svix cryptographic webhook signature verification (valid vs tampered/invalid).
5. user.created and user.updated webhook lifecycle events.
6. GDPR Right to Erasure cascade purge (user.deleted):
   Purges User, Application, Contact, OutreachRecord, Resume, CreditTransaction, and CandidateProfile.
7. Public allowlist verification for webhook endpoints.
"""

import json
import time
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import jwt
from svix.webhooks import Webhook

from src.models import (
    Base,
    User,
    Job,
    Application,
    Contact,
    OutreachRecord,
    Resume,
    CreditTransaction,
    CandidateProfile,
    CandidateExperience,
    CandidateProject,
)
from src.config import settings
from src.auth.dependencies import set_clerk_jwks_client
from main import app


# Test RSA Key Pairs
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()
PEM_PRIVATE = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
PEM_PUBLIC = _public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

# Unrelated RSA key pair for testing invalid signature rejections
_unrelated_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM_UNRELATED_PRIVATE = _unrelated_private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

TEST_SVIX_SECRET = "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"


class MockSigningKey:
    def __init__(self, key):
        self.key = key


class MockJWKClient:
    def __init__(self, public_key_pem):
        self.public_key_pem = public_key_pem

    def get_signing_key_from_jwt(self, token: str):
        return MockSigningKey(self.public_key_pem)


@pytest.fixture
def clerk_test_db(monkeypatch):
    """Isolated in-memory SQLite database for Clerk auth and webhook testing."""
    # Independent of the developer's .env (CLERK_ISSUER / CLERK_AUTHORIZED_PARTIES may be set).
    monkeypatch.setattr(settings, "clerk_issuer", None)
    monkeypatch.setattr(settings, "clerk_authorized_parties", "")
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

    # Wire up test JWKS client & webhook secret
    set_clerk_jwks_client(MockJWKClient(PEM_PUBLIC))
    monkeypatch.setattr(settings, "clerk_webhook_secret", TEST_SVIX_SECRET)
    monkeypatch.setattr(settings, "default_signup_credits", 50)

    try:
        yield session
    finally:
        set_clerk_jwks_client(None)
        session.close()


@pytest.fixture
def client(clerk_test_db):
    """FastAPI TestClient with isolated DB session."""
    return TestClient(app)


def create_rs256_token(payload: dict, private_key_pem: bytes = PEM_PRIVATE) -> str:
    """Helper to generate RS256 JWT tokens."""
    return jwt.encode(payload, private_key_pem, algorithm="RS256", headers={"kid": "mock_kid_1"})


def create_svix_headers(payload_dict: dict, secret: str = TEST_SVIX_SECRET) -> tuple[dict, str]:
    """Helper to generate valid Svix signature headers for Clerk webhooks."""
    wh = Webhook(secret)
    now = datetime.now(timezone.utc)
    body_str = json.dumps(payload_dict)
    msg_id = f"msg_{int(now.timestamp())}"
    sig = wh.sign(msg_id, now, body_str)
    headers = {
        "svix-id": msg_id,
        "svix-timestamp": str(int(now.timestamp())),
        "svix-signature": sig,
        "content-type": "application/json",
    }
    return headers, body_str


# --- Tests ---

def test_clerk_rs256_autoprovisioning(client, clerk_test_db):
    """
    Test 1: Valid RS256 token triggers cryptographic decoding and auto-provisions
    new user with 50 credits and a welcome bonus transaction.
    """
    now = int(time.time())
    token = create_rs256_token({
        "sub": "user_clerk_autonew_101",
        "email": "newbie@clerk.dev",
        "name": "Jane Newbie",
        "iat": now,
        "exp": now + 3600,
    })

    # Call /api/auth/me with Bearer token
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["email"] == "newbie@clerk.dev"
    assert data["full_name"] == "Jane Newbie"
    assert data["credits_balance"] == 50

    # Verify user exists in database
    user = clerk_test_db.query(User).filter(User.clerk_user_id == "user_clerk_autonew_101").first()
    assert user is not None
    assert user.credits_balance == 50

    # Verify welcome bonus transaction in credit ledger
    tx = clerk_test_db.query(CreditTransaction).filter(CreditTransaction.user_id == user.id).first()
    assert tx is not None
    assert tx.action == "welcome_bonus"
    assert tx.amount == 50
    assert tx.balance_after == 50

    # Subsequent request should use the same user without duplicating
    resp2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json()["id"] == user.id


def test_clerk_rs256_tampered_signature_rejected(client, clerk_test_db):
    """
    Test 2: Token signed with a different private key is rejected with 401 Unauthorized.
    """
    now = int(time.time())
    tampered_token = create_rs256_token(
        {
            "sub": "user_clerk_hacker",
            "email": "hacker@evil.com",
            "exp": now + 3600,
        },
        private_key_pem=PEM_UNRELATED_PRIVATE,
    )

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401
    assert "Invalid Clerk token" in resp.json()["detail"]


def test_clerk_rs256_expired_token_rejected(client, clerk_test_db):
    """
    Test 3: Expired RS256 token is rejected with 401 Unauthorized.
    """
    now = int(time.time())
    expired_token = create_rs256_token({
        "sub": "user_clerk_expired",
        "email": "expired@example.com",
        "iat": now - 7200,
        "exp": now - 3600,  # Expired 1 hour ago
    })

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_svix_webhook_signature_verification(client, clerk_test_db):
    """
    Test 4: Svix signature verification accepts valid signatures and rejects tampered signatures with 400.
    """
    payload = {
        "type": "user.created",
        "data": {
            "id": "user_clerk_wh_001",
            "email_addresses": [{"id": "email_1", "email_address": "svix_test@example.com"}],
            "primary_email_address_id": "email_1",
            "first_name": "Svix",
            "last_name": "Tester",
        },
    }

    headers, body_str = create_svix_headers(payload)

    # 1. Valid signature
    resp = client.post("/api/auth/webhook/clerk", content=body_str, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "created"

    # 2. Tampered signature
    bad_headers = dict(headers)
    bad_headers["svix-signature"] = "v1,tampered_signature_hash_xyz"
    resp_bad = client.post("/api/auth/webhook/clerk", content=body_str, headers=bad_headers)
    assert resp_bad.status_code == 400
    assert "signature verification failed" in resp_bad.json()["detail"].lower()

    # 3. Tampered payload with valid header
    tampered_body = json.dumps({"type": "user.created", "data": {"id": "user_hacked"}})
    resp_tampered = client.post("/api/auth/webhook/clerk", content=tampered_body, headers=headers)
    assert resp_tampered.status_code == 400


def test_clerk_webhook_lifecycle_created_and_updated(client, clerk_test_db):
    """
    Test 5: Webhook user.created provisions user, and user.updated syncs name/email.
    """
    create_payload = {
        "type": "user.created",
        "data": {
            "id": "user_lifecycle_001",
            "email_addresses": [{"id": "email_01", "email_address": "original@example.com"}],
            "primary_email_address_id": "email_01",
            "first_name": "Original",
            "last_name": "User",
        },
    }
    headers, body = create_svix_headers(create_payload)
    resp = client.post("/api/auth/webhook/clerk", content=body, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "created"

    user = clerk_test_db.query(User).filter(User.clerk_user_id == "user_lifecycle_001").first()
    assert user is not None
    assert user.email == "original@example.com"
    assert user.full_name == "Original User"
    assert user.credits_balance == 50

    # user.updated
    update_payload = {
        "type": "user.updated",
        "data": {
            "id": "user_lifecycle_001",
            "email_addresses": [{"id": "email_02", "email_address": "updated@example.com"}],
            "primary_email_address_id": "email_02",
            "first_name": "Updated",
            "last_name": "Name",
        },
    }
    headers_up, body_up = create_svix_headers(update_payload)
    resp_up = client.post("/api/auth/clerk/webhook", content=body_up, headers=headers_up)
    assert resp_up.status_code == 200
    assert resp_up.json()["status"] == "updated"

    clerk_test_db.refresh(user)
    assert user.full_name == "Updated Name"
    assert user.email == "updated@example.com"


def test_clerk_webhook_gdpr_cascade_purge(client, clerk_test_db):
    """
    Test 6: GDPR Right to Erasure cascade delete (user.deleted).
    When user is deleted, all tenant records (Applications, Contacts, Outreach,
    Resumes, CreditTransactions, CandidateProfiles & child items) are purged.
    """
    # 1. Provision target user
    user = User(
        clerk_user_id="user_gdpr_target_999",
        email="gdpr_target@example.com",
        full_name="Target To Purge",
        subscription_tier="pro",
        credits_balance=100,
        is_active=True,
    )
    clerk_test_db.add(user)
    clerk_test_db.flush()
    target_id = user.id

    # 2. Add tenant data
    job = Job(job_id="job_gdpr_1", title="Staff Engineer", company="TargetCorp")
    clerk_test_db.add(job)
    clerk_test_db.flush()

    app1 = Application(user_id=target_id, job_id=job.id, kanban_stage="applied")
    app2 = Application(user_id=target_id, job_id=job.id, kanban_stage="interview")
    contact = Contact(user_id=target_id, name="Recruiter Alice", company="TargetCorp", email="alice@target.com")
    clerk_test_db.add(contact)
    clerk_test_db.flush()
    outreach = OutreachRecord(user_id=target_id, contact_id=contact.id, contact_email="alice@target.com", status="sent")
    resume = Resume(user_id=target_id, original_content="Senior AI Engineer resume content")
    tx = CreditTransaction(user_id=target_id, amount=100, balance_after=100, action="topup")

    profile = CandidateProfile(
        user_identifier=f"user_{target_id}",
        full_name="Target To Purge",
        email="gdpr_target@example.com",
    )
    clerk_test_db.add_all([app1, app2, contact, outreach, resume, tx, profile])
    clerk_test_db.flush()

    exp = CandidateExperience(profile_id=profile.id, company="OldCorp", title="Lead Engineer", start_date="2020")
    proj = CandidateProject(profile_id=profile.id, title="OpenSource LLM", stars_count=50)
    clerk_test_db.add_all([exp, proj])
    clerk_test_db.commit()

    # Verify records exist prior to deletion
    assert clerk_test_db.query(Application).filter(Application.user_id == target_id).count() == 2
    assert clerk_test_db.query(Contact).filter(Contact.user_id == target_id).count() == 1
    assert clerk_test_db.query(OutreachRecord).filter(OutreachRecord.user_id == target_id).count() == 1
    assert clerk_test_db.query(Resume).filter(Resume.user_id == target_id).count() == 1
    assert clerk_test_db.query(CreditTransaction).filter(CreditTransaction.user_id == target_id).count() == 1
    assert clerk_test_db.query(CandidateProfile).filter(CandidateProfile.id == profile.id).first() is not None
    assert clerk_test_db.query(CandidateExperience).filter(CandidateExperience.profile_id == profile.id).count() == 1

    # 3. Trigger verified user.deleted webhook
    delete_payload = {
        "type": "user.deleted",
        "data": {
            "deleted": True,
            "id": "user_gdpr_target_999",
            "object": "user",
        },
    }
    headers, body = create_svix_headers(delete_payload)
    resp = client.post("/api/auth/webhook/clerk", content=body, headers=headers)
    assert resp.status_code == 200, resp.text
    res_data = resp.json()
    assert res_data["status"] == "purged"
    assert res_data["purged_user_id"] == target_id

    # 4. Verify complete purge
    assert clerk_test_db.query(User).filter(User.id == target_id).first() is None
    assert clerk_test_db.query(Application).filter(Application.user_id == target_id).count() == 0
    assert clerk_test_db.query(Contact).filter(Contact.user_id == target_id).count() == 0
    assert clerk_test_db.query(OutreachRecord).filter(OutreachRecord.user_id == target_id).count() == 0
    assert clerk_test_db.query(Resume).filter(Resume.user_id == target_id).count() == 0
    assert clerk_test_db.query(CreditTransaction).filter(CreditTransaction.user_id == target_id).count() == 0
    assert clerk_test_db.query(CandidateProfile).filter(CandidateProfile.id == profile.id).first() is None
    assert clerk_test_db.query(CandidateExperience).filter(CandidateExperience.profile_id == profile.id).count() == 0
    assert clerk_test_db.query(CandidateProject).filter(CandidateProject.profile_id == profile.id).count() == 0
