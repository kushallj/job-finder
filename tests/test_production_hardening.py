"""Production hardening: security headers, body cap, trace ids, probes, startup refusal,
JSON logs, legacy-auth guard. Mini apps keep middleware tests independent of main.py."""

import json
import logging
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from src.api.hardening import BodySizeLimitMiddleware, SecurityHeadersMiddleware, safe_trace_id
from src.observability import JsonFormatter, trace_id_var
from src.production_checks import production_problems


def mini_app(*, hsts: bool = False, max_bytes: int = 100) -> FastAPI:
    app = FastAPI()

    @app.post("/echo")
    async def echo(payload: dict) -> dict:
        return payload

    @app.get("/stream")
    def stream() -> StreamingResponse:
        return StreamingResponse(iter([b"data: a\n\n", b"data: b\n\n"]), media_type="text/event-stream")

    app.add_middleware(SecurityHeadersMiddleware, hsts=hsts)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=max_bytes, overrides={"/big": 10_000})
    return app


def test_security_headers_and_hsts_toggle():
    r = TestClient(mini_app(hsts=False)).get("/stream")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert "strict-transport-security" not in r.headers
    assert r.text == "data: a\n\ndata: b\n\n"  # streaming (SSE) passes through untouched
    assert "max-age=31536000" in TestClient(mini_app(hsts=True)).get("/stream").headers["strict-transport-security"]


def test_body_cap_by_content_length_and_by_streamed_chunks():
    client = TestClient(mini_app(max_bytes=100))
    assert client.post("/echo", json={"a": "x" * 10}).status_code == 200
    r = client.post("/echo", json={"a": "x" * 500})
    assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

    def chunks():  # no Content-Length: must still be capped while streaming
        yield b'{"a": "'
        yield b"x" * 500
        yield b'"}'
    assert client.post("/echo", content=chunks(), headers={"content-type": "application/json"}).status_code == 413


@pytest.mark.parametrize(("given", "kept"), [
    ("abc12345-good", True), ("a" * 64, True),
    ("short", False), ("has space here", False), ("line\nbreak-injection", False), ("x" * 65, False), (None, False),
])
def test_safe_trace_id(given, kept):
    out = safe_trace_id(given)
    assert (out == given) is kept
    if not kept:
        assert len(out) == 36  # fresh UUID


GOOD = dict(
    database_url="postgresql://u:p@db/x", multi_tenant_enabled=True, allow_dev_auth_tokens=False, seed_dev_admin=False,
    clerk_issuer="https://clerk.example.com", clerk_jwks_url=None, clerk_authorized_parties="https://app.example.com",
    clerk_webhook_secret="whsec_x", token_encryption_key="k", cors_origins="https://app.example.com",
    frontend_url="https://app.example.com", auto_send_emails=False, inbox_domain=None, inbound_webhook_secret=None,
)


def test_production_settings_good_config_passes():
    assert production_problems(SimpleNamespace(**GOOD)) == []


@pytest.mark.parametrize(("override", "needle"), [
    ({"database_url": "sqlite:///jobs.db"}, "DATABASE_URL"),
    ({"multi_tenant_enabled": False}, "MULTI_TENANT_ENABLED"),
    ({"allow_dev_auth_tokens": True}, "ALLOW_DEV_AUTH_TOKENS"),
    ({"seed_dev_admin": True}, "SEED_DEV_ADMIN"),
    ({"clerk_issuer": None}, "CLERK_ISSUER"),
    ({"clerk_authorized_parties": ""}, "CLERK_AUTHORIZED_PARTIES"),
    ({"clerk_webhook_secret": None}, "CLERK_WEBHOOK_SECRET"),
    ({"token_encryption_key": None}, "TOKEN_ENCRYPTION_KEY"),
    ({"cors_origins": "https://app.example.com,http://localhost:3000"}, "CORS_ORIGINS"),
    ({"frontend_url": "http://app.example.com"}, "FRONTEND_URL"),
    ({"auto_send_emails": True}, "AUTO_SEND_EMAILS"),
    ({"inbox_domain": "mail.example.com"}, "INBOUND_WEBHOOK_SECRET"),
])
def test_production_settings_each_unsafe_value_is_named(override, needle):
    problems = production_problems(SimpleNamespace(**{**GOOD, **override}))
    assert len(problems) == 1 and needle in problems[0]


def test_json_log_line_carries_trace_id_and_extras():
    token = trace_id_var.set("trace-abc-123")
    try:
        record = logging.LogRecord("qa", logging.INFO, __file__, 1, "hello %s", ("world",), None)
        record.trace_id = trace_id_var.get()
        record.user_id = 7
        line = json.loads(JsonFormatter().format(record))
    finally:
        trace_id_var.reset(token)
    assert line["msg"] == "hello world" and line["trace_id"] == "trace-abc-123" and line["user_id"] == 7


def test_probes_and_app_hardening_in_development():
    import main

    client = TestClient(main.app)
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz")
    assert ready.status_code in (200, 503) and "database" in ready.json()["checks"]
    r = client.get("/healthz", headers={"X-Trace-ID": "evil\tinjected-trace"})
    assert r.headers["x-trace-id"] != "evil\tinjected-trace" and r.headers["x-content-type-options"] == "nosniff"
    assert client.get("/metrics").status_code == 401  # admin only, never public


