"""
Job Scrapers Package

This package provides:
- Multiple platform-specific scrapers (Naukri, LinkedIn, Indeed, etc.)
- ATS scrapers (Greenhouse, Lever)
- Unified scraper orchestrator for parallel execution and deduplication

Main components:
- ScraperOrchestrator: Unified interface for all scrapers
- create_orchestrator: Factory function for easy setup
- quick_search: Convenience function for simple searches
"""

from src.scrapers.orchestrator import (
    ScraperOrchestrator,
    ScraperConfig,
    ScraperResult,
    OrchestratorResult,
    ScraperStatus,
    NormalizedJob,
    JobDeduplicator,
    UnifiedScraperInterface,
    create_orchestrator,
    quick_search,
)
from src.scrapers.base import BaseScraper

__all__ = [
    # Orchestrator
    "ScraperOrchestrator",
    "ScraperConfig",
    "ScraperResult", 
    "OrchestratorResult",
    "ScraperStatus",
    "NormalizedJob",
    "JobDeduplicator",
    "UnifiedScraperInterface",
    "create_orchestrator",
    "quick_search",
    # Base
    "BaseScraper",
]
