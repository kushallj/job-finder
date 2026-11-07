"""Jobify Phase 6: conversations, SSE send, credits/refunds, stop, provider seam."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.routers.jobify_chat_router import chat_provider, get_session_factory
from src.config import settings
from src.database import get_db
from src.models import Base, ChatConversation, ChatMessage, CreditTransaction, User
from src.services import chat_providers as cp
from src.services import jobify_chat as jc


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(db_session, clerk_auth, monkeypatch):
    from main import app

    monkeypatch.setattr(settings, "chat_echo_delay_ms", 0)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_session_factory] = lambda: (lambda: db_session)
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_session_factory, None)
    app.dependency_overrides.pop(chat_provider, None)


def _auth(clerk_auth, who="a"):
    return clerk_auth.headers(f"user_{who}", f"{who}@example.com")


def _events(text):
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def _new(client, h, mode="agent"):
    r = client.post("/api/conversations", headers=h, json={"mode": mode})
    assert r.status_code == 200, r.text
    return r.json()


def _send(client, h, cid, content="hello world", mode="agent"):
    return client.post(f"/api/conversations/{cid}/messages", headers=h, json={"content": content, "mode": mode})


def _user(db, who="a"):
    return db.query(User).filter(User.clerk_user_id == f"user_{who}").one()


class ScriptedProvider:
    """Yields `chunks`, then raises `fail` if given. Records the prompt it was called with."""
    name = "scripted"

    def __init__(self, chunks, fail=None):
        self.chunks, self.fail, self.prompts = chunks, fail, []

    async def stream(self, messages, *, mode):
        self.prompts.append(messages)
        for c in self.chunks:
            yield c
        if self.fail:
            raise self.fail


def test_requires_auth(client):
    assert client.get("/api/conversations").status_code == 401
    assert client.post("/api/conversations", json={}).status_code == 401
    assert client.patch("/api/conversations/1", json={"title": "x"}).status_code == 401
    assert client.delete("/api/conversations/1").status_code == 401
    assert client.post("/api/conversations/1/messages", json={"content": "hi"}).status_code == 401


def test_crud_and_shape(client, clerk_auth):
    h = _auth(clerk_auth)
    c = _new(client, h, "ask")
    assert set(c) == {"id", "title", "mode", "updatedAt", "messages"}
    assert (c["title"], c["mode"], c["messages"]) == ("New chat", "ask", [])
    assert c["updatedAt"].endswith("Z")

    r = client.patch(f"/api/conversations/{c['id']}", headers=h, json={"title": "  Renamed   chat "})
    assert r.json()["title"] == "Renamed chat"
    assert client.patch(f"/api/conversations/{c['id']}", headers=h, json={"title": "   "}).status_code == 422
    assert client.post("/api/conversations", headers=h, json={"mode": "bogus"}).status_code == 422

    body = client.get("/api/conversations", headers=h).json()
    assert set(body) == {"items", "total", "page", "pageSize"} and body["total"] == 1
    assert client.delete(f"/api/conversations/{c['id']}", headers=h).status_code == 204
    assert client.get("/api/conversations", headers=h).json()["total"] == 0


def test_send_streams_echo_and_persists(client, clerk_auth, db_session):
    h = _auth(clerk_auth)
    c = _new(client, h)
    before = _user(db_session).credits_balance
    r = _send(client, h, c["id"], "Find founders hiring React devs")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ev = _events(r.text)
    assert ev[0][0] == "user" and ev[0][1]["content"] == "Find founders hiring React devs"
    deltas = "".join(d["text"] for e, d in ev if e == "delta")
    assert deltas == "Echo (agent mode, no AI model connected yet): Find founders hiring React devs"
    assert ev[-1][0] == "done" and ev[-1][1]["creditsCharged"] == 5
    assert ev[-1][1]["message"]["content"] == deltas and ev[-1][1]["message"]["provider"] == "echo"

    db_session.expire_all()
    assert _user(db_session).credits_balance == before - 5
    conv = client.get("/api/conversations", headers=h).json()["items"][0]
    assert conv["title"] == "Find founders hiring React devs"
    assert [(m["role"], m["status"]) for m in conv["messages"]] == [("user", "complete"), ("assistant", "complete")]


def test_title_only_from_first_message_and_history_sent(client, clerk_auth):
    from main import app

    h = _auth(clerk_auth)
    c = _new(client, h)
    provider = ScriptedProvider(["ok"])
    app.dependency_overrides[chat_provider] = lambda: provider
    _send(client, h, c["id"], "first", "ask")
    _send(client, h, c["id"], "second", "ask")
    conv = client.get("/api/conversations", headers=h).json()["items"][0]
    assert conv["title"] == "first" and conv["mode"] == "ask"
    last_prompt = provider.prompts[-1]
    assert last_prompt[0]["role"] == "system" and "job-search assistant" in last_prompt[0]["content"]
    assert [m["content"] for m in last_prompt[1:]] == ["first", "ok", "second"]


def test_402_when_out_of_credits_stores_nothing(client, clerk_auth, db_session):
    h = _auth(clerk_auth)
    c = _new(client, h)
    user = _user(db_session)
    user.credits_balance = 4
    db_session.commit()
    r = _send(client, h, c["id"])
    assert r.status_code == 402 and r.json()["error"]["code"] == "CREDITS_REQUIRED"
    assert db_session.query(ChatMessage).count() == 0


def test_validation(client, clerk_auth):
    h = _auth(clerk_auth)
    c = _new(client, h)
    assert _send(client, h, c["id"], "   ").status_code == 422
    assert _send(client, h, c["id"], "x" * 8001).status_code == 422
    assert client.post(f"/api/conversations/{c['id']}/messages", headers=h,
                       json={"content": "hi", "mode": "send-it"}).status_code == 422


def test_provider_failure_before_text_is_refunded(client, clerk_auth, db_session):
    from main import app

    h = _auth(clerk_auth)
    c = _new(client, h)
    before = _user(db_session).credits_balance
    app.dependency_overrides[chat_provider] = lambda: ScriptedProvider([], fail=cp.ChatProviderError("quota exceeded"))
    ev = _events(_send(client, h, c["id"]).text)
    assert ev[-1] == ("error", {"code": "PROVIDER_ERROR", "message": "quota exceeded", "refunded": True})
    db_session.expire_all()
    assert _user(db_session).credits_balance == before
    assert db_session.query(CreditTransaction).filter(CreditTransaction.action == "chat_message_refund").count() == 1
    assert db_session.query(ChatMessage).filter(ChatMessage.role == "assistant").count() == 0


def test_unexpected_provider_crash_is_not_leaked(client, clerk_auth):
    from main import app

    h = _auth(clerk_auth)
    c = _new(client, h)
    app.dependency_overrides[chat_provider] = lambda: ScriptedProvider([], fail=KeyError("secret-internal"))
    ev = _events(_send(client, h, c["id"]).text)
    assert ev[-1][0] == "error" and "secret-internal" not in json.dumps(ev[-1][1])


def test_provider_failure_after_text_keeps_partial_and_charge(client, clerk_auth, db_session):
    from main import app

    h = _auth(clerk_auth)
    c = _new(client, h)
    before = _user(db_session).credits_balance
    app.dependency_overrides[chat_provider] = lambda: ScriptedProvider(["half "], fail=cp.ChatProviderError("timeout"))
    ev = _events(_send(client, h, c["id"]).text)
    assert ev[-1][0] == "error" and ev[-1][1]["refunded"] is False
    assert ev[-1][1]["partial"]["content"] == "half " and ev[-1][1]["partial"]["status"] == "stopped"
    db_session.expire_all()
    assert _user(db_session).credits_balance == before - 5


def test_empty_reply_is_refunded(client, clerk_auth, db_session):
    from main import app

    h = _auth(clerk_auth)
    c = _new(client, h)
    before = _user(db_session).credits_balance
    app.dependency_overrides[chat_provider] = lambda: ScriptedProvider([])
    ev = _events(_send(client, h, c["id"]).text)
    assert ev[-1][0] == "error" and ev[-1][1]["code"] == "EMPTY_REPLY" and ev[-1][1]["refunded"] is True
    db_session.expire_all()
    assert _user(db_session).credits_balance == before


def test_stop_mid_stream_saves_partial_as_stopped(db_session):
    """Client disconnect closes the generator (GeneratorExit); the partial reply is kept."""
    user = User(email="s@example.com", full_name="S", hashed_password="", credits_balance=50)
    db_session.add(user)
    db_session.commit()
    conv = ChatConversation(user_id=user.id, title="t", mode="agent")
    db_session.add(conv)
    db_session.commit()

    async def run():
        gen = jc.stream_reply(session_factory=lambda: db_session, provider=ScriptedProvider(["one ", "two ", "three"]),
                              user_id=user.id, conversation_id=conv.id, user_message={"id": "1"}, prompt=[],
                              mode="agent", is_disconnected=lambda: asyncio.sleep(0, result=False))
        assert (await gen.__anext__()).startswith("event: user")
        assert '"one "' in await gen.__anext__()
        await gen.aclose()

    asyncio.run(run())
    msg = db_session.query(ChatMessage).filter(ChatMessage.role == "assistant").one()
    assert (msg.content, msg.status) == ("one ", "stopped")


def test_disconnect_check_stops_and_saves(db_session):
    user = User(email="d@example.com", full_name="D", hashed_password="", credits_balance=50)
    db_session.add(user)
    db_session.commit()
    conv = ChatConversation(user_id=user.id, title="t", mode="ask")
    db_session.add(conv)
    db_session.commit()
    calls = {"n": 0}

    async def disconnected():
        calls["n"] += 1
        return calls["n"] > 1  # connected for the first chunk only

    async def run():
        gen = jc.stream_reply(session_factory=lambda: db_session, provider=ScriptedProvider(["a ", "b ", "c"]),
                              user_id=user.id, conversation_id=conv.id, user_message={"id": "1"}, prompt=[],
                              mode="ask", is_disconnected=disconnected)
        return [e async for e in gen]

    events = asyncio.run(run())
    assert sum(e.startswith("event: delta") for e in events) == 1 and not any("event: done" in e for e in events)
    msg = db_session.query(ChatMessage).filter(ChatMessage.role == "assistant").one()
    assert (msg.content, msg.status) == ("a ", "stopped")


def test_tenant_isolation(client, clerk_auth, db_session):
    a, b = _auth(clerk_auth, "a"), _auth(clerk_auth, "b")
    c = _new(client, a)
    _send(client, a, c["id"], "private question")
    assert client.get("/api/conversations", headers=b).json()["total"] == 0
    assert client.patch(f"/api/conversations/{c['id']}", headers=b, json={"title": "pwned"}).status_code == 404
    assert client.delete(f"/api/conversations/{c['id']}", headers=b).status_code == 404
    b_before = _user(db_session, "b").credits_balance
    assert _send(client, b, c["id"], "inject").status_code == 404
    db_session.expire_all()
    assert _user(db_session, "b").credits_balance == b_before        # not charged for a 404
    assert db_session.query(ChatMessage).count() == 2                # A's two turns only


def test_unknown_provider_is_503(client, clerk_auth, monkeypatch, db_session):
    h = _auth(clerk_auth)
    c = _new(client, h)
    before = _user(db_session).credits_balance
    monkeypatch.setattr(settings, "chat_provider", "gpt-nonexistent")
    r = _send(client, h, c["id"])
    assert r.status_code == 503 and r.json()["error"]["code"] == "CHAT_UNAVAILABLE"
    db_session.expire_all()
    assert _user(db_session).credits_balance == before


def test_fallback_records_the_provider_that_answered_and_usage(client, clerk_auth, db_session):
    import httpx
    from main import app

    h = _auth(clerk_auth)
    c = _new(client, h)
    body = ('data: {"choices":[{"delta":{"content":"real answer"}}]}\n\n'
            'data: {"choices":[],"usage":{"total_tokens":9}}\n\ndata: [DONE]\n\n')
    free = cp.OpenAICompatibleProvider(name="openrouter", base_url="http://x/v1", model="m",
                                       transport=httpx.MockTransport(lambda r: httpx.Response(429)))
    local = cp.OpenAICompatibleProvider(name="ollama", base_url="http://y/v1", model="m",
                                        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body.encode())))
    app.dependency_overrides[chat_provider] = lambda: cp.FallbackProvider([free, local])
    ev = _events(_send(client, h, c["id"]).text)
    assert ev[-1][0] == "done" and ev[-1][1]["message"]["provider"] == "ollama"
    row = db_session.query(ChatMessage).filter(ChatMessage.role == "assistant").one()
    assert row.content == "real answer" and json.loads(row.usage) == {"total_tokens": 9}


def test_prompt_is_grounded_in_own_profile_only(client, clerk_auth, db_session):
    from main import app
    from src.models import Application

    a, b = _auth(clerk_auth, "a"), _auth(clerk_auth, "b")
    client.put("/api/me/profile", headers=a, json={"skills": ["React", "TypeScript"], "targetRoles": ["Frontend Engineer"],
                                                   "yearsOfExperience": 3, "locations": ["Remote"]})
    p = client.get("/api/portfolio", headers=a).json()
    p["identity"].update(fullName="Asha Rao", jobTitle="Frontend Engineer")
    p["projects"] = [{"title": "Gridline", "subtitle": "https://grid.dev", "description": "Virtualised grid, 1M rows"}]
    client.put("/api/portfolio", headers=a, json=p)
    ua = _user(db_session, "a")
    db_session.add(Application(user_id=ua.id, company="Razorpay", position="SDE 2", kanban_stage="interview",
                               notes="PRIVATE: recruiter said salary cap 30L"))
    db_session.commit()

    provider = ScriptedProvider(["ok"])
    app.dependency_overrides[chat_provider] = lambda: provider
    _send(client, a, _new(client, a)["id"], "draft an email")
    system = provider.prompts[-1][0]["content"]
    for fact in ("Asha Rao", "Frontend Engineer", "react", "typescript", "Years of experience: 3", "Remote",
                 "Gridline", "1M rows", "Razorpay — SDE 2 (interview)"):
        assert fact in system, fact
    assert "PRIVATE" not in system and "salary cap" not in system
    assert "never invent" in system.lower()

    _send(client, b, _new(client, b)["id"], "who am I?")
    system_b = provider.prompts[-1][0]["content"]
    assert "Asha" not in system_b and "Razorpay" not in system_b and "none saved yet" in system_b


def test_rate_limit_is_429_and_not_charged(client, clerk_auth, db_session, monkeypatch):
    h = _auth(clerk_auth)
    c = _new(client, h)
    monkeypatch.setattr(settings, "chat_rate_per_minute", 2)
    assert _send(client, h, c["id"], "1").status_code == 200
    assert _send(client, h, c["id"], "2").status_code == 200
    db_session.expire_all()
    before = _user(db_session).credits_balance
    r = _send(client, h, c["id"], "3")
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED" and r.headers["retry-after"] == "60"
    db_session.expire_all()
    assert _user(db_session).credits_balance == before
    assert db_session.query(ChatMessage).filter(ChatMessage.role == "user").count() == 2


def test_echo_provider_streams_words():
    async def run():
        return [c async for c in cp.EchoProvider(0).stream([{"role": "user", "content": "a b"}], mode="ask")]

    chunks = asyncio.run(run())
    assert "".join(chunks) == "Echo (ask mode, no AI model connected yet): a b" and len(chunks) > 3
