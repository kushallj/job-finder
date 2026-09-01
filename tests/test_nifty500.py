"""
Unit tests for Nifty 500 Registry & Tech Leadership Outreach Engine.
"""
import pytest
from src.nifty500_registry import (
    NIFTY_500_REGISTRY,
    get_all_nifty500_companies,
    filter_by_sector,
    filter_by_cap,
    search_by_symbol,
)
from src.nifty500_miner import (
    Nifty500Miner,
    get_role_priority,
    MAX_OUTREACH_PER_COMPANY,
)


def test_nifty500_registry_loaded():
    companies = get_all_nifty500_companies()
    assert len(companies) >= 60

    # Verify key IT, Consumer Tech and BFSI names
    symbols = [c.symbol for c in companies]
    assert "TCS" in symbols
    assert "INFY" in symbols
    assert "ZOMATO" in symbols
    assert "HDFCBANK" in symbols
    assert "DIXON" in symbols
    assert "TATAMOTORS" in symbols


def test_filter_by_sector():
    it_companies = filter_by_sector("Information Technology")
    assert len(it_companies) >= 15
    
    fin_companies = filter_by_sector("Banking & Financial Services")
    assert len(fin_companies) >= 10


def test_search_by_symbol():
    zomato = search_by_symbol("ZOMATO")
    assert zomato is not None
    assert zomato.name == "Zomato"
    assert zomato.sector == "Consumer Internet & Tech"


def test_compose_nifty500_outreach():
    miner = Nifty500Miner()
    contact = {
        "name": "Nitin Gupta",
        "title": "Head of Engineering",
        "company": "Zomato",
        "sector": "Consumer Internet & Tech",
        "symbol": "ZOMATO",
    }
    subj, text, html = miner.compose_nifty500_outreach(contact)
    assert "Zomato" in subj
    assert "Nifty 500" in subj
    assert "Nitin" in text
    assert "Python, FastAPI, React" in text
    assert "<html>" in html


def test_max_outreach_per_company_constraint_nifty500():
    assert MAX_OUTREACH_PER_COMPANY == 2