def test_legacy_password_routes_404_in_production(monkeypatch):
    from src.api.routers import auth_router
    from src.config import settings

    monkeypatch.setattr(settings, "env", "production")
    monkeypatch.setattr(settings, "legacy_password_auth_enabled", False)
    with pytest.raises(HTTPException) as exc:
        auth_router.legacy_password_auth_guard()
    assert exc.value.status_code == 404
    monkeypatch.setattr(settings, "legacy_password_auth_enabled", True)
    auth_router.legacy_password_auth_guard()  # explicit opt-in allows it


# --- payment webhooks: signatures are mandatory outside local dev -------------------------

def _dodo_secret() -> str:
    import base64
    import os
    return "whsec_" + base64.b64encode(os.urandom(24)).decode()


def _sign(secret: str, body: bytes, ts=None) -> dict:
    from datetime import UTC, datetime

    from svix.webhooks import Webhook
    stamp = ts or datetime.now(tz=UTC)
    return {"webhook-id": "msg_1", "webhook-timestamp": str(int(stamp.timestamp())),
            "webhook-signature": Webhook(secret).sign("msg_1", stamp, body.decode())}


def test_dodo_signature_verification():
    from datetime import UTC, datetime, timedelta

    from src.services.billing_service import verify_dodo_signature
    secret, body = _dodo_secret(), b'{"data":{"metadata":{"user_id":"1"}}}'
    assert verify_dodo_signature(body, _sign(secret, body), secret=secret)
    assert not verify_dodo_signature(body + b" ", _sign(secret, body), secret=secret)          # tampered body
    assert not verify_dodo_signature(body, _sign(_dodo_secret(), body), secret=secret)        # wrong key
    assert not verify_dodo_signature(body, {}, secret=secret)                                 # unsigned
    stale = datetime.now(tz=UTC) - timedelta(hours=1)
    assert not verify_dodo_signature(body, _sign(secret, body, stale), secret=secret)         # replay


def test_unsigned_payment_webhooks_rejected_without_secret_outside_dev(monkeypatch):
    from src.config import settings
    from src.services.billing_service import verify_dodo_signature, verify_webhook_signature

    monkeypatch.setattr(settings, "dodo_payments_webhook_secret", None)
    monkeypatch.setattr(settings, "stripe_webhook_secret", None)
    for env in ("production", "staging"):
        monkeypatch.setattr(settings, "env", env)
        assert not verify_dodo_signature(b"{}", {})
        assert not verify_webhook_signature(b"{}", "")
    monkeypatch.setattr(settings, "env", "development")
    assert verify_dodo_signature(b"{}", {})  # local demo flow only


def test_dodo_route_rejects_forged_upgrade(monkeypatch):
    import main
    from src.config import settings

    monkeypatch.setattr(settings, "dodo_payments_webhook_secret", _dodo_secret())
    client = TestClient(main.app)
    forged = {"type": "payment.succeeded", "data": {"metadata": {"user_id": "1", "type": "subscription"}}}
    assert client.post("/api/billing/webhook/dodo", json=forged).status_code == 401


# --- production route policy: customers reach only the product API -------------------------

def _request_for(endpoint):
    from starlette.requests import Request
    return Request({"type": "http", "method": "GET", "path": "/x", "headers": [], "endpoint": endpoint})


def test_route_policy(monkeypatch):
    import main
    from src.auth.dependencies import enforce_route_policy
    from src.config import settings
    from src.jobify.routers import me_jobs

    customer, admin = SimpleNamespace(is_superuser=False), SimpleNamespace(is_superuser=True)
    product, legacy = me_jobs.list_jobs, main.capture_job

    monkeypatch.setattr(settings, "env", "production")
    monkeypatch.setattr(settings, "legacy_routes_enabled", False)
    enforce_route_policy(_request_for(product), customer)          # product API: allowed
    with pytest.raises(HTTPException) as exc:
        enforce_route_policy(_request_for(legacy), customer)       # legacy shared-catalog write
    assert exc.value.status_code == 404
    enforce_route_policy(_request_for(legacy), admin)              # admins keep legacy tools
    monkeypatch.setattr(settings, "legacy_routes_enabled", True)
    enforce_route_policy(_request_for(legacy), customer)           # explicit transition switch
    monkeypatch.setattr(settings, "legacy_routes_enabled", False)
    monkeypatch.setattr(settings, "env", "development")
    enforce_route_policy(_request_for(legacy), customer)           # no effect outside production


def test_matched_endpoint_is_visible_to_dependencies():
    """The policy relies on FastAPI exposing the matched endpoint in request.scope."""
    from fastapi import Depends, Request

    seen = {}

    def dep(request: Request) -> None:
        seen["module"] = getattr(request.scope.get("endpoint"), "__module__", None)

    app = FastAPI(dependencies=[Depends(dep)])

    @app.get("/ping")
    def ping() -> dict:
        return {}

    TestClient(app).get("/ping")
    assert seen["module"] == __name__
