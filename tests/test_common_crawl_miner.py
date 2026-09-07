"""
test_common_crawl_miner.py — Comprehensive Unit & Integration Tests for Common Crawl S3 Stealth Miner.
Tests CDX indexing, S3 byte-range simulation, contact extraction, tech stack detection,
email discovery provider integration, and FastAPI endpoints.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app
from src.email_engine.common_crawl_miner import CommonCrawlMiner, common_crawl_miner
from src.email_discovery import EmailDiscoveryService, CommonCrawlEmailProvider


@pytest.fixture
def client():
    return TestClient(app)


def test_miner_initialization():
    miner = CommonCrawlMiner(default_index="CC-MAIN-2024-51")
    assert miner.default_index == "CC-MAIN-2024-51"
    assert "commoncrawl.org" in miner.index_base_url
    assert "data.commoncrawl.org" in miner.s3_base_url


@pytest.mark.asyncio
async def test_get_available_indices():
    miner = CommonCrawlMiner()
    indices = await miner.get_available_indices()
    assert isinstance(indices, list)
    assert len(indices) > 0
    assert "id" in indices[0]


def test_contact_and_email_extraction():
    miner = CommonCrawlMiner()
    sample_text = """
    About Our Team:
    Reach out to our recruiting team at talent@uber.com or careers@uber.com.
    For technical inquiries, contact our CTO alex.chen@uber.com or engineering lead sarah@uber.com.
    Ignore sample logos at logo@uber.png and analytics tracker bug@sentry.io.
    """
    contacts = miner.extract_emails_and_contacts(sample_text, domain="uber.com")
    assert len(contacts) >= 3

    emails = [c["email"] for c in contacts]
    assert "talent@uber.com" in emails
    assert "careers@uber.com" in emails
    assert "alex.chen@uber.com" in emails
    # False positives must be filtered
    assert "logo@uber.png" not in emails
    assert "bug@sentry.io" not in emails

    # Check confidence
    talent_contact = next(c for c in contacts if c["email"] == "talent@uber.com")
    assert talent_contact["confidence"] >= 80
    assert talent_contact["source"] == "Common Crawl S3 Archive"


def test_tech_stack_detection():
    miner = CommonCrawlMiner()
    sample_code_snippet = """
    We run Kubernetes clusters on AWS with microservices written in Go and Python FastAPI.
    Our state is stored in PostgreSQL and Redis, and our frontend uses React and TypeScript.
    For financial accounting, we integrate with Tally and Busy software.
    """
    stack = miner.detect_tech_stack(sample_code_snippet)
    assert "Kubernetes" in stack
    assert "Python" in stack
    assert "Go" in stack
    assert "AWS" in stack
    assert "PostgreSQL" in stack
    assert "React" in stack
    assert "TypeScript" in stack
    assert "Tally" in stack
    assert "Busy" in stack


def test_job_posting_extraction():
    miner = CommonCrawlMiner()
    sample_career_page = """
    Open Opportunities at Stripe:
    1. Senior Backend Engineer
    We are looking for a Senior Backend Engineer to scale our distributed payment rails using Go and Kubernetes.
    2. Staff Platform Engineer
    Join our cloud foundation team to manage AWS infrastructure and Terraform deployments.
    3. Senior Accountant
    Manage ledger closing and Tally ERP reconciliations.
    """
    jobs = miner.extract_job_postings(sample_career_page, source_url="https://stripe.com/jobs", domain="stripe.com")
    assert len(jobs) >= 2
    titles = [j["title"] for j in jobs]
    assert any("Senior Backend Engineer" in t for t in titles)
    assert any("Staff Platform Engineer" in t for t in titles)
    assert jobs[0]["company_domain"] == "stripe.com"


@pytest.mark.asyncio
async def test_mine_stealth_intel_end_to_end():
    miner = CommonCrawlMiner()
    res = await miner.mine_stealth_intel("stripe.com", company_name="Stripe")
    assert res["status"] == "success"
    assert res["domain"] == "stripe.com"
    assert "S3 Byte-Range" in res["stealth_mode"]
    assert len(res["contacts_discovered"]) >= 1
    assert len(res["jobs_discovered"]) >= 1
    assert len(res["detected_tech_stack"]) >= 1


@pytest.mark.asyncio
async def test_common_crawl_email_provider():
    provider = CommonCrawlEmailProvider()
    assert provider.name == "common_crawl_s3"

    res = await provider.discover_emails(
        first_name="Alex",
        last_name="Chen",
        company_name="Datadog",
        domain="datadog.com"
    )
    assert res["provider"] == "common_crawl_s3"
    assert res["confidence"] >= 80
    assert len(res["emails"]) >= 1
    assert "@datadog.com" in res["emails"][0]


@pytest.mark.asyncio
async def test_email_discovery_service_integration():
    service = EmailDiscoveryService()
    # Ensure common_crawl_s3 provider is registered
    provider_names = [p.name for p in service.providers]
    assert "common_crawl_s3" in provider_names

    res = await service.discover(
        first_name="Patrick",
        last_name="Collison",
        company="Stripe",
        domain="stripe.com"
    )
    assert "primary_email" in res
    assert len(res["discovered_emails"]) >= 1


def test_fastapi_common_crawl_endpoints(client):
    # 1. GET /api/common-crawl/indices
    res = client.get("/api/common-crawl/indices")
    assert res.status_code == 200
    indices = res.json()["indices"]
    assert len(indices) > 0

    # 2. POST /api/common-crawl/search
    search_payload = {
        "domain": "razorpay.com",
        "limit": 10
    }
    res = client.post("/api/common-crawl/search", json=search_payload)
    assert res.status_code == 200
    search_data = res.json()
    assert search_data["status"] == "success"
    assert search_data["domain"] == "razorpay.com"
    assert "records" in search_data

    # 3. POST /api/common-crawl/mine
    mine_payload = {
        "domain": "razorpay.com",
        "company_name": "Razorpay"
    }
    res = client.post("/api/common-crawl/mine", json=mine_payload)
    assert res.status_code == 200
    mine_data = res.json()
    assert mine_data["status"] == "success"
    assert mine_data["domain"] == "razorpay.com"
    assert "contacts_discovered" in mine_data
    assert "jobs_discovered" in mine_data
    assert "detected_tech_stack" in mine_data
