"""
Unit and integration tests for Multi-Tenant Auth and Centralized AI Credit Metering.
Covers:
- PBKDF2 cryptographic hashing
- RFC 7519 HMAC-SHA256 JWT encoding, decoding, tampering, and expiration
- FastAPI Auth endpoints (/register, /login, /me, /credits/history, /credits/topup)
- Atomic credit deduction, audit logging, and HTTP 402 Payment Required guards
- Unified AI Service metered execution integration
"""

import pytest
from datetime import timedelta
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, User, CreditTransaction
from src.auth.crypto import hash_password, verify_password
from src.auth.jwt_handler import create_access_token, decode_access_token
from src.services.credit_service import add_credits, deduct_credits, get_user_credits, get_credit_history
from src.database import get_db
from main import app


from sqlalchemy.pool import StaticPool

@pytest.fixture
def test_db_session():
    """Isolated SQLite in-memory test database fixture with StaticPool for thread safety."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def test_crypto_hashing_and_verification():
    """Verify PBKDF2 password hashing works deterministically and rejects bad passwords."""
    pwd = "super_secure_password_99"
    hashed = hash_password(pwd)
    
    assert hashed.startswith("pbkdf2_sha256$100000$")
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(pwd, "invalid$format") is False


def test_jwt_encoding_decoding_and_expiration():
    """Verify RFC 7519 HS256 JWT generation, decoding, expiry, and signature validation."""
    payload = {"sub": "42", "email": "candidate@example.com"}
    token = create_access_token(data=payload, expires_delta=timedelta(minutes=15), secret_key="test-secret")
    
    decoded = decode_access_token(token, secret_key="test-secret")
    assert decoded["sub"] == "42"
    assert decoded["email"] == "candidate@example.com"
    assert "exp" in decoded

    # Tampered signature
    parts = token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.tampered_signature"
    with pytest.raises(ValueError, match="Invalid token signature"):
        decode_access_token(tampered_token, secret_key="test-secret")

    # Expired token
    expired_token = create_access_token(data=payload, expires_delta=timedelta(seconds=-10), secret_key="test-secret")
    with pytest.raises(ValueError, match="Token has expired"):
        decode_access_token(expired_token, secret_key="test-secret")


def test_credit_service_deduction_and_depletion(test_db_session):
    """Verify atomic credit deduction, audit trails, and HTTP 402 when balance is depleted."""
    from fastapi import HTTPException
    
    user = User(
        email="test_credit@example.com",
        hashed_password=hash_password("password123"),
        full_name="Credit Tester",
        subscription_tier="free",
        credits_balance=10,
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)

    # 1. Successful deduction
    new_bal = deduct_credits(
        db=test_db_session,
        user_id=user.id,
        amount=3,
        action="resume_tailor",
        reference_id="job_101",
    )
    assert new_bal == 7
    assert get_user_credits(test_db_session, user.id) == 7

    # Check transaction log
    history = get_credit_history(test_db_session, user.id)
    assert len(history) == 1
    assert history[0]["amount"] == -3
    assert history[0]["balance_after"] == 7
    assert history[0]["action"] == "resume_tailor"

    # 2. Add credits
    new_bal = add_credits(
        db=test_db_session,
        user_id=user.id,
        amount=5,
        action="topup",
    )
    assert new_bal == 12

    # 3. Exhaust credits and trigger 402 Payment Required
    with pytest.raises(HTTPException) as exc_info:
        deduct_credits(
            db=test_db_session,
            user_id=user.id,
            amount=50,  # exceeds balance of 12
            action="high_volume_batch_apply",
        )
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "INSUFFICIENT_CREDITS"
    assert exc_info.value.detail["balance"] == 12


def test_fastapi_auth_endpoints_lifecycle(test_db_session):
    """Test full API lifecycle: register, duplicate prevention, login, /me, and topup."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        # 1. Register new user
        reg_payload = {
            "email": "sarah.connor@cyberdyne.io",
            "password": "resistance_2026",
            "full_name": "Sarah Connor",
        }
        res = client.post("/api/auth/register", json=reg_payload)
        assert res.status_code == 201, res.text
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == "sarah.connor@cyberdyne.io"
        assert data["user"]["credits_balance"] == 50  # Default signup credits
        token = data["access_token"]

        # 2. Duplicate email should fail with 400
        res_dup = client.post("/api/auth/register", json=reg_payload)
        assert res_dup.status_code == 400

        # 3. Login with bad password -> 401
        res_bad = client.post("/api/auth/login", json={"email": reg_payload["email"], "password": "wrong"})
        assert res_bad.status_code == 401

        # 4. Login with correct password -> 200
        res_login = client.post("/api/auth/login", json={"email": reg_payload["email"], "password": reg_payload["password"]})
        assert res_login.status_code == 200
        assert "access_token" in res_login.json()

        # 5. Get current profile via /me
        res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me.status_code == 200
        assert res_me.json()["email"] == "sarah.connor@cyberdyne.io"
        assert res_me.json()["credits_balance"] == 50

        # 6. Topup credits
        res_topup = client.post("/api/auth/credits/topup", json={"amount": 25}, headers={"Authorization": f"Bearer {token}"})
        assert res_topup.status_code == 200
        assert res_topup.json()["credits_balance"] == 75

        # 7. Check credits history
        res_hist = client.get("/api/auth/credits/history", headers={"Authorization": f"Bearer {token}"})
        assert res_hist.status_code == 200
        assert len(res_hist.json()["history"]) >= 2
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_metered_unified_ai_service(test_db_session):
    """Test that UnifiedAIService metered generation checks credits properly."""
    from src.ai.unified_ai_service import UnifiedAIService
    from fastapi import HTTPException
    
    ai_service = UnifiedAIService()
    user = User(
        email="ai_user@example.com",
        hashed_password=hash_password("ai_pass_123"),
        full_name="AI Applicant",
        subscription_tier="free",
        credits_balance=1,
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)

    # First tailor should succeed and deduct 1 credit
    tailored = await ai_service.metered_rewrite_resume(
        original_resume="Senior Python Engineer with 6 years experience",
        job_description="Looking for Python backend developer",
        db=test_db_session,
        user_id=user.id,
        cost_credits=1,
    )
    assert tailored is not None
    assert get_user_credits(test_db_session, user.id) == 0

    # Second tailor should fail with 402 since balance is 0
    with pytest.raises(HTTPException) as exc_info:
        await ai_service.metered_rewrite_resume(
            original_resume="Senior Python Engineer",
            job_description="Python developer",
            db=test_db_session,
            user_id=user.id,
            cost_credits=1,
        )
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "INSUFFICIENT_CREDITS"
