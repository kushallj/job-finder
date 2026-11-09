"""Jobify Phase 3: real Gmail connection (OAuth, encrypted token, scoped sync, disconnect)."""

import base64
import time
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config import settings
from src.database import get_db
from src.models import Application, Base, InboundRecruiterMessage, MailboxAccount, User
from src.jobify.services import gmail_sync as gs


def _msg(mid, sender, subject, body, ts=None):
    data = base64.urlsafe_b64encode(body.encode()).decode().rstrip("=")
    return {"id": mid, "threadId": f"t-{mid}", "snippet": body[:80], "internalDate": str(int((ts or time.time()) * 1000)),
            "payload": {"mimeType": "multipart/alternative", "headers": [{"name": "From", "value": sender}, {"name": "Subject", "value": subject}],
                        "parts": [{"mimeType": "text/plain", "body": {"data": data}}]}}


class FakeGoogle:
    def __init__(self):
        self.messages = {}
        self.scope = f"openid email {gs.GMAIL_SCOPE}"
        self.email = "qa.user@example.com"
        self.refresh_error = None
        self.revoked = []
        self.queries = []

    def exchange_code(self, code):
        return {"access_token": "at", "refresh_token": "rt-secret", "scope": self.scope}

    def refresh(self, rt):
        if self.refresh_error:
            raise self.refresh_error
        assert rt == "rt-secret"
        return "at"

    def userinfo(self, at):
        return {"email": self.email}

    def list_messages(self, at, query, limit):
        self.queries.append(query)
        return list(self.messages)[:limit]

    def get_message(self, at, mid):
        return self.messages[mid]

    def revoke(self, token):
        self.revoked.append(token)


