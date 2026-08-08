"""
orchestrator.py — Unified scraper orchestration and deduplication.

This module provides a centralized orchestrator that:
- Provides a unified interface for all job scrapers
- Executes scraping across multiple platforms in parallel
- Deduplicates results based on job_id generation
- Aggregates results from all enabled scrapers
- Handles errors gracefully without failing the entire pipeline

Requirements: 10.1, 10.2, 10.3, 10.5
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import logging.handlers
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple, Type

import aiohttp

# =============================================================================
# Logging Setup
# =============================================================================

_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)

_fmt = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)-30s | trace=%(trace_id)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_logger = logging.getLogger("scraper.orchestrator")
if not _logger.handlers:
    _ch = logging.StreamHandler()
    _ch.setFormatter(_fmt)
    _fh = logging.handlers.RotatingFileHandler(
        _LOG_DIR / "scraper_orchestrator.log",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    _fh.setFormatter(_fmt)
    _logger.addHandler(_ch)
    _logger.addHandler(_fh)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


class TLog:
    """Trace-bound logger for correlation."""
    def __init__(self, name: str, trace_id: str = "-"):
        self._l = logging.getLogger(f"scraper.orchestrator.{name}")
        self.trace_id = trace_id

    def _x(self) -> Dict: 
        return {"trace_id": self.trace_id}
    
    def debug(self, m, *a, **k):   
        self._l.debug(m, *a, extra=self._x(), **k)
    def info(self, m, *a, **k):    
        self._l.info(m, *a, extra=self._x(), **k)
    def warning(self, m, *a, **k): 
        self._l.warning(m, *a, extra=self._x(), **k)
    def error(self, m, *a, **k):   
        self._l.error(m, *a, extra=self._x(), **k)


# =============================================================================
# Data Contracts
# =============================================================================

class ScraperStatus(str, Enum):
    """Status of a scraper execution."""
    SUCCESS = "success"
    PARTIAL = "partial"  # Some results, but with errors
    FAILED = "failed"
    TIMEOUT = "timeout"
    DISABLED = "disabled"


@dataclass
class NormalizedJob:
    """Canonical job shape. All scrapers produce this format."""
    job_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_date: Optional[str] = None
    salary: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    experience: Optional[str] = None
    job_type: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    trust_score: int = 50

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ScraperResult:
    """Result from a single scraper execution."""
    scraper_name: str
    status: ScraperStatus
    jobs: List[NormalizedJob]
    job_count: int
    duration_ms: float
    error_message: Optional[str] = None
    trace_id: str = ""


@dataclass
class OrchestratorResult:
    """Aggregated result from all scrapers."""
    total_jobs: int
    unique_jobs: int
    duplicates_removed: int
    scraper_results: List[ScraperResult]
    duration_ms: float
    errors: List[str]
    jobs: List[NormalizedJob]
    trace_id: str = ""


@dataclass
class ScraperConfig:
    """Configuration for the scraper orchestrator."""
    enabled_scrapers: List[str] = field(default_factory=lambda: [
        "multi_platform", "ats", "jobspy", "google_careers"
    ])
    max_concurrent_scrapers: int = 5
    scraper_timeout_seconds: float = 60.0
    max_jobs_per_scraper: int = 100
    enable_deduplication: bool = True
    parallel_execution: bool = True


# =============================================================================
# Unified Scraper Interface
# =============================================================================

class UnifiedScraperInterface(ABC):
    """
    Abstract interface that all scrapers must implement.
    Provides a consistent API for the orchestrator.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this scraper."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        location: str = "",
        max_results: int = 50,
    ) -> List[Dict]:
        """
        Search for jobs matching the query.
        
        Args:
            query: Search term (e.g., "Python Developer")
            location: Optional location filter
            max_results: Maximum number of results to return
            
        Returns:
            List of job dictionaries in normalized format
        """
        pass

    def normalize_job(self, job: Dict) -> NormalizedJob:
        """Convert a raw job dict to NormalizedJob."""
        return NormalizedJob(
            job_id=job.get("job_id") or self._generate_job_id(job),
            title=str(job.get("title", "")).strip()[:200],
            company=str(job.get("company", "")).strip()[:200],
            location=str(job.get("location", "Unknown")).strip()[:200],
            description=str(job.get("description", "")).strip()[:3000],
            url=str(job.get("url", "")).strip(),
            source=job.get("source", self.name),
            posted_date=job.get("posted_date"),
            salary=job.get("salary"),
            skills=job.get("skills", []),
            experience=job.get("experience"),
            job_type=job.get("job_type"),
        )


    def _generate_job_id(self, job: Dict) -> str:
        """Generate a unique job ID for deduplication."""
        parts = [
            str(job.get("title", "")).strip().lower(),
            str(job.get("company", "")).strip().lower(),
            str(job.get("url", "")).strip().lower(),
            datetime.utcnow().strftime("%Y%m%d"),
        ]
        unique_string = "||".join(filter(None, parts))
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]


