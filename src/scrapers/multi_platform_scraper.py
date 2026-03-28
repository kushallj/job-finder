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
    job_type: Optional[str] = None
    scraped_at: str = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.now().isoformat()
        if self.skills is None:
            self.skills = []

class JobSearchConfig:
    PROFILE = {
        "keywords": [
            "Backend Developer", "Python Developer", "FastAPI Developer",
            "Django Developer", "Full Stack Developer", "Software Engineer",
            "GenAI Engineer", "AI Engineer", "Machine Learning Engineer",
            "Data Engineer", "DevOps Engineer", "React Developer", "Node.js Developer",
        ],
        "experience": "3",
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

    TOP_COMPANIES = [
        "TCS", "Infosys", "Wipro", "HCL", "Tech Mahindra",
        "Google", "Microsoft", "Amazon", "Meta", "Apple",
        "Netflix", "Adobe", "Salesforce", "Oracle", "SAP",
        "Flipkart", "PhonePe", "Paytm", "Razorpay", "CRED",
        "Swiggy", "Zomato", "Ola", "Uber", "Meesho",
        "Sharechat", "Dream11", "Byju's", "Unacademy", "Upgrad",
        "Dunzo", "Licious", "Urban Company", "Zerodha", "Groww",
        "Stripe", "Square", "Robinhood", "Coinbase", "Plaid",
        "OpenAI", "Anthropic", "Hugging Face", "Scale AI", "Cohere",
        "Atlassian", "Slack", "Zoom", "Notion", "Figma",
        "Canva", "MongoDB", "Snowflake", "Databricks",
        "Shopify", "Etsy", "eBay", "Walmart", "Target",
        "Cloudflare", "DigitalOcean", "HashiCorp", "Terraform",
    ]

    FILTERS = {
        "max_days_old": 7,
        "remote_ok": True,
        "min_salary": None,
        "job_types": ["Full-time", "Contract"]
    }

class BaseJobScraper:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        raise NotImplementedError

    def normalize_job(self, job_data: Dict, source: str) -> JobPosting:
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
    BASE_URL = "https://www.naukri.com"

    # Selectors in priority order — Naukri updates their DOM frequently
    _CARD_SELECTORS = ["article.jobTuple", "div.srp-jobtuple-wrapper",
                       "div[class*='job-tuple']", "div.jobTuple"]

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        url = (f"{self.BASE_URL}/"
               f"{keyword.lower().replace(' ', '-')}-jobs-in-"
               f"{location.lower().replace(' ', '-')}")
        logger.info(f"Searching Naukri for: {keyword} in {location}")

        html = await self._fetch_via_cloudflare(url) or await self._fetch_via_http(url)
        if not html:
            return []
        return self._parse(html, location)

    async def _fetch_via_cloudflare(self, url: str):
        """Render via Cloudflare Browser Rendering — networkidle2 waits for SPA data."""
        try:
            from src.scrapers.crawl import cloudflare_render_page
            html = await cloudflare_render_page(url)
            if html and len(html) > 50_000:   # guard: full SPA page > 50KB
                logger.info(f"Naukri CF render OK — {len(html):,} chars")
                return html
        except Exception as exc:
            logger.warning(f"Naukri CF render failed: {exc}")
        return None

    async def _fetch_via_http(self, url: str):
        """Direct HTTP fallback — fast but often blocked by Naukri."""
        try:
            async with self.session.get(url, headers=self.headers, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception as exc:
            logger.warning(f"Naukri direct HTTP failed: {exc}")
        return None

    def _parse(self, html: str, location: str) -> List[JobPosting]:
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        for selector in self._CARD_SELECTORS:
            # BeautifulSoup doesn't support attribute selectors natively
            tag, *cls = selector.replace("[class*='", " ").rstrip("']").split()
            cards = soup.find_all(tag, class_=cls[0] if cls else False) if cls else soup.find_all(tag)
            if cards:
                break
        else:
            cards = []

        for card in cards[:20]:
            try:
                title_elem   = card.find('a', class_='title') or card.find('a', attrs={'class': lambda c: c and 'title' in c})
                company_elem = card.find('a', class_='subTitle') or card.find('a', attrs={'class': lambda c: c and ('comp' in c or 'company' in c)})
                loc_elem     = card.find('span', class_='locWdth') or card.find('span', attrs={'class': lambda c: c and 'loc' in c})
                if title_elem and company_elem:
                    jobs.append(self.normalize_job({
                        'title':       title_elem.get_text(strip=True),
                        'company':     company_elem.get_text(strip=True),
                        'location':    loc_elem.get_text(strip=True) if loc_elem else location,
                        'url':         urljoin(self.BASE_URL, title_elem.get('href', '')),
                        'description': card.get_text(separator=' ', strip=True)[:500],
                        'job_id':      f"naukri_{hash(title_elem.get('href', ''))}",
                    }, JobSource.NAUKRI.value))
            except Exception as exc:
                logger.debug(f"Naukri card parse error: {exc}")
        return jobs

class LinkedInScraper(BaseJobScraper):
    BASE_URL = "https://www.linkedin.com"

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        return []  # Requires auth

class HiristScraper(BaseJobScraper):
    BASE_URL = "https://www.hirist.com"

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        jobs = []
        try:
            search_url = f"{self.BASE_URL}/jobs"
            params = {'q': keyword, 'l': location}
            logger.info(f"Searching Hirist for: {keyword} in {location}")
            async with self.session.get(search_url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    job_cards = soup.find_all('div', class_='job-card')
                    for card in job_cards[:15]:
                        try:
                            title_elem = card.find('h3')
                            company_elem = card.find('div', class_='company-name')
                            if title_elem and company_elem:
                                jobs.append(self.normalize_job({
                                    'title': title_elem.get_text(strip=True),
                                    'company': company_elem.get_text(strip=True),
                                    'location': location,
                                    'url': urljoin(self.BASE_URL, card.find('a')['href'] if card.find('a') else ''),
                                    'description': card.get_text(strip=True)[:500],
                                    'job_id': f"hirist_{hash(str(card))}"
                                }, JobSource.HIRIST.value))
                        except Exception as e:
                            logger.error(f"Error parsing Hirist job card: {e}")
        except Exception as e:
            logger.error(f"Error scraping Hirist: {e}")
        return jobs

class WellfoundScraper(BaseJobScraper):
    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        return []  # Requires auth

class RemoteCoScraper(BaseJobScraper):
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
                    job_cards = soup.find_all('div', class_='job_board_list')
                    for card in job_cards[:10]:
                        try:
                            title_elem = card.find('span', class_='font-weight-bold')
                            company_elem = card.find('p', class_='m-0')
                            if title_elem and company_elem:
                                jobs.append(self.normalize_job({
                                    'title': title_elem.get_text(strip=True),
                                    'company': company_elem.get_text(strip=True),
                                    'location': 'Remote',
                                    'url': urljoin(self.BASE_URL, card.find('a')['href'] if card.find('a') else ''),
                                    'description': card.get_text(strip=True)[:500],
                                    'job_type': 'Remote',
                                    'job_id': f"remote_co_{hash(str(card))}"
                                }, JobSource.REMOTE_CO.value))
                        except Exception as e:
                            logger.error(f"Error parsing Remote.co job card: {e}")
        except Exception as e:
            logger.error(f"Error scraping Remote.co: {e}")
        return jobs

class IndeedScraper(BaseJobScraper):
    BASE_URL = "https://in.indeed.com"

    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        jobs = []
        try:
            search_url = f"{self.BASE_URL}/jobs"
            params = {'q': keyword, 'l': location, 'fromage': '7'}
            logger.info(f"Searching Indeed for: {keyword} in {location}")
            async with self.session.get(search_url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    job_cards = soup.find_all('div', class_='job_seen_beacon')
                    for card in job_cards[:15]:
                        try:
                            title_elem = card.find('h2', class_='jobTitle')
                            company_elem = card.find('span', class_='companyName')
                            location_elem = card.find('div', class_='companyLocation')
                            if title_elem and company_elem:
                                title_link = title_elem.find('a')
                                jobs.append(self.normalize_job({
                                    'title': title_link.get_text(strip=True) if title_link else title_elem.get_text(strip=True),
                                    'company': company_elem.get_text(strip=True),
                                    'location': location_elem.get_text(strip=True) if location_elem else location,
                                    'url': urljoin(self.BASE_URL, title_link['href']) if title_link else '',
                                    'description': card.get_text(strip=True)[:500],
                                    'job_id': f"indeed_{hash(str(card))}"
                                }, JobSource.INDEED.value))
                        except Exception as e:
                            logger.error(f"Error parsing Indeed job card: {e}")
        except Exception as e:
            logger.error(f"Error scraping Indeed: {e}")
        return jobs

class InstahyreScraper(BaseJobScraper):
    async def search(self, keyword: str, location: str) -> List[JobPosting]:
        return []  # Requires auth

class CompanyCareerScraper:
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
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    async def scrape_company(self, company: str, keyword: str) -> List[JobPosting]:
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
                        job_titles = soup.find_all(['h1', 'h2', 'h3', 'h4'])
                        for i, title in enumerate(job_titles[:5]):
                            title_text = title.get_text(strip=True)
                            if any(word in title_text.lower() for word in keyword.lower().split()):
                                jobs.append(JobPosting(
                                    job_id=f"company_{company_lower}_{i}",
                                    title=title_text,
                                    company=company,
                                    location='Multiple Locations',
                                    url=url,
                                    description=f"Job at {company}",
                                    source=JobSource.COMPANY_CAREER.value,
                                ))
        except Exception as e:
            logger.error(f"Error scraping {company} career page: {e}")
        return jobs


class MultiPlatformJobScraper:
    """
    Main orchestrator for multi-platform job search.

    FIX #6: search_all_platforms now accepts an optional `query` parameter.
    When provided, it searches ONLY that query across a limited set of locations
    (fast path). When omitted, falls back to the full PROFILE keyword sweep.

    FIX — timeout: removed the 0.5s sleep between every task creation.
    Tasks are now created instantly and run concurrently. A single 2s delay
    only happens between batches to avoid overwhelming servers.

    FIX — batch sizing: batch_size raised from 10 → 20 so 35s budget is met.
    """

    def __init__(self):
        self.config = JobSearchConfig()
        self.all_jobs: List[JobPosting] = []

    async def search_all_platforms(self, query: Optional[str] = None) -> List[JobPosting]:
        """
        Search all platforms concurrently.

        Args:
            query: Optional specific search term. When provided, searches only
                   this query across a small set of locations (fast path, fits
                   inside the 35s timeout). When None, uses PROFILE keywords.
        """
        self.all_jobs = []  # reset per call — was accumulating across calls

        # FIX: fast path when a specific query is given (called from api_scraper)
        if query:
            keywords  = [query]
            locations = self.config.PROFILE['locations'][:3]  # Delhi, Noida, Bangalore
        else:
            keywords  = self.config.PROFILE['keywords'][:5]
            locations = self.config.PROFILE['locations'][:5]

        timeout = aiohttp.ClientTimeout(total=25)  # slightly under our 35s budget
        async with aiohttp.ClientSession(timeout=timeout) as session:
            from src.scrapers.foorilla_scraper import FoorillaScraper

            scrapers = {
                JobSource.NAUKRI:    NaukriScraper(session),
                JobSource.HIRIST:    HiristScraper(session),
                JobSource.REMOTE_CO: RemoteCoScraper(session),
                JobSource.INDEED:    IndeedScraper(session),
                JobSource.FOORILLA:  FoorillaScraper(session),
            }

            company_scraper = CompanyCareerScraper(session)

            # Build task list WITHOUT sleep between task creation
            # (sleeping here blocked the event loop before tasks even started)
            tasks = []
            for keyword in keywords:
                for location in locations:
                    for source, scraper in scrapers.items():
                        if source == JobSource.REMOTE_CO and location != "Remote":
                            continue
                        tasks.append(scraper.search(keyword, location))

            # Company pages only in full sweep mode (too slow for fast path)
            if not query:
                for company in self.config.TOP_COMPANIES[:5]:
                    for keyword in keywords[:2]:
                        tasks.append(company_scraper.scrape_company(company, keyword))

            logger.info(f"Starting {len(tasks)} search tasks (query='{query or 'full sweep'}')...")

            # Process in batches — larger batch = fewer inter-batch delays
            batch_size = 20  # was 10; bigger batches finish faster
            for i in range(0, len(tasks), batch_size):
                batch   = tasks[i:i + batch_size]
                results = await asyncio.gather(*batch, return_exceptions=True)

                for result in results:
                    if isinstance(result, list):
                        self.all_jobs.extend(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Task failed: {result}")

                # Only delay between batches, not between every task
                if i + batch_size < len(tasks):
                    await asyncio.sleep(1)  # was 2s; reduced to stay inside budget

            logger.info(f"Found {len(self.all_jobs)} total jobs before dedup/filter")

            self.all_jobs = self._deduplicate_jobs(self.all_jobs)
            self.all_jobs = self._filter_jobs(self.all_jobs)

            return self.all_jobs

    def _deduplicate_jobs(self, jobs: List[JobPosting]) -> List[JobPosting]:
        seen = set()
        unique = []
        for job in jobs:
            key = job.job_id or job.url or f"{job.company}_{job.title}_{job.location}_{job.source}"
            if key not in seen:
                seen.add(key)
                unique.append(job)
        logger.info(f"Deduplicated: {len(jobs)} → {len(unique)} jobs")
        return unique

    def _filter_jobs(self, jobs: List[JobPosting]) -> List[JobPosting]:
        skills   = [s.lower() for s in self.config.PROFILE['skills']]
        filtered = []
        for job in jobs:
            text = " ".join([job.title or "", job.description or "",
                             " ".join(job.skills or [])]).lower()
            if any(skill in text for skill in skills):
                filtered.append(job)
            else:
                logger.debug(f"Filtered out: {job.title} @ {job.company}")
        logger.info(f"Filtered: {len(jobs)} → {len(filtered)} jobs")
        return filtered

    def generate_report(self) -> Dict:
        if not self.all_jobs:
            return {}
        report = {"total_jobs": len(self.all_jobs), "by_source": {},
                  "by_location": {}, "by_company": {}, "remote_jobs": 0}
        for job in self.all_jobs:
            report['by_source'][job.source]     = report['by_source'].get(job.source, 0) + 1
            report['by_location'][job.location] = report['by_location'].get(job.location, 0) + 1
            report['by_company'][job.company]   = report['by_company'].get(job.company, 0) + 1
            if 'remote' in job.location.lower() or job.job_type == 'Remote':
                report['remote_jobs'] += 1
        report['by_source']   = dict(sorted(report['by_source'].items(),   key=lambda x: x[1], reverse=True))
        report['by_location'] = dict(sorted(report['by_location'].items(), key=lambda x: x[1], reverse=True)[:10])
        report['by_company']  = dict(sorted(report['by_company'].items(),  key=lambda x: x[1], reverse=True)[:20])
        return report