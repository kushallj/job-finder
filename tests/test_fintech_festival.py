import pytest
import httpx
from src.fintech_festival_companies import (
    FINTECH_FESTIVAL_REGISTRY,
    get_fintech_festival_company,
    filter_fintech_festival_companies,
)
from src.scrapers.fintech_festival_scraper import FinTechFestivalScraper


def test_festival_registry_loads_sponsors():
    assert len(FINTECH_FESTIVAL_REGISTRY) >= 50

    razorpay = get_fintech_festival_company("razorpay")
    assert razorpay is not None
    assert razorpay.category == "Payments & Gateways"
    assert razorpay.ats_platform == "greenhouse"

    adyen = get_fintech_festival_company("adyen")
    assert adyen is not None
    assert adyen.ats_platform == "smartrecruiters"

    elevenlabs = get_fintech_festival_company("elevenlabs")
    assert elevenlabs is not None
    assert elevenlabs.category == "RegTech & AI"

    phonepe = get_fintech_festival_company("phonepe")
    assert phonepe is not None
    assert phonepe.tier_role == "Co-Powered By"


def test_filter_fintech_festival_companies():
    payments = filter_fintech_festival_companies(category="Payments & Gateways")
    assert len(payments) >= 10
    assert any(p.name == "Razorpay" for p in payments)

    gff = filter_fintech_festival_companies(festival="Global FinTech Fest")
    assert len(gff) >= 20

    ai_partners = filter_fintech_festival_companies(category="RegTech & AI")
    assert len(ai_partners) >= 10


@pytest.mark.asyncio
async def test_fintech_festival_scraper_greenhouse():
    async def handler(request: httpx.Request):
        if "boards-api.greenhouse.io/v1/boards/juspay/jobs" in str(request.url):
            return httpx.Response(200, json={
                "jobs": [
                    {
                        "id": 112233,
                        "title": "Backend Architect - UPI Switch",
                        "content": "Scale high-concurrency payment switches using Haskell and Python.",
                        "location": {"name": "Bengaluru, India"},
                        "absolute_url": "https://boards.greenhouse.io/juspay/jobs/112233",
                        "updated_at": "2026-08-29T10:00:00Z"
                    }
                ]
            })
        return httpx.Response(404)

    scraper = FinTechFestivalScraper(transport=httpx.MockTransport(handler))
    jobs = await scraper.scrape_all_festival_sponsors(company_ids=["juspay"], keywords=["UPI"])
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Backend Architect - UPI Switch"
    assert jobs[0]["company"] == "Juspay"
    assert "FinTech-Festival-Sponsor" in jobs[0]["tags"]
    assert jobs[0]["festival_info"]["category"] == "Payments & Gateways"


@pytest.mark.asyncio
async def test_fintech_festival_scraper_smartrecruiters():
    async def handler(request: httpx.Request):
        if "api.smartrecruiters.com/v1/companies/adyen/postings" in str(request.url):
            return httpx.Response(200, json={
                "content": [
                    {
                        "id": "adyen-101",
                        "name": "Backend Software Engineer - Global Payouts",
                        "location": {"city": "Singapore", "country": "Singapore"},
                        "releasedDate": "2026-08-25T10:00:00Z"
                    }
                ]
            })
        return httpx.Response(404)

    scraper = FinTechFestivalScraper(transport=httpx.MockTransport(handler))
    jobs = await scraper.scrape_all_festival_sponsors(company_ids=["adyen"], keywords=["Payouts"])
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Backend Software Engineer - Global Payouts"
    assert jobs[0]["company"] == "Adyen"
    assert jobs[0]["festival_info"]["category"] == "Payments & Gateways"