# =============================================================================
# Scraper Adapters
# =============================================================================

class MultiPlatformScraperAdapter(UnifiedScraperInterface):
    """Adapter for MultiPlatformJobScraper."""
    
    def __init__(self):
        self._scraper = None
    
    @property
    def name(self) -> str:
        return "multi_platform"
    
    async def search(
        self, query: str, location: str = "", max_results: int = 50
    ) -> List[Dict]:
        from src.scrapers.multi_platform_scraper import MultiPlatformJobScraper
        
        if self._scraper is None:
            self._scraper = MultiPlatformJobScraper()
        
        jobs = await self._scraper.search_all_platforms(query=query)
        
        # Convert JobPosting dataclass to dict
        result = []
        for job in jobs[:max_results]:
            if hasattr(job, '__dict__'):
                result.append(asdict(job) if hasattr(job, '__dataclass_fields__') else job.__dict__)
            elif isinstance(job, dict):
                result.append(job)
        return result


class ATSScraperAdapter(UnifiedScraperInterface):
    """Adapter for ATSScraper (Greenhouse/Lever)."""
    
    def __init__(self):
        self._scraper = None
    
    @property
    def name(self) -> str:
        return "ats"
    
    async def search(
        self, query: str, location: str = "", max_results: int = 50
    ) -> List[Dict]:
        from src.scrapers.ats_scraper import ATSScraper
        
        if self._scraper is None:
            self._scraper = ATSScraper()
        
        jobs = await self._scraper.search(query=query, location=location)
        return jobs[:max_results]


class JobSpyScraperAdapter(UnifiedScraperInterface):
    """Adapter for JobSpyScraper."""
    
    def __init__(self):
        self._scraper = None
    
    @property
    def name(self) -> str:
        return "jobspy"
    
    async def search(
        self, query: str, location: str = "", max_results: int = 50
    ) -> List[Dict]:
        from src.scrapers.jobspy_scraper import JobSpyScraper
        
        if self._scraper is None:
            self._scraper = JobSpyScraper()
        
        loc = location if location else "india"
        jobs = await self._scraper.search(
            query=query, 
            location=loc, 
            results_wanted=max_results
        )
        return jobs[:max_results]


class GoogleCareersScraperAdapter(UnifiedScraperInterface):
    """Adapter for GoogleCareerScraper."""
    
    def __init__(self):
        self._scraper = None
    
    @property
    def name(self) -> str:
        return "google_careers"
    
    async def search(
        self, query: str, location: str = "", max_results: int = 50
    ) -> List[Dict]:
        from src.scrapers.google_career_scraper import GoogleCareerScraper
        
        if self._scraper is None:
            self._scraper = GoogleCareerScraper()
        
        jobs = await self._scraper.fetch_jobs(
            job_title=query, 
            location=location, 
            num_pages=5
        )
        return jobs[:max_results]


class FirecrawlScraperAdapter(UnifiedScraperInterface):
    """Adapter for FirecrawlCareerScraper (top Indian startups' career pages)."""

    def __init__(self):
        self._scraper = None

    @property
    def name(self) -> str:
        return "firecrawl"

    async def search(
        self, query: str, location: str = "", max_results: int = 50
    ) -> List[Dict]:
        from src.config import settings
        from src.scrapers.firecrawl_scraper import FirecrawlCareerScraper

        if self._scraper is None:
            self._scraper = FirecrawlCareerScraper(
                api_key=getattr(settings, "firecrawl_api_key", None)
            )

        jobs = await self._scraper.search(
            query=query, location=location, max_results=max_results
        )
        return jobs


