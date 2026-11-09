"""
Unit tests for FinTech Decision Maker Mining and Autonomous Outreach Engine
"""
import pytest
from src.company_sources.miners.fintech_decision_maker_miner import (
    FinTechDecisionMakerMiner,
    DecisionMakerContact,
)
from src.company_sources.registries.fintech_festival_companies import FinTechFestivalCompany


def test_email_synthesis_and_phone_extraction():
    miner = FinTechDecisionMakerMiner()
    email1 = miner.synthesize_candidate_email("Example Person", "example.com")
    assert email1 == "example.person@example.com"

    email2 = miner.synthesize_candidate_email("Sample", "example.com")
    assert email2 == "sample@example.com"

    text_with_phone = "Contact the office at +1 202-555-0147 or email info@example.com"
    phone = miner.extract_phone(text_with_phone)
    assert phone is not None
    assert "202" in phone


def test_compose_personalized_outreach():
    miner = FinTechDecisionMakerMiner()
    miner.sender_name = ""
    miner.sender_linkedin = ""
    dm = DecisionMakerContact(
        company="Example Company",
        name="Example Person",
        title="Founder & CEO",
        domain="example.com",
        email="example.person@example.com",
        phone_number="+1 202-555-0147",
        linkedin_url="https://linkedin.com/in/example",
        confidence_score=95,
    )

    subject, body_text, body_html = miner.compose_personalized_outreach(dm)
    assert "Example Company" in subject
    assert "Hi Example," in body_text
    assert "hiring for engineering roles" in body_text
    assert "Python, FastAPI, React" not in body_text
    assert "Naveen" not in body_text
    assert "<html>" in body_html


@pytest.mark.asyncio
async def test_search_company_decision_makers_mock():
    miner = FinTechDecisionMakerMiner()
    comp = FinTechFestivalCompany(
        "example", "Example Company", "Payments & Gateways", "Example Event",
        "Sponsor", "greenhouse", "example", "https://example.com", "example.com"
    )

    # Search (will gracefully handle API key or network)
    contacts = await miner.search_company_decision_makers_serpapi(comp, max_results=3)
    assert isinstance(contacts, list)
    if contacts:
        for c in contacts:
            assert c.company == "Example Company"
            assert "@example.com" in c.email
            assert c.title is not None

def test_role_priority_ranking():
    from src.company_sources.miners.fintech_decision_maker_miner import get_role_priority
    assert get_role_priority("Founder & CEO") == 1
    assert get_role_priority("Chief Technology Officer") == 1
    assert get_role_priority("VP of Engineering") == 2
    assert get_role_priority("Director of Engineering") == 3
    assert get_role_priority("Engineering Manager") == 4
    assert get_role_priority("Talent Acquisition") == 5


def test_max_outreach_per_company_constant():
    from src.company_sources.miners.fintech_decision_maker_miner import MAX_OUTREACH_PER_COMPANY
    assert MAX_OUTREACH_PER_COMPANY == 2
