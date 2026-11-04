"""
VC Intelligence Package
Production-grade portfolio intelligence and founder contact discovery.
"""

from src.vc_intelligence.models import (
    RawPortfolioCompany,
    RawFounder,
    VCFirmDTO,
    PortfolioCompanyDTO,
    CompanyFounderDTO,
    VCSyncRequest,
    VCSyncResponse,
)
from src.vc_intelligence.interfaces import (
    IVCPortfolioScraper,
    IFounderEnricher,
    IVCRepository,
)
from src.vc_intelligence.repository import VCIntelligenceRepository
from src.vc_intelligence.service import VCIntelligenceService
from src.vc_intelligence.scrapers.registry import VCScraperRegistry

__all__ = [
    "RawPortfolioCompany",
    "RawFounder",
    "VCFirmDTO",
    "PortfolioCompanyDTO",
    "CompanyFounderDTO",
    "VCSyncRequest",
    "VCSyncResponse",
    "IVCPortfolioScraper",
    "IFounderEnricher",
    "IVCRepository",
    "VCIntelligenceRepository",
    "VCIntelligenceService",
    "VCScraperRegistry",
]
