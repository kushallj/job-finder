"""
tests/test_sp500_referral_miner.py — Unit Tests for S&P 500 LinkedIn & X Referral Miner
"""
import pytest
from src.scrapers.sp500_referral_miner import (
    SP500ReferralMiner,
    get_referral_role_priority,
    MAX_OUTREACH_PER_COMPANY,
)


def test_sp500_referral_miner_initialization():
    miner = SP500ReferralMiner()
    assert miner is not None
    assert MAX_OUTREACH_PER_COMPANY == 2


def test_synthesize_email_formats():
    miner = SP500ReferralMiner()
    assert miner.synthesize_email("Satya Nadella", "microsoft.com") == "satya.nadella@microsoft.com"
    assert miner.synthesize_email("Jensen Huang", "nvidia.com") == "jensen.huang@nvidia.com"
    assert miner.synthesize_email("Alex Karp", "palantir.com") == "alex.karp@palantir.com"
    assert miner.synthesize_email("Brian Chesky", "airbnb.com") == "brian.chesky@airbnb.com"


def test_referral_role_priority_ranking():
    assert get_referral_role_priority("Engineering Manager") == 1
    assert get_referral_role_priority("Software Engineering Manager") == 1
    assert get_referral_role_priority("Director of Engineering") == 1
    assert get_referral_role_priority("Tech Lead") == 2
    assert get_referral_role_priority("Principal Engineer") == 2
    assert get_referral_role_priority("Senior Software Engineer") == 3
    assert get_referral_role_priority("Technical Recruiter") == 4
    assert get_referral_role_priority("CTO") == 5
    assert get_referral_role_priority("Product Manager") == 6


def test_compose_referral_outreach_linkedin():
    miner = SP500ReferralMiner()
    contact = {
        "name": "Sarah Connor",
        "title": "Engineering Manager",
        "company": "Palantir Technologies",
        "domain": "palantir.com",
        "email": "sarah.connor@palantir.com",
        "source": "sp500_linkedin_referral",
    }
    subject, body_text, body_html = miner.compose_referral_outreach(contact, "Distributed Systems Engineer")
    assert "Palantir Technologies" in subject
    assert "Sarah" in body_text
    assert "on LinkedIn" in body_text
    assert "FastAPI, React" in body_text
    assert "Kushall Jain" in body_text
    assert "https://linkedin.com/in/kushall-jain-263009261" in body_text


def test_compose_referral_outreach_x_twitter():
    miner = SP500ReferralMiner()
    contact = {
        "name": "Alex Dev",
        "title": "Engineering Lead (Nvidia)",
        "company": "Nvidia",
        "domain": "nvidia.com",
        "email": "alex.dev@nvidia.com",
        "source": "sp500_x_referral",
    }
    subject, body_text, body_html = miner.compose_referral_outreach(contact, "Deep Learning Engineer")
    assert "Nvidia" in subject
    assert "on X" in body_text
    assert "Alex" in body_text
