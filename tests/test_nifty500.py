"""
Unit tests for Official Nifty 500 Database (500 NSE Companies) & Outreach Engine.
"""
import pytest
from src.nifty500_registry import (
    get_all_nifty500_companies,
    filter_by_industry,
    filter_by_sector,
    search_by_symbol,
    search_by_keyword,
    get_industry_breakdown,
)
from src.nifty500_miner import (
    Nifty500Miner,
    get_role_priority,
    MAX_OUTREACH_PER_COMPANY,
)


def test_official_nifty500_dataset_loaded_500_companies():
    companies = get_all_nifty500_companies()
    assert len(companies) == 500, f"Expected exactly 500 official companies, got {len(companies)}"

    # Check key symbols
    symbols = set(c.symbol for c in companies)
    assert "TCS" in symbols
    assert "INFY" in symbols
    assert "HDFCBANK" in symbols
    assert "RELIANCE" in symbols
    assert "DIXON" in symbols
    assert "360ONE" in symbols
    assert "ABB" in symbols
    assert "ADANIGREEN" in symbols


def test_filter_by_industry():
    financials = filter_by_industry("Financial Services")
    assert len(financials) >= 90
    
    it = filter_by_industry("Information Technology")
    assert len(it) >= 25


def test_search_by_symbol_official():
    tcs = search_by_symbol("TCS")
    assert tcs is not None
    assert "Tata Consultancy" in tcs.name
    assert tcs.industry == "Information Technology"


def test_search_by_keyword():
    results = search_by_keyword("Tata")
    assert len(results) >= 5
    names = [r.name for r in results]
    assert any("Tata Motors" in n or "Tata Consultancy" in n for n in names)


def test_get_industry_breakdown():
    breakdown = get_industry_breakdown()
    assert "Financial Services" in breakdown
    assert "Information Technology" in breakdown
    assert "Capital Goods" in breakdown
    assert sum(breakdown.values()) == 500


def test_compose_nifty500_outreach():
    miner = Nifty500Miner()
    contact = {
        "name": "Ananth Krishnan",
        "title": "Chief Technology Officer",
        "company": "Tata Consultancy Services Ltd.",
        "industry": "Information Technology",
        "symbol": "TCS",
    }

    subj, text, html = miner.compose_nifty500_outreach(contact)
    assert "Tata Consultancy Services Ltd." in subj
    assert "Nifty 500" in subj
    assert "Ananth" in text
    assert "Python, FastAPI, React" in text
    assert "<html>" in html


def test_max_outreach_per_company_constraint():
    assert MAX_OUTREACH_PER_COMPANY == 2
