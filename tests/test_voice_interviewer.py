import pytest
from fastapi.testclient import TestClient
from main import app
from src.voice_interviewer.analyzer import VoiceInterviewAnalyzer


@pytest.fixture
def client():
    return TestClient(app)


def test_voice_interviewer_clean_star_delivery():
    analyzer = VoiceInterviewAnalyzer()
    transcript = (
        "In my previous role at company, we were facing major database bottlenecks during peak traffic. "
        "My goal was to reduce p99 latency without increasing infrastructure costs. "
        "I designed and implemented an asynchronous Redis write-back caching layer in Python. "
        "As a result, we reduced p99 latency by 45% and scaled to 50,000 queries per second."
    )
    res = analyzer.analyze_spoken_response(
        transcript=transcript,
        duration_seconds=22.0,
        target_focus="Distributed Systems",
    )
    assert res.speech_delivery_score >= 80.0
    assert res.filler_stats.total_fillers == 0
    assert res.cadence_stats.wpm >= 120.0
    assert res.star_eval.overall_star_score >= 85.0


def test_voice_interviewer_fillers_and_fast_pace():
    analyzer = VoiceInterviewAnalyzer()
    transcript = (
        "Um, like, basically in my project, you know, we had to, like, fix the code. "
        "So yeah, I literally changed some configs, um, and like it was working."
    )
    res = analyzer.analyze_spoken_response(
        transcript=transcript,
        duration_seconds=6.0,
        target_focus="General Engineering",
    )
    assert res.filler_stats.total_fillers >= 4
    assert res.filler_stats.filler_percentage > 10.0
    assert len(res.delivery_tips) > 0


def test_voice_feedback_api_endpoint(client):
    res = client.post("/api/interview/voice-feedback", json={
        "transcript": "When I was at Stripe, my task was to scale the ledger. I built an event-driven queue, resulting in 99.99% uptime.",
        "duration_seconds": 15.0,
        "target_focus": "System Design",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "speech_delivery_score" in data
    assert "filler_stats" in data
    assert "cadence_stats" in data
    assert "star_eval" in data
