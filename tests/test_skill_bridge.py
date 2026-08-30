import pytest
from fastapi.testclient import TestClient
from main import app
from src.skill_bridge.service import SkillBridgeService
from src.skill_bridge.models import ProjectGenerateRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_skill_bridge_service_generate():
    service = SkillBridgeService()
    req = ProjectGenerateRequest(
        company="Figma",
        role_title="Senior Real-Time Backend Engineer",
        job_description="Looking for engineers experienced with Redis, concurrency, WebSockets, and low-latency APIs.",
        candidate_skills=["Python", "FastAPI", "SQL"],
    )
    result = service.generate_project(req)
    assert result.company == "Figma"
    assert result.gap_analysis.match_percentage >= 50.0
    assert len(result.project_spec.starter_code_files) >= 3
    assert "main.py" in result.project_spec.starter_code_files
    assert "README.md" in result.project_spec.starter_code_files
    assert "Figma" in result.project_spec.demonstration_prompt


def test_skill_bridge_api_endpoints(client):
    res = client.post("/api/skill-bridge/generate-project", json={
        "company": "Stripe",
        "role_title": "Staff Payment Engineer",
        "job_description": "We build idempotent payment pipelines with Redis, Kafka, and distributed consistency.",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "project_spec" in data
    assert "gap_analysis" in data
    assert len(data["project_spec"]["starter_code_files"]) >= 3
