"""Groundwork for the Jobify MVP: auth hardening, error/list contract, tenant scoping."""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from src.api.contract import paginate, scoped
from src.api_error_handlers import register_error_handlers
from src.auth.dependencies import get_current_user, set_clerk_jwks_client
from src.config import settings
from src.models import Application, Job, User


def _creds(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# --- auth ------------------------------------------------------------------

def test_valid_clerk_token_provisions_user(clerk_auth, test_db):
    user = get_current_user(_creds(clerk_auth.token("user_new", "new@example.com")), test_db)
    assert user.clerk_user_id == "user_new"
    assert user.credits_balance == settings.default_signup_credits


def test_clerk_token_rejected_when_jwks_not_configured(clerk_auth, test_db):
    token = clerk_auth.token("user_forged")
    set_clerk_jwks_client(None)
    settings_issuer = settings.clerk_issuer
    try:
        settings.clerk_issuer = None
        with pytest.raises(HTTPException) as exc:
            get_current_user(_creds(token), test_db)
        assert exc.value.status_code == 401
        assert test_db.query(User).filter(User.clerk_user_id == "user_forged").first() is None
    finally:
        settings.clerk_issuer = settings_issuer


def test_token_for_other_origin_rejected(clerk_auth, test_db):
    with pytest.raises(HTTPException) as exc:
        get_current_user(_creds(clerk_auth.token(azp="https://evil.example.com")), test_db)
    assert exc.value.status_code == 401
    assert "not issued for this app" in exc.value.detail


@pytest.mark.multi_tenant
def test_dev_admin_token_disabled_by_default(test_db, monkeypatch):
    monkeypatch.setattr(settings, "env", "development")
    test_db.add(User(email="admin@example.com", is_superuser=True, credits_balance=0))
    test_db.commit()
    with pytest.raises(HTTPException) as exc:
        get_current_user(_creds("dev_token_admin"), test_db)
    assert exc.value.status_code == 401


def test_global_auth_blocks_anonymous_non_public_route(clerk_auth):
    from main import app

    client = TestClient(app)
    res = client.get("/api/jobs")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"
    assert client.get("/api/health").status_code != 401


# --- error / list contract ---------------------------------------------------

@pytest.fixture
def contract_client():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/missing")
    def missing():
        raise HTTPException(404, "Job not found")

    @app.get("/broke")
    def broke():
        raise HTTPException(402, {"error": "INSUFFICIENT_CREDITS", "message": "Not enough credits", "balance": 2})

    @app.get("/typed")
    def typed(n: int):
        return {"n": n}

    return TestClient(app, raise_server_exceptions=False)


def test_http_exception_uses_contract_envelope(contract_client):
    body = contract_client.get("/missing").json()
    assert body["error"] == {"code": "NOT_FOUND", "message": "Job not found"}
    assert body["detail"] == "Job not found"


def test_402_maps_to_credits_required(contract_client):
    res = contract_client.get("/broke")
    assert res.status_code == 402
    err = res.json()["error"]
    assert err["code"] == "CREDITS_REQUIRED"
    assert err["message"] == "Not enough credits"
    assert err["balance"] == 2


def test_validation_error_uses_contract_envelope(contract_client):
    res = contract_client.get("/typed", params={"n": "abc"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_paginate_shape_and_clamping(test_db):
    for i in range(5):
        test_db.add(User(email=f"u{i}@example.com", credits_balance=0))
    test_db.commit()
    page = paginate(test_db.query(User).order_by(User.id), page=2, page_size=2, mapper=lambda u: u.email)
    assert page == {"items": ["u2@example.com", "u3@example.com"], "total": 5, "page": 2, "pageSize": 2}
    assert paginate(test_db.query(User), page=0, page_size=10_000)["pageSize"] == 100


# --- tenant scoping ------------------------------------------------------------

def test_scoped_hides_other_users_rows(test_db):
    a, b = User(email="a@example.com", credits_balance=0), User(email="b@example.com", credits_balance=0)
    test_db.add_all([a, b])
    test_db.commit()
    test_db.add_all([Application(user_id=a.id, status="applied"), Application(user_id=b.id, status="applied")])
    test_db.commit()
    rows = scoped(test_db.query(Application), Application, a).all()
    assert [r.user_id for r in rows] == [a.id]


def test_scoped_refuses_models_without_user_id(test_db):
    with pytest.raises(TypeError):
        scoped(test_db.query(Job), Job, User(id=1))
