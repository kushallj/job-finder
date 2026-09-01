"""
Application Use Case: IngestJobsUseCase
Coordinates scraping strategies, taxonomy classification, and bulk repository persistence.
"""
import asyncio
from typing import List, Dict, Any, Tuple
from src.domain.entities.job import Job
from src.domain.interfaces.repositories.i_job_repository import IJobRepository
from src.domain.interfaces.services.i_scraper_strategy import IScraperStrategy
from src.application.services.job_deduplicator import JobDeduplicator
from src.application.services.taxonomy_classifier import TaxonomyClassifier


class IngestJobsUseCase:
    """
    Orchestrates ingestion sweep across ATS strategies and persists enriched jobs.

    Time Complexity:
        execute_sweep(): O(N * (Scrape + DB_Upsert) / Concurrency)
    Space Complexity:
        O(Batch_Size)
    """

    def __init__(
        self,
        job_repository: IJobRepository,
        strategies: List[IScraperStrategy],
    ):
        self.job_repository = job_repository
        self.strategies = strategies

    async def execute_sweep(
        self, targets: List[Dict[str, Any]], max_per_target: int = 50
    ) -> Dict[str, Any]:
        """Run concurrent scraping sweep over registered company targets."""
        all_raw_jobs: List[Job] = []

        for strat in self.strategies:
            strat_targets = [t for t in targets if t.get("strategy") == strat.strategy_name or not t.get("strategy")]
            tasks = [
                strat.fetch_jobs_for_target(target, max_jobs=max_per_target)
                for target in strat_targets
            ]
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, list):
                        all_raw_jobs.extend(res)

        # Classify and enrich jobs with taxonomy
        enriched_jobs: List[Job] = []
        for j in all_raw_jobs:
            stack, level, is_remote, work_mode = TaxonomyClassifier.classify(j.title, j.description)
            j.tech_stack = stack
            j.experience_level = level
            j.has_remote = is_remote
            j.work_mode = work_mode
            enriched_jobs.append(j)

        # Deduplicate and persist in bulk
        unique_jobs, _ = JobDeduplicator.deduplicate_batch(enriched_jobs)
        inserted, updated = await self.job_repository.save_batch(unique_jobs)

        return {
            "total_fetched": len(all_raw_jobs),
            "total_inserted": inserted,
            "total_updated": updated,
            "strategies_executed": [s.strategy_name for s in self.strategies],
        }
