"""
sp500_registry.py — Official S&P 500 Index Database (US Equity Market Leaders).

Dynamically loads and indexes all 503 official constituents from the S&P 500 index
sourced directly from official financial archives (data/sp500_official.csv).
"""
from __future__ import annotations

import csv
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sp500_registry")

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "sp500_official.csv"

# Domain mapping for top tech & financial titans
KNOWN_DOMAINS: Dict[str, str] = {
    "AAPL": "apple.com",
    "MSFT": "microsoft.com",
    "NVDA": "nvidia.com",
    "GOOGL": "google.com",
    "GOOG": "google.com",
    "AMZN": "amazon.com",
    "META": "meta.com",
    "TSLA": "tesla.com",
    "JPM": "jpmorganchase.com",
    "V": "visa.com",
    "MA": "mastercard.com",
    "CRM": "salesforce.com",
    "ORCL": "oracle.com",
    "ADBE": "adobe.com",
    "NFLX": "netflix.com",
    "AMD": "amd.com",
    "INTC": "intel.com",
    "CSCO": "cisco.com",
    "AVGO": "broadcom.com",
    "QCOM": "qualcomm.com",
    "TXN": "ti.com",
    "NOW": "servicenow.com",
    "INTU": "intuit.com",
    "IBM": "ibm.com",
    "PYPL": "paypal.com",
    "UBER": "uber.com",
    "ABNB": "airbnb.com",
    "PANW": "paloaltonetworks.com",
    "SNPS": "synopsys.com",
    "CDNS": "cadence.com",
    "CRWD": "crowdstrike.com",
    "PLTR": "palantir.com",
}


def derive_sp500_domain(name: str, symbol: str) -> str:
    """Derive clean, authoritative domain for S&P 500 company."""
    if symbol in KNOWN_DOMAINS:
        return KNOWN_DOMAINS[symbol]
    
    clean = re.sub(r"(?i)\b(inc|corp|corporation|co|company|holdings|group|plc|llc|class\s+[a-z]|the)\b", "", name)
    clean = re.sub(r"[^a-zA-Z0-9]", "", clean).lower()
    if len(clean) >= 3:
        return f"{clean}.com"
    return f"{symbol.lower()}.com"


@dataclass
class SP500Company:
    symbol: str             # Ticker e.g. "AAPL", "MSFT", "NVDA", "JPM"
    name: str               # e.g. "Apple Inc.", "Microsoft", "Nvidia"
    sector: str             # GICS Sector e.g. "Information Technology", "Financials"
    sub_industry: str       # GICS Sub-Industry e.g. "Semiconductors", "Systems Software"
    headquarters: str       # e.g. "Cupertino, California"
    date_added: str         # e.g. "1982-11-30"
    cik: str                # Central Index Key
    founded: str            # Year founded
    domain: str
    careers_url: Optional[str] = None
    key_roles: List[str] = field(default_factory=lambda: [
        "Software Engineer", "Backend Developer", "Staff Engineer",
        "Engineering Director", "Solutions Architect", "Data Engineer"
    ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "sub_industry": self.sub_industry,
            "headquarters": self.headquarters,
            "date_added": self.date_added,
            "cik": self.cik,
            "founded": self.founded,
            "domain": self.domain,
            "careers_url": self.careers_url,
            "key_roles": self.key_roles,
        }


_SP500_CACHE: Optional[List[SP500Company]] = None


def load_sp500_from_csv() -> List[SP500Company]:
    """Load all 503 official S&P 500 companies from CSV."""
    global _SP500_CACHE
    if _SP500_CACHE is not None:
        return _SP500_CACHE

    companies: List[SP500Company] = []
    if not CSV_PATH.exists():
        logger.warning(f"S&P 500 CSV not found at {CSV_PATH}.")
        return []

    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row.get("Symbol", "").strip()
                name = row.get("Security", "").strip()
                sector = row.get("GICS Sector", "").strip()
                sub_ind = row.get("GICS Sub-Industry", "").strip()
                hq = row.get("Headquarters Location", "").strip()
                dt_added = row.get("Date added", "").strip()
                cik = row.get("CIK", "").strip()
                founded = row.get("Founded", "").strip()

                if symbol and name:
                    domain = derive_sp500_domain(name, symbol)
                    careers_url = f"https://www.{domain}/careers"
                    companies.append(SP500Company(
                        symbol=symbol,
                        name=name,
                        sector=sector,
                        sub_industry=sub_ind,
                        headquarters=hq,
                        date_added=dt_added,
                        cik=cik,
                        founded=founded,
                        domain=domain,
                        careers_url=careers_url,
                    ))

        _SP500_CACHE = companies
        logger.info(f"Loaded {len(companies)} official S&P 500 companies from dataset.")
    except Exception as exc:
        logger.error(f"Failed to load S&P 500 CSV: {exc}")

    return companies


# Pre-load cache
SP500_REGISTRY: List[SP500Company] = load_sp500_from_csv()


def get_all_sp500_companies() -> List[SP500Company]:
    """Return all 503 official S&P 500 companies."""
    return load_sp500_from_csv()


def filter_by_sector(sector_name: str) -> List[SP500Company]:
    """Filter companies by GICS Sector (e.g. 'Information Technology', 'Financials')."""
    s_lower = sector_name.strip().lower()
    return [c for c in get_all_sp500_companies() if s_lower in c.sector.lower()]


def filter_by_sub_industry(sub_industry_name: str) -> List[SP500Company]:
    """Filter companies by GICS Sub-Industry (e.g. 'Semiconductors', 'Systems Software')."""
    sub_lower = sub_industry_name.strip().lower()
    return [c for c in get_all_sp500_companies() if sub_lower in c.sub_industry.lower()]


def search_by_symbol(symbol: str) -> Optional[SP500Company]:
    """Find S&P 500 company by ticker symbol."""
    sym_upper = symbol.strip().upper()
    for c in get_all_sp500_companies():
        if c.symbol == sym_upper:
            return c
    return None


def search_by_keyword(query: str) -> List[SP500Company]:
    """Search companies by symbol, company name, sector, or sub-industry."""
    q_lower = query.strip().lower()
    return [
        c for c in get_all_sp500_companies()
        if q_lower in c.name.lower() or q_lower in c.symbol.lower() or q_lower in c.sector.lower() or q_lower in c.sub_industry.lower()
    ]


def get_sector_breakdown() -> Dict[str, int]:
    """Return distribution of companies across all 11 GICS Sectors."""
    from collections import Counter
    return dict(Counter(c.sector for c in get_all_sp500_companies()))
