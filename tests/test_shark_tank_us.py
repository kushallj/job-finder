"""
Unit tests for Shark Tank US Startups Registry & Outreach Engine.
"""
import pytest
from src.shark_tank_us_startups import (
    SHARK_TANK_US_REGISTRY,
    get_all_shark_tank_us_startups,
    filter_by_season_us,
    filter_by_shark_us,
    filter_by_category_us,
)
from src.shark_tank_us_miner import (
    SharkTankUSMiner,
    get_role_priority,
    MAX_OUTREACH_PER_COMPANY,
)


def test_shark_tank_us_registry_loaded():
    startups = get_all_shark_tank_us_startups()
    assert len(startups) >= 20

    # Verify iconic billion-dollar breakouts
    names = [s.name for s in startups]
    assert "Ring (Doorbot)" in names
    assert "Bombas" in names
    assert "Scrub Daddy" in names
    assert "Everlywell" in names
    assert "Manscaped" in names


def test_filter_by_shark_us():
    lori_deals = filter_by_shark_us("Lori Greiner")
    assert len(lori_deals) >= 4
    names = [s.name for s in lori_deals]
    assert "Scrub Daddy" in names or "Squatty Potty" in names or "Everlywell" in names

    cuban_deals = filter_by_shark_us("Mark Cuban")
    assert len(cuban_deals) >= 4


def test_compose_shark_tank_us_outreach():
    miner = SharkTankUSMiner()
    contact = {
        "name": "David Heath",
        "title": "Co-Founder & CEO",
        "company": "Bombas",
        "season": 6,
        "sharks": "Daymond John",
    }
    subj, text, html = miner.compose_shark_tank_us_outreach(contact)
    assert "Bombas" in subj
    assert "Shark Tank Season 6" in subj
    assert "David" in text
    assert "Daymond John" in text
    assert "Python, FastAPI, React" in text
    assert "<html>" in html


def test_max_outreach_per_company_constraint_us():
    assert MAX_OUTREACH_PER_COMPANY == 2
