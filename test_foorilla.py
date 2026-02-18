#!/usr/bin/env python3
"""
Test Foorilla scraper integration
"""

import asyncio
import aiohttp
from src.scrapers.foorilla_scraper import FoorillaScraper

async def test_foorilla():
    """Test Foorilla scraper"""
    print("🧪 Testing Foorilla scraper...")
    
    async with aiohttp.ClientSession() as session:
        scraper = FoorillaScraper(session)
        
        # Test search
        jobs = await scraper.search("python developer", "remote")
        
        print(f"\n📊 Foorilla Test Results:")
        print(f"   Jobs found: {len(jobs)}")
        
        if jobs:
            print(f"\n📋 Sample Jobs:")
            for i, job in enumerate(jobs[:3]):
                print(f"   {i+1}. {job.title} at {job.company}")
                print(f"      Location: {job.location}")
                print(f"      URL: {job.url}")
                print(f"      Description: {job.description[:100]}...")
                print()
        else:
            print("   No jobs found - this might be expected if:")
            print("   - Foorilla requires authentication")
            print("   - The site structure has changed")
            print("   - Rate limiting is in effect")

if __name__ == "__main__":
    asyncio.run(test_foorilla())