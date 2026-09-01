"""
celery_crawler_tasks.py — Celery-compatible Task & Periodic Beat Definition for Distributed Job Ingestion.

Allows running the Autonomous Job Crawler on enterprise distributed worker pools (Celery + Redis / RabbitMQ).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    from celery import Celery
    _CELERY_AVAILABLE = True
except ImportError:
    _CELERY_AVAILABLE = False
    Celery = None


if _CELERY_AVAILABLE:
    celery_app = Celery(
        "job_finder_crawler",
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/1",
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        beat_schedule={
            "continuous-job-crawler-every-5-minutes": {
                "task": "src.celery_crawler_tasks.run_crawler_task",
                "schedule": 300.0,  # every 5 minutes
            },
        },
    )

    @celery_app.task(name="src.celery_crawler_tasks.run_crawler_task")
    def run_crawler_task(max_per_source: int = 50) -> Dict[str, Any]:
        """Celery distributed task entry point."""
        from src.autonomous_job_crawler import autonomous_crawler
        return asyncio.run(autonomous_crawler.run_single_pass(max_per_source=max_per_source))
else:
    celery_app = None

    def run_crawler_task(max_per_source: int = 50) -> Dict[str, Any]:
        from src.autonomous_job_crawler import autonomous_crawler
        return asyncio.run(autonomous_crawler.run_single_pass(max_per_source=max_per_source))
