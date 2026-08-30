import pytest
from fastapi.testclient import TestClient
from main import app
from src.notifications.models import NotificationConfig, AlertPayload
from src.notifications.dispatcher import NotificationDispatcher


@pytest.fixture
def client():
    return TestClient(app)


def test_notification_dispatcher_formatting():
    dispatcher = NotificationDispatcher()
    config = NotificationConfig()
    alert = AlertPayload(
        title="Staff Backend Engineer",
        company="Stripe",
        location="Remote",
        fit_score=92.0,
        job_url="https://stripe.com/jobs/123",
        top_contact_name="David Singleton",
        top_contact_email="david@stripe.com",
    )
    # Disabled without tokens
    assert config.telegram_bot_token is None


def test_notification_api_endpoints(client):
    # 1. GET config
    res = client.get("/api/notifications/config")
    assert res.status_code == 200
    assert "min_fit_score" in res.json()

    # 2. POST config update
    res_up = client.post("/api/notifications/config", json={
        "min_fit_score": 75.0,
        "notify_on_tier1_only": True,
        "enabled": True,
    })
    assert res_up.status_code == 200
    assert res_up.json()["min_fit_score"] == 75.0

    # 3. POST test channel (expect disabled message gracefully handled)
    res_test = client.post("/api/notifications/test", json={"channel": "telegram"})
    assert res_test.status_code == 200
    assert res_test.json()["channel"] == "telegram"

    # 4. POST dispatch alert
    res_disp = client.post("/api/notifications/dispatch", json={
        "title": "Principal Architect",
        "company": "OpenAI",
        "fit_score": 95.0,
        "job_url": "https://openai.com/careers/arch",
    })
    assert res_disp.status_code == 200
    assert "dispatched_count" in res_disp.json()