@pytest.fixture
def google(monkeypatch):
    fake = FakeGoogle()
    monkeypatch.setattr(gs, "get_client", lambda: fake)
    monkeypatch.setattr(settings, "google_oauth_client_id", "cid.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "csecret")
    monkeypatch.setattr(settings, "token_encryption_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:3000")
    return fake


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(db_session, clerk_auth):
    from main import app

    app.dependency_overrides[get_db] = lambda: db_session
    c = TestClient(app)
    c.follow_redirects = False  # assert on the OAuth callback redirect itself
    yield c
    app.dependency_overrides.pop(get_db, None)


def _auth(clerk_auth, who="a"):
    return clerk_auth.headers(f"user_{who}", f"{who}@example.com")


def _user(client, clerk_auth, db, who="a"):
    client.get("/api/me", headers=_auth(clerk_auth, who))
    return db.query(User).filter(User.clerk_user_id == f"user_{who}").one()


def _connect(client, clerk_auth, db, who="a"):
    url = client.post("/api/gmail/connect", headers=_auth(clerk_auth, who)).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    res = client.get("/api/gmail/callback", params={"code": "c", "state": state})
    return res


def _card(db, user, company, stage="applied", **kw):
    app = Application(user_id=user.id, company=company, position="Engineer", kanban_stage=stage,
                      applied_at=datetime(2026, 10, 1), created_at=datetime(2026, 10, 1), updated_at=datetime(2026, 10, 1), **kw)
    db.add(app)
    db.commit()
    return app


# --- connect -----------------------------------------------------------------------------

def test_state_shape_when_not_connected(client, clerk_auth, google):
    assert client.get("/api/gmail", headers=_auth(clerk_auth)).json() == {"status": "not_connected", "email": None, "lastSync": None, "nextScan": None, "available": True}


def test_connect_refuses_when_not_configured(client, clerk_auth, monkeypatch):
    monkeypatch.setattr(settings, "google_oauth_client_id", None)
    res = client.post("/api/gmail/connect", headers=_auth(clerk_auth))
    assert res.status_code == 503 and res.json()["error"]["code"] == "GMAIL_NOT_CONFIGURED"


def test_connect_returns_readonly_offline_consent_url(client, clerk_auth, db_session, google):
    user = _user(client, clerk_auth, db_session)
    url = client.post("/api/gmail/connect", headers=_auth(clerk_auth)).json()["url"]
    q = parse_qs(urlparse(url).query)
    assert url.startswith(gs.AUTH_URL)
    assert gs.GMAIL_SCOPE in q["scope"][0] and "gmail.send" not in q["scope"][0] and "gmail.modify" not in q["scope"][0]
    assert q["access_type"] == ["offline"] and q["prompt"] == ["consent"]
    assert gs.read_state(q["state"][0]) == user.id


def test_callback_connects_and_encrypts_token(client, clerk_auth, db_session, google):
    res = _connect(client, clerk_auth, db_session)
    assert res.status_code == 302 and res.headers["location"] == "http://localhost:3000/app/applications?gmail=connected"
    mb = db_session.query(MailboxAccount).one()
    assert mb.email_address == "qa.user@example.com" and mb.sync_status == "connected"
    assert mb.oauth_refresh_token_enc and "rt-secret" not in mb.oauth_refresh_token_enc
    assert gs.decrypt_token(mb.oauth_refresh_token_enc) == "rt-secret"
    state = client.get("/api/gmail", headers=_auth(clerk_auth)).json()
    assert state["status"] == "connected" and state["email"] == "qa.user@example.com"
    assert "rt-secret" not in str(state) and "token" not in str(state).lower()


@pytest.mark.parametrize("params,reason", [
    ({"error": "access_denied"}, "ACCESS_DENIED"),
    ({"code": "c"}, "INVALID_CALLBACK"),
    ({"code": "c", "state": "forged"}, "INVALID_STATE"),
])
def test_callback_errors_redirect_without_connecting(client, db_session, google, params, reason):
    res = client.get("/api/gmail/callback", params=params)
    assert res.status_code == 302 and res.headers["location"].endswith(f"gmail=error&reason={reason}")
    assert db_session.query(MailboxAccount).count() == 0


def test_callback_rejects_expired_or_foreign_state(client, clerk_auth, db_session, google):
    user = _user(client, clerk_auth, db_session)
    expired = jwt.encode({"uid": user.id, "purpose": "gmail_connect", "exp": int(time.time()) - 5}, settings.jwt_secret_key, algorithm="HS256")
    wrong_purpose = jwt.encode({"uid": user.id, "purpose": "other", "exp": int(time.time()) + 60}, settings.jwt_secret_key, algorithm="HS256")
    other_key = jwt.encode({"uid": user.id, "purpose": "gmail_connect", "exp": int(time.time()) + 60}, "not-the-key", algorithm="HS256")
    for state in (expired, wrong_purpose, other_key):
        assert client.get("/api/gmail/callback", params={"code": "c", "state": state}).headers["location"].endswith("reason=INVALID_STATE")
    assert db_session.query(MailboxAccount).count() == 0


def test_callback_requires_gmail_scope(client, clerk_auth, db_session, google):
    google.scope = "openid email"
    assert _connect(client, clerk_auth, db_session).headers["location"].endswith("reason=GMAIL_SCOPE_DENIED")


def test_same_gmail_cannot_attach_to_two_accounts(client, clerk_auth, db_session, google):
    _connect(client, clerk_auth, db_session, "a")
    assert _connect(client, clerk_auth, db_session, "b").headers["location"].endswith("reason=GMAIL_IN_USE")


def test_callback_is_public_but_other_endpoints_are_not(client, google):
    assert client.get("/api/gmail").status_code == 401
    assert client.post("/api/gmail/sync").status_code == 401
    assert client.get("/api/gmail/callback", params={"error": "access_denied"}).status_code == 302


# --- sync ----------------------------------------------------------------------------------

def test_sync_advances_matched_cards_and_discards_unrelated_mail(client, clerk_auth, db_session, google):
    user = _user(client, clerk_auth, db_session)
    acme = _card(db_session, user, "Acme")
    globex = _card(db_session, user, "Globex", recruiter_email="talent@hire.example")
    _connect(client, clerk_auth, db_session)
    google.messages = {
        "m1": _msg("m1", "Priya <priya@acme.com>", "Interview invitation", "We would like to schedule an interview with you next week."),
        "m2": _msg("m2", "talent@hire.example", "Update on your application", "Unfortunately we have decided to move forward with other candidates."),
        "m3": _msg("m3", "Deals <news@shop.example>", "50% off everything", "Big sale this weekend only."),
    }
    res = client.post("/api/gmail/sync", headers=_auth(clerk_auth))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "connected" and body["lastSync"].endswith("Z") and body["nextScan"].endswith("Z")
    assert body["result"] == {"scanned": 3, "stored": 2, "advanced": 2}
    db_session.refresh(acme), db_session.refresh(globex)
    assert (acme.kanban_stage, globex.kanban_stage) == ("interview", "rejected")
    stored = {m.message_id for m in db_session.query(InboundRecruiterMessage).all()}
    assert stored == {"m1", "m2"}  # the newsletter was never stored
    cards = {c["company"]: c for c in client.get("/api/applications", headers=_auth(clerk_auth)).json()["items"]}
    assert cards["Acme"]["messages"] == 2 and cards["Acme"]["subject"] == "Interview invitation"


def test_sync_never_moves_cards_backwards_and_dedupes(client, clerk_auth, db_session, google):
    user = _user(client, clerk_auth, db_session)
    card = _card(db_session, user, "Acme", stage="offer")
    _connect(client, clerk_auth, db_session)
    google.messages = {"m1": _msg("m1", "hr@acme.com", "Interview invitation", "We would like to schedule an interview.")}
    client.post("/api/gmail/sync", headers=_auth(clerk_auth))
    db_session.refresh(card)
    assert card.kanban_stage == "offer"
    db_session.query(MailboxAccount).one().sync_status = "connected"
    db_session.commit()
    second = client.post("/api/gmail/sync", headers=_auth(clerk_auth)).json()
    assert second["result"]["stored"] == 0 and db_session.query(InboundRecruiterMessage).count() == 1


def test_sync_only_touches_the_mailbox_owners_cards(client, clerk_auth, db_session, google):
    user_a = _user(client, clerk_auth, db_session, "a")
    user_b = _user(client, clerk_auth, db_session, "b")
    b_card = _card(db_session, user_b, "Globex")
    _connect(client, clerk_auth, db_session, "a")
    google.messages = {"m1": _msg("m1", "hr@globex.com", "Offer letter", "We are pleased to offer you the role.")}
    result = client.post("/api/gmail/sync", headers=_auth(clerk_auth, "a")).json()["result"]
    db_session.refresh(b_card)
    assert result["stored"] == 0 and b_card.kanban_stage == "applied"
    assert user_a.id != user_b.id


def test_revoked_access_disconnects_and_asks_to_reconnect(client, clerk_auth, db_session, google):
    _user(client, clerk_auth, db_session)
    _connect(client, clerk_auth, db_session)
    google.refresh_error = gs.GmailError("GMAIL_REAUTH_REQUIRED", "Gmail access was revoked or expired. Connect again.", 409)
    res = client.post("/api/gmail/sync", headers=_auth(clerk_auth))
    assert res.status_code == 409 and res.json()["error"]["code"] == "GMAIL_REAUTH_REQUIRED"
    mb = db_session.query(MailboxAccount).one()
    assert mb.sync_status == "disconnected" and mb.oauth_refresh_token_enc is None


def test_unexpected_failure_marks_failed_without_leaking_details(client, clerk_auth, db_session, google):
    _user(client, clerk_auth, db_session)
    _connect(client, clerk_auth, db_session)
    google.refresh_error = RuntimeError("socket exploded at 10.0.0.5")
    res = client.post("/api/gmail/sync", headers=_auth(clerk_auth))
    assert res.status_code == 502 and "10.0.0.5" not in res.text
    state = client.get("/api/gmail", headers=_auth(clerk_auth)).json()
    assert state["status"] == "failed" and state["error"] == "Sync failed. Try again later."


def test_sync_requires_connection(client, clerk_auth, google):
    res = client.post("/api/gmail/sync", headers=_auth(clerk_auth))
    assert res.status_code == 409 and res.json()["error"]["code"] == "GMAIL_NOT_CONNECTED"


# --- disconnect -------------------------------------------------------------------------------

def test_disconnect_revokes_token_and_clears_bodies(client, clerk_auth, db_session, google):
    user = _user(client, clerk_auth, db_session)
    _card(db_session, user, "Acme")
    _connect(client, clerk_auth, db_session)
    google.messages = {"m1": _msg("m1", "hr@acme.com", "Interview invitation", "Private details about the interview.")}
    client.post("/api/gmail/sync", headers=_auth(clerk_auth))
    state = client.delete("/api/gmail", headers=_auth(clerk_auth)).json()
    assert state == {"status": "disconnected", "email": None, "lastSync": None, "nextScan": None}
    assert google.revoked == ["rt-secret"]
    mb = db_session.query(MailboxAccount).one()
    assert mb.oauth_refresh_token_enc is None
    msg = db_session.query(InboundRecruiterMessage).one()
    assert msg.body_text is None and msg.snippet is None
    assert client.post("/api/gmail/sync", headers=_auth(clerk_auth)).status_code == 409


# --- parsing / matching units ---------------------------------------------------------------------

def test_parse_prefers_plain_text_and_strips_html():
    html = base64.urlsafe_b64encode(b"<p>Hello <b>there</b></p>").decode()
    raw = {"id": "x", "payload": {"headers": [{"name": "From", "value": "A <a@b.com>"}], "mimeType": "text/html", "body": {"data": html}}}
    msg = gs.parse_message(raw)
    assert msg.sender_email == "a@b.com" and "Hello" in msg.body and "<b>" not in msg.body


def test_access_log_redacts_oauth_code_and_state():
    import logging
    from main import _RedactOAuthParams

    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d', ("127.0.0.1", "GET", "/api/gmail/callback?state=abc.def&code=4/0Ab-secret&scope=x", "1.1", 302), None)
    _RedactOAuthParams().filter(rec)
    line = rec.getMessage()
    assert "4/0Ab-secret" not in line and "abc.def" not in line and "scope=x" in line


def test_matching_ignores_generic_domains():
    app = Application(company="Gmail")
    msg = gs.ParsedMessage("1", "", "someone@example.com", "", "hi", "", "", datetime.utcnow())
    assert gs.match_application([app], msg) is None
