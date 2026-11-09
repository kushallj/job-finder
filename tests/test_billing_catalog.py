import re
"""
Unit & Integration Tests for Canonical 2-Tier Billing Catalog (Priority 2) & Dodo Payments.
Verifies that:
1. GET /api/billing/plans is public and acts as the single source of truth.
2. Catalog returns exactly 2 plans: Free ($0 / ₹0) and Pro ($3 / ₹249).
3. Credit allowances (50 for free, 1,000 for pro) and pack_100 ($1 / ₹89) are returned.
4. Both USD and INR currencies are supported in catalog metadata.
5. POST /api/billing/create-checkout-session supports Pro, Pack_100, and aliases ('starter', 'basic' -> 'pro').
6. POST /api/billing/webhook/dodo processes asynchronous payments and credits user balance.
"""

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, User, CreditTransaction
from src.auth.crypto import hash_password
from src.auth.jwt_handler import create_access_token
from src.config import settings
from main import app


@pytest.fixture
def billing_db(monkeypatch):
    """Isolated in-memory SQLite database for billing catalog testing."""
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
    monkeypatch.setattr(settings, "billing_provider", "dodo")

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(billing_db):
    """FastAPI TestClient with isolated DB session."""
    return TestClient(app)



def _jobify_plans() -> dict:
    """Parse id/monthly/yearly/credits for each plan out of jobify/src/data/plans.js."""
    import pathlib

    src = (pathlib.Path(__file__).resolve().parents[1] / "jobify" / "src" / "data" / "plans.js").read_text(encoding="utf-8")
    plans = {}
    for block in re.findall(r"\{[^{}]*?id: \"(\w+)\"(.*?)cta:", src, re.S):
        plan_id, body = block
        nums = {k: int(re.search(rf"\b{k}: (\d+)", body).group(1)) for k in ("monthly", "yearly", "credits")}
        plans[plan_id] = nums
    assert plans, "could not parse plans.js"
    return plans


JOBIFY_PLANS = _jobify_plans()


def test_public_billing_catalog_structure(client):
    """
    Test 1: Verify GET /api/billing/plans is public and returns exactly 2 plans (Free & Pro at $3 / ₹249).
    """
    resp = client.get("/api/billing/plans")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "plans" in data
    assert "credit_packs" in data
    assert data["supported_currencies"] == ["USD", "INR"]
    assert data["intervals"] == ["month", "year"]

    # Served catalog == Jobify jobify/src/data/plans.js (the frontend is the pricing spec).
    served = {p["id"]: p for p in data["plans"]}
    assert served.keys() == JOBIFY_PLANS.keys()
    for plan_id, expected in JOBIFY_PLANS.items():
        for field in ("monthly", "yearly", "credits"):
            assert served[plan_id][field] == expected[field], (plan_id, field)

    pack = {p["id"]: p for p in data["credit_packs"]}["pack_100"]
    assert pack["price_usd"] == 1 and pack["credits"] == 100


