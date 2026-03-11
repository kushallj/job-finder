from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from src.scrapers.base import BaseScraper
import asyncio
import random


class GoogleCareerScraper(BaseScraper):
    """Scrape jobs from company career pages found via Google"""

    def __init__(self, pw_engine=None):
        super().__init__("google_careers")
        self._pw = pw_engine  # Injected shared PlaywrightEngine — no per-request browser launch

    # ── URL discovery ──────────────────────────────────────────────────────────

    async def find_career_pages(self, job_title: str, location: str = "",
                                 num_results: int = 10) -> List[str]:
        """
        Find company career pages via Google search.
        Runs googlesearch in executor to avoid blocking the event loop.
        """
        query_parts = [job_title]
        if location:
            query_parts.append(location)
        query_parts.extend([
            "jobs careers",
            "site:greenhouse.io OR site:lever.co OR site:linkedin.com/jobs OR site:careers",
        ])
        search_query = " ".join(query_parts)
        print(f"🔍 Google searching: {search_query}")

        def _blocking_search():
            try:
                from googlesearch import search
                return list(search(search_query, num_results=num_results, sleep_interval=2))
            except Exception as e:
                print(f"❌ Google search error: {e}")
                return []

        # Run blocking googlesearch in a thread so we don't freeze the event loop
        loop = asyncio.get_event_loop()
        all_urls: List[str] = await loop.run_in_executor(None, _blocking_search)

        career_urls = [
            url for url in all_urls
            if any(kw in url.lower() for kw in ["job", "career", "opening", "position", "hiring"])
        ]
        for url in career_urls:
            print(f"  📄 Found: {url}")
        return career_urls

    # ── Page scrapers (share one browser via self._pw) ─────────────────────────

    async def scrape_greenhouse_jobs(self, url: str) -> List[Dict]:
        """Scrape jobs from Greenhouse job boards."""
        html = await self._get_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for job_elem in soup.find_all("div", class_="opening")[:10]:
            try:
                title_elem    = job_elem.find("a")
                location_elem = job_elem.find("span", class_="location")
                if not title_elem:
                    continue

                job_url = title_elem.get("href", "")
                if not job_url.startswith("http"):
                    from urllib.parse import urljoin
                    job_url = urljoin(url, job_url)

                jobs.append(self.normalize_job({
                    "title":       title_elem.text.strip(),
                    "company":     self._extract_company_from_url(url),
                    "location":    location_elem.text.strip() if location_elem else "Remote",
                    "url":         job_url,
                    "description": "",
                    "source":      "greenhouse",
                }))
            except Exception as e:
                print(f"❌ Error parsing Greenhouse job: {e}")
        return jobs

    async def scrape_lever_jobs(self, url: str) -> List[Dict]:
        """Scrape jobs from Lever job boards."""
        html = await self._get_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for job_elem in soup.find_all("div", class_="posting")[:10]:
            try:
                title_elem    = job_elem.find("h5")
                link_elem     = job_elem.find("a", class_="posting-title")
                location_elem = job_elem.find("span", class_="sort-by-location")
                if not (title_elem and link_elem):
                    continue

                jobs.append(self.normalize_job({
                    "title":       title_elem.text.strip(),
                    "company":     self._extract_company_from_url(url),
                    "location":    location_elem.text.strip() if location_elem else "Remote",
                    "url":         link_elem.get("href", url),
                    "description": "",
                    "source":      "lever",
                }))
            except Exception as e:
                print(f"❌ Error parsing Lever job: {e}")
        return jobs

    async def scrape_generic_career_page(self, url: str) -> List[Dict]:
        """Scrape jobs from generic career pages."""
        html = await self._get_html(url, wait_ms=3000)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        potential = []
        potential.extend(soup.find_all("div", class_=lambda x: x and "job" in x.lower()))
        potential.extend(soup.find_all("li",  class_=lambda x: x and "job" in x.lower()))
        potential.extend(soup.find_all("a",   href=lambda x:  x and "job" in x.lower()))

        jobs = []
        for job_elem in potential[:15]:
            try:
                title = None
                for tag in ["h2", "h3", "h4", "a"]:
                    el = job_elem.find(tag)
                    if el:
                        title = el.text.strip()
                        break
                if not title or len(title) < 5:
                    continue

                link    = job_elem.find("a")
                job_url = link.get("href", url) if link else url
                if not job_url.startswith("http"):
                    from urllib.parse import urljoin
                    job_url = urljoin(url, job_url)

                jobs.append(self.normalize_job({
                    "title":       title,
                    "company":     self._extract_company_from_url(url),
                    "location":    "Remote/Hybrid",
                    "url":         job_url,
                    "description": "",
                    "source":      "career_page",
                }))
            except Exception:
                continue
        return jobs

    # ── Shared HTML fetch via injected PlaywrightEngine ───────────────────────

    async def _get_html(self, url: str, wait_ms: int = 2000) -> Optional[str]:
        """
        Get page HTML using the injected PlaywrightEngine.
        Falls back to plain httpx if no engine is available.
        """
        if self._pw:
            return await self._pw.get_page_html(url, timeout=30.0)

        # Fallback: plain httpx (no JS rendering)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/122.0.0.0 Safari/537.36"
                })
                return resp.text if resp.status_code == 200 else None
        except Exception as e:
            print(f"❌ HTTP fallback failed for {url}: {e}")
            return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_company_from_url(self, url: str) -> str:
        from urllib.parse import urlparse
        domain  = urlparse(url).netloc
        company = domain.replace("www.", "").replace("careers.", "").replace("jobs.", "")
        return company.split(".")[0].title()

    def _scrape_url(self, url: str):
        """Route URL to the right scraper."""
        if "greenhouse.io" in url:
            return self.scrape_greenhouse_jobs(url)
        elif "lever.co" in url:
            return self.scrape_lever_jobs(url)
        else:
            return self.scrape_generic_career_page(url)

    # ── Main entry point ──────────────────────────────────────────────────────

    async def fetch_jobs(self, job_title: str = "software engineer",
                         location: str = "", num_pages: int = 5) -> List[Dict]:
        """
        Main method to fetch jobs via Google search.
        - find_career_pages runs in executor (non-blocking)
        - All URLs scraped concurrently via asyncio.gather
        """
        career_urls = await self.find_career_pages(job_title, location, num_results=num_pages)

        if not career_urls:
            print("❌ No career pages found")
            return []

        # Scrape all URLs concurrently instead of one-by-one
        tasks   = [self._scrape_url(url) for url in career_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        for url, result in zip(career_urls, results):
            if isinstance(result, Exception):
                print(f"  ❌ Error scraping {url}: {result}")
            elif isinstance(result, list):
                print(f"  ✅ {url} → {len(result)} jobs")
                all_jobs.extend(result)

        print(f"\n✅ Total jobs from Google search: {len(all_jobs)}")
        return all_jobs