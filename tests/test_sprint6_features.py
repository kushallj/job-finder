"""
test_sprint6_features.py — Unit & Integration tests for Sprint 6:
1. Feature 11: System Design Whiteboard Co-Pilot (Agent 24)
2. Feature 12: Autonomous Executive Outbound Pitch Engine (Agent 25)
3. Feature 13: Live Architecture Interactive Sandbox Simulator (Agent 26)
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from src.services.system_design_whiteboard import SystemDesignWhiteboardService
from src.agents.agent_24_system_design_whiteboard import SystemDesignWhiteboardAgent
from src.services.executive_outreach_service import ExecutiveOutreachService
from src.agents.agent_25_executive_outreach import ExecutiveOutreachAgent
from src.services.sandbox_simulation_service import SandboxSimulationService
from src.agents.agent_26_sandbox_simulation import SandboxSimulationAgent

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# 1. System Design Whiteboard Co-Pilot (Agent 24) Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_system_design_archetypes_directory():
    service = SystemDesignWhiteboardService()
    archetypes = service.get_archetypes()
    assert len(archetypes) >= 4
    ids = [a["archetype_id"] for a in archetypes]
    assert "realtime_trading_engine" in ids
    assert "ride_hailing_platform" in ids
    assert "video_streaming_platform" in ids
    assert "distributed_rate_limiter" in ids


def test_system_design_capacity_and_diagram_generation():
    service = SystemDesignWhiteboardService()
    res = service.estimate_and_diagram(
        archetype_id="realtime_trading_engine",
        dau=10000000,
        actions_per_day=20,
        payload_bytes=1024,
    )
    assert res["status"] == "success"
    assert res["title"] == "Design a Low-Latency High-Frequency Trading & Order-Matching Engine"
    cap = res["capacity_estimates"]
    assert cap["total_requests_per_day"] == 200000000
    assert cap["avg_qps"] > 2000
    assert cap["peak_qps"] > cap["avg_qps"]
    assert cap["daily_storage_gb"] > 150
    assert cap["annual_storage_tb"] > 50
    assert cap["ram_cache_required_gb"] > 30

    assert "graph TD" in res["mermaid_diagram"]
    assert "L4/L7 HAProxy / Envoy" in res["mermaid_diagram"]
    assert len(res["failure_matrix"]) == 4
    assert any("Cache Stampede" in fm["failure_mode"] for fm in res["failure_matrix"])
    assert any("Split-Brain" in fm["failure_mode"] for fm in res["failure_matrix"])


def test_agent_24_system_design_whiteboard_execution():
    agent = SystemDesignWhiteboardAgent()
    result = agent.run(
        archetype_id="ride_hailing_platform",
        dau=25000000,
    )
    assert result.ok is True
    assert result.agent == "system_design_whiteboard"
    assert "System Design Blueprint" in result.summary
    assert "capacity_estimates" in result.data
    assert "mermaid_diagram" in result.data


# ═══════════════════════════════════════════════════════════════════════════
# 2. Autonomous Executive Outbound Pitch Engine (Agent 25) Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_executive_pain_points_directory():
    service = ExecutiveOutreachService()
    pain_points = service.get_pain_points()
    assert len(pain_points) >= 3
    ids = [p["pain_id"] for p in pain_points]
    assert "p99_latency_bottleneck" in ids
    assert "cloud_cost_overrun" in ids
    assert "kafka_lag_backpressure" in ids


def test_executive_campaign_generation():
    service = ExecutiveOutreachService()
    res = service.generate_campaign(
        candidate_name="Ujjwal",
        target_company="Databricks",
        executive_name="David",
        executive_title="VP of Core Infrastructure",
        pain_point_id="p99_latency_bottleneck",
        custom_proof_of_work_url="https://github.com/ujjwal-sovereign/distributed-idempotency",
    )
    assert res["status"] == "success"
    assert res["candidate_name"] == "Ujjwal"
    assert res["target_company"] == "Databricks"
    assert len(res["campaign_stages"]) == 3

    # Verify Stage 1
    assert "David" in res["campaign_stages"][0]["body"]
    assert "https://github.com/ujjwal-sovereign/distributed-idempotency" in res["campaign_stages"][0]["body"]
    assert "Architecture note regarding" in res["campaign_stages"][0]["subject"]

    # Verify Stage 2
    assert "50,000 concurrent" in res["campaign_stages"][1]["body"]

    # Verify Stage 3
    assert "15-minute" in res["campaign_stages"][2]["body"]
    assert "Closing the loop" in res["campaign_stages"][2]["subject"]


def test_agent_25_executive_outreach_execution():
    agent = ExecutiveOutreachAgent()
    result = agent.run(
        candidate_name="Ujjwal",
        target_company="Stripe",
        executive_name="Patrick",
        executive_title="Head of Engineering",
        pain_point_id="cloud_cost_overrun",
    )
    assert result.ok is True
    assert result.agent == "executive_outreach"
    assert "Synthesized 3-Stage Executive Drip Campaign" in result.summary
    assert "campaign_stages" in result.data


# ═══════════════════════════════════════════════════════════════════════════
# 3. Live Sandbox Simulator (Agent 26) Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_sandbox_models_directory():
    service = SandboxSimulationService()
    models = service.get_models()
    assert len(models) >= 3
    ids = [m["model_id"] for m in models]
    assert "distributed_cache_eviction" in ids
    assert "raft_consensus_partition" in ids
    assert "token_bucket_rate_limiter" in ids


def test_sandbox_cache_simulation():
    service = SandboxSimulationService()
    res = service.run_simulation(
        model_id="distributed_cache_eviction",
        concurrency_rps=35000,
        failure_injection=True,
    )
    assert res["status"] == "success"
    assert res["metrics"]["concurrency_rps"] == 35000
    assert res["metrics"]["p99_latency_ms"] > 0
    assert len(res["telemetry_timeline"]) >= 4
    assert any("Singleflight mutex" in evt["event"] for evt in res["telemetry_timeline"])


def test_sandbox_raft_partition_simulation():
    service = SandboxSimulationService()
    res = service.run_simulation(
        model_id="raft_consensus_partition",
        concurrency_rps=5000,
        failure_injection=True,
    )
    assert res["status"] == "success"
    assert len(res["telemetry_timeline"]) >= 4
    assert any("Quorum" in evt["event"] for evt in res["telemetry_timeline"])


def test_agent_26_sandbox_simulation_execution():
    agent = SandboxSimulationAgent()
    result = agent.run(
        model_id="token_bucket_rate_limiter",
        concurrency_rps=20000,
        failure_injection=True,
    )
    assert result.ok is True
    assert result.agent == "sandbox_simulation"
    assert "Executed Simulation" in result.summary
    assert "metrics" in result.data
    assert "telemetry_timeline" in result.data


# ═══════════════════════════════════════════════════════════════════════════
# 4. FastAPI REST Endpoints Integration Tests
# ═══════════════════════════════════════════════════════════════════════════

def test_api_system_design_archetypes():
    response = client.get("/api/system-design/archetypes")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["archetypes"]) >= 4


def test_api_system_design_estimate_and_diagram():
    payload = {
        "archetype_id": "realtime_trading_engine",
        "daily_active_users": 8000000,
        "avg_actions_per_user_day": 25,
        "payload_size_bytes": 1024,
    }
    response = client.post("/api/system-design/estimate-and-diagram", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "capacity_estimates" in data
    assert "mermaid_diagram" in data
    assert data["capacity_estimates"]["peak_qps"] > 0


def test_api_executive_outreach_pain_points():
    response = client.get("/api/executive-outreach/pain-points")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["pain_points"]) >= 3


def test_api_executive_outreach_campaign():
    payload = {
        "candidate_name": "Ujjwal",
        "target_company": "Databricks",
        "executive_name": "David",
        "executive_title": "VP Engineering",
        "pain_point_id": "p99_latency_bottleneck",
    }
    response = client.post("/api/executive-outreach/campaign", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["campaign_stages"]) == 3


def test_api_sandbox_models():
    response = client.get("/api/sandbox/models")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["models"]) >= 3


def test_api_sandbox_simulate():
    payload = {
        "model_id": "distributed_cache_eviction",
        "concurrency_rps": 30000,
        "failure_injection_enabled": True,
    }
    response = client.post("/api/sandbox/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "metrics" in data
    assert "telemetry_timeline" in data
