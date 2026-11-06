"""Jobify job-hunt inbox: address, signed inbound webhook, auto-tracking, in-app inbox, replies."""

import re
import smtplib
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config import settings
from src.database import get_db
from src.models import Application, Base, InboundRecruiterMessage, User
from src.services import jobify_inbox as ib

SECRET = "test-inbound-secret"
DOMAIN = "mail.jobify.test"


@pytest.fixture(autouse=True)
def inbox_settings(monkeypatch):
    monkeypatch.setattr(settings, "inbox_domain", DOMAIN)
    monkeypatch.setattr(settings, "inbound_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "inbox_smtp_host", None)
    monkeypatch.setattr(settings, "inbox_smtp_username", None)
    monkeypatch.setattr(settings, "inbox_smtp_password", None)


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
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def _auth(clerk_auth, who="a"):
    return clerk_auth.headers(f"user_{who}", f"{who}@example.com")


def _inbox(client, clerk_auth, who="a"):
    return client.get("/api/inbox", headers=_auth(clerk_auth, who)).json()["address"]


def _raw(sender, subject, body, to, msg_id=None, extra=""):
    msg_id = msg_id or f"<{time.time_ns()}@sender.example>"
    return (f"From: {sender}\r\nTo: {to}\r\nSubject: {subject}\r\nMessage-ID: {msg_id}\r\n"
            f"Date: Thu, 05 Nov 2026 10:00:00 +0530\r\n{extra}Content-Type: text/plain; charset=utf-8\r\n\r\n{body}\r\n").encode()


def _deliver(client, raw, to, secret=SECRET, ts=None):
    ts = ts or str(int(time.time()))
    return client.post("/api/inbound/email", content=raw, headers={
        "Content-Type": "message/rfc822", "X-Jobify-Timestamp": ts,
        "X-Jobify-Signature": ib.sign(secret, ts, raw), "X-Jobify-Envelope-To": to})


def _card(db, clerk_id, company, stage="applied"):
    user = db.query(User).filter(User.clerk_user_id == clerk_id).one()
    app = Application(user_id=user.id, company=company, position="Engineer", kanban_stage=stage,
                      applied_at=datetime(2026, 10, 1), created_at=datetime(2026, 10, 1), updated_at=datetime(2026, 10, 1))
    db.add(app)
    db.commit()
    return app


# --- address -------------------------------------------------------------------------------

def test_address_format_and_stability(client, clerk_auth, db_session):
    first = client.get("/api/inbox", headers=_auth(clerk_auth)).json()
    assert re.fullmatch(rf"[a-z0-9.]+\.[a-z2-9]{{4}}@{re.escape(DOMAIN)}", first["address"])
    assert first == {"address": first["address"], "receiving": True, "sending": False, "unread": 0}
    assert _inbox(client, clerk_auth) == first["address"]  # same address every time


def test_address_uses_name_and_never_leaks_clerk_placeholder(db_session):
    named = User(email="x@clerk.user", full_name="Kushall Jain", credits_balance=0)
    anon = User(email="user_3abc@clerk.user", credits_balance=0)
    clerk_named = User(email="user_3LhDZ48grUxt@clerk.user", full_name="User_3Lhdz48Gruxtjjoav", credits_balance=0)
    db_session.add_all([named, anon, clerk_named])
    db_session.commit()
    assert ib.get_or_create_inbox(db_session, named).email_address.startswith("kushall.jain.")
    assert ib.get_or_create_inbox(db_session, anon).email_address.startswith("jobseeker.")
    assert ib.get_or_create_inbox(db_session, clerk_named).email_address.startswith("jobseeker.")


def test_no_address_until_domain_configured(client, clerk_auth, monkeypatch):
    monkeypatch.setattr(settings, "inbox_domain", None)
    assert client.get("/api/inbox", headers=_auth(clerk_auth)).json()["address"] is None


def test_addresses_are_unique_per_user(client, clerk_auth):
    assert _inbox(client, clerk_auth, "a") != _inbox(client, clerk_auth, "b")


# --- webhook security -------------------------------------------------------------------------

def test_webhook_rejects_bad_missing_and_stale_signatures(client, clerk_auth, db_session):
    to = _inbox(client, clerk_auth)
    raw = _raw("hr@acme.com", "Hi", "Hello", to)
    assert _deliver(client, raw, to, secret="wrong").status_code == 401
    assert client.post("/api/inbound/email", content=raw, headers={"X-Jobify-Envelope-To": to}).status_code == 401
    assert _deliver(client, raw, to, ts=str(int(time.time()) - 3600)).status_code == 401
    assert db_session.query(InboundRecruiterMessage).count() == 0


def test_webhook_signature_covers_the_body(client, clerk_auth, db_session):
    to = _inbox(client, clerk_auth)
    ts = str(int(time.time()))
    signed_for = _raw("hr@acme.com", "Hi", "original", to)
    res = client.post("/api/inbound/email", content=_raw("hr@acme.com", "Hi", "tampered", to), headers={
        "X-Jobify-Timestamp": ts, "X-Jobify-Signature": ib.sign(SECRET, ts, signed_for), "X-Jobify-Envelope-To": to})
    assert res.status_code == 401


def test_unknown_recipient_is_accepted_but_not_stored(client, db_session):
    res = _deliver(client, _raw("x@y.com", "Hi", "Hello", f"nobody.zzzz@{DOMAIN}"), f"nobody.zzzz@{DOMAIN}")
    assert res.status_code == 202 and res.json() == {"accepted": True, "stored": False}
    assert db_session.query(InboundRecruiterMessage).count() == 0


def test_oversized_message_rejected(client, clerk_auth, monkeypatch):
    monkeypatch.setattr(settings, "inbound_max_bytes", 200)
    to = _inbox(client, clerk_auth)
    assert _deliver(client, _raw("hr@acme.com", "Big", "x" * 500, to), to).status_code == 413


# --- auto-tracking ----------------------------------------------------------------------------------

def test_recruiter_reply_moves_card_and_lands_in_inbox(client, clerk_auth, db_session):
    to = _inbox(client, clerk_auth)
    card = _card(db_session, "user_a", "Acme")
    res = _deliver(client, _raw("Priya <priya@acme.com>", "Interview invitation", "We'd like to schedule an interview with you next week.", to), to)
    assert res.json() == {"accepted": True, "stored": True}
    db_session.refresh(card)
    assert card.kanban_stage == "interview" and card.recruiter_email == "priya@acme.com"
    msgs = client.get("/api/inbox/messages", headers=_auth(clerk_auth)).json()
    m = msgs["items"][0]
    assert msgs["total"] == 1 and m["from"] == {"name": "Priya", "email": "priya@acme.com"}
    assert (m["applicationId"], m["movedTo"], m["read"], m["direction"]) == (str(card.id), "interview", False, "in")
    assert m["receivedAt"] == "2026-11-05T04:30:00Z"  # +0530 normalised to UTC
    assert client.get("/api/inbox", headers=_auth(clerk_auth)).json()["unread"] == 1


def test_unmatched_mail_is_still_kept_in_the_job_inbox(client, clerk_auth, db_session):
    to = _inbox(client, clerk_auth)
    _deliver(client, _raw("talent@newco.io", "Opportunity at NewCo", "Are you open to a chat?", to), to)
    m = client.get("/api/inbox/messages", headers=_auth(clerk_auth)).json()["items"][0]
    assert m["applicationId"] is None and m["subject"] == "Opportunity at NewCo"


def test_forged_sender_is_stored_but_never_moves_a_card(client, clerk_auth, db_session):
    to = _inbox(client, clerk_auth)
    card = _card(db_session, "user_a", "Acme")
    raw = _raw("hr@acme.com", "Update on your application", "Unfortunately we will not move forward.", to,
               extra="Authentication-Results: mx.cloudflare.net; spf=fail; dkim=none; dmarc=fail\r\n")
    _deliver(client, raw, to)
    db_session.refresh(card)
    assert card.kanban_stage == "applied"
    m = client.get("/api/inbox/messages", headers=_auth(clerk_auth)).json()["items"][0]
    assert m["senderVerified"] is False and m["movedTo"] is None


def test_thread_reply_links_to_same_card_even_from_another_address(client, clerk_auth, db_session):
    to = _inbox(client, clerk_auth)
    card = _card(db_session, "user_a", "Acme")
    _deliver(client, _raw("priya@acme.com", "Next steps", "Thanks for applying", to, msg_id="<thread-1@acme.com>"), to)
    _deliver(client, _raw("scheduler@calendly-like.example", "Re: Next steps", "Pick a time", to,
                          extra="In-Reply-To: <thread-1@acme.com>\r\nReferences: <thread-1@acme.com>\r\n"), to)
    items = client.get("/api/inbox/messages", params={"applicationId": card.id}, headers=_auth(clerk_auth)).json()["items"]
    assert len(items) == 2


def test_duplicate_delivery_is_stored_once(client, clerk_auth, db_session):
    to = _inbox(client, clerk_auth)
    raw = _raw("hr@acme.com", "Hi", "Hello", to, msg_id="<same@acme.com>")
    _deliver(client, raw, to)
    assert _deliver(client, raw, to).json()["stored"] is False
    assert db_session.query(InboundRecruiterMessage).count() == 1


def test_html_only_email_is_readable(client, clerk_auth):
    to = _inbox(client, clerk_auth)
    raw = (f"From: hr@acme.com\r\nTo: {to}\r\nSubject: Hello\r\nMessage-ID: <h1@acme.com>\r\nContent-Type: text/html\r\n\r\n"
           "<html><style>p{color:red}</style><p>We'd love to <b>talk</b></p></html>").encode()
    _deliver(client, raw, to)
    mid = client.get("/api/inbox/messages", headers=_auth(clerk_auth)).json()["items"][0]["id"]
    body = client.get(f"/api/inbox/messages/{mid}", headers=_auth(clerk_auth)).json()["body"]
    assert "talk" in body and "<b>" not in body and "color:red" not in body


# --- inbox reads ----------------------------------------------------------------------------------------

def test_opening_marks_read_and_other_users_cannot_see_it(client, clerk_auth):
    to = _inbox(client, clerk_auth, "a")
    _inbox(client, clerk_auth, "b")
    _deliver(client, _raw("hr@acme.com", "Private", "Secret offer details", to), to)
    mid = client.get("/api/inbox/messages", headers=_auth(clerk_auth)).json()["items"][0]["id"]
    assert client.get(f"/api/inbox/messages/{mid}", headers=_auth(clerk_auth, "b")).status_code == 404
    assert client.get("/api/inbox/messages", headers=_auth(clerk_auth, "b")).json()["total"] == 0
    full = client.get(f"/api/inbox/messages/{mid}", headers=_auth(clerk_auth)).json()
    assert full["body"].strip() == "Secret offer details" and full["read"] is True
    assert client.get("/api/inbox", headers=_auth(clerk_auth)).json()["unread"] == 0


def test_inbox_requires_auth(client):
    assert client.get("/api/inbox").status_code == 401
    assert client.get("/api/inbox/messages").status_code == 401


# --- replies -------------------------------------------------------------------------------------------------

@pytest.fixture
def smtp(monkeypatch):
    monkeypatch.setattr(settings, "inbox_smtp_host", "smtp.example")
    monkeypatch.setattr(settings, "inbox_smtp_username", "u")
    monkeypatch.setattr(settings, "inbox_smtp_password", "p")
    sent = []
    monkeypatch.setattr(ib, "_smtp_send", lambda m: sent.append(m))
    return sent


def _received_id(client, clerk_auth, to, **kw):
    _deliver(client, _raw("Priya <priya@acme.com>", "Interview invitation", "Can you do Tuesday?", to, msg_id="<orig-1@acme.com>", **kw), to)
    return client.get("/api/inbox/messages", headers=_auth(clerk_auth)).json()["items"][0]["id"]


def test_reply_not_available_without_smtp(client, clerk_auth):
    to = _inbox(client, clerk_auth)
    res = client.post(f"/api/inbox/messages/{_received_id(client, clerk_auth, to)}/reply", headers=_auth(clerk_auth), json={"body": "Yes"})
    assert res.status_code == 503 and res.json()["error"]["code"] == "INBOX_SENDING_NOT_CONFIGURED"


def test_reply_threads_correctly_and_is_recorded(client, clerk_auth, smtp):
    to = _inbox(client, clerk_auth)
    mid = _received_id(client, clerk_auth, to)
    res = client.post(f"/api/inbox/messages/{mid}/reply", headers=_auth(clerk_auth), json={"body": "Tuesday works, thanks!"})
    assert res.status_code == 201
    out = res.json()
    assert (out["direction"], out["to"], out["subject"]) == ("out", "priya@acme.com", "Re: Interview invitation")
    email = smtp[0]
    assert email["To"] == "priya@acme.com" and to in email["From"]
    assert email["In-Reply-To"] == "<orig-1@acme.com>" and "<orig-1@acme.com>" in email["References"]
    assert email.get_content().strip() == "Tuesday works, thanks!"
    assert client.get("/api/inbox/messages", headers=_auth(clerk_auth)).json()["total"] == 2


def test_cannot_reply_to_own_sent_message_or_others_mail(client, clerk_auth, smtp):
    to = _inbox(client, clerk_auth)
    _inbox(client, clerk_auth, "b")
    mid = _received_id(client, clerk_auth, to)
    out_id = client.post(f"/api/inbox/messages/{mid}/reply", headers=_auth(clerk_auth), json={"body": "Hi"}).json()["id"]
    assert client.post(f"/api/inbox/messages/{out_id}/reply", headers=_auth(clerk_auth), json={"body": "x"}).status_code == 400
    assert client.post(f"/api/inbox/messages/{mid}/reply", headers=_auth(clerk_auth, "b"), json={"body": "x"}).status_code == 404
    assert client.post(f"/api/inbox/messages/{mid}/reply", headers=_auth(clerk_auth), json={"body": ""}).status_code == 422


def test_daily_send_limit(client, clerk_auth, smtp, monkeypatch):
    monkeypatch.setattr(settings, "inbox_daily_send_limit", 2)
    to = _inbox(client, clerk_auth)
    mid = _received_id(client, clerk_auth, to)
    for _ in range(2):
        assert client.post(f"/api/inbox/messages/{mid}/reply", headers=_auth(clerk_auth), json={"body": "Hi"}).status_code == 201
    res = client.post(f"/api/inbox/messages/{mid}/reply", headers=_auth(clerk_auth), json={"body": "Hi"})
    assert res.status_code == 429 and res.json()["error"]["code"] == "SEND_LIMIT_REACHED"


def test_smtp_failure_is_reported_and_not_recorded(client, clerk_auth, smtp, monkeypatch):
    def boom(_):
        raise smtplib.SMTPServerDisconnected("down")
    monkeypatch.setattr(ib, "_smtp_send", boom)
    to = _inbox(client, clerk_auth)
    mid = _received_id(client, clerk_auth, to)
    res = client.post(f"/api/inbox/messages/{mid}/reply", headers=_auth(clerk_auth), json={"body": "Hi"})
    assert res.status_code == 502 and res.json()["error"]["code"] == "SEND_FAILED"
    assert client.get("/api/inbox/messages", headers=_auth(clerk_auth)).json()["total"] == 1
