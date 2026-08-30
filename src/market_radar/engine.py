from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import (
    RemoteArbitrageRole,
    GCCHubInsight,
    MarketRadarResponse,
)

USD_INR_RATE = 87.20
EUR_INR_RATE = 94.50


class MarketRadarEngine:
    """
    Surfaces high-paying global USD/EUR remote contracts with purchasing power parity (PPP)
    and maps top Indian GCC (Global Capability Center) tech hubs.
    """

    def get_market_radar(self) -> MarketRadarResponse:
        roles = [
            RemoteArbitrageRole(
                title="Staff Backend Engineer (Async Distributed Systems)",
                company="Supabase / GitBook Scale",
                country="United States (Remote)",
                currency="USD",
                base_comp_range="$140k – $185k / yr",
                inr_equivalent_range="₹1.22 Cr – ₹1.61 Cr / yr",
                ppp_multiplier=3.6,
                tz_overlap_hours="3 hrs async overlap",
                tax_advantage="Eligible for Section 44ADA (50% presumptive income tax)",
                source_url="https://remoteok.com",
                skills_required=["Python", "FastAPI", "PostgreSQL", "Distributed Systems"],
            ),
            RemoteArbitrageRole(
                title="Senior Platform & Reliability Engineer",
                company="European Fintech / Scale-Up",
                country="Germany / UK (Remote)",
                currency="EUR",
                base_comp_range="€110k – €145k / yr",
                inr_equivalent_range="₹1.04 Cr – ₹1.37 Cr / yr",
                ppp_multiplier=3.2,
                tz_overlap_hours="5–6 hrs European timezone overlap",
                tax_advantage="Direct B2B EUR Wire Transfer",
                source_url="https://weworkremotely.com",
                skills_required=["Kubernetes", "Docker", "AWS", "Go / Python"],
            ),
            RemoteArbitrageRole(
                title="Principal AI Infrastructure Engineer",
                company="Silicon Valley AI Lab",
                country="San Francisco (Remote Global)",
                currency="USD",
                base_comp_range="$165k – $220k / yr",
                inr_equivalent_range="₹1.44 Cr – ₹1.92 Cr / yr",
                ppp_multiplier=3.8,
                tz_overlap_hours="4 hrs PST morning overlap",
                tax_advantage="50% 44ADA Tax Deduction + US W8-BEN",
                source_url="https://wellfound.com",
                skills_required=["LLMs", "CUDA / PyTorch", "FastAPI", "Low-Latency Caching"],
            ),
        ]

        gcc_hubs = [
            GCCHubInsight(
                hub_city="Bangalore Tech Corridor",
                active_openings=14200,
                top_employers=["Goldman Sachs GCC", "Walmart Global Tech", "Target Enterprise", "JPMorgan Chase"],
                median_senior_ctc="₹42L – ₹68L / yr",
                growth_yoy="+24% YoY hiring expansion",
            ),
            GCCHubInsight(
                hub_city="Hyderabad Cyberabad",
                active_openings=9800,
                top_employers=["Microsoft India R&D", "Google India", "ServiceNow", "Qualcomm GCC"],
                median_senior_ctc="₹38L – ₹62L / yr",
                growth_yoy="+19% YoY hiring expansion",
            ),
            GCCHubInsight(
                hub_city="NCR (Gurugram / Noida)",
                active_openings=7600,
                top_employers=["Airtel X Labs", "Zomato / Blinkit Tech", "MakeMyTrip", "American Express GCC"],
                median_senior_ctc="₹36L – ₹58L / yr",
                growth_yoy="+16% YoY hiring expansion",
            ),
        ]

        return MarketRadarResponse(
            status="success",
            usd_to_inr_rate=USD_INR_RATE,
            eur_to_inr_rate=EUR_INR_RATE,
            remote_global_roles=roles,
            top_gcc_hubs=gcc_hubs,
            timestamp=datetime.utcnow().isoformat(),
        )


market_radar_engine = MarketRadarEngine()
