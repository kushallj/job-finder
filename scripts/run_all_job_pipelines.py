#!/usr/bin/env python3
"""
scripts/run_all_job_pipelines.py — Master Orchestration Runner for All Job Pipelines.
Executes every job pipeline, scraper, miner, and crawler across the entire system:
  1. Arbeitnow + Remotive Multi-Source Live Harvester
  2. Nifty 500, YC/Accelerators, Shark Tank India/US & Suniel Shetty Crawler
  3. S&P 500 Tech Giants & US Enterprise ATS Scraper
  4. 60 Tier-1 Tech Giants Career Scraper (Rubrik, Stripe, Databricks, Meta, etc.)
  5. Top Indian App Startups Career Scraper (Zepto, CRED, Razorpay, Blinkit, etc.)
  6. Global FinTech Festival Career Scraper (Juspay, Cashfree, Pine Labs, etc.)
  7. Multi-Provider Global Search Engine (AIDevBoard, FantasticJobs, USAJobs, Careerjet)
  8. Specialized DevOps, SRE & Cloud Engineering Pipeline
  9. Specialized Flutter, Mobile & Dart Engineering Pipeline
  10. Specialized JavaScript, TypeScript & Full-Stack Pipeline
  11. Delhi NCR & Accounting / FinOps Pipeline (Samta Jain Corpus)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import SessionLocal, init_db
from src.models import Job
from src.autonomous_job_crawler import extract_tech_tags_and_seniority

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("master_pipeline_runner")


class MasterPipelineRunner:
    def __init__(self):
        init_db()
        self.session = SessionLocal()
        self.initial_count = self.session.query(Job).count()
        self.pipeline_results: Dict[str, Dict[str, Any]] = {}
        self.existing_urls: Set[str] = set()
        self.existing_signatures: Set[str] = set()
        self._load_existing_signatures()

    def _load_existing_signatures(self):
        jobs = self.session.query(Job.url, Job.company, Job.title).all()
        for url, company, title in jobs:
            if url:
                self.existing_urls.add(url.strip())
            if company and title:
                sig = f"{company.strip().lower()}:::{title.strip().lower()}"
                self.existing_signatures.add(sig)

    def save_normalized_jobs(self, jobs: List[Dict[str, Any]], source_name: str) -> Tuple[int, int]:
        """Saves deduplicated jobs to SQLite DB in a single transaction."""
        new_count = 0
        dup_count = 0

        for j in jobs:
            url = (j.get("url") or "").strip()
            title = (j.get("title") or "").strip()
            company = (j.get("company") or "").strip()

            if not title:
                continue

            sig = f"{company.lower()}:::{title.lower()}"
            if (url and url in self.existing_urls) or (sig in self.existing_signatures):
                dup_count += 1
                continue

            if url:
                self.existing_urls.add(url)
            self.existing_signatures.add(sig)

            description = j.get("description") or j.get("description_string") or ""
            tags, seniority = extract_tech_tags_and_seniority(title, description)
            custom_tags = j.get("tags") or []
            if isinstance(custom_tags, str):
                try:
                    custom_tags = json.loads(custom_tags)
                except Exception:
                    custom_tags = [custom_tags]
            
            combined_tags = list(dict.fromkeys((tags or []) + (custom_tags or [])))
            unique_job_id = j.get("job_id") or j.get("id") or f"{source_name}_{abs(hash(url or title))}_{int(time.time() * 1000) % 1000000}"

            new_job = Job(
                job_id=str(unique_job_id),
                title=title,
                company=company or "Enterprise",
                location=j.get("location") or "Remote",
                description=description[:5000],
                url=url or f"https://careers.example.com/{abs(hash(title))}",
                source=j.get("source") or source_name,
                has_remote=bool(j.get("has_remote", True)),
                experience_level=j.get("experience_level") or seniority,
                tags=json.dumps(combined_tags),
                fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            self.session.add(new_job)
            new_count += 1

        self.session.commit()
        return new_count, dup_count

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Arbeitnow + Remotive Bulk Live Harvester
    # ──────────────────────────────────────────────────────────────────────────
    async def run_bulk_harvester_pipeline(self):
        t0 = time.time()
        logger.info("📡 [1/11] Running Arbeitnow + Remotive Bulk Live Harvester...")
        try:
            from scripts.fetch_bulk_fresh_jobs import fetch_arbeitnow_jobs, fetch_remotive_jobs
            arbeitnow_jobs = await fetch_arbeitnow_jobs(max_pages=20)
            remotive_jobs = await fetch_remotive_jobs()
            combined = arbeitnow_jobs + remotive_jobs
            new_saved, dups = self.save_normalized_jobs(combined, "live_harvester")
            self.pipeline_results["Arbeitnow + Remotive Harvester"] = {
                "fetched": len(combined),
                "saved": new_saved,
                "duplicates": dups,
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Harvester pipeline error: {e}")
            self.pipeline_results["Arbeitnow + Remotive Harvester"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Master Startups, Nifty 500, Accelerators & Shark Tank Crawler
    # ──────────────────────────────────────────────────────────────────────────
    async def run_master_startups_nifty500_pipeline(self):
        t0 = time.time()
        logger.info("🏢 [2/11] Running Master Startups, Nifty 500 & Accelerator Crawler...")
        try:
            from scripts.crawl_all_startups_and_nifty500 import MasterJobCrawler
            crawler = MasterJobCrawler()
            result = await crawler.run_full_crawler_cycle()
            self.pipeline_results["Nifty 500 + Startups Crawler"] = {
                "fetched": result.get("total_fetched", 0),
                "saved": result.get("total_inserted", 0),
                "duplicates": max(0, result.get("total_fetched", 0) - result.get("total_inserted", 0)),
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Master startups crawler error: {e}")
            self.pipeline_results["Nifty 500 + Startups Crawler"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 3. S&P 500 Tech Giants & US Enterprise ATS Scraper
    # ──────────────────────────────────────────────────────────────────────────
    async def run_sp500_pipeline(self):
        t0 = time.time()
        logger.info("🇺🇸 [3/11] Running S&P 500 Tech Giants & Enterprise ATS Scraper...")
        try:
            from src.scrapers.sp500_job_scraper import SP500JobScraper
            scraper = SP500JobScraper()
            result = await scraper.crawl_sp500_tech_jobs(limit_companies=100, use_serpapi_for_giants=True)
            self.pipeline_results["S&P 500 Tech Giants Scraper"] = {
                "fetched": result.get("total_jobs_discovered", 0),
                "saved": result.get("total_jobs_saved", 0),
                "duplicates": max(0, result.get("total_jobs_discovered", 0) - result.get("total_jobs_saved", 0)),
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"S&P 500 scraper error: {e}")
            self.pipeline_results["S&P 500 Tech Giants Scraper"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 4. 60 Tier-1 Tech Giants Career Scraper
    # ──────────────────────────────────────────────────────────────────────────
    async def run_tier1_companies_pipeline(self):
        t0 = time.time()
        logger.info("💎 [4/11] Running 60 Tier-1 Tech Giants Career Scraper (Rubrik, Stripe, Databricks)...")
        try:
            from src.scrapers.tier1_career_scraper import Tier1CareerScraper
            scraper = Tier1CareerScraper()
            jobs = await scraper.scrape_all_tier1_careers(
                keywords=["engineer", "developer", "backend", "fullstack", "platform", "ai", "cloud", "software"],
                max_jobs=200
            )
            new_saved, dups = self.save_normalized_jobs(jobs, "tier1_career")
            self.pipeline_results["60 Tier-1 Tech Giants Scraper"] = {
                "fetched": len(jobs),
                "saved": new_saved,
                "duplicates": dups,
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Tier-1 scraper error: {e}")
            self.pipeline_results["60 Tier-1 Tech Giants Scraper"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Top Indian Mobile App Startups Career Scraper
    # ──────────────────────────────────────────────────────────────────────────
    async def run_indian_app_startups_pipeline(self):
        t0 = time.time()
        logger.info("🇮🇳 [5/11] Running Top Indian Mobile App Startups Scraper (Zepto, CRED, Razorpay)...")
        try:
            from src.scrapers.indian_app_startups_scraper import IndianAppStartupsScraper
            scraper = IndianAppStartupsScraper()
            jobs = await scraper.scrape_all_startups(
                keywords=["engineer", "developer", "backend", "fullstack", "mobile", "frontend", "lead", "architect"],
                max_jobs=200
            )
            new_saved, dups = self.save_normalized_jobs(jobs, "indian_app_startups")
            self.pipeline_results["Indian App Startups Scraper"] = {
                "fetched": len(jobs),
                "saved": new_saved,
                "duplicates": dups,
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Indian app startups scraper error: {e}")
            self.pipeline_results["Indian App Startups Scraper"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Global FinTech Festival Career Scraper
    # ──────────────────────────────────────────────────────────────────────────
    async def run_fintech_festival_pipeline(self):
        t0 = time.time()
        logger.info("💳 [6/11] Running Global FinTech Festival Career Scraper (Juspay, Cashfree, Pine Labs)...")
        try:
            from src.scrapers.fintech_festival_scraper import FinTechFestivalScraper
            scraper = FinTechFestivalScraper()
            jobs = await scraper.scrape_all_festival_sponsors(
                keywords=["engineer", "developer", "backend", "fullstack", "platform", "payments", "software"],
                max_jobs=200
            )
            new_saved, dups = self.save_normalized_jobs(jobs, "gff_fintech")
            self.pipeline_results["FinTech Festival Scraper"] = {
                "fetched": len(jobs),
                "saved": new_saved,
                "duplicates": dups,
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Fintech festival scraper error: {e}")
            self.pipeline_results["FinTech Festival Scraper"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Open Multi-Provider Global Search Engine
    # ──────────────────────────────────────────────────────────────────────────
    async def run_multi_provider_global_search(self):
        t0 = time.time()
        logger.info("🌐 [7/11] Running Multi-Provider Global Search Engine (AIDevBoard, FantasticJobs, USAJobs)...")
        try:
            from src.job_data_providers import search_all
            queries = [
                "Software Engineer",
                "Backend Engineer Python",
                "Full Stack Developer React",
                "DevOps Engineer Kubernetes",
                "Machine Learning Engineer AI",
                "Data Engineer Distributed Systems",
            ]
            all_jobs = []
            for q in queries:
                res_dict = await search_all(query=q, limit=50)
                for prov_name, job_list in res_dict.items():
                    if job_list:
                        all_jobs.extend(job_list)

            new_saved, dups = self.save_normalized_jobs(all_jobs, "multi_provider_search")
            self.pipeline_results["Multi-Provider Global Search"] = {
                "fetched": len(all_jobs),
                "saved": new_saved,
                "duplicates": dups,
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Multi-provider search error: {e}")
            self.pipeline_results["Multi-Provider Global Search"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 8. Specialized DevOps, SRE & Cloud Engineering Pipeline
    # ──────────────────────────────────────────────────────────────────────────
    async def run_devops_specialized_pipeline(self):
        t0 = time.time()
        logger.info("☁️ [8/11] Running Specialized DevOps / SRE / Cloud Engineering Pipeline...")
        try:
            from scripts.run_devops_pipeline import harvest_devops_live_jobs
            jobs = await harvest_devops_live_jobs()
            new_saved, dups = self.save_normalized_jobs(jobs, "devops_live_pipeline")
            self.pipeline_results["DevOps & SRE Pipeline"] = {
                "fetched": len(jobs),
                "saved": new_saved,
                "duplicates": dups,
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"DevOps pipeline error: {e}")
            self.pipeline_results["DevOps & SRE Pipeline"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 9. Specialized Flutter & Mobile Engineering Pipeline
    # ──────────────────────────────────────────────────────────────────────────
    async def run_flutter_specialized_pipeline(self):
        t0 = time.time()
        logger.info("📱 [9/11] Running Specialized Flutter, Mobile & Dart Engineering Pipeline...")
        try:
            from scripts.run_flutter_pipeline import harvest_flutter_live_jobs
            jobs = await harvest_flutter_live_jobs()
            new_saved, dups = self.save_normalized_jobs(jobs, "flutter_live_pipeline")
            self.pipeline_results["Flutter & Mobile Pipeline"] = {
                "fetched": len(jobs),
                "saved": new_saved,
                "duplicates": dups,
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Flutter pipeline error: {e}")
            self.pipeline_results["Flutter & Mobile Pipeline"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 10. Specialized JavaScript, TypeScript & Full-Stack Pipeline
    # ──────────────────────────────────────────────────────────────────────────
    async def run_javascript_specialized_pipeline(self):
        t0 = time.time()
        logger.info("⚡ [10/11] Running Specialized JavaScript / TypeScript / React Full-Stack Pipeline...")
        try:
            import httpx
            js_searches = ["javascript", "typescript", "react", "next.js", "node.js", "frontend", "fullstack", "backend python"]
            harvested = []
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                for q in js_searches:
                    url = f"https://remotive.com/api/remote-jobs?search={q}&limit=50"
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            for item in resp.json().get("jobs", []):
                                harvested.append({
                                    "title": item.get("title", ""),
                                    "company": item.get("company_name", ""),
                                    "location": item.get("candidate_required_location", "Remote / Global"),
                                    "description": item.get("description", "")[:2500],
                                    "url": item.get("url", ""),
                                    "source": "javascript_live_pipeline",
                                    "has_remote": True,
                                    "tags": item.get("tags", ["JavaScript", "TypeScript"]),
                                })
                    except Exception:
                        pass

            new_saved, dups = self.save_normalized_jobs(harvested, "javascript_live_pipeline")
            self.pipeline_results["JavaScript & TypeScript Pipeline"] = {
                "fetched": len(harvested),
                "saved": new_saved,
                "duplicates": dups,
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"JavaScript pipeline error: {e}")
            self.pipeline_results["JavaScript & TypeScript Pipeline"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # 11. Delhi NCR & Accounting / FinOps Pipeline (Samta Jain Corpus)
    # ──────────────────────────────────────────────────────────────────────────
    async def run_delhi_accounting_pipeline(self):
        t0 = time.time()
        logger.info("📊 [11/11] Running Delhi NCR & Accounting / FinOps Pipeline...")
        try:
            from scripts.fetch_bulk_samta_jain_jobs import generate_delhi_accounting_jobs_corpus
            corpus = generate_delhi_accounting_jobs_corpus()
            new_saved, dups = self.save_normalized_jobs(corpus, "samta_jain_delhi_corpus")
            self.pipeline_results["Delhi NCR & FinOps Pipeline"] = {
                "fetched": len(corpus),
                "saved": new_saved,
                "duplicates": dups,
                "duration_s": round(time.time() - t0, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Delhi accounting pipeline error: {e}")
            self.pipeline_results["Delhi NCR & FinOps Pipeline"] = {
                "fetched": 0, "saved": 0, "duplicates": 0,
                "duration_s": round(time.time() - t0, 2),
                "status": f"error: {e}",
            }

    async def run_all(self):
        start_overall = time.time()
        print("\n" + "=" * 80)
        print("  🚀 MASTER JOB PIPELINES HARVESTER & SYNCHRONIZER")
        print(f"  • Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  • Initial Database Jobs Count: {self.initial_count}")
        print("=" * 80 + "\n")

        # Execute all pipelines in sequence / groups
        await self.run_bulk_harvester_pipeline()
        await self.run_master_startups_nifty500_pipeline()
        await self.run_sp500_pipeline()
        await self.run_tier1_companies_pipeline()
        await self.run_indian_app_startups_pipeline()
        await self.run_fintech_festival_pipeline()
        await self.run_multi_provider_global_search()
        await self.run_devops_specialized_pipeline()
        await self.run_flutter_specialized_pipeline()
        await self.run_javascript_specialized_pipeline()
        await self.run_delhi_accounting_pipeline()

        final_count = self.session.query(Job).count()
        total_new_saved = final_count - self.initial_count
        total_time = round(time.time() - start_overall, 2)

        print("\n" + "=" * 85)
        print("  🏁 ALL PIPELINES EXECUTION SUMMARY")
        print("=" * 85)
        print(f"{'Pipeline Name':<42} | {'Fetched':<8} | {'New Saved':<10} | {'Dups':<6} | {'Time (s)':<8} | {'Status'}")
        print("-" * 85)
        for name, r in self.pipeline_results.items():
            print(f"{name:<42} | {r['fetched']:<8} | {r['saved']:<10} | {r['duplicates']:<6} | {r['duration_s']:<8} | {r['status']}")
        print("-" * 85)
        print(f"{'TOTAL ACROSS ALL PIPELINES':<42} | {sum(r['fetched'] for r in self.pipeline_results.values()):<8} | {total_new_saved:<10} | {'-':<6} | {total_time:<8}s | ✅ COMPLETE")
        print(f"\n📊 Initial Jobs in DB: {self.initial_count}  ➔  Final Jobs in DB: {final_count} (+{total_new_saved} Fresh Opportunities)")
        print("=" * 85 + "\n")
        self.session.close()


if __name__ == "__main__":
    runner = MasterPipelineRunner()
    asyncio.run(runner.run_all())
