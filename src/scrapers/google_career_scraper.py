from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import List, Dict
from src.scrapers.base import BaseScraper
import asyncio
import random
from googlesearch import search

class GoogleCareerScraper(BaseScraper):
    """Scrape jobs from company career pages found via Google"""

    def __init__(self):
        super().__init__("google_careers")
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        ]

    def find_career_pages(self, job_title: str, location: str = "", num_results: int = 10) -> List[str]:
        """Find company career pages using Google search"""

        # Build search query
        query_parts = [job_title]
        if location:
            query_parts.append(location)
        query_parts.extend(['jobs', 'careers', 'site:greenhouse.io OR site:lever.co OR site:linkedin.com/jobs OR site:careers'])

        search_query = ' '.join(query_parts)

        print(f"🔍 Google searching: {search_query}")

        career_urls = []
        try:
            for url in search(search_query, num_results=num_results, sleep_interval=2):
                # Filter for actual job listing pages
                if any(keyword in url.lower() for keyword in ['job', 'career', 'opening', 'position', 'hiring']):
                    career_urls.append(url)
                    print(f"  📄 Found: {url}")
        except Exception as e:
            print(f"❌ Google search error: {e}")

        return career_urls

    async def scrape_greenhouse_jobs(self, url: str) -> List[Dict]:
        """Scrape jobs from Greenhouse job boards"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)

                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')

                # Greenhouse specific selectors
                job_elements = soup.find_all('div', class_='opening')

                for job_elem in job_elements[:10]:  # Limit to 10 per page
                    try:
                        title_elem = job_elem.find('a')
                        location_elem = job_elem.find('span', class_='location')

                        if title_elem:
                            job_url = title_elem.get('href', '')
                            if not job_url.startswith('http'):
                                # Get base URL from original URL
                                from urllib.parse import urljoin
                                job_url = urljoin(url, job_url)

                            jobs.append(self.normalize_job({
                                'title': title_elem.text.strip(),
                                'company': self._extract_company_from_url(url),
                                'location': location_elem.text.strip() if location_elem else 'Remote',
                                'url': job_url,
                                'description': '',
                                'source': 'greenhouse'
                            }))
                    except Exception as e:
                        print(f"❌ Error parsing Greenhouse job: {e}")
                        continue

            except Exception as e:
                print(f"❌ Error scraping Greenhouse page: {e}")
            finally:
                await browser.close()

        return jobs

    async def scrape_lever_jobs(self, url: str) -> List[Dict]:
        """Scrape jobs from Lever job boards"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)

                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')

                # Lever specific selectors
                job_elements = soup.find_all('div', class_='posting')

                for job_elem in job_elements[:10]:
                    try:
                        title_elem = job_elem.find('h5')
                        link_elem = job_elem.find('a', class_='posting-title')
                        location_elem = job_elem.find('span', class_='sort-by-location')

                        if title_elem and link_elem:
                            jobs.append(self.normalize_job({
                                'title': title_elem.text.strip(),
                                'company': self._extract_company_from_url(url),
                                'location': location_elem.text.strip() if location_elem else 'Remote',
                                'url': link_elem.get('href', url),
                                'description': '',
                                'source': 'lever'
                            }))
                    except Exception as e:
                        print(f"❌ Error parsing Lever job: {e}")
                        continue

            except Exception as e:
                print(f"❌ Error scraping Lever page: {e}")
            finally:
                await browser.close()

        return jobs

    async def scrape_generic_career_page(self, url: str) -> List[Dict]:
        """Scrape jobs from generic career pages"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)

                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')

                # Generic job listing patterns
                potential_job_elements = []

                # Try various common patterns
                potential_job_elements.extend(soup.find_all('div', class_=lambda x: x and 'job' in x.lower()))
                potential_job_elements.extend(soup.find_all('li', class_=lambda x: x and 'job' in x.lower()))
                potential_job_elements.extend(soup.find_all('a', href=lambda x: x and 'job' in x.lower()))

                for job_elem in potential_job_elements[:15]:
                    try:
                        # Try to extract title
                        title = None
                        for tag in ['h2', 'h3', 'h4', 'a']:
                            title_elem = job_elem.find(tag)
                            if title_elem:
                                title = title_elem.text.strip()
                                break

                        if not title or len(title) < 5:
                            continue

                        # Try to extract URL
                        link = job_elem.find('a')
                        job_url = link.get('href', url) if link else url

                        if not job_url.startswith('http'):
                            from urllib.parse import urljoin
                            job_url = urljoin(url, job_url)

                        jobs.append(self.normalize_job({
                            'title': title,
                            'company': self._extract_company_from_url(url),
                            'location': 'Remote/Hybrid',
                            'url': job_url,
                            'description': '',
                            'source': 'career_page'
                        }))

                    except Exception as e:
                        continue

            except Exception as e:
                print(f"❌ Error scraping generic page: {e}")
            finally:
                await browser.close()

        return jobs

    def _extract_company_from_url(self, url: str) -> str:
        """Extract company name from URL"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        # Remove common prefixes/suffixes
        company = domain.replace('www.', '').replace('careers.', '').replace('jobs.', '')
        company = company.split('.')[0]

        return company.title()

    async def fetch_jobs(self, job_title: str = "software engineer",
                        location: str = "", num_pages: int = 5) -> List[Dict]:
        """Main method to fetch jobs via Google search"""

        # Find career pages
        career_urls = self.find_career_pages(job_title, location, num_results=num_pages)

        if not career_urls:
            print("❌ No career pages found")
            return []

        all_jobs = []

        for url in career_urls:
            print(f"\n🔍 Scraping: {url}")

            try:
                # Determine scraper based on URL
                if 'greenhouse.io' in url:
                    jobs = await self.scrape_greenhouse_jobs(url)
                elif 'lever.co' in url:
                    jobs = await self.scrape_lever_jobs(url)
                else:
                    jobs = await self.scrape_generic_career_page(url)

                all_jobs.extend(jobs)
                print(f"  ✅ Found {len(jobs)} jobs")

                # Rate limiting
                await asyncio.sleep(random.randint(2, 4))

            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue

        print(f"\n✅ Total jobs from Google search: {len(all_jobs)}")
        return all_jobs
