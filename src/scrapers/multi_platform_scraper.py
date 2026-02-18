"""
Multi-Platform Job Search Automation System
Searches for jobs across Naukri, LinkedIn, Hirist, Wellfound, Remote.co, and top company career pages
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict
from enum import Enum
import re
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, quote_plus
import time

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JobSource(Enum):
    NAUKRI = "naukri"
    LINKEDIN = "linkedin"
    HIRIST = "hirist"
    WELLFOUND = "wellfound"
    REMOTE_CO = "remote.co"
    COMPANY_CAREER = "company_career"
    INDEED = "indeed"
    INSTAHYRE = "instahyre"
    ADZUNA = "adzuna"
    REMOTIVE = "remotive"
    FOORILLA = "foorilla"

@dataclass
class JobPosting:
    """Data class for job posting"""
    job_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_date: Optional[str] = None
    salary: Optional[str] = None
    experience: Optional[str] = None
    skills: List[str] = None
    job_type: Optional[str] = None  # Remote, Hybrid, Onsite
    scraped_at: str = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.now().isoformat()
        if self.skills is None:
            self.skills = []

class JobSearchConfig:
    """Configuration for job search"""
    
    # Your profile
    PROFILE = {
        "keywords": [
            "Backend Developer",
            "Python Developer", 
            "FastAPI Developer",
            "Django Developer",
            "Full Stack Developer",
            "Software Engineer",
            "GenAI Engineer",
            "AI Engineer",
            "Machine Learning Engineer",
            "Data Engineer",
            "DevOps Engineer",
            "React Developer",
            "Node.js Developer",

        ],
        "experience": "3",  # Years
        "locations": [
            "Delhi", "Noida", "Gurgaon", "Bangalore", "Mumbai", 
            "Pune", "Hyderabad", "Chennai", "Kolkata", "Remote"
        ],
        "skills": [
            "Python", "FastAPI", "Django", "React", "PostgreSQL", 
            "AWS", "Docker", "REST API", "GenAI", "LLM", "RAG",
            "JavaScript", "Node.js", "MongoDB", "Redis", "Kubernetes"
        ]
    }

    # Top companies to search
    TOP_COMPANIES = [
        # Indian Tech Giants
        "TCS", "Infosys", "Wipro", "HCL", "Tech Mahindra",
        
        # Global Tech Giants
        "Google", "Microsoft", "Amazon", "Meta", "Apple",
        "Netflix", "Adobe", "Salesforce", "Oracle", "SAP",
        
        # Indian Startups/Unicorns
        "Flipkart", "PhonePe", "Paytm", "Razorpay", "CRED",
        "Swiggy", "Zomato", "Ola", "Uber", "Meesho",
        "Sharechat", "Dream11", "Byju's", "Unacademy", "Upgrad",
        "Dunzo", "Licious", "Urban Company", "Zerodha", "Groww",
        
        # FinTech
        "Stripe", "Square", "Robinhood", "Coinbase", "Plaid",
        
        # AI/ML Companies
        "OpenAI", "Anthropic", "Hugging Face", "Scale AI", "Cohere",
        
        # SaaS Companies
        "Atlassian", "Slack", "Zoom", "Notion", "Figma",
        "Canva", "MongoDB", "Snowflake", "Databricks",
        
        # E-commerce
        "Shopify", "Etsy", "eBay", "Walmart", "Target",
        
        # Cloud & Infrastructure
        "Cloudflare", "DigitalOcean", "HashiCorp", "Terraform",
    ]

    # Search filters
    FILTERS = {
        "max_days_old": 7,  # Only jobs posted in last 7 days
        "remote_ok": True,
        "min_salary": None,
        "job_types": ["Full-time", "Contract"]
    }

class BaseJobScraper:
    """Base class for job scrapers"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        """Override in child classes"""
        raise NotImplementedError

    def normalize_job(self, job_data: Dict, source: str) -> JobPosting:
        """Normalize job data to JobPosting format"""
        return JobPosting(
            job_id=job_data.get('job_id', f"{source}_{hash(job_data.get('url', ''))}"),
            title=job_data.get('title', ''),
            company=job_data.get('company', ''),
            location=job_data.get('location', ''),
            description=job_data.get('description', ''),
            url=job_data.get('url', ''),
            source=source,
            posted_date=job_data.get('posted_date'),
            salary=job_data.get('salary'),
            experience=job_data.get('experience'),
            skills=job_data.get('skills', []),
            job_type=job_data.get('job_type')
        )

class NaukriScraper(BaseJobScraper):
    """Scraper for Naukri.com"""
    
    BASE_URL = "https://www.naukri.com"

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        jobs = []
        try:
            # Naukri search URL
            search_url = f"{self.BASE_URL}/jobs-in-{location.lower()}"
            params = {
                'k': keyword,
                'l': location,
                'experience': '2'
            }
            
            logger.info(f"Searching Naukri for: {keyword} in {location}")
            
            async with self.session.get(search_url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parse job listings (Naukri structure)
                    job_cards = soup.find_all('div', class_='jobTuple')
                    
                    for card in job_cards[:20]:  # Limit to 20 jobs per search
                        try:
                            title_elem = card.find('a', class_='title')
                            company_elem = card.find('a', class_='subTitle')
                            location_elem = card.find('span', class_='locationsContainer')
                            
                            if title_elem and company_elem:
                                job_data = {
                                    'title': title_elem.get_text(strip=True),
                                    'company': company_elem.get_text(strip=True),
                                    'location': location_elem.get_text(strip=True) if location_elem else location,
                                    'url': urljoin(self.BASE_URL, title_elem.get('href', '')),
                                    'description': card.get_text(strip=True)[:500],
                                    'job_id': f"naukri_{hash(title_elem.get('href', ''))}"
                                }
                                jobs.append(self.normalize_job(job_data, JobSource.NAUKRI.value))
                        except Exception as e:
                            logger.error(f"Error parsing Naukri job card: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Error scraping Naukri: {e}")
        
        return jobs

class LinkedInScraper(BaseJobScraper):
    """Scraper for LinkedIn Jobs"""
    
    BASE_URL = "https://www.linkedin.com"

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        jobs = []
        try:
            # LinkedIn Jobs search
            search_url = f"{self.BASE_URL}/jobs/search"
            params = {
                'keywords': keyword,
                'location': location,
                'f_TPR': 'r604800',  # Past week
                'f_JT': 'F'  # Full-time
            }
            
            logger.info(f"Searching LinkedIn for: {keyword} in {location}")
            
            # Note: LinkedIn requires authentication for full access
            # This is a basic implementation - you might need LinkedIn API access
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {e}")
        
        return jobs

class HiristScraper(BaseJobScraper):
    """Scraper for Hirist (Tech jobs)"""
    
    BASE_URL = "https://www.hirist.com"

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        jobs = []
        try:
            search_url = f"{self.BASE_URL}/jobs"
            params = {
                'q': keyword,
                'l': location
            }
            
            logger.info(f"Searching Hirist for: {keyword} in {location}")
            
            async with self.session.get(search_url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parse Hirist job listings
                    job_cards = soup.find_all('div', class_='job-card')
                    
                    for card in job_cards[:15]:
                        try:
                            title_elem = card.find('h3')
                            company_elem = card.find('div', class_='company-name')
                            
                            if title_elem and company_elem:
                                job_data = {
                                    'title': title_elem.get_text(strip=True),
                                    'company': company_elem.get_text(strip=True),
                                    'location': location,
                                    'url': urljoin(self.BASE_URL, card.find('a')['href'] if card.find('a') else ''),
                                    'description': card.get_text(strip=True)[:500],
                                    'job_id': f"hirist_{hash(str(card))}"
                                }
                                jobs.append(self.normalize_job(job_data, JobSource.HIRIST.value))
                        except Exception as e:
                            logger.error(f"Error parsing Hirist job card: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Error scraping Hirist: {e}")
        
        return jobs

class WellfoundScraper(BaseJobScraper):
    """Scraper for Wellfound (formerly AngelList)"""
    
    BASE_URL = "https://wellfound.com"

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        jobs = []
        try:
            search_url = f"{self.BASE_URL}/jobs"
            params = {
                'q': keyword,
                'l': location
            }
            
            logger.info(f"Searching Wellfound for: {keyword} in {location}")
            
            # Wellfound implementation would go here
            
        except Exception as e:
            logger.error(f"Error scraping Wellfound: {e}")
        
        return jobs

class RemoteCoScraper(BaseJobScraper):
    """Scraper for Remote.co"""
    
    BASE_URL = "https://remote.co"

    async def search(self, keyword: str, location: str = "Remote") -> List[JobPosting]:
        jobs = []
        try:
            search_url = f"{self.BASE_URL}/remote-jobs/search"
            params = {'search': keyword}
            
            logger.info(f"Searching Remote.co for: {keyword}")
            
            async with self.session.get(search_url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parse Remote.co job listings
                    job_cards = soup.find_all('div', class_='job_board_list')
                    
                    for card in job_cards[:10]:
                        try:
                            title_elem = card.find('span', class_='font-weight-bold')
                            company_elem = card.find('p', class_='m-0')
                            
                            if title_elem and company_elem:
                                job_data = {
                                    'title': title_elem.get_text(strip=True),
                                    'company': company_elem.get_text(strip=True),
                                    'location': 'Remote',
                                    'url': urljoin(self.BASE_URL, card.find('a')['href'] if card.find('a') else ''),
                                    'description': card.get_text(strip=True)[:500],
                                    'job_type': 'Remote',
                                    'job_id': f"remote_co_{hash(str(card))}"
                                }
                                jobs.append(self.normalize_job(job_data, JobSource.REMOTE_CO.value))
                        except Exception as e:
                            logger.error(f"Error parsing Remote.co job card: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Error scraping Remote.co: {e}")
        
        return jobs

class IndeedScraper(BaseJobScraper):
    """Scraper for Indeed"""
    
    BASE_URL = "https://in.indeed.com"

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        jobs = []
        try:
            search_url = f"{self.BASE_URL}/jobs"
            params = {
                'q': keyword,
                'l': location,
                'fromage': '7'  # Last 7 days
            }
            
            logger.info(f"Searching Indeed for: {keyword} in {location}")
            
            async with self.session.get(search_url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parse Indeed job listings
                    job_cards = soup.find_all('div', class_='job_seen_beacon')
                    
                    for card in job_cards[:15]:
                        try:
                            title_elem = card.find('h2', class_='jobTitle')
                            company_elem = card.find('span', class_='companyName')
                            location_elem = card.find('div', class_='companyLocation')
                            
                            if title_elem and company_elem:
                                title_link = title_elem.find('a')
                                job_data = {
                                    'title': title_link.get_text(strip=True) if title_link else title_elem.get_text(strip=True),
                                    'company': company_elem.get_text(strip=True),
                                    'location': location_elem.get_text(strip=True) if location_elem else location,
                                    'url': urljoin(self.BASE_URL, title_link['href']) if title_link else '',
                                    'description': card.get_text(strip=True)[:500],
                                    'job_id': f"indeed_{hash(str(card))}"
                                }
                                jobs.append(self.normalize_job(job_data, JobSource.INDEED.value))
                        except Exception as e:
                            logger.error(f"Error parsing Indeed job card: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Error scraping Indeed: {e}")
        
        return jobs

class InstahyreScraper(BaseJobScraper):
    """Scraper for Instahyre"""
    
    BASE_URL = "https://www.instahyre.com"

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        jobs = []
        try:
            logger.info(f"Searching Instahyre for: {keyword} in {location}")
            
            # Instahyre API implementation would go here
            # Note: Instahyre might require authentication
            
        except Exception as e:
            logger.error(f"Error scraping Instahyre: {e}")
        
        return jobs

class CompanyCareerScraper:
    """Scraper for company career pages"""
    
    # Company career page patterns
    CAREER_PAGE_PATTERNS = {
        "google": "https://careers.google.com/jobs/results/",
        "microsoft": "https://careers.microsoft.com/professionals/us/en/search-results",
        "amazon": "https://www.amazon.jobs/en/search",
        "meta": "https://www.metacareers.com/jobs",
        "netflix": "https://jobs.netflix.com/search",
        "flipkart": "https://www.flipkartcareers.com/",
        "razorpay": "https://razorpay.com/jobs/",
        "cred": "https://careers.cred.club/",
        "swiggy": "https://careers.swiggy.com/",
        "zomato": "https://www.zomato.com/careers",
        "paytm": "https://jobs.paytm.com/",
        "ola": "https://www.olacabs.com/careers",
        "uber": "https://www.uber.com/careers/",
        "salesforce": "https://salesforce.wd1.myworkdayjobs.com/External_Career_Site",
        "adobe": "https://careers.adobe.com/us/en/search-results",
        "atlassian": "https://www.atlassian.com/company/careers/all-jobs",
    }

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def scrape_company(self, company: str, keyword: str) -> List[JobPosting]:
        """Scrape a specific company's career page"""
        jobs = []
        try:
            company_lower = company.lower().replace(" ", "")
            if company_lower in self.CAREER_PAGE_PATTERNS:
                url = self.CAREER_PAGE_PATTERNS[company_lower]
                logger.info(f"Scraping {company} career page")
                
                async with self.session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Generic job parsing (would need customization per company)
                        job_links = soup.find_all('a', href=True)
                        job_titles = soup.find_all(['h1', 'h2', 'h3', 'h4'])
                        
                        for i, title in enumerate(job_titles[:5]):  # Limit to 5 per company
                            title_text = title.get_text(strip=True)
                            if any(word in title_text.lower() for word in keyword.lower().split()):
                                job_data = {
                                    'title': title_text,
                                    'company': company,
                                    'location': 'Multiple Locations',
                                    'url': url,
                                    'description': f"Job at {company}",
                                    'job_id': f"company_{company_lower}_{i}"
                                }
                                jobs.append(JobPosting(**job_data, source=JobSource.COMPANY_CAREER.value))
                                
        except Exception as e:
            logger.error(f"Error scraping {company} career page: {e}")
        
        return jobs

