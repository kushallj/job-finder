"""
Presentation Router: CrawlerRouter
Endpoints for controlling and observing the autonomous background crawler engine.
Adheres to Single Responsibility Principle (SRP).
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.autonomous_job_crawler import autonomous_crawler

router = APIRouter(prefix="/api/crawler", tags=["crawler"])


class CrawlerControlRequest(BaseModel):
    interval_seconds: Optional[int] = Field(default=120, ge=15, le=86400)


@router.get("/status")
async def get_crawler_status():
    """Get live real-time metrics, telemetry, and health of autonomous crawler."""
    try:
        return autonomous_crawler.get_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/start")
async def start_crawler(req: CrawlerControlRequest = CrawlerControlRequest()):
    """Activate continuous background scraping daemon."""
    try:
        autonomous_crawler.start_continuous_crawler(interval_seconds=req.interval_seconds or 120)
        return {
            "status": "started",
            "message": f"Autonomous crawler started with {req.interval_seconds}s interval.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/stop")
async def stop_crawler():
    """Halt background crawler execution."""
    try:
        autonomous_crawler.stop_continuous_crawler()
        return {"status": "stopped", "message": "Autonomous crawler stopped."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/run-single-pass")
async def run_crawler_single_pass():
    """Execute immediate full ingestion pass across all sourcing engines."""
    try:
        summary = await autonomous_crawler.run_single_pass()
        return {"status": "success", "results": summary}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/metrics")
async def get_crawler_metrics():
    """Retrieve categorized job metrics breakdown for dashboard pitch."""
    try:
        return autonomous_crawler.get_metrics_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
