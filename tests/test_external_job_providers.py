import pytest
import httpx

from src.job_data_providers import JobDataAPIClient, AIDevBoardClient, normalize_job


def test_normalize_job_preserves_provider_intelligence():
    row = normalize_job({
        "id": 123,
        "ext_id": "abc",
        "title": "Senior Backend Engineer",
        "company": {"name": "Acme", "website": "https://acme.example"},
        "location": "Bengaluru",
        "application_url": "https://jobs.example/apply",
        "published": "2026-08-29T10:00:00Z",
        "salary_min": 1800000,
        "salary_max": 2600000,
        "salary_currency": "INR",
        "has_remote": True,
        "experience_level": "SE",
        "tags": [{"name": "Backend"}, "Python"],
    }, "jobdataapi")
    assert row["job_id"] == "jobdataapi:abc"
    assert row["company"] == "Acme"
    assert row["salary_min"] == 1800000
    assert row["has_remote"] is True
    assert row["tags"] == ["Backend", "Python"]


@pytest.mark.asyncio
async def test_jobdata_client_builds_documented_request():
    seen = {}
    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"results": [{"id": 1, "title": "Python Engineer", "company": {"name": "Acme"}}]})
    client = JobDataAPIClient(api_key="secret", transport=httpx.MockTransport(handler))
    rows = await client.search(query="Python Engineer", location="India", max_age=14, page_size=5)
    assert len(rows) == 1
    assert "Python" in seen["url"] and "Engineer" in seen["url"]
    assert "location=India" in seen["url"]
    assert "max_age=14" in seen["url"]
    assert seen["auth"] == "Api-Key secret"


@pytest.mark.asyncio
async def test_aidevboard_match_uses_candidate_profile():
    seen = {}
    async def handler(request: httpx.Request):
        seen["json"] = request.content.decode()
        return httpx.Response(200, json={"matches": [], "total": 0})
    client = AIDevBoardClient(api_key="aidv", transport=httpx.MockTransport(handler))
    result = await client.match(skills=["python", "fastapi"], salary_min=120000, workplace="remote", level="senior")
    assert result["total"] == 0
    import json
    parsed = json.loads(seen["json"])
    assert parsed["skills"] == ["python", "fastapi"]
    assert parsed["workplace"] == "remote"


def test_normalize_job_handles_fantastic_jobs_schema():
    from src.job_data_providers import FantasticJobsClient
    row = normalize_job({
        "id": 987654,
        "title": "Lead AI Platform Engineer",
        "organization": "OpenPlatform AI",
        "organization_url": "https://openplatform.ai",
        "locations_derived": ["San Francisco, CA", "Remote"],
        "url": "https://jobs.ashbyhq.com/openplatform/123",
        "date_created": "2026-08-30T12:00:00Z",
        "remote_derived": True,
        "salary_min": 190000,
        "salary_max": 250000,
        "salary_currency": "USD",
        "tags": ["AI", "Infrastructure", "Ashby"],
    }, "fantastic_jobs")
    assert row["job_id"] == "fantastic_jobs:987654"
    assert row["company"] == "OpenPlatform AI"
    assert row["company_website"] == "https://openplatform.ai"
    assert "San Francisco, CA" in row["location"]
    assert row["has_remote"] is True
    assert row["salary_min"] == 190000


@pytest.mark.asyncio
async def test_fantastic_jobs_client_builds_documented_request():
    from src.job_data_providers import FantasticJobsClient
    seen = {}
    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json=[
            {
                "id": 101,
                "title": "Senior Distributed Systems Engineer",
                "organization": "FastScale",
                "locations_derived": ["New York, NY"],
                "url": "https://boards.greenhouse.io/fastscale/jobs/101",
            }
        ])

    client = FantasticJobsClient(api_key="test_fantastic_key_xyz", transport=httpx.MockTransport(handler))
    rows = await client.search_ats(query="Distributed Systems", location="New York", time_frame="24h", limit=10)
    assert len(rows) == 1
    assert "data.fantastic.jobs/v1/active-ats" in seen["url"]
    assert "time_frame=24h" in seen["url"]
    assert "title=Distributed+Systems" in seen["url"] or "title=Distributed%20Systems" in seen["url"]
    assert seen["auth"] == "Bearer test_fantastic_key_xyz"
    assert rows[0]["company"] == "FastScale"
    assert rows[0]["job_id"] == "fantastic_jobs:101"


