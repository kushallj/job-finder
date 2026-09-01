"""
Unit tests for FinTech Decision Maker Mining and Autonomous Outreach Engine
"""
import pytest
from src.fintech_decision_maker_miner import (
    FinTechDecisionMakerMiner,
    DecisionMakerContact,
)
from src.fintech_festival_companies import FinTechFestivalCompany


def test_email_synthesis_and_phone_extraction():
    miner = FinTechDecisionMakerMiner()
    email1 = miner.synthesize_candidate_email("Vimal Kumar", "juspay.in")
    assert email1 == "vimal.kumar@juspay.in"

    email2 = miner.synthesize_candidate_email("Sheetal", "juspay.in")
    assert email2 == "sheetal@juspay.in"

    text_with_phone = "Contact our Bangalore office at +91 9876543210 or email info@juspay.in"
    phone = miner.extract_phone(text_with_phone)
    assert phone is not None
    assert "9876543210" in phone


def test_compose_personalized_outreach():
    miner = FinTechDecisionMakerMiner()
    dm = DecisionMakerContact(
        company="Juspay",
        name="Vimal Kumar",
        title="Founder & CEO",
        domain="juspay.in",
        email="vimal.kumar@juspay.in",
        phone_number="+91 9876543210",
        linkedin_url="https://in.linkedin.com/in/kumarvimal",
        confidence_score=95,
    )

    subject, body_text, body_html = miner.compose_personalized_outreach(dm)
    assert "Juspay" in subject
    assert "Vimal" in body_text
    assert "Founder & CEO" in body_text
    assert "Python, FastAPI, React" in body_text
    assert "linkedin.com" in body_text
    assert "<html>" in body_html


@pytest.mark.asyncio
async def test_search_company_decision_makers_mock():
    miner = FinTechDecisionMakerMiner()
    comp = FinTechFestivalCompany(
        "juspay", "Juspay", "Payments & Gateways", "Global FinTech Fest (GFF)",
        "Gold Sponsor", "greenhouse", "juspay", "https://juspay.in", "juspay.in"
    )

    # Search (will gracefully handle API key or network)
    contacts = await miner.search_company_decision_makers_serpapi(comp, max_results=3)
    assert isinstance(contacts, list)
    if contacts:
        for c in contacts:
            assert c.company == "Juspay"
            assert "@juspay.in" in c.email
            assert c.title is not None

def test_role_priority_ranking():
    from src.fintech_decision_maker_miner import get_role_priority
    assert get_role_priority("Founder & CEO") == 1
    assert get_role_priority("Chief Technology Officer") == 1
    assert get_role_priority("VP of Engineering") == 2
    assert get_role_priority("Director of Engineering") == 3
    assert get_role_priority("Engineering Manager") == 4
    assert get_role_priority("Talent Acquisition") == 5


def test_max_outreach_per_company_constant():
    from src.fintech_decision_maker_miner import MAX_OUTREACH_PER_COMPANY
    assert MAX_OUTREACH_PER_COMPANY == 2
