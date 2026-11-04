"""
VC Intelligence Scrapers Package
Automatically imports and registers all default VC scraper strategies into VCScraperRegistry.
"""

from src.vc_intelligence.scrapers.registry import VCScraperRegistry
from src.vc_intelligence.scrapers.yc_scraper import YCScraper
from src.vc_intelligence.scrapers.accel_scraper import AccelScraper
from src.vc_intelligence.scrapers.blume_scraper import BlumeScraper
from src.vc_intelligence.scrapers.tiger_global_scraper import TigerGlobalScraper
from src.vc_intelligence.scrapers.india_accelerator_scraper import IndiaAcceleratorScraper

__all__ = [
    "VCScraperRegistry",
    "YCScraper",
    "AccelScraper",
    "BlumeScraper",
    "TigerGlobalScraper",
    "IndiaAcceleratorScraper",
]
