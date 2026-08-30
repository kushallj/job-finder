import pytest
from fastapi.testclient import TestClient
from main import app
from src.instagram_referral.service import InstagramReferralService
from src.instagram_referral.models import InstagramSearchRequest, InstagramMessageRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_instagram_service_search_and_generate():
    service = InstagramReferralService()
    search_res = service.search_profiles(InstagramSearchRequest(company="Stripe", founder_only=False))
    assert search_res.total_found >= 2
    assert len(search_res.profiles) >= 2

    # Generate DM
    msg_res = service.generate_message(InstagramMessageRequest(
        action_type="dm",
        target_username="patrickcollison",
        company="Stripe",
        name="Patrick Collison",
        role_title="Staff Distributed Systems Engineer",
        portfolio_link="https://kushall.in",
    ))
    assert msg_res.status == "success"
    assert "patrickcollison" in msg_res.intent_url
    assert "Stripe" in msg_res.message
    assert msg_res.character_count > 20


def test_instagram_api_endpoints(client):
    # 1. POST /api/instagram/search
    res_search = client.post("/api/instagram/search", json={
        "company": "OpenAI",
        "founder_only": False,
    })
    assert res_search.status_code == 200
    assert res_search.json()["total_found"] >= 1

    # 2. POST /api/instagram/generate-message
    res_msg = client.post("/api/instagram/generate-message", json={
        "action_type": "story_reply",
        "target_username": "sama",
        "company": "OpenAI",
        "name": "Sam Altman",
        "role_title": "AI Infrastructure Lead",
        "portfolio_link": "https://github.com/kushallj",
    })
    assert res_msg.status_code == 200
    data = res_msg.json()
    assert data["status"] == "success"
    assert "ig.me" in data["intent_url"]
