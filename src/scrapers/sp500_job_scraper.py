"""
sp500_job_scraper.py — Autonomous High-Throughput Tech Job Scraper for S&P 500 Companies.

Discovers, extracts, and ingests live software, backend, fullstack, AI/ML, and platform engineering
opportunities across S&P 500 giants via:
1. Direct ATS Public Endpoints (Greenhouse, Lever, SmartRecruiters)
2. SerpAPI Google Jobs Engine for Mega-Cap Tech (Apple, Microsoft, Nvidia, Google, Amazon, Meta, Tesla, JPMorgan)
3. Tech taxonomy enrichment and duplicate-free SQLite ingestion
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

from src.database import SessionLocal
from src.models import Job
from src.sp500_registry import SP500_REGISTRY, SP500Company, get_all_sp500_companies, filter_by_sector

logger = logging.getLogger("sp500_job_scraper")
logger.setLevel(logging.INFO)

# Direct ATS slugs mapped to S&P 500 and leading US tech giants
SP500_ATS_MAPPING: Dict[str, Dict[str, str]] = {
    # Greenhouse boards
    "UBER": {"platform": "greenhouse", "slug": "uber"},
    "ABNB": {"platform": "greenhouse", "slug": "airbnb"},
    "DASH": {"platform": "greenhouse", "slug": "doordash"},
    "PINS": {"platform": "greenhouse", "slug": "pinterest"},
    "HOOD": {"platform": "greenhouse", "slug": "robinhood"},
    "SQ": {"platform": "greenhouse", "slug": "squareup"},
    "PLTR": {"platform": "greenhouse", "slug": "palantir"},
    "COIN": {"platform": "greenhouse", "slug": "coinbase"},
    "TWLO": {"platform": "greenhouse", "slug": "twilio"},
    "SNOW": {"platform": "greenhouse", "slug": "snowflake"},
    "TOST": {"platform": "greenhouse", "slug": "toast"},
    "APP": {"platform": "greenhouse", "slug": "applovin"},
    "MDB": {"platform": "greenhouse", "slug": "mongodb"},
    "OKTA": {"platform": "greenhouse", "slug": "okta"},
    "NET": {"platform": "greenhouse", "slug": "cloudflare"},
    "CFLT": {"platform": "greenhouse", "slug": "confluent"},
    "GTLB": {"platform": "greenhouse", "slug": "gitlab"},
    "IOT": {"platform": "greenhouse", "slug": "samsara"},
    "ESTC": {"platform": "greenhouse", "slug": "elastic"},
    "NTNX": {"platform": "greenhouse", "slug": "nutanix"},
    "DDOG": {"platform": "greenhouse", "slug": "datadog"},
    "CRWD": {"platform": "greenhouse", "slug": "crowdstrike"},
    "PANW": {"platform": "greenhouse", "slug": "paloaltonetworks"},
    "NOW": {"platform": "greenhouse", "slug": "servicenow"},
    # Lever boards
    "NFLX": {"platform": "lever", "slug": "netflix"},
    "BOX": {"platform": "lever", "slug": "box"},
    "CPNG": {"platform": "lever", "slug": "coupang"},
    "TEAM": {"platform": "lever", "slug": "atlassian"},
    "RDDT": {"platform": "lever", "slug": "reddit"},
    "LYFT": {"platform": "lever", "slug": "lyft"},
    "ROKU": {"platform": "lever", "slug": "roku"},
    "SPOT": {"platform": "lever", "slug": "spotify"},
    # SmartRecruiters boards
    "V": {"platform": "smartrecruiters", "slug": "visa"},
    "EQIX": {"platform": "smartrecruiters", "slug": "equinix"},
    "MCD": {"platform": "smartrecruiters", "slug": "mcdonalds"},
    "WDC": {"platform": "smartrecruiters", "slug": "westerndigital"},
}

TECH_PATTERNS = [
    re.compile(r"\b(software|engineer|developer|backend|frontend|full\s*stack|fullstack)\b", re.I),
    re.compile(r"\b(devops|sre|data\s+engineer|platform|cloud|machine\s+learning|architect)\b", re.I),
    re.compile(r"\b(python|react|golang|java|tech\s+lead|systems|infrastructure|qa|sdet)\b", re.I),
    re.compile(r"\b(ai|ml)\b", re.I),
]


def is_tech_job(title: str) -> bool:
    """Check if title matches software/tech engineering profile with word boundaries."""
    t = title or ""
    return any(p.search(t) for p in TECH_PATTERNS)



def extract_tech_stack(text: str) -> List[str]:
    """Extract tech stack tokens from job text."""
    stack = []
    tokens = {
        "Python": r"\bpython\b",
        "FastAPI": r"\bfastapi\b",
        "React": r"\breact(\.js)?\b",
        "Node.js": r"\bnode(\.js)?\b",
        "TypeScript": r"\btypescript\b",
        "Go": r"\b(golang|go)\b",
        "Java": r"\bjava\b",
        "C++": r"\b(c\+\+|cpp)\b",
        "PostgreSQL": r"\bpostgres(ql)?\b",
        "Redis": r"\bredis\b",
        "Kafka": r"\bkafka\b",
        "AWS": r"\baws\b",
        "GCP": r"\b(gcp|google\s+cloud)\b",
        "Kubernetes": r"\b(k8s|kubernetes)\b",
        "Docker": r"\bdocker\b",
        "PyTorch": r"\bpytorch\b",
        "TensorFlow": r"\btensorflow\b",
    }
    for tech, pat in tokens.items():
        if re.search(pat, text, re.I):
            stack.append(tech)
    return stack or ["Python", "FastAPI", "React"]


class SP500JobScraper:
    """Scrapes tech jobs across S&P 500 corporations."""

    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_API_KEY") or os.getenv("SERP_API_KEY")
        self.client = httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=True,
            headers={"User-Agent": "JobFinder/2.0 (S&P 500 Sourcing)"}
        )
        self.total_fetched = 0
        self.total_inserted = 0

    async def scrape_greenhouse(self, company_name: str, slug: str, symbol: str) -> List[Dict[str, Any]]:
        """Scrape Greenhouse public API."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        results = []
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for j in data.get("jobs", []):
                    title = j.get("title", "")
                    if is_tech_job(title):
                        loc = j.get("location", {}).get("name", "US / Remote")
                        results.append({
                            "title": title,
                            "company": company_name,
                            "location": loc,
                            "url": j.get("absolute_url", ""),
                            "source": f"sp500_{symbol.lower()}_greenhouse",
                            "tags": ["S&P 500", "Engineering", "Greenhouse", symbol],
                        })
        except Exception as exc:
            logger.debug(f"Greenhouse error for {company_name}: {exc}")
        return results

    async def scrape_lever(self, company_name: str, slug: str, symbol: str) -> List[Dict[str, Any]]:
        """Scrape Lever public API."""
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        results = []
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for j in data:
                    title = j.get("text", "")
                    if is_tech_job(title):
                        loc = (j.get("categories", {}) or {}).get("location", "US / Remote")
                        results.append({
                            "title": title,
                            "company": company_name,
                            "location": loc,
                            "url": j.get("hostedUrl") or j.get("applyUrl", ""),
                            "source": f"sp500_{symbol.lower()}_lever",
                            "tags": ["S&P 500", "Engineering", "Lever", symbol],
                        })
        except Exception as exc:
            logger.debug(f"Lever error for {company_name}: {exc}")
        return results

    async def scrape_smartrecruiters(self, company_name: str, slug: str, symbol: str) -> List[Dict[str, Any]]:
        """Scrape SmartRecruiters public API."""
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        results = []
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for j in data.get("content", []):
                    title = j.get("name", "")
                    if is_tech_job(title):
                        loc = j.get("location", {}).get("city", "US / Remote")
                        results.append({
                            "title": title,
                            "company": company_name,
                            "location": loc,
                            "url": f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
                            "source": f"sp500_{symbol.lower()}_smartrecruiters",
                            "tags": ["S&P 500", "Engineering", "SmartRecruiters", symbol],
                        })
        except Exception as exc:
            logger.debug(f"SmartRecruiters error for {company_name}: {exc}")
        return results

    async def scrape_google_jobs_serpapi(self, company: SP500Company, max_jobs: int = 10) -> List[Dict[str, Any]]:
        """Scrape Google Jobs for S&P 500 giant via SerpAPI."""
        if not self.serpapi_key:
            return []

        clean_name = company.name.split("(")[0].strip()
        query = f"software engineer {clean_name}"
        url = f"https://serpapi.com/search.json?engine=google_jobs&q={urllib.parse.quote(query)}&api_key={self.serpapi_key}"

        results = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JobFinder/2.0"})
            loop = asyncio.get_event_loop()
            resp_bytes = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=18).read())
            data = json.loads(resp_bytes.decode())
            jobs = data.get("jobs_results", [])

            for j in jobs[:max_jobs]:
                title = j.get("title", "")
                comp = j.get("company_name", company.name)
                loc = j.get("location", "US / Remote")
                
                # Extract best apply link
                apply_options = j.get("apply_options", [])
                job_url = apply_options[0].get("link") if apply_options else f"https://www.google.com/search?q={urllib.parse.quote(query)}"

                if is_tech_job(title):
                    results.append({
                        "title": title,
                        "company": company.name,
                        "location": loc,
                        "url": job_url,
                        "source": f"sp500_{company.symbol.lower()}_google_jobs",
                        "tags": ["S&P 500", company.sector, "GoogleJobs", company.symbol],
                    })
        except Exception as exc:
            logger.debug(f"SerpAPI Google Jobs error for {company.name}: {exc}")

        return results

    def save_jobs_to_db(self, jobs: List[Dict[str, Any]]) -> int:
        """Upsert jobs into SQLite."""
        if not jobs:
            return 0

        inserted = 0
        with SessionLocal() as db:
            for j in jobs:
                title = j["title"]
                comp = j["company"]
                existing = db.query(Job).filter(
                    (Job.url == j["url"]) | ((Job.company == comp) & (Job.title == title))
                ).first()

                if not existing:
                    job_id = f"sp500_{abs(hash(comp + title + j['url'])) % 10000000}"
                    tech_stack = extract_tech_stack(title + " " + " ".join(j.get("tags", [])))
                    new_job = Job(
                        job_id=job_id,
                        title=title,
                        company=comp,
                        location=j.get("location", "US / Remote"),
                        url=j.get("url", ""),
                        source=j.get("source", "sp500_crawler"),
                        tags=json.dumps(j.get("tags", ["S&P 500", "Engineering"])),
                        description=f"Software engineering role at {comp} (S&P 500). Tech Stack: {', '.join(tech_stack)}.",
                        fetched_at=datetime.now(timezone.utc),
                    )
                    db.add(new_job)
                    inserted += 1

            db.commit()
        return inserted

    async def crawl_sp500_tech_jobs(
        self,
        sector: Optional[str] = None,
        limit_companies: int = 50,
        use_serpapi_for_giants: bool = True
    ) -> Dict[str, Any]:
        """Execute concurrent multi-strategy crawl for S&P 500 companies."""
        logger.info("🚀 Starting S&P 500 Tech Job Crawl...")
        companies = get_all_sp500_companies()
        if sector:
            companies = filter_by_sector(sector)

        target_companies = companies[:limit_companies]
        tasks = []

        # 1. Check known ATS mappings first
        for c in target_companies:
            sym = c.symbol.upper()
            if sym in SP500_ATS_MAPPING:
                cfg = SP500_ATS_MAPPING[sym]
                plat = cfg["platform"]
                slug = cfg["slug"]
                if plat == "greenhouse":
                    tasks.append(self.scrape_greenhouse(c.name, slug, sym))
                elif plat == "lever":
                    tasks.append(self.scrape_lever(c.name, slug, sym))
                elif plat == "smartrecruiters":
                    tasks.append(self.scrape_smartrecruiters(c.name, slug, sym))

        # 2. Add top tech giants for Google Jobs search
        if use_serpapi_for_giants and self.serpapi_key:
            priority_symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "CRM", "ORCL", "ADBE", "AMD", "CSCO", "QCOM", "NOW", "INTU", "PYPL", "PANW", "CRWD", "PLTR"]
            for sym in priority_symbols:
                for c in companies:
                    if c.symbol == sym and c not in target_companies:
                        target_companies.append(c)

            for c in target_companies:
                if c.symbol in priority_symbols:
                    tasks.append(self.scrape_google_jobs_serpapi(c, max_jobs=10))

        logger.info(f"Executing {len(tasks)} scraping tasks across S&P 500 companies...")
        
        batch_size = 15
        total_discovered = 0
        total_saved = 0

        for i in range(0, len(tasks), batch_size):
            chunk = tasks[i:i + batch_size]
            results = await asyncio.gather(*chunk, return_exceptions=True)
            for r in results:
                if isinstance(r, list) and r:
                    total_discovered += len(r)
                    saved = self.save_jobs_to_db(r)
                    total_saved += saved

            logger.info(f"S&P 500 Crawl Progress: [{min(i + batch_size, len(tasks))}/{len(tasks)}] tasks completed | Jobs Saved: {total_saved}")

        await self.client.aclose()
        self.total_fetched = total_discovered
        self.total_inserted = total_saved

        logger.info(f"✅ S&P 500 Tech Job Crawl Completed! Discovered: {total_discovered} | Saved to DB: {total_saved}")
        return {
            "status": "success",
            "companies_scanned": len(target_companies),
            "total_jobs_discovered": total_discovered,
            "total_jobs_saved": total_saved,
        }


sp500_job_scraper = SP500JobScraper()
