import pytest
import httpx
from src.tier1_companies import TIER1_REGISTRY, get_tier1_company
from src.referral_engine import generate_referral_xray_queries, compose_referral_request, search_company_referral_contacts
from src.scrapers.tier1_career_scraper import Tier1CareerScraper


def test_tier1_registry_loads_all_60_companies():
    assert len(TIER1_REGISTRY) == 60

    rubrik = get_tier1_company("Rubrik")
    assert rubrik is not None
    assert rubrik.rank == 1
    assert rubrik.likely_level == "L4 / SWE II"
    assert rubrik.negotiation_target_lakhs == "₹105–115L"

    stripe = get_tier1_company("Stripe")
    assert stripe is not None
    assert stripe.negotiation_target_lakhs == "₹105–120L"

    zepto = get_tier1_company("Zepto")
    assert zepto is not None
    assert zepto.ats_platform == "lever"
    assert zepto.negotiation_target_lakhs == "₹50–55L"

    makemytrip = get_tier1_company("MakeMyTrip")
    assert makemytrip is not None
    assert makemytrip.rank == 60


def test_generate_referral_xray_queries():
    queries = generate_referral_xray_queries("Rubrik")
    assert len(queries) == 3
    assert "site:linkedin.com/in" in queries[0]["query"]
    assert "Rubrik" in queries[0]["query"]
    assert "Engineering Manager" in queries[1]["query"]


def test_compose_referral_request():
    msg = compose_referral_request(
        contact_name="Aarav Sharma",
        company_name="Rubrik",
        role_title="Software Engineer - Cloud Systems",
        job_id_or_url="https://rubrik.com/jobs/123",
        candidate_name="Kushall Jain"
    )
    assert len(msg["connection_note_300chars"]) <= 300
    assert "Rubrik" in msg["connection_note_300chars"]
    assert "Kushall Jain" in msg["full_referral_message"]
    assert "Software Engineer - Cloud Systems" in msg["full_referral_message"]
    assert "https://rubrik.com/jobs/123" in msg["full_referral_message"]


@pytest.mark.asyncio
async def test_tier1_career_scraper_greenhouse():
    async def handler(request: httpx.Request):
        if "boards-api.greenhouse.io/v1/boards/rubrik/jobs" in str(request.url):
            return httpx.Response(200, json={
                "jobs": [
                    {
                        "id": 554433,
                        "title": "Software Engineer II - Backend",
                        "content": "Work on distributed systems and Python/Go microservices.",
                        "location": {"name": "Bengaluru, India"},
                        "absolute_url": "https://boards.greenhouse.io/rubrik/jobs/554433",
                        "updated_at": "2026-08-25T10:00:00Z"
                    }
                ]
            })
        return httpx.Response(404)

    scraper = Tier1CareerScraper(transport=httpx.MockTransport(handler))
    jobs = await scraper.scrape_all_tier1_careers(companies=["Rubrik"], keywords=["Backend"])
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Software Engineer II - Backend"
    assert jobs[0]["company"] == "Rubrik"
    assert jobs[0]["compensation_benchmark"]["negotiation_target_lakhs"] == "₹105–115L"


@pytest.mark.asyncio
async def test_search_company_referral_contacts_serpapi(monkeypatch):
    from src.config import settings
    monkeypatch.setattr(settings, "serpapi_api_key", "test_mock_key")

    async def handler(request: httpx.Request):
        return httpx.Response(200, json={
            "organic_results": [
                {
                    "title": "Rajesh Kumar - Staff Software Engineer - Rubrik | LinkedIn",
                    "link": "https://www.linkedin.com/in/rajesh-kumar-swe",
                    "snippet": "Staff Software Engineer at Rubrik Bangalore building cloud data management."
                }
            ]
        })

    leads = await search_company_referral_contacts("Rubrik", max_leads=5, transport=httpx.MockTransport(handler))
    assert len(leads) == 1
    assert leads[0]["name"] == "Rajesh Kumar"
    assert leads[0]["role"] == "Staff Software Engineer"
    assert leads[0]["company"] == "Rubrik"
    assert "linkedin.com/in/rajesh-kumar-swe" in leads[0]["linkedin_url"]
