"""
test_sprint2_cadence.py — Unit & Integration tests for Sprint 2:
Live Voice Biomarker & Cadence Telemetry HUD & Executive Delivery Scorecard.
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from src.services.cadence_coach_service import CadenceCoachService

client = TestClient(app)


def test_cadence_golden_range():
    service = CadenceCoachService()
    # ~130 words in 60 seconds = 130 WPM
    transcript = " ".join(["word"] * 130)
    res = service.analyze_cadence(transcript, duration_seconds=60.0)

    assert res["status"] == "success"
    assert res["wpm"] == 130.0
    assert res["cadence_status"] == "Golden Executive Range"
    assert res["cadence_color"] == "#00FFA3"
    assert "Perfect pacing" in res["pacing_advice"]
    assert res["total_fillers_detected"] == 0
    assert res["clarity_score"] == 100.0
    assert not res["is_ramble_warning"]


def test_cadence_slow_and_fast():
    service = CadenceCoachService()
    
    # Slow: 40 words in 60 seconds = 40 WPM
    slow_res = service.analyze_cadence(" ".join(["slow"] * 40), duration_seconds=60.0)
    assert slow_res["cadence_status"] == "Too Slow / Hesitant"
    assert slow_res["cadence_color"] == "#00F0FF"

    # Fast: 190 words in 60 seconds = 190 WPM
    fast_res = service.analyze_cadence(" ".join(["fast"] * 190), duration_seconds=60.0)
    assert fast_res["cadence_status"] == "Panic Speed / Rushing"
    assert fast_res["cadence_color"] == "#FF0055"


def test_filler_word_detection():
    service = CadenceCoachService()
    transcript = "Basically, like, um, we actually built this sort of pipeline, you know?"
    res = service.analyze_cadence(transcript, duration_seconds=30.0)

    assert res["total_fillers_detected"] >= 5
    assert "basically" in res["filler_breakdown"]
    assert "like" in res["filler_breakdown"]
    assert "um" in res["filler_breakdown"]
    assert "actually" in res["filler_breakdown"]
    assert "you know" in res["filler_breakdown"]
    assert res["clarity_score"] < 100.0


def test_ramble_guard_threshold():
    service = CadenceCoachService()
    text = "We built a microservice architecture with Redis and Kafka."

    # Under threshold (45 seconds)
    normal = service.analyze_cadence(text, duration_seconds=45.0)
    assert not normal["is_ramble_warning"]
    assert normal["ramble_check_in_cue"] is None

    # Warning threshold (72 seconds)
    ramble = service.analyze_cadence(text, duration_seconds=72.0)
    assert ramble["is_ramble_warning"]
    assert ramble["ramble_check_in_cue"] is not None
    assert "Wrap up your point" in ramble["ramble_check_in_cue"]


def test_executive_scorecard_generation():
    service = CadenceCoachService()
    transcripts = [
        "In my last role, the situation was our distributed ledger was bottlenecked.",
        "The task was redesigning the transactional consistency pipeline.",
        "For my action, I designed and implemented an asynchronous Redis lock with Kafka event streaming.",
        "As a result, latency dropped by 64% and saved 20 LPA in cloud computing costs.",
    ]
    scorecard = service.generate_scorecard(
        session_id="test_sess_001",
        total_duration_seconds=50.0,
        transcripts=transcripts,
    )

    assert scorecard["status"] == "success"
    assert scorecard["session_id"] == "test_sess_001"
    assert scorecard["overall_executive_score"] >= 75
    assert scorecard["star_framework_adherence"]["situation_detected"]
    assert scorecard["star_framework_adherence"]["task_detected"]
    assert scorecard["star_framework_adherence"]["action_detected"]
    assert scorecard["star_framework_adherence"]["result_metrics_detected"]
    assert scorecard["star_framework_adherence"]["score"] == 100.0


def test_fastapi_analyze_cadence_endpoint():
    payload = {
        "transcript": "I refactored the Postgres connection pool reducing contention.",
        "duration_seconds": 4.0,
        "is_continuous_monologue": True,
    }
    response = client.post("/api/sidekick/cadence/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "wpm" in data
    assert "cadence_status" in data
    assert "clarity_score" in data


def test_fastapi_scorecard_endpoint():
    payload = {
        "session_id": "api_test_session",
        "total_duration_seconds": 60.0,
        "transcripts": [
            "In my last role the situation was high latency.",
            "My action was designing Redis cache.",
            "As a result throughput increased by 40 percent.",
        ],
    }
    response = client.post("/api/sidekick/cadence/scorecard", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["session_id"] == "api_test_session"
    assert "overall_executive_score" in data
    assert "star_framework_adherence" in data
