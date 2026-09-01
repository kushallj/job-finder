"""
nifty500_registry.py — Official Nifty 500 Companies Database from National Stock Exchange (NSE India).

Dynamically loads and indexes all 500 official companies listed on the NSE Nifty 500 index
sourced directly from the official NSE Archives (ind_nifty500list.csv).
"""
from __future__ import annotations

import csv
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nifty500_registry")

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "nifty500_official.csv"


def derive_domain(company_name: str, symbol: str) -> str:
    """Derive clean, standard web domain from company name and symbol."""
    clean = re.sub(r"(?i)\b(ltd|limited|india|corporation|holdings|enterprises|industries|technologies|finance|bank|services|infra|co|corp)\b", "", company_name)
    clean = re.sub(r"[^a-zA-Z0-9]", "", clean).lower()
    if len(clean) >= 3:
        return f"{clean}.com"
    return f"{symbol.lower()}.com"


@dataclass
class Nifty500Company:
    symbol: str        # NSE Symbol e.g. "TCS", "INFY", "360ONE", "ZOMATO"
    name: str          # Official Company Name e.g. "Tata Consultancy Services Ltd."
    industry: str      # Official NSE Industry e.g. "Information Technology", "Financial Services"
    series: str        # e.g. "EQ"
    isin_code: str      # e.g. "INE466L01038"
    domain: str
    careers_url: Optional[str] = None
    key_roles: List[str] = field(default_factory=lambda: ["Software Engineer", "Backend Developer", "Full Stack Engineer", "Engineering Manager", "Data Engineer"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "industry": self.industry,
            "series": self.series,
            "isin_code": self.isin_code,
            "domain": self.domain,
            "careers_url": self.careers_url,
            "key_roles": self.key_roles,
        }


_REGISTRY_CACHE: Optional[List[Nifty500Company]] = None


def load_nifty500_from_csv() -> List[Nifty500Company]:
    """Load all 500 official companies from official NSE CSV file."""
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE

    companies: List[Nifty500Company] = []
    if not CSV_PATH.exists():
        logger.warning(f"Official NSE CSV not found at {CSV_PATH}. Loading fallback.")
        return []

    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row.get("Symbol", "").strip()
                name = row.get("Company Name", "").strip()
                industry = row.get("Industry", "").strip()
                series = row.get("Series", "EQ").strip()
                isin = row.get("ISIN Code", "").strip()

                if symbol and name:
                    domain = derive_domain(name, symbol)
                    careers_url = f"https://www.{domain}/careers"
                    companies.append(Nifty500Company(
                        symbol=symbol,
                        name=name,
                        industry=industry,
                        series=series,
                        isin_code=isin,
                        domain=domain,
                        careers_url=careers_url,
                    ))

        _REGISTRY_CACHE = companies
        logger.info(f"Loaded {len(companies)} official Nifty 500 companies from NSE dataset.")
    except Exception as exc:
        logger.error(f"Failed to load official Nifty 500 CSV: {exc}")

    return companies


# Pre-load registry
NIFTY_500_REGISTRY: List[Nifty500Company] = load_nifty500_from_csv()


def get_all_nifty500_companies() -> List[Nifty500Company]:
    """Return all 500 official Nifty 500 companies."""
    return load_nifty500_from_csv()


def filter_by_industry(industry_name: str) -> List[Nifty500Company]:
    """Filter companies by official NSE industry name."""
    ind_lower = industry_name.strip().lower()
    return [c for c in get_all_nifty500_companies() if ind_lower in c.industry.lower()]


def filter_by_sector(sector_name: str) -> List[Nifty500Company]:
    """Alias for filter_by_industry."""
    return filter_by_industry(sector_name)


def search_by_symbol(symbol: str) -> Optional[Nifty500Company]:
    """Find company by NSE symbol."""
    sym_upper = symbol.strip().upper()
    for c in get_all_nifty500_companies():
        if c.symbol == sym_upper:
            return c
    return None


def search_by_keyword(query: str) -> List[Nifty500Company]:
    """Search companies by symbol, company name, or industry substring."""
    q_lower = query.strip().lower()
    return [
        c for c in get_all_nifty500_companies()
        if q_lower in c.name.lower() or q_lower in c.symbol.lower() or q_lower in c.industry.lower()
    ]


def get_industry_breakdown() -> Dict[str, int]:
    """Return count of companies across all official NSE industries."""
    from collections import Counter
    return dict(Counter(c.industry for c in get_all_nifty500_companies()))
