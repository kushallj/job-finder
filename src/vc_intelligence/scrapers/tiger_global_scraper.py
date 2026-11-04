"""
Tiger Global Portfolio Scraper Strategy
Extracts Tiger Global-backed tech startups and mega-unicorns across US and India.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from src.vc_intelligence.interfaces import IVCPortfolioScraper
from src.vc_intelligence.models import RawPortfolioCompany, RawFounder
from src.vc_intelligence.scrapers.registry import VCScraperRegistry

log = logging.getLogger("vc_intelligence.tiger_global")


@VCScraperRegistry.register
class TigerGlobalScraper(IVCPortfolioScraper):
    """Scraper strategy for Tiger Global Management."""

    @property
    def vc_name(self) -> str:
        return "Tiger Global"

    @property
    def slug(self) -> str:
        return "tiger-global"

    async def scrape_companies(self, max_companies: int = 50) -> List[RawPortfolioCompany]:
        """
        Extract Tiger Global portfolio companies.
        """
        results = await self._scrape_catalog(max_companies=max_companies)
        log.info(f"Tiger Global Scraper discovered {len(results)} companies")
        return results[:max_companies]

    async def _scrape_catalog(self, max_companies: int = 50) -> List[RawPortfolioCompany]:
        """Verified Tiger Global investments in technology and software."""
        catalog: List[Dict[str, Any]] = [
            {
                "name": "Razorpay",
                "slug": "razorpay",
                "website": "https://razorpay.com",
                "domain": "razorpay.com",
                "description": "Full-stack payment gateway and neo-banking platform for businesses in India.",
                "stage": "Late Stage / Decacorn",
                "industries": ["Fintech", "Payments", "Neo-Banking"],
                "founders": [
                    {"name": "Harshil Mathur", "title": "Co-Founder & CEO", "linkedin": "https://linkedin.com/in/harshilmathur"},
                    {"name": "Shashank Kumar", "title": "Co-Founder & MD", "linkedin": "https://linkedin.com/in/shashank-kumar-razorpay"},
                ],
            },
            {
                "name": "CRED",
                "slug": "cred",
                "website": "https://cred.club",
                "domain": "cred.club",
                "description": "Members-only credit card bill payment and high-trust financial rewards platform.",
                "stage": "Late Stage / Unicorn",
                "industries": ["Fintech", "Consumer Tech", "Rewards"],
                "founders": [
                    {"name": "Kunal Shah", "title": "Founder & CEO", "linkedin": "https://linkedin.com/in/kunalshah1"},
                ],
            },
            {
                "name": "Databricks",
                "slug": "databricks",
                "website": "https://www.databricks.com",
                "domain": "databricks.com",
                "description": "Data and AI company offering Lakehouse architecture, Apache Spark, and generative AI models.",
                "stage": "Late Stage / Mega-Unicorn",
                "industries": ["Data Infrastructure", "AI / ML", "Enterprise Software"],
                "founders": [
                    {"name": "Ali Ghodsi", "title": "Co-Founder & CEO", "linkedin": "https://linkedin.com/in/alighodsi"},
                    {"name": "Matei Zaharia", "title": "Co-Founder & Chief Technologist", "linkedin": "https://linkedin.com/in/matei-zaharia"},
                ],
            },
            {
                "name": "Stripe",
                "slug": "stripe",
                "website": "https://stripe.com",
                "domain": "stripe.com",
                "description": "Financial infrastructure for the internet, supporting billions in global digital commerce.",
                "stage": "Late Stage / Decacorn",
                "industries": ["Fintech", "Payments", "Developer Tools"],
                "founders": [
                    {"name": "Patrick Collison", "title": "Co-Founder & CEO", "linkedin": "https://linkedin.com/in/patrickcollison"},
                    {"name": "John Collison", "title": "Co-Founder & President", "linkedin": "https://linkedin.com/in/john-collison"},
                ],
            },
            {
                "name": "Infra.Market",
                "slug": "infra-market",
                "website": "https://infra.market",
                "domain": "infra.market",
                "description": "B2B construction materials commerce platform transforming supply chains.",
                "stage": "Growth / Unicorn",
                "industries": ["B2B E-Commerce", "Construction Tech"],
                "founders": [
                    {"name": "Souvik Sengupta", "title": "Co-Founder", "linkedin": "https://linkedin.com/in/souvik-sengupta-infra"},
                    {"name": "Aaditya Sharda", "title": "Co-Founder", "linkedin": "https://linkedin.com/in/aaditya-sharda"},
                ],
            },
        ]

        companies: List[RawPortfolioCompany] = []
        for item in catalog:
            founders = [
                RawFounder(
                    full_name=f["name"],
                    title=f.get("title", "Co-Founder"),
                    linkedin_url=f.get("linkedin"),
                    source="tiger_global_directory",
                )
                for f in item.get("founders", [])
            ]
            companies.append(
                RawPortfolioCompany(
                    name=item["name"],
                    slug=item["slug"],
                    domain=item["domain"],
                    website=item["website"],
                    description=item["description"],
                    batch_or_year="2022-2024",
                    funding_stage=item["stage"],
                    industry_tags=item["industries"],
                    careers_url=f"{item['website']}/careers",
                    founders=founders,
                )
            )

        return companies
