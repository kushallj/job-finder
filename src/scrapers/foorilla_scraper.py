"""
Foorilla Job Scraper
Scrapes jobs from Foorilla.com job aggregation platform
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse
import logging
from src.scrapers.multi_platform_scraper import BaseJobScraper, JobPosting, JobSource

logger = logging.getLogger(__name__)

class FoorillaScraper(BaseJobScraper):
    """Scraper for Foorilla.com job platform"""
    
    BASE_URL = "https://foorilla.com"
    
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__(session)
        self.session_cookies = None
        self.csrf_token = None
        
        # Headers based on your curl command
        self.headers.update({
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
            'hx-request': 'true',
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-screen': 'D'
        })

    async def initialize_session(self):
        """Initialize session by visiting the main page to get cookies and CSRF token"""
        try:
            main_url = f"{self.BASE_URL}/hiring/jobs/"
            
            async with self.session.get(main_url, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Extract CSRF token from HTML
                    soup = BeautifulSoup(html, 'html.parser')
                    csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
                    if csrf_input:
                        self.csrf_token = csrf_input.get('value')
                    
                    # Store cookies
                    self.session_cookies = response.cookies
                    
                    # Update headers with CSRF token
                    if self.csrf_token:
                        self.headers['x-csrftoken'] = self.csrf_token
                    
                    logger.info("✅ Foorilla session initialized successfully")
                    return True
                else:
                    logger.error(f"Failed to initialize Foorilla session: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error initializing Foorilla session: {e}")
            return False

    async def search(self, keyword: str, location: str = "") -> List[JobPosting]:
        """Search for jobs on Foorilla"""
        jobs = []
        
        try:
            # Initialize session first
            if not await self.initialize_session():
                return jobs
            
            logger.info(f"Searching Foorilla for: {keyword} in {location}")
            
            # Search for jobs
            search_url = f"{self.BASE_URL}/hiring/jobs/"
            
            # Try different search approaches
            jobs.extend(await self._search_by_keyword(keyword, location))
            jobs.extend(await self._browse_recent_jobs(keyword))
            
            logger.info(f"Found {len(jobs)} jobs on Foorilla")
            
        except Exception as e:
            logger.error(f"Error searching Foorilla: {e}")
        
        return jobs

    async def _search_by_keyword(self, keyword: str, location: str) -> List[JobPosting]:
        """Search jobs by keyword"""
        jobs = []
        
        try:
            # Foorilla search endpoint (may need adjustment based on actual API)
            search_url = f"{self.BASE_URL}/hiring/jobs/"
            
            # Search parameters
            params = {
                'q': keyword,
                'location': location,
                'page': 1
            }
            
            # Add cookies to headers
            request_headers = self.headers.copy()
            if self.session_cookies:
                cookie_header = '; '.join([f"{k}={v.value}" for k, v in self.session_cookies.items()])
                request_headers['cookie'] = cookie_header
            
            async with self.session.get(search_url, params=params, headers=request_headers) as response:
                if response.status == 200:
                    html = await response.text()
                    jobs = self._parse_job_listings(html, keyword)
                else:
                    logger.warning(f"Foorilla search returned status: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error in Foorilla keyword search: {e}")
        
        return jobs

    async def _browse_recent_jobs(self, keyword: str) -> List[JobPosting]:
        """Browse recent jobs and filter by keyword"""
        jobs = []
        
        try:
            # Browse recent jobs page
            browse_url = f"{self.BASE_URL}/hiring/jobs/"
            
            request_headers = self.headers.copy()
            if self.session_cookies:
                cookie_header = '; '.join([f"{k}={v.value}" for k, v in self.session_cookies.items()])
                request_headers['cookie'] = cookie_header
            
            async with self.session.get(browse_url, headers=request_headers) as response:
                if response.status == 200:
                    html = await response.text()
                    all_jobs = self._parse_job_listings(html)
                    
                    # Filter jobs by keyword
                    keyword_lower = keyword.lower()
                    for job in all_jobs:
                        job_text = f"{job.title} {job.description}".lower()
                        if any(word in job_text for word in keyword_lower.split()):
                            jobs.append(job)
                            
        except Exception as e:
            logger.error(f"Error browsing Foorilla recent jobs: {e}")
        
        return jobs

    def _parse_job_listings(self, html: str, keyword: str = "") -> List[JobPosting]:
        """Parse job listings from HTML"""
        jobs = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for job cards/listings (adjust selectors based on actual HTML structure)
            job_cards = soup.find_all(['div', 'article'], class_=re.compile(r'job|card|listing'))
            
            if not job_cards:
                # Try alternative selectors
                job_cards = soup.find_all('a', href=re.compile(r'/hiring/jobs/'))
            
            for card in job_cards[:20]:  # Limit to 20 jobs
                try:
                    job = self._parse_single_job(card)
                    if job and job.title and job.company:
                        jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing Foorilla job card: {e}")
                    continue
            
            # If no jobs found with standard parsing, try extracting from links
            if not jobs:
                jobs = self._extract_jobs_from_links(soup)
                
        except Exception as e:
            logger.error(f"Error parsing Foorilla HTML: {e}")
        
        return jobs

    def _parse_single_job(self, card) -> Optional[JobPosting]:
        """Parse a single job card"""
        try:
            # Extract job details (adjust based on actual HTML structure)
            title = ""
            company = ""
            location = ""
            url = ""
            description = ""
            
            # Try to find title
            title_elem = (
                card.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'title|job')) or
                card.find('a', href=re.compile(r'/hiring/jobs/')) or
                card.find(['h1', 'h2', 'h3', 'h4'])
            )
            
            if title_elem:
                title = title_elem.get_text(strip=True)
                # Extract URL if it's a link
                if title_elem.name == 'a':
                    url = urljoin(self.BASE_URL, title_elem.get('href', ''))
            
            # Try to find company
            company_elem = (
                card.find(class_=re.compile(r'company|employer')) or
                card.find('span', string=re.compile(r'Company|Employer', re.I))
            )
            
            if company_elem:
                company = company_elem.get_text(strip=True)
            
            # Try to find location
            location_elem = (
                card.find(class_=re.compile(r'location|city')) or
                card.find('span', string=re.compile(r'Location|City', re.I))
            )
            
            if location_elem:
                location = location_elem.get_text(strip=True)
            
            # Get description
            description = card.get_text(strip=True)[:500]
            
            # Generate job ID
            job_id = f"foorilla_{hash(url or title)}"
            
            # Only create job if we have minimum required fields
            if title and (company or "Foorilla" in description):
                return JobPosting(
                    job_id=job_id,
                    title=title,
                    company=company or "Various Companies",
                    location=location or "Not specified",
                    description=description,
                    url=url or f"{self.BASE_URL}/hiring/jobs/",
                    source="foorilla"
                )
                
        except Exception as e:
            logger.error(f"Error parsing single Foorilla job: {e}")
        
        return None

    def _extract_jobs_from_links(self, soup) -> List[JobPosting]:
        """Extract jobs from job links when card parsing fails"""
        jobs = []
        
        try:
            # Find all job links
            job_links = soup.find_all('a', href=re.compile(r'/hiring/jobs/[^/]+'))
            
            for link in job_links[:15]:  # Limit to 15 jobs
                try:
                    href = link.get('href', '')
                    title = link.get_text(strip=True)
                    
                    if title and href:
                        # Extract job info from URL if possible
                        url_parts = href.split('/')
                        job_slug = url_parts[-1] if url_parts else ""
                        
                        # Try to extract company and location from slug or surrounding text
                        company = "Various Companies"
                        location = "Multiple Locations"
                        
                        # Look for company info near the link
                        parent = link.parent
                        if parent:
                            parent_text = parent.get_text(strip=True)
                            # Simple heuristics to extract company
                            if " at " in parent_text:
                                parts = parent_text.split(" at ")
                                if len(parts) > 1:
                                    company = parts[1].split()[0]
                        
                        job = JobPosting(
                            job_id=f"foorilla_{hash(href)}",
                            title=title,
                            company=company,
                            location=location,
                            description=f"Job opportunity: {title}",
                            url=urljoin(self.BASE_URL, href),
                            source="foorilla"
                        )
                        jobs.append(job)
                        
                except Exception as e:
                    logger.error(f"Error extracting job from link: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting jobs from links: {e}")
        
        return jobs

    async def get_job_details(self, job_url: str) -> Dict:
        """Get detailed job information from job page"""
        details = {}
        
        try:
            request_headers = self.headers.copy()
            if self.session_cookies:
                cookie_header = '; '.join([f"{k}={v.value}" for k, v in self.session_cookies.items()])
                request_headers['cookie'] = cookie_header
            
            async with self.session.get(job_url, headers=request_headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract detailed job information
                    details['full_description'] = soup.get_text(strip=True)
                    
                    # Look for salary information
                    salary_elem = soup.find(string=re.compile(r'salary|compensation|pay', re.I))
                    if salary_elem:
                        details['salary'] = salary_elem.strip()
                    
                    # Look for experience requirements
                    exp_elem = soup.find(string=re.compile(r'experience|years', re.I))
                    if exp_elem:
                        details['experience'] = exp_elem.strip()
                        
        except Exception as e:
            logger.error(f"Error getting Foorilla job details: {e}")
        
        return details

# Integration function to add Foorilla to the multi-platform scraper
def add_foorilla_to_scrapers(scrapers_dict, session):
    """Add Foorilla scraper to the scrapers dictionary"""
    scrapers_dict['foorilla'] = FoorillaScraper(session)
    return scrapers_dict