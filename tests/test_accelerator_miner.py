"""
Unit tests for Y Combinator & Global Accelerators Sourcing and Outreach Engine.
"""
import pytest
from src.accelerators_registry import (
    ACCELERATORS_REGISTRY,
    get_all_accelerator_startups,
    filter_by_accelerator,
    filter_by_category,
)
from src.accelerator_miner import (
    AcceleratorMiner,
    get_role_priority,
    MAX_OUTREACH_PER_COMPANY,
)


def test_accelerators_registry_loaded():
    startups = get_all_accelerator_startups()
    assert len(startups) >= 30
    
    # Check YC Startups
    yc_startups = filter_by_accelerator("Y Combinator")
    assert len(yc_startups) >= 15
    yc_names = [s.name for s in yc_startups]
    assert "Zepto" in yc_names
    assert "Razorpay" in yc_names
    assert "Groww" in yc_names
    assert "Postman" in yc_names
    assert "Supabase" in yc_names
    assert "Cursor (Anysphere)" in yc_names


def test_filter_by_accelerator_surge_and_antler():
    surge = filter_by_accelerator("Surge by Peak XV")
    assert len(surge) >= 5
    surge_names = [s.name for s in surge]
    assert "Atlan" in surge_names
    assert "Plum Insurance" in surge_names

    antler = filter_by_accelerator("Antler")
    assert len(antler) >= 2


def test_accelerator_role_priority_ranking():
    assert get_role_priority("Co-Founder & CEO") == 1
    assert get_role_priority("Chief Technology Officer") == 1
    assert get_role_priority("Founding Engineer") == 2
    assert get_role_priority("VP of Engineering") == 2
    assert get_role_priority("Director of Engineering") == 3
    assert get_role_priority("Lead Software Engineer") == 4
    assert get_role_priority("Technical Recruiter") == 5


def test_compose_accelerator_outreach():
    miner = AcceleratorMiner()
    contact = {
        "name": "Aadit Palicha",
        "title": "Co-Founder & CEO",
        "company": "Zepto",
        "accelerator": "Y Combinator",
        "batch": "YC W21",
    }
    subj, text, html = miner.compose_accelerator_outreach(contact)
    assert "Zepto" in subj
    assert "Y Combinator" in subj
    assert "Aadit" in text
    assert "YC W21" in text
    assert "Python, FastAPI, React" in text
    assert "<html>" in html


def test_max_outreach_per_company_constraint():
    assert MAX_OUTREACH_PER_COMPANY == 2