class MultiPlatformJobScraper:
    """Main orchestrator for multi-platform job search"""
    
    def __init__(self):
        self.config = JobSearchConfig()
        self.all_jobs = []

    async def search_all_platforms(self) -> List[JobPosting]:
        """Search all platforms concurrently"""
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Import Foorilla scraper
            from src.scrapers.foorilla_scraper import FoorillaScraper
            
            # Initialize scrapers
            scrapers = {
                JobSource.NAUKRI: NaukriScraper(session),
                JobSource.HIRIST: HiristScraper(session),
                JobSource.REMOTE_CO: RemoteCoScraper(session),
                JobSource.INDEED: IndeedScraper(session),
                JobSource.FOORILLA: FoorillaScraper(session),
                # JobSource.LINKEDIN: LinkedInScraper(session),  # Requires auth
                # JobSource.WELLFOUND: WellfoundScraper(session),  # Requires auth
                # JobSource.INSTAHYRE: InstahyreScraper(session),  # Requires auth
            }
            
            company_scraper = CompanyCareerScraper(session)
            
            tasks = []
            
            # Search job boards
            for keyword in self.config.PROFILE['keywords'][:5]:  # Limit keywords
                for location in self.config.PROFILE['locations'][:5]:  # Limit locations
                    for source, scraper in scrapers.items():
                        if source == JobSource.REMOTE_CO and location != "Remote":
                            continue  # Skip non-remote for Remote.co
                        
                        task = scraper.search(keyword, location)
                        tasks.append(task)
                        
                        # Add delay to avoid overwhelming servers
                        await asyncio.sleep(0.5)
            
            # Search company career pages (limited)
            for company in self.config.TOP_COMPANIES[:10]:  # Limit companies
                for keyword in self.config.PROFILE['keywords'][:2]:  # Sample keywords
                    task = company_scraper.scrape_company(company, keyword)
                    tasks.append(task)
            
            # Execute searches with concurrency limit
            logger.info(f"Starting {len(tasks)} search tasks...")
            
            # Process in batches to avoid overwhelming servers
            batch_size = 10
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                results = await asyncio.gather(*batch, return_exceptions=True)
                
                # Process results
                for result in results:
                    if isinstance(result, list):
                        self.all_jobs.extend(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Task failed: {result}")
                
                # Delay between batches
                await asyncio.sleep(2)
            
            logger.info(f"Found {len(self.all_jobs)} total jobs")
            
            # Deduplicate and filter
            self.all_jobs = self._deduplicate_jobs(self.all_jobs)
            self.all_jobs = self._filter_jobs(self.all_jobs)
            
            return self.all_jobs

    def _deduplicate_jobs(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """Remove duplicate job postings"""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            # Create a unique identifier
            identifier = f"{job.company.lower()}_{job.title.lower()}_{job.location.lower()}"
            if identifier not in seen:
                seen.add(identifier)
                unique_jobs.append(job)
        
        logger.info(f"Deduplicated: {len(jobs)} -> {len(unique_jobs)} jobs")
        return unique_jobs

    def _filter_jobs(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """Filter jobs based on criteria"""
        filtered = []
        
        for job in jobs:
            # Check if matches skills
            job_text = f"{job.title} {job.description}".lower()
            skill_match = any(skill.lower() in job_text for skill in self.config.PROFILE['skills'])
            
            if skill_match:
                filtered.append(job)
        
        logger.info(f"Filtered: {len(jobs)} -> {len(filtered)} jobs")
        return filtered

    def generate_report(self) -> Dict:
        """Generate a summary report"""
        if not self.all_jobs:
            return {}

        report = {
            "total_jobs": len(self.all_jobs),
            "by_source": {},
            "by_location": {},
            "by_company": {},
            "remote_jobs": 0
        }

        for job in self.all_jobs:
            # By source
            report['by_source'][job.source] = report['by_source'].get(job.source, 0) + 1
            
            # By location
            report['by_location'][job.location] = report['by_location'].get(job.location, 0) + 1
            
            # By company
            report['by_company'][job.company] = report['by_company'].get(job.company, 0) + 1
            
            # Remote jobs
            if 'remote' in job.location.lower() or job.job_type == 'Remote':
                report['remote_jobs'] += 1

        # Sort by count
        report['by_source'] = dict(sorted(report['by_source'].items(), key=lambda x: x[1], reverse=True))
        report['by_location'] = dict(sorted(report['by_location'].items(), key=lambda x: x[1], reverse=True)[:10])
        report['by_company'] = dict(sorted(report['by_company'].items(), key=lambda x: x[1], reverse=True)[:20])

        return report