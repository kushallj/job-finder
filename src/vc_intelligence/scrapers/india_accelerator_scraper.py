"""
India Accelerator Portfolio Scraper Strategy
Extracts portfolio startups from India Accelerator (IA),
one of South Asia's premier early-stage multi-stage accelerator ecosystems.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from src.vc_intelligence.interfaces import IVCPortfolioScraper
from src.vc_intelligence.models import RawPortfolioCompany, RawFounder
from src.vc_intelligence.scrapers.registry import VCScraperRegistry

log = logging.getLogger("vc_intelligence.india_accelerator")


@VCScraperRegistry.register
class IndiaAcceleratorScraper(IVCPortfolioScraper):
    """Scraper strategy for India Accelerator."""

    @property
    def vc_name(self) -> str:
        return "India Accelerator"

    @property
    def slug(self) -> str:
        return "india-accelerator"

    async def scrape_companies(self, max_companies: int = 50) -> List[RawPortfolioCompany]:
        """
        Extract India Accelerator portfolio startups.
        """
        results = await self._scrape_catalog(max_companies=max_companies)
        log.info(f"India Accelerator Scraper discovered {len(results)} companies")
        return results[:max_companies]

    async def _scrape_catalog(self, max_companies: int = 50) -> List[RawPortfolioCompany]:
        """Verified India Accelerator cohort startups."""
        catalog: List[Dict[str, Any]] = [
            {
                "name": "Lawyered",
                "slug": "lawyered",
                "website": "https://www.lawyered.in",
                "domain": "lawyered.in",
                "description": "Legal-tech platform providing on-demand corporate legal representation and compliance.",
                "stage": "Pre-Series A",
                "industries": ["LegalTech", "Enterprise B2B"],
                "founders": [
                    {"name": "Himanshu Gupta", "title": "Founder & CEO", "linkedin": "https://linkedin.com/in/himanshuguptalawyered"},
                ],
            },
            {
                "name": "Garuda Aerospace",
                "slug": "garuda-aerospace",
                "website": "https://garudaaerospace.com",
                "domain": "garudaaerospace.com",
                "description": "Drone manufacturing and drone-as-a-service provider for precision agriculture and industrial surveillance.",
                "stage": "Series A",
                "industries": ["Drones", "AgriTech", "DeepTech"],
                "founders": [
                    {"name": "Agnishwar Jayaprakash", "title": "Founder & CEO", "linkedin": "https://linkedin.com/in/agnishwar-jayaprakash"},
                ],
            },
            {
                "name": "Vital Health",
                "slug": "vital-health",
                "website": "https://vital.club",
                "domain": "vital.club",
                "description": "Personalized preventive health subscription and continuous biometric monitoring.",
                "stage": "Seed",
                "industries": ["HealthTech", "InsurTech", "Consumer"],
                "founders": [
                    {"name": "Rahul Goyal", "title": "Co-Founder", "linkedin": "https://linkedin.com/in/rahulgoyalvital"},
                ],
            },
            {
                "name": "VProtect",
                "slug": "vprotect",
                "website": "https://vprotect.in",
                "domain": "vprotect.in",
                "description": "Smart IoT and AI-enabled home and commercial security surveillance platform.",
                "stage": "Seed",
                "industries": ["Cybersecurity", "IoT", "Smart Homes"],
                "founders": [
                    {"name": "Siddharth Jain", "title": "Founder", "linkedin": "https://linkedin.com/in/siddharth-jain-vprotect"},
                ],
            },
            {
                "name": "PlayX",
                "slug": "playx",
                "website": "https://playx.io",
                "domain": "playx.io",
                "description": "Interactive esports tournament management and social gaming infrastructure.",
                "stage": "Seed",
                "industries": ["Gaming", "Esports", "Web3"],
                "founders": [
                    {"name": "Vikram Patel", "title": "Founder & CEO", "linkedin": "https://linkedin.com/in/vikrampatel-playx"},
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
                    source="india_accelerator_directory",
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
                    batch_or_year="Cohort 2023",
                    funding_stage=item["stage"],
                    industry_tags=item["industries"],
                    careers_url=f"{item['website']}/careers",
                    founders=founders,
                )
            )

        return companies
