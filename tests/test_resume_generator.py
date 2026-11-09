import pytest
from fastapi.testclient import TestClient
from main import app
from src.resume_generator.models import ResumeGenerateRequest, CoverLetterGenerateRequest
from src.resume_generator.generator import ATSResumeGenerator


@pytest.fixture
def client():
    return TestClient(app)


def test_ats_resume_generator():
    generator = ATSResumeGenerator()
    req = ResumeGenerateRequest(
        candidate_name="Candidate Example",
        candidate_email="candidate@example.com",
        role_title="Staff Backend Engineer",
        company="Example Company",
        job_description="Scale low latency distributed payments ledger in Python, FastAPI, and Redis.",
        custom_bullets=["Built an example API using FastAPI."],
    )
    res = generator.generate_ats_resume(req)
    assert res.status == "success"
    assert res.document_type == "ats_resume"
    assert "Candidate Example" in res.html_content
    assert "Example Company" in res.html_content
    assert "FastAPI" in res.html_content
    assert len(res.suggested_keywords) > 0
    assert "50,000" not in res.html_content
    assert "99.99%" not in res.html_content


def test_cover_letter_generator():
    generator = ATSResumeGenerator()
    req = CoverLetterGenerateRequest(
        candidate_name="Candidate Example",
        candidate_email="candidate@example.com",
        role_title="Staff Backend Engineer",
        company="Example Company",
    )
    res = generator.generate_cover_letter(req)
    assert res.status == "success"
    assert "Example Company" in res.html_content
    assert "Candidate Example" in res.html_content
    assert "50,000" not in res.html_content


def test_resume_api_endpoints(client):
    # 1. POST /api/resume/generate-ats
    res = client.post("/api/resume/generate-ats", json={
        "candidate_name": "Candidate Example",
        "role_title": "Principal Systems Engineer",
        "company": "Example Company",
        "job_description": "Distributed WebSockets, low latency collaboration, Redis caching.",
        "custom_bullets": ["Built an example collaboration service."],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Candidate Example" in data["html_content"]
    assert "50,000" not in data["html_content"]

    # 2. POST /api/resume/generate-cover-letter
    res_cl = client.post("/api/resume/generate-cover-letter", json={
        "candidate_name": "Candidate Example",
        "role_title": "Principal Systems Engineer",
        "company": "Example Company",
    })
    assert res_cl.status_code == 200
    assert "Example Company" in res_cl.json()["html_content"]
    assert "50,000" not in res_cl.json()["html_content"]
