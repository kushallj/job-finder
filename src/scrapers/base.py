from abc import ABC, abstractmethod
from typing import List, Dict
import asyncio
import hashlib

class BaseScraper(ABC):
    """Base class for all job scrapers"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
    
    @abstractmethod
    async def fetch_jobs(self, **kwargs) -> List[Dict]:
        """Fetch jobs from source"""
        pass
    
    def generate_job_id(self, job: Dict) -> str:
        """Generate a reasonably unique ID for a job posting."""
        parts = [
            job.get('title', '').strip().lower(),
            job.get('company', '').strip().lower(),
            job.get('location', '').strip().lower(),
            job.get('url', '').strip().lower(),
            job.get('posted_date', '') or job.get('scraped_at', ''),
        ]
        unique_string = "||".join(filter(None, parts))
        if not unique_string:
            unique_string = self.source_name
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def normalize_job(self, job: Dict) -> Dict:
        """Normalize job data structure without clobbering provided IDs."""
        if not job.get('job_id'):
            job['job_id'] = self.generate_job_id(job)
        job.setdefault('source', self.source_name)
        return job