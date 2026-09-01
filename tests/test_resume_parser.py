import pytest
import httpx
from src.resume_parser import SharpAPIResumeParser, ApyHubResumeParserClient


def test_sharpapi_parser_initialization():
    parser = SharpAPIResumeParser(token="test_token_123")
    assert parser.enabled is True
    assert parser.token == "test_token_123"


def test_sharpapi_parser_normalizes_parsed_profile():
    parser = SharpAPIResumeParser(token="mock_token")
    raw_payload = {
        "candidate_name": "Kushall Jain",
        "candidate_email": "kushall.jain07@gmail.com",
        "candidate_phone": "9990079764",
        "candidate_city": "Delhi",
        "candidate_country": "India",
        "candidate_spoken_languages": ["English", "Hindi"],
        "positions": [
            {
                "position_name": "Software Engineer",
                "company_name": "Tech Corp",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"]
            },
            {
                "position_name": "Frontend Developer",
                "company_name": "Web Solutions",
                "skills": ["React", "TypeScript", "TailwindCSS"]
            }
        ],
        "education": [
            {
                "degree": "B.Tech Computer Science",
                "school_name": "University Institute of Technology"
            }
        ],
        "skills": ["Git", "CI/CD"]
    }
    normalized = parser._normalize_parsed_resume(raw_payload, job_id="test_job_99")
    assert normalized["status"] == "success"
    assert normalized["candidate"]["name"] == "Kushall Jain"
    assert normalized["candidate"]["email"] == "kushall.jain07@gmail.com"
    assert normalized["candidate"]["city"] == "Delhi"
    assert "Python" in normalized["skills"]
    assert "React" in normalized["skills"]
    assert "Git" in normalized["skills"]
    assert len(normalized["positions"]) == 2
    assert len(normalized["education"]) == 1


@pytest.mark.asyncio
async def test_sharpapi_parser_builds_documented_request_and_polls():
    mock_job_id = "test-job-uuid-12345"
    seen_calls = []

    async def mock_handler(request: httpx.Request):
        seen_calls.append((request.method, str(request.url), request.headers.get("apy-token")))
        if request.method == "POST" and "sharpapi/parse-resume" in str(request.url):
            return httpx.Response(202, json={"status_url": f"https://apyhub.com/.../{mock_job_id}", "job_id": mock_job_id})
        if request.method == "GET" and f"status/{mock_job_id}" in str(request.url):
            return httpx.Response(200, json={
                "data": {
                    "type": "api_job_result",
                    "id": mock_job_id,
                    "attributes": {
                        "status": "success",
                        "type": "hr_parse_resume",
                        "result": {
                            "candidate_name": "Kushall Jain",
                            "candidate_email": "kushall@example.com",
                            "positions": [
                                {"company_name": "Acme", "skills": ["Python", "AsyncIO"]}
                            ]
                        }
                    }
                }
            })
        return httpx.Response(404)

    client = SharpAPIResumeParser(token="secret_apy_token", transport=httpx.MockTransport(mock_handler))
    dummy_pdf = b"%PDF-1.4 mock resume content"
    result = await client.parse_resume_bytes(dummy_pdf, filename="resume.pdf", poll_interval=0.01)

    assert result["status"] == "success"
    assert result["candidate"]["name"] == "Kushall Jain"
    assert result["skills"] == ["Python", "AsyncIO"]
    assert len(seen_calls) == 2
    assert seen_calls[0][0] == "POST"
    assert seen_calls[0][2] == "secret_apy_token"
    assert seen_calls[1][0] == "GET"
    assert mock_job_id in seen_calls[1][1]


@pytest.mark.asyncio
async def test_sharpapi_evaluate_resume_calculates_fit_score():
    mock_job_id = "eval-job-456"

    async def mock_handler(request: httpx.Request):
        if request.method == "POST":
            return httpx.Response(202, json={"job_id": mock_job_id})
        return httpx.Response(200, json={
            "data": {
                "attributes": {
                    "status": "success",
                    "result": {
                        "candidate_name": "Kushall Jain",
                        "positions": [
                            {"skills": ["Python", "FastAPI", "PostgreSQL", "React"]}
                        ]
                    }
                }
            }
        })

    client = SharpAPIResumeParser(token="token", transport=httpx.MockTransport(mock_handler))
    evaluation = await client.evaluate_resume(
        b"%PDF-1.4 content",
        job_description="Looking for Senior Python and FastAPI Engineer with React expertise",
        job_title="Senior Python Backend Engineer"
    )

    assert evaluation["evaluation_status"] == "completed"
    assert evaluation["match_score"] >= 75.0
    assert "Python" in evaluation["matched_skills"]
    assert "FastAPI" in evaluation["matched_skills"]
    assert "React" in evaluation["matched_skills"]
