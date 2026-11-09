"""
Unit and integration tests for Stripe Billing, Subscription Lifecycle & Webhook Processing.
Covers:
- Plans and credit packs catalog
- Checkout session creation (plans & top-up packs)
- RFC-compliant HMAC-SHA256 Stripe-Signature verification and tamper rejection
- Webhook lifecycle: subscription activation, recurring renewal, top-up pack grant, and cancellation downgrade
- FastAPI billing endpoints (/plans, /create-checkout-session, /create-portal-session, /webhook)
"""

import json
import time
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, User, CreditTransaction
from src.auth.crypto import hash_password
from src.auth.jwt_handler import create_access_token
from src.services.billing_service import (
    PLANS,
    CREDIT_PACKS,
    get_plans_catalog,
    create_checkout_session,
    create_customer_portal_session,
    verify_webhook_signature,
    process_webhook_event,
)

PACK_ID = next(iter(CREDIT_PACKS))  # whichever top-up pack the catalog currently sells
from src.database import get_db
from main import app


@pytest.fixture
def billing_db_session():
    """Isolated SQLite in-memory test database fixture with StaticPool."""
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


def test_plans_catalog_structure():
    """The catalog served to the UI mirrors PLANS/CREDIT_PACKS and is well formed.

    Asserts invariants, not tier names: the old test froze a 4-tier catalog
    (free/starter/pro/unlimited) that the code no longer has. Aligning prices with
    Jobify plans.js is CLAUDE.md Phase 7 (pending pricing decision).
    """
    catalog = get_plans_catalog()
    assert {p["id"] for p in catalog["plans"]} == set(PLANS)
    assert {p["id"] for p in catalog["credit_packs"]} == set(CREDIT_PACKS)
    assert set(PLANS) == {"basic", "pro"}  # Jobify plans.js; "free" = no subscription
    assert all(p["credits"] > 0 for p in catalog["plans"] + catalog["credit_packs"])
    assert len(catalog["plans"]) >= 2 and catalog["credit_packs"]


def test_create_checkout_session_mock_mode(billing_db_session):
    """Verify checkout session URL generation for plans and top-up packs."""
    user = User(
        email="billing_user@example.com",
        hashed_password=hash_password("password123"),
        full_name="Billing Tester",
        subscription_tier="free",
        credits_balance=20,
        is_active=True,
    )
    billing_db_session.add(user)
    billing_db_session.commit()
    billing_db_session.refresh(user)

    # 1. Plan checkout
    session_pro = create_checkout_session(db=billing_db_session, user=user, target="pro")
    assert "checkout_url" in session_pro
    assert "session_id" in session_pro
    assert session_pro["mode"] == "subscription"
    assert "target=pro" in session_pro["checkout_url"]

    # 2. Credit pack checkout
    session_pack = create_checkout_session(db=billing_db_session, user=user, target="pack_100")
    assert "checkout_url" in session_pack
    assert session_pack["mode"] == "payment"
    assert "target=pack_100" in session_pack["checkout_url"]


def test_webhook_signature_verification_and_tampering():
    """Verify HMAC-SHA256 signature verification matching Stripe webhook protocol."""
    test_secret = "whsec_test_secret_key_123"
    payload = json.dumps({"id": "evt_test_123", "type": "ping"}).encode("utf-8")
    timestamp = str(int(time.time()))

    # Generate valid signature
    signed_input = f"{timestamp}.".encode("utf-8") + payload
    valid_sig = hmac.new(test_secret.encode("utf-8"), signed_input, hashlib.sha256).hexdigest()
    sig_header = f"t={timestamp},v1={valid_sig}"

    # Valid check
    assert verify_webhook_signature(payload, sig_header, secret=test_secret) is True

    # Tampered signature
    bad_header = f"t={timestamp},v1=wrong_signature_hex"
    assert verify_webhook_signature(payload, bad_header, secret=test_secret) is False

    # Tampered payload
    tampered_payload = json.dumps({"id": "evt_test_123", "type": "malicious"}).encode("utf-8")
    assert verify_webhook_signature(tampered_payload, sig_header, secret=test_secret) is False