class FoorillaScraperAdapter(UnifiedScraperInterface):
    """Adapter for FoorillaScraper."""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._scraper = None
    
    @property
    def name(self) -> str:
        return "foorilla"
    
    async def search(
        self, query: str, location: str = "", max_results: int = 50
    ) -> List[Dict]:
        from src.scrapers.foorilla_scraper import FoorillaScraper
        
        # Create session if not provided
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        
        if self._scraper is None:
            self._scraper = FoorillaScraper(self._session)
        
        jobs = await self._scraper.search(keyword=query, location=location)
        
        # Convert JobPosting to dict
        result = []
        for job in jobs[:max_results]:
            if hasattr(job, '__dict__'):
                result.append(asdict(job) if hasattr(job, '__dataclass_fields__') else job.__dict__)
            elif isinstance(job, dict):
                result.append(job)
        return result


# =============================================================================
# Job Deduplication Engine
# =============================================================================

class JobDeduplicator:
    """
    Trie-based job deduplication with O(k) complexity.
    
    Uses multiple strategies:
    1. Exact job_id match
    2. URL-based deduplication
    3. Fuzzy title+company match
    """
    
    def __init__(self):
        self._seen_ids: Set[str] = set()
        self._seen_urls: Set[str] = set()
        self._seen_title_company: Set[str] = set()
        self._log = TLog("deduplicator")
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        url = url.lower().strip()
        # Remove tracking parameters
        if "?" in url:
            url = url.split("?")[0]
        # Remove trailing slashes
        url = url.rstrip("/")
        return url
    
    def _title_company_key(self, title: str, company: str) -> str:
        """Create a normalized key from title and company."""
        t = "".join(c for c in title.lower() if c.isalnum())
        c = "".join(c for c in company.lower() if c.isalnum())
        return f"{t}::{c}"
    
    def is_duplicate(self, job: NormalizedJob) -> bool:
        """Check if job is a duplicate."""
        # Check job_id
        if job.job_id in self._seen_ids:
            return True
        
        # Check URL
        if job.url:
            norm_url = self._normalize_url(job.url)
            if norm_url in self._seen_urls:
                return True
        
        # Check title+company
        tc_key = self._title_company_key(job.title, job.company)
        if tc_key in self._seen_title_company:
            return True
        
        return False

    
    def add(self, job: NormalizedJob) -> bool:
        """
        Add job to deduplication index.
        Returns True if job was added (not a duplicate).
        """
        if self.is_duplicate(job):
            return False
        
        # Add to all indexes
        self._seen_ids.add(job.job_id)
        
        if job.url:
            self._seen_urls.add(self._normalize_url(job.url))
        
        tc_key = self._title_company_key(job.title, job.company)
        self._seen_title_company.add(tc_key)
        
        return True
    
    def deduplicate(self, jobs: List[NormalizedJob]) -> Tuple[List[NormalizedJob], int]:
        """
        Deduplicate a list of jobs.
        Returns (unique_jobs, duplicates_removed).
        """
        unique = []
        duplicates = 0
        
        for job in jobs:
            if self.add(job):
                unique.append(job)
            else:
                duplicates += 1
        
        return unique, duplicates
    
    def reset(self):
        """Reset the deduplication indexes."""
        self._seen_ids.clear()
        self._seen_urls.clear()
        self._seen_title_company.clear()
    
    @property
    def stats(self) -> Dict:
        return {
            "unique_ids": len(self._seen_ids),
            "unique_urls": len(self._seen_urls),
            "unique_title_company": len(self._seen_title_company),
        }


# =============================================================================
# Scraper Orchestrator
# =============================================================================

