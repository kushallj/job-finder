import httpx
import asyncio
from typing import List, Dict
from src.scrapers.base import BaseScraper
from src.config import settings
from datetime import datetime

class APIJobScraper(BaseScraper):
    """Scrape jobs from API sources"""
    
    def __init__(self):
        super().__init__("api_aggregator")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_jobs(self, query: str = "software engineer", location: str = "india") -> List[Dict]:
        """Implement abstract method: fetch jobs from all API sources"""
        return await self.fetch_all(query=query)
    
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
    
    async def fetch_all(self, query: str = "software engineer") -> List[Dict]:
        """Fetch from all API sources"""
        tasks = [
            self.fetch_remotive(),
            self.fetch_adzuna(query)
        ]
        
        results = await asyncio.gather(*tasks)
        all_jobs = [job for sublist in results for job in sublist]
        
        return all_jobs
    
    async def close(self):
        await self.client.aclose()