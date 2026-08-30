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
        candidate_name="Alex Mercer",
        candidate_email="alex@mercer.dev",
        role_title="Staff Backend Engineer",
        company="Stripe",
        job_description="Scale low latency distributed payments ledger in Python, FastAPI, and Redis.",
    )
    res = generator.generate_ats_resume(req)
    assert res.status == "success"
    assert res.document_type == "ats_resume"
    assert "Alex Mercer" in res.html_content
    assert "Stripe" in res.html_content
    assert "FastAPI" in res.html_content
    assert len(res.suggested_keywords) > 0


def test_cover_letter_generator():
    generator = ATSResumeGenerator()
    req = CoverLetterGenerateRequest(
        candidate_name="Alex Mercer",
        candidate_email="alex@mercer.dev",
        role_title="Staff Backend Engineer",
        company="OpenAI",
    )
    res = generator.generate_cover_letter(req)
    assert res.status == "success"
    assert "OpenAI" in res.html_content
    assert "Alex Mercer" in res.html_content


def test_resume_api_endpoints(client):
    # 1. POST /api/resume/generate-ats
    res = client.post("/api/resume/generate-ats", json={
        "candidate_name": "Sarah Connor",
        "role_title": "Principal Systems Engineer",
        "company": "Figma",
        "job_description": "Distributed WebSockets, low latency collaboration, Redis caching.",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Sarah Connor" in data["html_content"]

    # 2. POST /api/resume/generate-cover-letter
    res_cl = client.post("/api/resume/generate-cover-letter", json={
        "candidate_name": "Sarah Connor",
        "role_title": "Principal Systems Engineer",
        "company": "Figma",
    })
    assert res_cl.status_code == 200
    assert "Figma" in res_cl.json()["html_content"]
