import pytest
from fastapi.testclient import TestClient
from main import app
from src.ghost_hunter.detector import GhostJobDetector


@pytest.fixture
def client():
    return TestClient(app)


def test_ghost_job_detector_fresh_job():
    detector = GhostJobDetector()
    res = detector.analyze_job(
        title="Senior Python Backend Engineer",
        company="Stripe",
        description="Newly opened role for our core payments platform. Fast-track interview process for urgent start. Extensive distributed systems architecture in Python and FastAPI.",
        posted_date="1 day ago",
        has_decision_maker=True,
    )
    assert res.ghost_score < 35.0
    assert res.urgency_label == "Active Hiring ⚡"
    assert res.is_ghost_risk is False
    assert any(s.name == "fresh_posting" for s in res.signals)


def test_ghost_job_detector_stale_ghost():
    detector = GhostJobDetector()
    res = detector.analyze_job(
        title="Software Engineer - Talent Pool",
        company="GenericCorp",
        description="We are always looking for talent. Join our talent pool for future opportunities and continuous hiring consideration.",
        posted_date="90+ days ago",
        has_decision_maker=False,
    )
    assert res.ghost_score >= 60.0
    assert res.urgency_label == "High Ghost Risk 👻"
    assert res.is_ghost_risk is True
    assert any(s.name == "stale_age" or s.name == "ghost_phrase_matched" for s in res.signals)


def test_ghost_hunter_api_endpoints(client):
    # 1. POST /api/ghost-hunter/analyze
    res = client.post("/api/ghost-hunter/analyze", json={
        "title": "Staff Backend Engineer",
        "company": "OpenAI",
        "description": "Urgent requirement for scaling inference engine. Newly funded initiative.",
        "posted_date": "2 days ago",
        "has_decision_maker": True,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["ghost_score"] < 40.0
    assert "signals" in data

    # 2. GET /api/jobs/{id}/ghost-score
    # Grab an existing job ID
    jobs_res = client.get("/api/jobs?limit=1")
    if jobs_res.json().get("jobs"):
        j_id = jobs_res.json()["jobs"][0]["id"]
        res_g = client.get(f"/api/jobs/{j_id}/ghost-score")
        assert res_g.status_code == 200
        assert res_g.json()["ghost_score"] >= 0
