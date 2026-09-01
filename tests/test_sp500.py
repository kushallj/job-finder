"""
Unit tests for Official S&P 500 Database (503 US Constituents) & Outreach Engine.
"""
import pytest
from src.sp500_registry import (
    get_all_sp500_companies,
    filter_by_sector,
    filter_by_sub_industry,
    search_by_symbol,
    search_by_keyword,
    get_sector_breakdown,
)
from src.sp500_miner import (
    SP500Miner,
    get_role_priority,
    MAX_OUTREACH_PER_COMPANY,
)


def test_official_sp500_dataset_loaded_503_companies():
    companies = get_all_sp500_companies()
    assert len(companies) >= 500, f"Expected ~503 official companies, got {len(companies)}"

    # Check key symbols
    symbols = set(c.symbol for c in companies)
    assert "AAPL" in symbols
    assert "MSFT" in symbols
    assert "NVDA" in symbols
    assert "GOOGL" in symbols
    assert "AMZN" in symbols
    assert "META" in symbols
    assert "JPM" in symbols
    assert "V" in symbols
    assert "TSLA" in symbols
    assert "CRM" in symbols
    assert "ORCL" in symbols


def test_filter_by_sector_sp500():
    tech = filter_by_sector("Information Technology")
    assert len(tech) >= 65
    
    fin = filter_by_sector("Financials")
    assert len(fin) >= 70


def test_search_by_symbol_sp500():
    nvda = search_by_symbol("NVDA")
    assert nvda is not None
    assert "Nvidia" in nvda.name
    assert nvda.sector == "Information Technology"
    assert nvda.domain == "nvidia.com"


def test_search_by_keyword_sp500():
    results = search_by_keyword("Apple")
    assert len(results) >= 1
    assert any("Apple" in r.name for r in results)


def test_get_sector_breakdown_sp500():
    breakdown = get_sector_breakdown()
    assert "Information Technology" in breakdown
    assert "Financials" in breakdown
    assert "Industrials" in breakdown
    assert "Health Care" in breakdown
    assert sum(breakdown.values()) >= 500


def test_compose_sp500_outreach():
    miner = SP500Miner()
    contact = {
        "name": "Satya Nadella",
        "title": "Chief Executive Officer",
        "company": "Microsoft",
        "sector": "Information Technology",
        "symbol": "MSFT",
    }
    subj, text, html = miner.compose_sp500_outreach(contact)
    assert "Microsoft" in subj
    assert "S&P 500" in subj
    assert "Satya" in text
    assert "Python, FastAPI, React" in text
    assert "<html>" in html


def test_max_outreach_per_company_constraint_sp500():
    assert MAX_OUTREACH_PER_COMPANY == 2
