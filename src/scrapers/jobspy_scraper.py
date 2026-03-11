"""
jobspy_scraper.py — JobSpy integration for api_scraper.py

Replaces the brittle hand-rolled scrapers for LinkedIn, Indeed, Naukri
with JobSpy's maintained, battle-tested scrapers.

JobSpy runs synchronously (returns a pandas DataFrame), so we run it
in an executor to avoid blocking the async event loop.

Usage in api_scraper.py:
    from src.scrapers.jobspy_scraper import JobSpyScraper
    self._jobspy = JobSpyScraper()

    # In fetch_all():
    self._timed("jobspy", self._jobspy.search(query, location))
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

# Set up a separate logger for jobspy to avoid the trace_id format issue
# from api_scraper.py handlers
_jobspy_logger = logging.getLogger("jobspy")
_jobspy_logger.propagate = False  # Prevent propagation to parent handlers
if not _jobspy_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    _jobspy_logger.addHandler(_handler)
    _jobspy_logger.setLevel(logging.INFO)


# Sites to search — naukri for India, indeed + linkedin globally
_INDIA_SITES   = ["naukri", "indeed", "linkedin"]
_GLOBAL_SITES  = ["indeed", "linkedin", "glassdoor"]


class JobSpyScraper:
    """
    Async wrapper around JobSpy's synchronous scrape_jobs().

    scrape_jobs() is CPU-bound + blocking HTTP — we run it in
    asyncio's default ThreadPoolExecutor so it never blocks the loop.
    """

    def __init__(self):
        # Use standalone logger to avoid trace_id format issues from api_scraper.py
        self._log = _jobspy_logger
        self._check_installed()

    def _check_installed(self):
        pass  # remove eager check — fail gracefully at search time instead

    async def search(
        self,
        query:          str,
        location:       str  = "india",
        results_wanted: int  = 20,
        hours_old:      int  = 72,       # jobs posted in last 3 days
        sites:          Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Search jobs via JobSpy. Runs in executor — non-blocking.

        Args:
            query:          Search term e.g. "Python Developer"
            location:       Location e.g. "Bangalore" or "india"
            results_wanted: Per-site result count (total = sites × this)
            hours_old:      Only jobs newer than this many hours
            sites:          Override site list. Defaults to India sites.

        Returns:
            List of normalized job dicts compatible with api_scraper.normalize()
        """
        _sites = sites or _INDIA_SITES
        loop   = asyncio.get_event_loop()

        self._log.info(
            "JobSpy search: '%s' in '%s' | sites=%s results=%d",
            query, location, _sites, results_wanted
        )

        try:
            # Run blocking scrape_jobs in thread pool
            df = await loop.run_in_executor(
                None,
                lambda: self._scrape(query, location, results_wanted, hours_old, _sites)
            )

            if df is None or df.empty:
                self._log.warning("JobSpy returned 0 results for '%s' in '%s'", query, location)
                return []

            jobs = self._df_to_jobs(df)
            self._log.info("JobSpy: %d jobs found for '%s'", len(jobs), query)
            return jobs

        except Exception as exc:
            self._log.error("JobSpy search failed: %s | type=%s", exc, type(exc).__name__, exc_info=True)
            return []

    def _scrape(
        self,
        query:          str,
        location:       str,
        results_wanted: int,
        hours_old:      int,
        sites:          List[str],
    ):
        """Blocking call — runs in thread pool via run_in_executor."""
        from jobspy import scrape_jobs

        # Determine country for Indeed
        country = "india" if "india" in location.lower() or location.lower() in [
            "delhi", "noida", "gurgaon", "bangalore", "mumbai",
            "pune", "hyderabad", "chennai", "kolkata", "bengaluru",
        ] else "USA"

        return scrape_jobs(
            site_name       = sites,
            search_term     = query,
            location        = location,
            results_wanted  = results_wanted,
            hours_old       = hours_old,
            country_indeed  = country,
            description_format = "markdown",
            verbose         = 0,       # suppress jobspy's own print statements
        )

    def _df_to_jobs(self, df) -> List[Dict]:
        """
        Convert JobSpy DataFrame → list of dicts compatible with
        api_scraper.normalize().

        JobSpy columns:
          site, job_url, job_url_direct, title, company, location,
          date_posted, job_type, salary_source, interval,
          min_amount, max_amount, currency, is_remote,
          job_level, job_function, listing_type, emails,
          description, company_industry, company_url,
          company_logo, company_url_direct, company_addresses,
          company_num_employees, company_revenue, company_description
        """
        jobs = []
        for _, row in df.iterrows():
            try:
                # Build salary string if available
                salary = None
                if row.get("min_amount") and row.get("max_amount"):
                    currency = row.get("currency", "INR")
                    interval = row.get("interval", "yearly")
                    salary   = f"{currency} {row['min_amount']:,.0f}–{row['max_amount']:,.0f} {interval}"
                elif row.get("min_amount"):
                    salary = f"{row.get('currency','INR')} {row['min_amount']:,.0f}+"

                # Job type
                job_type = None
                if row.get("is_remote"):
                    job_type = "Remote"
                elif row.get("job_type"):
                    job_type = str(row["job_type"]).title()

                jobs.append({
                    "title":       str(row.get("title")       or "").strip(),
                    "company":     str(row.get("company")     or "").strip(),
                    "location":    str(row.get("location")    or "").strip(),
                    "url":         str(row.get("job_url")     or row.get("job_url_direct") or "").strip(),
                    "description": str(row.get("description") or "").strip()[:3000],
                    "posted_date": str(row.get("date_posted") or ""),
                    "salary":      salary,
                    "job_type":    job_type,
                    "source":      f"jobspy_{row.get('site', 'unknown')}",
                    "skills":      [],
                })
            except Exception as exc:
                self._log.debug("Row conversion error: %s", exc)
                continue

        return [j for j in jobs if j["title"] and j["company"]]