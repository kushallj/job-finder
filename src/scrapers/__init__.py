"""
Legacy scrapers. Job fetching goes through src/job_sources (the single entry point);
modules here are wrapped there as sources (ats_scraper, jobspy, foorilla, firecrawl,
company career-page scrapers) or used by the VC-intelligence scrapers via BaseScraper.
"""

try:
    from src.scrapers.base import BaseScraper
except ImportError:
    pass
