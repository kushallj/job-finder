import pytest
from fastapi.testclient import TestClient
from main import app
from src.hiregram.service import HiregramService
from src.hiregram.models import InterviewerPersona


@pytest.fixture
def client():
    return TestClient(app)


def test_hiregram_service_lifecycle():
    service = HiregramService()
    init = service.start_session(
        company="Stripe",
        role_title="Senior Infrastructure Engineer",
        persona=InterviewerPersona.ARCHITECT_ALEX,
        total_questions_target=3,
    )
    s_id = init["session_id"]
    assert init["company"] == "Stripe"
    assert "current_turn" in init
    assert init["current_turn"]["turn_index"] == 1
    assert "Alex Mercer" in init["current_turn"]["interviewer_persona"]

    # Submit turn 1
    t1 = service.submit_turn(
        session_id=s_id,
        answer_text="When I was at my previous company, we were facing tail latency spikes on our payment API. My responsibility was to eliminate deadlocks. I architected a distributed lock manager using Redis Cluster and implemented exponential backoff. As a result, latency dropped by 45% and throughput increased by 3x.",
        duration_seconds=45.0,
    )
    assert t1["session_id"] == s_id
    assert t1["evaluated_turn"]["wpm"] > 50.0
    assert t1["evaluated_turn"]["turn_score"] >= 65.0
    assert len(t1["evaluated_turn"]["gold_standard_ideal_answer"]) > 20
    assert t1["next_turn"] is not None
    assert t1["is_finished"] is False

    # Finalize
    scorecard = service.finalize_session(s_id)
    assert scorecard.session_id == s_id
    assert scorecard.overall_score >= 60.0
    assert len(scorecard.key_strengths) >= 2
    assert len(scorecard.practice_drills_recommended) >= 2


def test_hiregram_api_endpoints(client):
    # 1. Start Session
    res_start = client.post("/api/hiregram/start-session", json={
        "company": "OpenAI",
        "role_title": "Research Infrastructure Engineer",
        "persona": "bar_raiser_marcus",
        "total_questions_target": 2,
    })
    assert res_start.status_code == 200
    start_data = res_start.json()
    assert start_data["status"] == "success"
    session_id = start_data["session_id"]
    assert start_data["persona"] == "bar_raiser_marcus"

    # 2. Submit Turn
    res_turn = client.post("/api/hiregram/submit-turn", json={
        "session_id": session_id,
        "answer_text": "In my previous role, I noticed our training checkpoint store had significant I/O contention. My goal was to eliminate GPU idle time. I refactored the checkpoint pipeline to use asynchronous chunked uploads. As a result, GPU idle time was reduced by 80%.",
        "duration_seconds": 35.0,
    })
    assert res_turn.status_code == 200
    turn_data = res_turn.json()
    assert turn_data["status"] == "success"
    assert "evaluated_turn" in turn_data

    # 3. Finalize Session
    res_final = client.post(f"/api/hiregram/finalize-session?session_id={session_id}")
    assert res_final.status_code == 200
    final_data = res_final.json()
    assert final_data["status"] == "success"
    assert "scorecard" in final_data
    assert final_data["scorecard"]["company"] == "OpenAI"

    # 4. Get Scorecard
    res_get = client.get(f"/api/hiregram/sessions/{session_id}")
    assert res_get.status_code == 200
    assert res_get.json()["scorecard"]["session_id"] == session_id