def test_normalize_job_handles_arbeitnow_schema():
    row = normalize_job({
        "slug": "senior-python-engineer-berlin-12345",
        "company_name": "TechCorp Berlin",
        "title": "Senior Python Backend Engineer (f/m/d)",
        "description": "<p>Build scalable services with Python and FastAPI.</p>",
        "remote": True,
        "url": "https://www.arbeitnow.com/jobs/companies/techcorp/senior-python-engineer-berlin-12345",
        "tags": ["Python", "FastAPI", "PostgreSQL"],
        "job_types": ["Full-time", "Permanent"],
        "location": "Berlin, Germany",
        "created_at": 1788228317,
    }, "arbeitnow")
    assert row["job_id"] == "arbeitnow:senior-python-engineer-berlin-12345"
    assert row["company"] == "TechCorp Berlin"
    assert row["title"] == "Senior Python Backend Engineer (f/m/d)"
    assert row["location"] == "Berlin, Germany"
    assert row["has_remote"] is True
    assert row["work_mode"] == "remote"
    assert "Python" in row["tags"]
    assert "Full-time" in row["tags"]
    assert row["posted_date"] is not None


@pytest.mark.asyncio
async def test_arbeitnow_client_fetches_and_filters_jobs():
    from src.job_data_providers import ArbeitnowClient
    seen = {}
    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={
            "data": [
                {
                    "slug": "lead-backend-developer-berlin-99",
                    "company_name": "Alpha Labs",
                    "title": "Lead Backend Developer",
                    "description": "Python, Django, AWS in Berlin",
                    "remote": False,
                    "url": "https://www.arbeitnow.com/jobs/99",
                    "tags": ["Backend"],
                    "job_types": ["Full-time"],
                    "location": "Berlin",
                    "created_at": 1788228317,
                },
                {
                    "slug": "junior-sales-manager-frankfurt-100",
                    "company_name": "Sales Corp",
                    "title": "Junior Sales Manager",
                    "description": "B2B Sales",
                    "remote": False,
                    "url": "https://www.arbeitnow.com/jobs/100",
                    "tags": ["Sales"],
                    "job_types": ["Full-time"],
                    "location": "Frankfurt",
                    "created_at": 1788228317,
                }
            ],
            "links": {"next": None},
            "meta": {"current_page": 1, "per_page": 175}
        })

    client = ArbeitnowClient(transport=httpx.MockTransport(handler))
    assert client.enabled is True
    rows = await client.search(query="Backend", location="Berlin", limit=10)
    assert len(rows) == 1
    assert rows[0]["job_id"] == "arbeitnow:lead-backend-developer-berlin-99"
    assert rows[0]["company"] == "Alpha Labs"
    assert "arbeitnow.com/api/job-board-api?page=1" in seen["url"]


def test_normalize_job_handles_careerjet_schema():
    row = normalize_job({
        "title": "Senior Python Developer",
        "company": "NBC Universal",
        "date": "Wed, 15 Nov 2025 19:13:43 GMT",
        "description": "Develop high throughput backend services using Python and FastAPI.",
        "locations": "London, UK",
        "salary": "$120000 - 140000",
        "salary_currency_code": "USD",
        "salary_min": 120000.0,
        "salary_max": 140000.0,
        "salary_type": "Y",
        "url": "https://jobviewtrack.com/v2/careerjet_role_123",
    }, "careerjet")
    assert row["job_id"] == "careerjet:https://jobviewtrack.com/v2/careerjet_role_123"
    assert row["company"] == "NBC Universal"
    assert row["title"] == "Senior Python Developer"
    assert row["location"] == "London, UK"
    assert row["salary_min"] == 120000.0
    assert row["salary_max"] == 140000.0
    assert row["salary_currency"] == "USD"
    assert row["posted_date"] is not None
    assert row["posted_date"].year == 2025


@pytest.mark.asyncio
async def test_careerjet_client_builds_documented_request():
    import base64
    from src.job_data_providers import CareerjetClient
    seen = {}
    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={
            "type": "JOBS",
            "hits": 1,
            "message": "1 matching jobs found",
            "pages": 1,
            "jobs": [
                {
                    "title": "Python Backend Engineer",
                    "company": "Tech Innovations",
                    "date": "Mon, 10 Nov 2025 10:00:00 GMT",
                    "description": "FastAPI, PostgreSQL and AWS backend systems.",
                    "locations": "New York, NY",
                    "salary_min": 130000.0,
                    "salary_max": 160000.0,
                    "salary_currency_code": "USD",
                    "url": "https://jobviewtrack.com/v2/test_role_99",
                }
            ]
        })

    api_key = "careerjet_test_key_xyz"
    client = CareerjetClient(api_key=api_key, transport=httpx.MockTransport(handler))
    assert client.enabled is True

    rows = await client.search(
        query="Python Backend",
        location="New York",
        page=1,
        page_size=10,
        locale_code="en_US",
        sort="date",
        contract_type="p",
        work_hours="f",
    )

    assert len(rows) == 1
    assert rows[0]["company"] == "Tech Innovations"
    assert "search.api.careerjet.net/v4/query" in seen["url"]
    assert "locale_code=en_US" in seen["url"]
    assert "user_ip=" in seen["url"]
    assert "user_agent=" in seen["url"]

    # Verify Basic Auth credentials format
    expected_auth = "Basic " + base64.b64encode(f"{api_key}:".encode()).decode()
    assert seen["auth"] == expected_auth