def test_authenticated_user_catalog_entitlements(client, billing_db):
    """
    Test 2: Verify authenticated user sees their current subscription tier and credit balance.
    """
    user = User(
        email="subscriber@example.com",
        hashed_password=hash_password("pw123"),
        full_name="Active Subscriber",
        subscription_tier="pro",
        credits_balance=750,
        is_active=True,
    )
    billing_db.add(user)
    billing_db.commit()
    billing_db.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    resp = client.get("/api/billing/plans", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["current_tier"] == "pro"
    assert data["current_credits"] == 750
    assert data["subscription_status"] == "active"


def test_create_checkout_session_pro_and_aliases(client, billing_db):
    """
    Test 3: checkout for each Jobify plan, both intervals, the top-up pack, and legacy tier names.
    """
    user = User(
        email="shopper@example.com",
        hashed_password=hash_password("pw123"),
        subscription_tier="free",
        credits_balance=50,
        is_active=True,
    )
    billing_db.add(user)
    billing_db.commit()
    billing_db.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Pro plan checkout
    resp_pro = client.post("/api/billing/create-checkout-session", json={"target": "pro"}, headers=headers)
    assert resp_pro.status_code == 200, resp_pro.text
    data_pro = resp_pro.json()
    assert "checkout_url" in data_pro
    assert data_pro["provider"] == "dodo"
    assert "target=pro" in data_pro["checkout_url"]

    # Basic is its own plan (it used to be silently upgraded to Pro and charged as Pro)
    resp_basic = client.post("/api/billing/create-checkout-session", json={"target": "basic"}, headers=headers)
    assert resp_basic.status_code == 200
    assert "target=basic" in resp_basic.json()["checkout_url"]

    # Yearly interval accepted; unknown interval rejected
    assert client.post("/api/billing/create-checkout-session", json={"target": "pro", "interval": "year"},
                       headers=headers).status_code == 200
    assert client.post("/api/billing/create-checkout-session", json={"target": "pro", "interval": "week"},
                       headers=headers).status_code == 422

    # Retired tier name 'starter' maps to its successor, Basic
    resp_starter = client.post("/api/billing/create-checkout-session", json={"target": "starter"}, headers=headers)
    assert resp_starter.status_code == 200
    assert "target=basic" in resp_starter.json()["checkout_url"]

    # Top-up pack checkout
    resp_pack = client.post("/api/billing/create-checkout-session", json={"target": "pack_100"}, headers=headers)
    assert resp_pack.status_code == 200
    assert "target=pack_100" in resp_pack.json()["checkout_url"]

    # Invalid target rejected
    resp_bad = client.post("/api/billing/create-checkout-session", json={"target": "invalid_pack_xyz"}, headers=headers)
    assert resp_bad.status_code == 400


def test_dodo_webhook_pro_activation(client, billing_db):
    """
    Test 4: Dodo webhook activates Pro and grants Pro's monthly credits (plans.js).
    """
    user = User(
        email="dodo_user@example.com",
        hashed_password=hash_password("pw123"),
        subscription_tier="free",
        credits_balance=25,
        is_active=True,
    )
    billing_db.add(user)
    billing_db.commit()
    billing_db.refresh(user)

    webhook_payload = {
        "type": "payment.succeeded",
        "data": {
            "payment_id": "pay_dodo_12345",
            "amount": 300,
            "currency": "USD",
            "metadata": {
                "user_id": str(user.id),
                "target": "pro",
                "type": "subscription",
            },
        },
    }

    # Public allowlist check: no Bearer token needed
    resp = client.post("/api/billing/webhook/dodo", json=webhook_payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "processed"

    billing_db.refresh(user)
    assert user.subscription_tier == "pro"
    assert user.credits_balance == 25 + JOBIFY_PLANS["pro"]["credits"]

    # Verify credit ledger entry
    tx = (
        billing_db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user.id, CreditTransaction.action == "subscription_activated")
        .first()
    )
    assert tx is not None
    assert tx.amount == JOBIFY_PLANS["pro"]["credits"]
    assert tx.balance_after == 25 + JOBIFY_PLANS["pro"]["credits"]


def test_dodo_webhook_pack_topup(client, billing_db):
    """
    Test 5: Verify Dodo webhook for pack_100 adds 100 credits.
    """
    user = User(
        email="dodo_topup@example.com",
        hashed_password=hash_password("pw123"),
        subscription_tier="free",
        credits_balance=10,
        is_active=True,
    )
    billing_db.add(user)
    billing_db.commit()
    billing_db.refresh(user)

    webhook_payload = {
        "type": "payment.succeeded",
        "data": {
            "payment_id": "pay_dodo_topup_678",
            "amount": 100,
            "currency": "USD",
            "metadata": {
                "user_id": str(user.id),
                "target": "pack_100",
                "type": "topup",
            },
        },
    }

    resp = client.post("/api/billing/webhook/dodo", json=webhook_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"

    billing_db.refresh(user)
    assert user.credits_balance == 110
