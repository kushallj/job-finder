"""
Unit tests for Shark Tank India Startups Registry & Outreach Engine.
"""
import pytest
from src.shark_tank_india_startups import (
    SHARK_TANK_INDIA_REGISTRY,
    get_all_shark_tank_startups,
    filter_by_season,
    filter_by_shark,
    filter_by_category,
)
from src.shark_tank_miner import (
    SharkTankMiner,
    get_role_priority,
    MAX_OUTREACH_PER_COMPANY,
)


def test_shark_tank_registry_loaded():
    startups = get_all_shark_tank_startups()
    assert len(startups) >= 30
    
    # Check seasons representation
    s1 = filter_by_season(1)
    s2 = filter_by_season(2)
    s3 = filter_by_season(3)
    s4 = filter_by_season(4)
    assert len(s1) >= 8
    assert len(s2) >= 8
    assert len(s3) >= 8
    assert len(s4) >= 4


def test_filter_by_shark():
    peyush_startups = filter_by_shark("Peyush Bansal")
    assert len(peyush_startups) >= 8
    names = [s.name for s in peyush_startups]
    assert "Snitch" in names or "Stage (OTT)" in names


def test_compose_shark_tank_outreach():
    miner = SharkTankMiner()
    contact = {
        "name": "Siddharth Dungarwal",
        "title": "Founder & CEO",
        "company": "Snitch",
        "season": 2,
        "sharks": "Peyush Bansal, Aman Gupta, Anupam Mittal, Namita Thapar, Vineeta Singh",
    }
    subj, text, html = miner.compose_shark_tank_outreach(contact)
    assert "Snitch" in subj
    assert "Shark Tank India S2" in subj
    assert "Siddharth" in text
    assert "Peyush Bansal" in text
    assert "Python, FastAPI, React" in text
    assert "<html>" in html


def test_role_priority_and_max_outreach_cap():
    assert get_role_priority("Co-Founder & CEO") == 1
    assert get_role_priority("CTO") == 1
    assert get_role_priority("Head of Engineering") == 2
    assert MAX_OUTREACH_PER_COMPANY == 2
