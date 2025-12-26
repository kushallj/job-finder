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
        """Generate unique ID for job"""
        unique_string = f"{job.get('title', '')}-{job.get('company', '')}-{job.get('location', '')}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def normalize_job(self, job: Dict) -> Dict:
        """Normalize job data structure"""
        job['job_id'] = self.generate_job_id(job)
        job['source'] = self.source_name
        return job