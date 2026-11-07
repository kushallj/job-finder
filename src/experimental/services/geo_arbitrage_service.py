"""
geo_arbitrage_service.py — Global Geo-Arbitrage & Cross-Border Opportunity Engine (Agent 21).
Unlocks high-income relocation & remote tech opportunities across Japan, China/Singapore, and Europe,
with tax-adjusted net take-home and Purchasing Power Parity (PPP) savings calculators.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("geo_arbitrage_service")

GEO_MARKETS: List[Dict[str, Any]] = [
    {
        "market_id": "japan_tokyo",
        "region": "Asia-Pacific (Japan)",
        "city": "Tokyo",
        "currency": "JPY",
        "currency_symbol": "¥",
        "average_gross_salary_range": "¥12,000,000 – ¥22,000,000 JPY ($80k – $150k USD)",
        "english_adoption_score": 92,
        "visa_type": "Highly Skilled Foreign Professional (HSFP) / Engineer Visa",
        "pr_timeline_months": 12,  # 1 year PR with 80+ HSFP points
        "key_employers": ["Mercari", "Woven by Toyota", "PayPay", "LINE Yahoo", "Rakuten"],
        "tax_bracket_effective_percent": 28.5,
        "col_index_vs_bangalore": 2.1,
        "fx_to_inr": 0.58,
        "visa_sponsorship_status": "FULL_RELOCATION_SPONSORED",
        "relocation_perks": "Flight + Temporary Housing (1-2 mo) + Visa & Family Sponsorship + Language Lessons",
    },
    {
        "market_id": "singapore_apac",
        "region": "Asia-Pacific (Singapore)",
        "city": "Singapore",
        "currency": "SGD",
        "currency_symbol": "S$",
        "average_gross_salary_range": "S$140,000 – S$260,000 SGD ($105k – $195k USD)",
        "english_adoption_score": 100,
        "visa_type": "Employment Pass (EP) / ONE Pass (Top Tier)",
        "pr_timeline_months": 36,
        "key_employers": ["ByteDance / TikTok", "Grab", "Sea / Shopee", "Tencent Overseas", "Stripe SG"],
        "tax_bracket_effective_percent": 15.0,  # Ultra-low income tax
        "col_index_vs_bangalore": 2.8,
        "fx_to_inr": 64.5,
        "visa_sponsorship_status": "FULL_RELOCATION_SPONSORED",
        "relocation_perks": "Flight + Tax Concessions + 0% Capital Gains + Central Tech Hub",
    },
    {
        "market_id": "netherlands_amsterdam",
        "region": "Europe (Netherlands)",
        "city": "Amsterdam",
        "currency": "EUR",
        "currency_symbol": "€",
        "average_gross_salary_range": "€85,000 – €145,000 EUR ($92k – $160k USD)",
        "english_adoption_score": 98,
        "visa_type": "Highly Skilled Migrant (Kennismigrant) + 30% Tax Ruling",
        "pr_timeline_months": 60,
        "key_employers": ["Booking.com", "Adyen", "Uber Amsterdam", "ASML", "Miro", "Databricks NL"],
        "tax_bracket_effective_percent": 26.0,  # Reduced via 30% ruling
        "col_index_vs_bangalore": 2.5,
        "fx_to_inr": 92.5,
        "visa_sponsorship_status": "FULL_RELOCATION_SPONSORED",
        "relocation_perks": "30% Tax-Free Income (5 Years) + Fast-Track Kennismigrant Permit + 25+ Vacation Days",
    },
    {
        "market_id": "germany_berlin_munich",
        "region": "Europe (Germany)",
        "city": "Berlin / Munich",
        "currency": "EUR",
        "currency_symbol": "€",
        "average_gross_salary_range": "€80,000 – €135,000 EUR ($88k – $148k USD)",
        "english_adoption_score": 90,
        "visa_type": "EU Blue Card (Fast-Track Permanent Residence)",
        "pr_timeline_months": 21,  # 21 months with B1 German, 27 months standard
        "key_employers": ["Zalando", "Delivery Hero", "N26", "Celonis", "Personio", "BMW Tech"],
        "tax_bracket_effective_percent": 38.0,
        "col_index_vs_bangalore": 2.2,
        "fx_to_inr": 92.5,
        "visa_sponsorship_status": "FULL_RELOCATION_SPONSORED",
        "relocation_perks": "EU Blue Card + Path to German Citizenship (3-5 yrs) + Free Healthcare & Education",
    },
    {
        "market_id": "uk_london",
        "region": "Europe (United Kingdom)",
        "city": "London",
        "currency": "GBP",
        "currency_symbol": "£",
        "average_gross_salary_range": "£90,000 – £170,000 GBP ($115k – $218k USD)",
        "english_adoption_score": 100,
        "visa_type": "Skilled Worker Visa / Global Talent Visa (No Sponsor Needed)",
        "pr_timeline_months": 36,  # 3 yrs on Global Talent
        "key_employers": ["Monzo", "Revolut", "DeepMind", "Checkout.com", "Bloomberg London"],
        "tax_bracket_effective_percent": 34.0,
        "col_index_vs_bangalore": 3.0,
        "fx_to_inr": 110.0,
        "visa_sponsorship_status": "FULL_RELOCATION_SPONSORED",
        "relocation_perks": "Global Talent Fast-Track + World Financial Capital + Direct US Entity Mobility",
    },
]


class PppCalculationRequest(BaseModel):
    gross_annual_salary: float = Field(..., description="Gross annual compensation in local currency")
    market_id: str = Field(..., description="Target market identifier e.g. japan_tokyo, netherlands_amsterdam")
    current_inr_ctc_lpa: Optional[float] = Field(default=35.0, description="Current compensation in India in INR Lakhs")


class GeoArbitrageService:
    """Calculates net purchasing power parity (PPP), tax take-home, and visa pathways."""

    def get_markets(self, region_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        markets = GEO_MARKETS
        if region_filter:
            rf = region_filter.lower().strip()
            markets = [m for m in markets if rf in m["region"].lower() or rf in m["city"].lower()]
        return markets

    def calculate_net_ppp(
        self,
        gross_annual_salary: float,
        market_id: str,
        current_inr_ctc_lpa: float = 35.0,
    ) -> Dict[str, Any]:
        market = next((m for m in GEO_MARKETS if m["market_id"] == market_id), GEO_MARKETS[0])

        tax_rate = market["tax_bracket_effective_percent"] / 100.0
        net_local_annual = gross_annual_salary * (1.0 - tax_rate)
        net_local_monthly = net_local_annual / 12.0

        # Foreign exchange conversion
        fx_inr = market["fx_to_inr"]
        gross_inr_annual = gross_annual_salary * fx_inr
        net_inr_annual = net_local_annual * fx_inr
        net_inr_monthly = net_inr_annual / 12.0
        gross_inr_lakhs = round(gross_inr_annual / 100000.0, 2)
        net_inr_lakhs = round(net_inr_annual / 100000.0, 2)
        usd_to_inr_rate = 86.5
        net_usd_annual = round(net_inr_annual / usd_to_inr_rate, 2)

        # Baseline cost of living deduction (monthly rent + living for comfortable engineer lifestyle)
        col_multiplier = market["col_index_vs_bangalore"]
        # Monthly base expenses in destination in INR
        est_monthly_expenses_inr = round(65000 * col_multiplier, 0)
        net_monthly_savings_inr = max(0.0, net_inr_monthly - est_monthly_expenses_inr)
        annual_savings_inr_lakhs = round((net_monthly_savings_inr * 12) / 100000.0, 2)

        # Current India baseline savings comparison (assuming 30% tax on current CTC and ₹50k/mo living cost)
        curr_net_inr_annual = current_inr_ctc_lpa * 100000 * 0.70
        curr_net_inr_monthly = curr_net_inr_annual / 12.0
        curr_monthly_savings_inr = max(0.0, curr_net_inr_monthly - 50000)
        curr_annual_savings_inr_lakhs = round((curr_monthly_savings_inr * 12) / 100000.0, 2)

        savings_delta_multiplier = round(
            (annual_savings_inr_lakhs / max(curr_annual_savings_inr_lakhs, 1.0)), 2
        )

        return {
            "status": "success",
            "market": market,
            "financials": {
                "gross_salary_local": gross_annual_salary,
                "currency": market["currency"],
                "effective_tax_percent": market["tax_bracket_effective_percent"],
                "net_salary_local_annual": round(net_local_annual, 2),
                "net_salary_local_monthly": round(net_local_monthly, 2),
                "gross_inr_lakhs": gross_inr_lakhs,
                "net_inr_lakhs": net_inr_lakhs,
                "net_usd_annual": net_usd_annual,
                "estimated_monthly_expenses_inr": est_monthly_expenses_inr,
                "net_monthly_savings_inr": round(net_monthly_savings_inr, 2),
                "annual_savings_inr_lakhs": annual_savings_inr_lakhs,
                "india_baseline_annual_savings_lakhs": curr_annual_savings_inr_lakhs,
                "savings_expansion_multiplier": savings_delta_multiplier,
            },
            "visa_dossier": {
                "visa_name": market["visa_type"],
                "permanent_residence_timeline": f"{market['pr_timeline_months']} months",
                "relocation_perks": market["relocation_perks"],
                "employer_sponsorship": market["visa_sponsorship_status"],
            },
            "takeaway_summary": f"Relocating to {market['city']} expands net annual liquid savings by {savings_delta_multiplier}x (saving ₹{annual_savings_inr_lakhs}L/yr vs ₹{curr_annual_savings_inr_lakhs}L/yr in India), with PR eligibility in {market['pr_timeline_months']} months.",
        }
