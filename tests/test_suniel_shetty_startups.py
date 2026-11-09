"""
Unit tests for Suniel Shetty Shows & Portfolio Startups Registry & Outreach Engine.
"""
import pytest
from src.company_sources.registries.suniel_shetty_startups import (
    SUNIEL_SHETTY_STARTUPS_REGISTRY,
    get_all_suniel_shetty_startups,
    filter_by_show,
    filter_by_shetty_category,
)
from src.company_sources.miners.suniel_shetty_miner import (
    SunielShettyMiner,
    get_role_priority,
    MAX_OUTREACH_PER_COMPANY,
)


def test_suniel_shetty_registry_loaded():
    startups = get_all_suniel_shetty_startups()
    assert len(startups) >= 15
    
    super_founders = filter_by_show("Bharat Ke Super Founders")
    assert len(super_founders) >= 6
    names = [s.name for s in super_founders]
    assert "Digital Labour Chowk" in names
    assert "Regrip" in names
    assert "CRASTE" in names

    horses_stable = filter_by_show("Horses Stable")
    assert len(horses_stable) >= 4
    hs_names = [s.name for s in horses_stable]
    assert "Medyseva" in hs_names or "Rupyz" in hs_names


def test_compose_shetty_outreach():
    miner = SunielShettyMiner()
    miner.sender_name = ""
    miner.sender_linkedin = ""
    contact = {
        "name": "Example Person",
        "title": "Founder & CEO",
        "company": "Example Company",
        "show_or_source": "Example Show",
    }
    subj, text, html = miner.compose_shetty_outreach(contact)
    assert "Example Company" in subj
    assert "Hi Example," in text
    assert "Python, FastAPI, React" not in text
    assert "<html>" in html


def test_max_outreach_per_company_constraint_shetty():
    assert MAX_OUTREACH_PER_COMPANY == 2