def test_webhook_full_subscription_lifecycle(billing_db_session):
    """
    Test full lifecycle via webhooks:
    1. checkout.session.completed (Pro) -> Tier updated to 'pro' + 1,000 credits added
    2. invoice.payment_succeeded -> 1,000 renewal credits added
    3. customer.subscription.deleted -> Tier reverted to 'free', status canceled
    """
    user = User(
        email="subscriber@example.com",
        hashed_password=hash_password("pwd123"),
        full_name="Subscriber",
        subscription_tier="free",
        credits_balance=10,
        is_active=True,
    )
    billing_db_session.add(user)
    billing_db_session.commit()
    billing_db_session.refresh(user)

    # 1. Activation webhook
    activation_event = {
        "id": "evt_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_pro_1",
                "customer": "cus_test_123",
                "subscription": "sub_test_pro_999",
                "metadata": {
                    "user_id": str(user.id),
                    "target": "pro",
                    "type": "subscription",
                },
            }
        },
    }
    res1 = process_webhook_event(db=billing_db_session, event=activation_event)
    assert res1["status"] == "success"
    assert res1["action"] == "subscription_activated"
    
    billing_db_session.refresh(user)
    assert user.subscription_tier == "pro"
    assert user.stripe_customer_id == "cus_test_123"
    assert user.stripe_subscription_id == "sub_test_pro_999"
    assert user.credits_balance == 10 + PLANS["pro"]["credits"]

    # 2. Monthly recurring renewal webhook
    renewal_event = {
        "id": "evt_2",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_test_cycle_1",
                "subscription": "sub_test_pro_999",
                "billing_reason": "subscription_cycle",
            }
        },
    }
    res2 = process_webhook_event(db=billing_db_session, event=renewal_event)
    assert res2["status"] == "success"
    billing_db_session.refresh(user)
    assert user.credits_balance == 10 + 2 * PLANS["pro"]["credits"]  # activation + renewal

    # 3. Subscription canceled webhook
    cancel_event = {
        "id": "evt_3",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test_pro_999",
            }
        },
    }
    res3 = process_webhook_event(db=billing_db_session, event=cancel_event)
    assert res3["status"] == "success"
    assert res3["action"] == "downgraded_to_free"
    billing_db_session.refresh(user)
    assert user.subscription_tier == "free"
    assert user.subscription_status == "canceled"


def test_webhook_credit_pack_topup(billing_db_session):
    """Verify one-time top-up pack purchase via checkout.session.completed."""
    user = User(
        email="topup_user@example.com",
        hashed_password=hash_password("pwd123"),
        full_name="Topup User",
        subscription_tier="free",
        credits_balance=5,
        is_active=True,
    )
    billing_db_session.add(user)
    billing_db_session.commit()
    billing_db_session.refresh(user)

    topup_event = {
        "id": "evt_pack_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_pack",
                "customer": "cus_topup_456",
                "metadata": {
                    "user_id": str(user.id),
                    "target": PACK_ID,
                    "type": "topup",
                },
            }
        },
    }
    res = process_webhook_event(db=billing_db_session, event=topup_event)
    assert res["status"] == "success"
    assert res["action"] == "topup_applied"
    
    billing_db_session.refresh(user)
    assert user.credits_balance == 5 + CREDIT_PACKS[PACK_ID]["credits"]


def test_fastapi_billing_endpoints(billing_db_session):
    """Test /api/billing/plans, /create-checkout-session, /create-portal-session, and /webhook."""
    def override_get_db():
        try:
            yield billing_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        user = User(
            email="api_billing@example.com",
            hashed_password=hash_password("pwd"),
            full_name="API Tester",
            subscription_tier="free",
            credits_balance=50,
            is_active=True,
        )
        billing_db_session.add(user)
        billing_db_session.commit()
        billing_db_session.refresh(user)
        token = create_access_token(data={"sub": str(user.id), "email": user.email})

        # 1. GET /api/billing/plans
        res_plans = client.get("/api/billing/plans", headers={"Authorization": f"Bearer {token}"})
        assert res_plans.status_code == 200
        data = res_plans.json()
        assert {p["id"] for p in data["plans"]} == set(PLANS)
        assert data["current_tier"] == "free"

        # 2. POST /api/billing/create-checkout-session
        res_checkout = client.post(
            "/api/billing/create-checkout-session",
            json={"target": "pro"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_checkout.status_code == 200
        assert "checkout_url" in res_checkout.json()

        # 3. POST /api/billing/create-portal-session
        res_portal = client.post(
            "/api/billing/create-portal-session",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_portal.status_code == 200
        assert "portal_url" in res_portal.json()

        # 4. POST /api/billing/webhook
        mock_event = {
            "id": "evt_wh_api",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_wh_api",
                    "metadata": {"user_id": str(user.id), "target": "pack_100", "type": "topup"},
                }
            },
        }
        res_wh = client.post("/api/billing/webhook", json=mock_event)
        assert res_wh.status_code == 200
        assert res_wh.json()["received"] is True
    finally:
        app.dependency_overrides.clear()


def test_apply_purchase_grants_exactly_what_was_bought(billing_db_session):
    """Basic stays Basic (it used to be upgraded to Pro); yearly grants 12 months of credits;
    retired tier names resolve to their successor; unknown targets grant nothing."""
    from src.services.billing_service import apply_purchase, credits_for

    user = User(email="grant@example.com", hashed_password=hash_password("pw"), credits_balance=0, is_active=True)
    billing_db_session.add(user)
    billing_db_session.commit()

    res = apply_purchase(billing_db_session, user, "basic", "subscription")
    assert res["tier"] == "basic" and user.subscription_tier == "basic"
    assert user.credits_balance == PLANS["basic"]["credits"]

    before = user.credits_balance
    apply_purchase(billing_db_session, user, "pro", "subscription", interval="year")
    assert user.subscription_tier == "pro"
    assert user.credits_balance - before == credits_for("pro", "year") == 12 * PLANS["pro"]["credits"]

    assert apply_purchase(billing_db_session, user, "starter", "subscription")["tier"] == "basic"
    before = user.credits_balance
    assert apply_purchase(billing_db_session, user, "gold", "subscription")["status"] == "ignored"
    assert user.credits_balance == before
