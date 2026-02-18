import httpx
import asyncio
from typing import List, Dict
from src.scrapers.base import BaseScraper
from src.scrapers.multi_platform_scraper import MultiPlatformJobScraper, JobPosting
from src.config import settings
from datetime import datetime

class APIJobScraper(BaseScraper):
    """Enhanced scraper that combines API sources with multi-platform scraping"""
    
    def __init__(self):
        super().__init__("enhanced_aggregator")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.multi_platform_scraper = MultiPlatformJobScraper()
    
    async def fetch_jobs(self, query: str = "software engineer", location: str = "india") -> List[Dict]:
        """Implement abstract method: fetch jobs from all sources"""
        return await self.fetch_all(query=query, location=location)
    
    async def fetch_remotive(self) -> List[Dict]:
        """Fetch from Remotive"""
        try:
            response = await self.client.get("https://remotive.com/api/remote-jobs")
            data = response.json()
            
            jobs = []
            for job in data.get('jobs', [])[:50]:
                jobs.append(self.normalize_job({
                    'title': job.get('title'),
                    'company': job.get('company_name'),
                    'location': job.get('candidate_required_location', 'Remote'),
                    'url': job.get('url'),
                    'description': job.get('description', ''),
                    'tags': job.get('tags', []),
                    'posted_date': job.get('publication_date')
                }))
            return jobs
        except Exception as e:
            print(f"❌ Remotive error: {e}")
            return []
    
    async def fetch_adzuna(self, query: str = "software engineer", location: str = "india") -> List[Dict]:
        """Fetch from Adzuna"""
        try:
            url = f"https://api.adzuna.com/v1/api/jobs/in/search/1"
            params = {
                'app_id': settings.adzuna_app_id,
                'app_key': settings.adzuna_app_key,
                'results_per_page': 50,
                'what': query,
                'where': location
            }
            
            response = await self.client.get(url, params=params)
            data = response.json()
            
            jobs = []
            for job in data.get('results', []):
                jobs.append(self.normalize_job({
                    'title': job.get('title'),
                    'company': job.get('company', {}).get('display_name', 'N/A'),
                    'location': job.get('location', {}).get('display_name', 'N/A'),
                    'url': job.get('redirect_url'),
                    'description': job.get('description', ''),
                    'posted_date': job.get('created')
                }))
            return jobs
        except Exception as e:
            print(f"❌ Adzuna error: {e}")
            return []
    
    async def fetch_foorilla(self, query: str = "software engineer", location: str = "") -> List[Dict]:
        """Fetch from Foorilla"""
        try:
            from src.scrapers.foorilla_scraper import FoorillaScraper
            
            # Create a temporary session for Foorilla
            timeout = httpx.Timeout(30.0)
            async with httpx.AsyncClient(timeout=timeout) as temp_client:
                # Convert httpx client to aiohttp session (simplified)
                import aiohttp
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    foorilla_scraper = FoorillaScraper(session)
                    job_postings = await foorilla_scraper.search(query, location)
                    
                    # Convert JobPosting objects to dict format
                    jobs = []
                    for job_posting in job_postings:
                        job_dict = {
                            'title': job_posting.title,
                            'company': job_posting.company,
                            'location': job_posting.location,
                            'url': job_posting.url,
                            'description': job_posting.description,
                            'posted_date': job_posting.posted_date,
                            'source': job_posting.source,
                            'job_id': job_posting.job_id,
                        }
                        jobs.append(self.normalize_job(job_dict))
                    
                    print(f"✅ Foorilla found {len(jobs)} jobs")
                    return jobs
                    
        except Exception as e:
            print(f"❌ Foorilla error: {e}")
            return []
    async def fetch_multi_platform_jobs(self, query: str = "software engineer") -> List[Dict]:
        """Fetch from multi-platform scraper"""
        try:
            print(f"🔍 Searching across multiple platforms for: {query}")
            
            # Get jobs from multi-platform scraper
            job_postings = await self.multi_platform_scraper.search_all_platforms()
            
            # Convert JobPosting objects to dict format
            jobs = []
            for job_posting in job_postings:
                job_dict = {
                    'title': job_posting.title,
                    'company': job_posting.company,
                    'location': job_posting.location,
                    'url': job_posting.url,
                    'description': job_posting.description,
                    'posted_date': job_posting.posted_date,
                    'source': job_posting.source,
                    'job_id': job_posting.job_id,
                    'salary': job_posting.salary,
                    'experience': job_posting.experience,
                    'skills': job_posting.skills,
                    'job_type': job_posting.job_type
                }
                jobs.append(self.normalize_job(job_dict))
            
            print(f"✅ Multi-platform search found {len(jobs)} jobs")
            return jobs
            
        except Exception as e:
            print(f"❌ Multi-platform scraper error: {e}")
            return []
    
    async def fetch_all(self, query: str = "software engineer", location: str = "india") -> List[Dict]:
        """Fetch from all sources including multi-platform scrapers"""
        print(f"🚀 Starting comprehensive job search for: {query}")
        
        tasks = [
            self.fetch_remotive(),
            self.fetch_adzuna(query, location),
            self.fetch_foorilla(query, location),
            self.fetch_multi_platform_jobs(query)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_jobs = []
        
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_jobs.extend(result)
                print(f"✅ Source {i+1} returned {len(result)} jobs")
            else:
                print(f"❌ Source {i+1} failed: {result}")
        
        # Remove duplicates based on URL and title
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            identifier = f"{job.get('company', '').lower()}_{job.get('title', '').lower()}"
            if identifier not in seen and job.get('title') and job.get('company'):
                seen.add(identifier)
                unique_jobs.append(job)
        
        print(f"🎯 Total unique jobs found: {len(unique_jobs)}")
        return unique_jobs
    
    async def close(self):
        await self.client.aclose()