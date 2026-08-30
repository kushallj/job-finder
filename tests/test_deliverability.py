import pytest
from fastapi.testclient import TestClient
from main import app
from src.deliverability.analyzer import DeliverabilityAnalyzer


@pytest.fixture
def client():
    return TestClient(app)


def test_deliverability_clean_executive_draft():
    analyzer = DeliverabilityAnalyzer()
    res = analyzer.analyze_draft(
        subject="Scaling distributed payments at Stripe",
        body=(
            "Hi David,\n\n"
            "I noticed your team is scaling the core payments ledger. In my previous role, "
            "I helped scale our high-throughput Redis and FastAPI microservices to handle 45,000 requests/sec "
            "with sub-15ms latency.\n\n"
            "Would you be open to a brief 10-minute intro chat sometime next week?\n\n"
            "Best,\nCandidate"
        )
    )
    assert res.spam_score < 25.0
    assert res.deliverability_tier == "Primary Inbox 🛡️"
    assert res.is_safe is True
    assert len(res.spam_matches) == 0
    assert res.reading_time_seconds <= 30


def test_deliverability_spammy_draft():
    analyzer = DeliverabilityAnalyzer()
    res = analyzer.analyze_draft(
        subject="URGENT: 100% FREE GUARANTEE MAKE MONEY NOW!!!",
        body=(
            "ACT NOW! CLICK HERE to see why I am a ROCKSTAR 10x engineer! "
            "I guarantee 100% free results. Call me now immediately asap! "
            "https://link1.com https://link2.com https://link3.com https://link4.com"
        )
    )
    assert res.spam_score >= 60.0
    assert res.deliverability_tier == "Spam Folder 🚨"
    assert res.is_safe is False
    assert len(res.spam_matches) >= 3


def test_deliverability_api_endpoint(client):
    res = client.post("/api/deliverability/analyze-draft", json={
        "subject": "Quick question regarding platform architecture",
        "body": "Hi Sarah, loved your recent talk on distributed event streaming with Kafka. Would love to share some metrics from our recent migration."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["is_safe"] is True
    assert "flesch_kincaid_grade" in data