def test_normalize_job_handles_usajobs_schema():
    payload = {
        "MatchedObjectId": "99887766",
        "MatchedObjectDescriptor": {
            "PositionTitle": "IT Specialist (APPSW / Python Developer)",
            "PositionURI": "https://www.usajobs.gov/job/99887766",
            "PositionLocationDisplay": "Anywhere in the U.S. (remote)",
            "OrganizationName": "Department of Veterans Affairs",
            "DepartmentName": "Veterans Affairs, Office of Information and Technology",
            "PublicationStartDate": "2026-08-20T00:00:00.0000",
            "JobCategory": [
                {"Name": "Information Technology Management", "Code": "2210"}
            ],
            "PositionRemuneration": [
                {
                    "MinimumRange": "125000",
                    "MaximumRange": "165000",
                    "RateIntervalCode": "Per Year"
                }
            ],
            "UserArea": {
                "Details": {
                    "JobSummary": "Develop modern cloud-native Python backend APIs and microservices.",
                    "MajorDuties": [
                        "Architect FastAPI web services",
                        "Build PostgreSQL data models"
                    ],
                    "LowGrade": "13",
                    "HighGrade": "14",
                    "RemoteIndicator": True,
                    "TeleworkEligible": True
                }
            }
        }
    }
    row = normalize_job(payload, "usajobs")
    assert row["job_id"] == "usajobs:99887766"
    assert row["company"] == "Department of Veterans Affairs"
    assert row["title"] == "IT Specialist (APPSW / Python Developer)"
    assert row["location"] == "Anywhere in the U.S. (remote)"
    assert row["has_remote"] is True
    assert row["work_mode"] == "remote"
    assert row["salary_min"] == 125000.0
    assert row["salary_max"] == 165000.0
    assert row["salary_currency"] == "USD"
    assert "FastAPI" in row["description"]
    assert "GS-13/14" in row["tags"]
    assert "Information Technology Management" in row["tags"]


@pytest.mark.asyncio
async def test_usajobs_client_builds_documented_request():
    from src.job_data_providers import USAJobsClient
    seen = {}

    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth_key"] = request.headers.get("authorization-key")
        seen["user_agent"] = request.headers.get("user-agent")
        return httpx.Response(200, json={
            "SearchResult": {
                "SearchResultCount": 1,
                "SearchResultCountAll": 1,
                "SearchResultItems": [
                    {
                        "MatchedObjectId": "11223344",
                        "MatchedObjectDescriptor": {
                            "PositionTitle": "Cloud Software Engineer",
                            "PositionURI": "https://www.usajobs.gov/job/11223344",
                            "PositionLocationDisplay": "Remote, United States",
                            "OrganizationName": "National Aeronautics and Space Administration",
                            "PositionRemuneration": [{"MinimumRange": "135000", "MaximumRange": "175000"}],
                            "UserArea": {
                                "Details": {
                                    "JobSummary": "Support NASA cloud engineering and data pipelines.",
                                    "RemoteIndicator": True
                                }
                            }
                        }
                    }
                ]
            }
        })

    api_key = "test_usajobs_auth_key"
    client = USAJobsClient(api_key=api_key, email="kushall.jain07@gmail.com", transport=httpx.MockTransport(handler))
    assert client.enabled is True

    jobs = await client.search(
        query="Python",
        remote_only=True,
        job_category_code="2210",
        who_may_apply="public",
        results_per_page=15
    )

    assert len(jobs) == 1
    assert jobs[0]["company"] == "National Aeronautics and Space Administration"
    assert jobs[0]["has_remote"] is True
    assert "data.usajobs.gov/api/search" in seen["url"]
    assert "Keyword=Python" in seen["url"]
    assert "RemoteIndicator=True" in seen["url"]
    assert "JobCategoryCode=2210" in seen["url"]
    assert "WhoMayApply=public" in seen["url"]
    assert "ResultsPerPage=15" in seen["url"]
    assert seen["auth_key"] == "test_usajobs_auth_key"
    assert seen["user_agent"] == "kushall.jain07@gmail.com"





