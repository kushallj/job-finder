import pytest
from fastapi.testclient import TestClient
from main import app
from src.copilot.engine import OSINTBooleanEngine


@pytest.fixture
def client():
    return TestClient(app)


def test_osint_dork_generation():
    engine = OSINTBooleanEngine()
    dorks = engine.generate_dorks(role="Staff Backend Engineer", company="Stripe", intent="all")
    assert len(dorks) >= 5
    queries_str = " ".join([d.query for d in dorks])
    assert "site:lever.co" in queries_str or "site:greenhouse.io" in queries_str
    assert "Stripe" in queries_str


def test_copilot_api_endpoints(client):
    # 1. GET /api/copilot/starters
    res_start = client.get("/api/copilot/starters")
    assert res_start.status_code == 200
    assert len(res_start.json()["starters"]) >= 3

    # 2. POST /api/copilot/generate-dorks
    res_dorks = client.post("/api/copilot/generate-dorks", json={
        "role_title": "Distributed Systems Engineer",
        "company": "OpenAI",
        "intent": "unindexed_jds",
    })
    assert res_dorks.status_code == 200
    data = res_dorks.json()
    assert data["status"] == "success"
    assert data["total_dorks"] >= 2

    # 3. POST /api/copilot/chat
    res_chat = client.post("/api/copilot/chat", json={
        "message": "Find hiring manager emails and LinkedIn profiles hiring for Senior Backend at Stripe",
        "target_company": "Stripe",
        "role_title": "Senior Backend Engineer",
    })
    assert res_chat.status_code == 200
    chat_data = res_chat.json()
    assert chat_data["status"] == "success"
    assert "session_id" in chat_data
    assert len(chat_data["reply"]) > 10
    assert len(chat_data["dorks"]) > 0