class ScraperOrchestrator:
    """
    Unified scraper orchestrator that:
    - Coordinates parallel scraping across multiple platforms
    - Deduplicates results based on job_id generation
    - Aggregates results from all enabled scrapers
    - Handles errors gracefully
    
    Requirements: 10.1, 10.2, 10.3, 10.5
    """
    
    # Registry of available scrapers
    SCRAPER_REGISTRY: Dict[str, Type[UnifiedScraperInterface]] = {
        "multi_platform": MultiPlatformScraperAdapter,
        "ats": ATSScraperAdapter,
        "jobspy": JobSpyScraperAdapter,
        "google_careers": GoogleCareersScraperAdapter,
        "foorilla": FoorillaScraperAdapter,
        "firecrawl": FirecrawlScraperAdapter,
    }
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self._scrapers: Dict[str, UnifiedScraperInterface] = {}
        self._deduplicator = JobDeduplicator()
        self._log = TLog("orchestrator")
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Initialize enabled scrapers
        self._initialize_scrapers()
    
    def _initialize_scrapers(self):
        """Initialize all enabled scrapers."""
        for name in self.config.enabled_scrapers:
            if name in self.SCRAPER_REGISTRY:
                try:
                    self._scrapers[name] = self.SCRAPER_REGISTRY[name]()
                    self._log.info("Initialized scraper: %s", name)
                except Exception as e:
                    self._log.error("Failed to initialize scraper %s: %s", name, e)
            else:
                self._log.warning("Unknown scraper: %s", name)

    
    async def _run_scraper(
        self,
        scraper: UnifiedScraperInterface,
        query: str,
        location: str,
        max_results: int,
        trace_id: str,
    ) -> ScraperResult:
        """
        Run a single scraper with timeout and error handling.
        Returns ScraperResult even on failure (graceful degradation).
        """
        log = TLog(f"scraper.{scraper.name}", trace_id)
        start = time.monotonic()
        
        try:
            log.info("Starting scraper: %s (query='%s', location='%s')",
                    scraper.name, query, location)
            
            # Run with timeout
            raw_jobs = await asyncio.wait_for(
                scraper.search(query=query, location=location, max_results=max_results),
                timeout=self.config.scraper_timeout_seconds,
            )
            
            # Normalize jobs
            jobs = []
            for job_dict in raw_jobs:
                try:
                    normalized = scraper.normalize_job(job_dict)
                    if normalized.title and normalized.company:
                        jobs.append(normalized)
                except Exception as e:
                    log.debug("Failed to normalize job: %s", e)
            
            duration = (time.monotonic() - start) * 1000
            log.info("Scraper %s completed: %d jobs in %.1fms",
                    scraper.name, len(jobs), duration)
            
            return ScraperResult(
                scraper_name=scraper.name,
                status=ScraperStatus.SUCCESS,
                jobs=jobs,
                job_count=len(jobs),
                duration_ms=duration,
                trace_id=trace_id,
            )

        
        except asyncio.TimeoutError:
            duration = (time.monotonic() - start) * 1000
            log.warning("Scraper %s timed out after %.1fms", scraper.name, duration)
            return ScraperResult(
                scraper_name=scraper.name,
                status=ScraperStatus.TIMEOUT,
                jobs=[],
                job_count=0,
                duration_ms=duration,
                error_message=f"Timeout after {self.config.scraper_timeout_seconds}s",
                trace_id=trace_id,
            )
        
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            log.error("Scraper %s failed: %s", scraper.name, e)
            return ScraperResult(
                scraper_name=scraper.name,
                status=ScraperStatus.FAILED,
                jobs=[],
                job_count=0,
                duration_ms=duration,
                error_message=str(e),
                trace_id=trace_id,
            )
    
    async def search(
        self,
        query: str,
        location: str = "",
        max_results_per_scraper: Optional[int] = None,
        scrapers: Optional[List[str]] = None,
    ) -> OrchestratorResult:
        """
        Search all enabled scrapers in parallel and aggregate results.
        
        Args:
            query: Search term (e.g., "Python Developer")
            location: Optional location filter
            max_results_per_scraper: Max results per scraper (default from config)
            scrapers: Specific scrapers to use (default: all enabled)
        
        Returns:
            OrchestratorResult with deduplicated jobs
        """
        trace_id = str(uuid.uuid4())[:8]
        log = TLog("search", trace_id)
        start = time.monotonic()
        
        # Reset deduplicator for fresh search
        self._deduplicator.reset()

        
        # Determine which scrapers to use
        scraper_names = scrapers or list(self._scrapers.keys())
        active_scrapers = {
            name: self._scrapers[name] 
            for name in scraper_names 
            if name in self._scrapers
        }
        
        max_results = max_results_per_scraper or self.config.max_jobs_per_scraper
        
        log.info("Starting orchestrated search: query='%s', location='%s', scrapers=%s",
                query, location, list(active_scrapers.keys()))
        
        # Execute scrapers
        if self.config.parallel_execution:
            # Parallel execution with semaphore for concurrency control
            sem = asyncio.Semaphore(self.config.max_concurrent_scrapers)
            
            async def bounded_run(scraper: UnifiedScraperInterface) -> ScraperResult:
                async with sem:
                    return await self._run_scraper(
                        scraper, query, location, max_results, trace_id
                    )
            
            tasks = [bounded_run(s) for s in active_scrapers.values()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Sequential execution
            results = []
            for scraper in active_scrapers.values():
                result = await self._run_scraper(
                    scraper, query, location, max_results, trace_id
                )
                results.append(result)
        
        # Process results
        scraper_results: List[ScraperResult] = []
        all_jobs: List[NormalizedJob] = []
        errors: List[str] = []

        
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
                continue
            
            if isinstance(result, ScraperResult):
                scraper_results.append(result)
                all_jobs.extend(result.jobs)
                
                if result.error_message:
                    errors.append(f"{result.scraper_name}: {result.error_message}")
        
        # Deduplicate
        total_jobs = len(all_jobs)
        if self.config.enable_deduplication:
            unique_jobs, duplicates_removed = self._deduplicator.deduplicate(all_jobs)
        else:
            unique_jobs = all_jobs
            duplicates_removed = 0
        
        duration = (time.monotonic() - start) * 1000
        
        log.info(
            "Search completed: %d total, %d unique, %d duplicates in %.1fms",
            total_jobs, len(unique_jobs), duplicates_removed, duration
        )
        
        return OrchestratorResult(
            total_jobs=total_jobs,
            unique_jobs=len(unique_jobs),
            duplicates_removed=duplicates_removed,
            scraper_results=scraper_results,
            duration_ms=duration,
            errors=errors,
            jobs=unique_jobs,
            trace_id=trace_id,
        )

    
    async def search_and_store(
        self,
        query: str,
        location: str = "",
        max_results_per_scraper: Optional[int] = None,
    ) -> OrchestratorResult:
        """
        Search all scrapers and store results in database.
        
        Requirements: 10.6 (Store scraped jobs in database)
        """
        result = await self.search(query, location, max_results_per_scraper)
        
        if result.jobs:
            try:
                from src.database import get_db, Job
                
                db = next(get_db())
                stored = 0
                
                for job in result.jobs:
                    # Check if job already exists
                    existing = db.query(Job).filter(Job.job_id == job.job_id).first()
                    if existing:
                        continue
                    
                    db_job = Job(
                        job_id=job.job_id,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        description=job.description,
                        url=job.url,
                        source=job.source,
                        posted_date=job.posted_date,
                        salary=job.salary,
                        experience=job.experience,
                        job_type=job.job_type,
                    )
                    db.add(db_job)
                    stored += 1
                
                db.commit()
                self._log.info("Stored %d new jobs in database", stored)
                
            except Exception as e:
                self._log.error("Failed to store jobs in database: %s", e)
        
        return result

    
    def get_available_scrapers(self) -> List[str]:
        """Get list of available scraper names."""
        return list(self.SCRAPER_REGISTRY.keys())
    
    def get_enabled_scrapers(self) -> List[str]:
        """Get list of currently enabled scraper names."""
        return list(self._scrapers.keys())
    
    def enable_scraper(self, name: str) -> bool:
        """Enable a scraper by name."""
        if name not in self.SCRAPER_REGISTRY:
            return False
        if name in self._scrapers:
            return True
        try:
            self._scrapers[name] = self.SCRAPER_REGISTRY[name]()
            return True
        except Exception as e:
            self._log.error("Failed to enable scraper %s: %s", name, e)
            return False
    
    def disable_scraper(self, name: str) -> bool:
        """Disable a scraper by name."""
        if name in self._scrapers:
            del self._scrapers[name]
            return True
        return False
    
    @property
    def stats(self) -> Dict:
        """Get orchestrator statistics."""
        return {
            "enabled_scrapers": list(self._scrapers.keys()),
            "available_scrapers": list(self.SCRAPER_REGISTRY.keys()),
            "deduplication_stats": self._deduplicator.stats,
            "config": asdict(self.config),
        }


# =============================================================================
# Factory and Convenience Functions
# =============================================================================

def create_orchestrator(
    enabled_scrapers: Optional[List[str]] = None,
    parallel: bool = True,
    timeout_seconds: float = 60.0,
) -> ScraperOrchestrator:
    """
    Factory function to create a configured orchestrator.
    
    Args:
        enabled_scrapers: List of scraper names to enable
        parallel: Whether to run scrapers in parallel
        timeout_seconds: Timeout for each scraper
    
    Returns:
        Configured ScraperOrchestrator instance
    """
    config = ScraperConfig(
        enabled_scrapers=enabled_scrapers or [
            "multi_platform", "ats", "jobspy", "google_careers"
        ],
        parallel_execution=parallel,
        scraper_timeout_seconds=timeout_seconds,
    )
    return ScraperOrchestrator(config)


async def quick_search(
    query: str,
    location: str = "",
    max_results: int = 100,
) -> List[Dict]:
    """
    Quick convenience function for searching jobs.
    
    Args:
        query: Search term
        location: Optional location filter
        max_results: Maximum total results
    
    Returns:
        List of job dictionaries
    """
    orchestrator = create_orchestrator()
    result = await orchestrator.search(
        query=query,
        location=location,
        max_results_per_scraper=max_results // 4,  # Distribute across scrapers
    )
    return [job.to_dict() for job in result.jobs[:max_results]]


# =============================================================================
# CLI / Main entry point
# =============================================================================

async def main():
    """CLI entry point for testing the orchestrator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Job Scraper Orchestrator")
    parser.add_argument("query", help="Search query (e.g., 'Python Developer')")
    parser.add_argument("--location", default="", help="Location filter")
    parser.add_argument("--max-results", type=int, default=50, help="Max results per scraper")
    parser.add_argument("--scrapers", nargs="*", help="Specific scrapers to use")
    parser.add_argument("--sequential", action="store_true", help="Run scrapers sequentially")
    args = parser.parse_args()
    
    config = ScraperConfig(
        enabled_scrapers=args.scrapers or ["multi_platform", "ats", "jobspy"],
        parallel_execution=not args.sequential,
    )
    
    orchestrator = ScraperOrchestrator(config)
    
    print(f"\n🔍 Searching for: {args.query}")
    if args.location:
        print(f"📍 Location: {args.location}")
    print(f"🔧 Scrapers: {', '.join(orchestrator.get_enabled_scrapers())}")
    print("-" * 60)
    
    result = await orchestrator.search(
        query=args.query,
        location=args.location,
        max_results_per_scraper=args.max_results,
    )
    
    print(f"\n✅ Search completed in {result.duration_ms:.1f}ms")
    print(f"   Total jobs found: {result.total_jobs}")
    print(f"   Unique jobs: {result.unique_jobs}")
    print(f"   Duplicates removed: {result.duplicates_removed}")
    
    print("\n📊 Results by scraper:")
    for sr in result.scraper_results:
        status_icon = "✅" if sr.status == ScraperStatus.SUCCESS else "❌"
        print(f"   {status_icon} {sr.scraper_name}: {sr.job_count} jobs ({sr.duration_ms:.1f}ms)")
        if sr.error_message:
            print(f"      Error: {sr.error_message}")
    
    if result.errors:
        print(f"\n⚠️  Errors: {len(result.errors)}")
        for err in result.errors[:5]:
            print(f"   - {err}")
    
    if result.jobs:
        print(f"\n📋 Sample jobs (first 5):")
        for job in result.jobs[:5]:
            print(f"   • {job.title} @ {job.company} ({job.source})")
            print(f"     {job.location} | {job.url[:60]}...")


if __name__ == "__main__":
    asyncio.run(main())
