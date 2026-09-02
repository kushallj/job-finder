"""
fetch_sp500_tech_jobs.py — CLI Script to Fetch Live Tech Jobs for S&P 500 Companies.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrapers.sp500_job_scraper import SP500JobScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def main():
    scraper = SP500JobScraper()
    result = await scraper.crawl_sp500_tech_jobs(limit_companies=80, use_serpapi_for_giants=True)
    print("\n" + "="*60)
    print("  S&P 500 TECH JOBS SOURCING SUMMARY")
    print("="*60)
    print(f"  • Companies Scanned:       {result.get('companies_scanned')}")
    print(f"  • Total Tech Jobs Found:   {result.get('total_jobs_discovered')}")
    print(f"  • New Jobs Saved to DB:    {result.get('total_jobs_saved')}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
