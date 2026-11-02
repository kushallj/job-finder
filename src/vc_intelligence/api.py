"""
FastAPI Router: VC Intelligence & Founder Contacts
Endpoints for venture capital portfolio discovery, founder extraction,
enrichment, and contact leads export.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import get_current_user, get_optional_current_user
from src.models import User
from src.vc_intelligence.models import (
    VCFirmDTO,
    PortfolioCompanyDTO,
    CompanyFounderDTO,
    VCSyncRequest,
    VCSyncResponse,
    BatchVCSyncRequest,
    BatchVCSyncResponse,
)
from src.vc_intelligence.repository import VCIntelligenceRepository
from src.vc_intelligence.service import VCIntelligenceService

log = logging.getLogger("vc_intelligence.api")

router = APIRouter()


def get_vc_service(db: Session = Depends(get_db)) -> VCIntelligenceService:
    """Dependency injection helper for VCIntelligenceService."""
    repo = VCIntelligenceRepository(db)
    return VCIntelligenceService(repository=repo)


@router.get(
    "/firms",
    response_model=List[VCFirmDTO],
    summary="List all tracked VC firms",
    description="Retrieve supported VC firms across global regions with summary metrics.",
)
def list_vc_firms(
    region: Optional[str] = Query(None, description="Filter by region (e.g. India, Europe, US & Global)"),
    service: VCIntelligenceService = Depends(get_vc_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    return service.list_firms(region=region)


@router.get(
    "/regions",
    summary="List VC regions and counts",
    description="Retrieve available regions and the count of firms in each.",
)
def get_vc_regions(
    service: VCIntelligenceService = Depends(get_vc_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    firms = service.list_firms()
    counts: dict[str, int] = {}
    for f in firms:
        r = f.region or "US & Global"
        counts[r] = counts.get(r, 0) + 1
    return {"total_firms": len(firms), "regions": counts}


@router.post(
    "/seed-100",
    summary="Seed 100 Global VC firms",
    description="Seed all 100 leading global VC firms across 6 regions into the database.",
)
def seed_100_vc_firms(
    service: VCIntelligenceService = Depends(get_vc_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    count = service.seed_100_firms()
    return {"status": "success", "firms_seeded": count}


@router.post(
    "/batch/sync",
    response_model=BatchVCSyncResponse,
    summary="Batch synchronize VC firms",
    description="Synchronize multiple VC firms across a region or slug list.",
)
async def batch_sync_vcs(
    payload: BatchVCSyncRequest,
    service: VCIntelligenceService = Depends(get_vc_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    return await service.batch_sync(payload)


@router.post(
    "/firms/{slug}/sync",
    response_model=VCSyncResponse,
    summary="Synchronize VC portfolio companies & founders",
    description="Trigger scraper strategy and enrichment cascade with automatic deduplication.",
)
async def sync_vc_firm(
    slug: str,
    payload: VCSyncRequest = VCSyncRequest(),
    service: VCIntelligenceService = Depends(get_vc_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    res = await service.sync_vc_firm(
        slug=slug,
        max_companies=payload.max_companies,
        enrich_contacts=payload.enrich_contacts,
    )
    if res.status == "error":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=res.message)
    return res


@router.get(
    "/companies",
    response_model=List[PortfolioCompanyDTO],
    summary="Query portfolio companies",
    description="Search and filter portfolio companies by VC firm, funding stage, or keyword.",
)
def list_portfolio_companies(
    vc_slug: Optional[str] = Query(None, description="Filter by VC firm slug (e.g. y-combinator)"),
    stage: Optional[str] = Query(None, description="Filter by stage (e.g. Seed, Series A, Growth)"),
    search: Optional[str] = Query(None, description="Search keyword in company name or description"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: VCIntelligenceService = Depends(get_vc_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    return service.list_companies(
        vc_slug=vc_slug,
        stage=stage,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/companies/{company_id}/founders",
    response_model=List[CompanyFounderDTO],
    summary="Get founders of a specific company",
)
def get_company_founders(
    company_id: int,
    service: VCIntelligenceService = Depends(get_vc_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    founders = service.get_company_founders(company_id)
    if not founders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No founders found for company ID {company_id}",
        )
    return founders


@router.post(
    "/companies/{company_id}/enrich",
    response_model=List[CompanyFounderDTO],
    summary="Enrich company founders on-demand",
    description="Trigger Firecrawl / Playwright contact discovery for a single portfolio company.",
)
async def enrich_company(
    company_id: int,
    force: bool = Query(False, description="Force re-scraping even if cached within 30 days"),
    service: VCIntelligenceService = Depends(get_vc_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    founders = await service.enrich_company_founders(company_id=company_id, force=force)
    return founders


@router.get(
    "/export",
    summary="Export founder contact leads",
    description="Export discovered founders and verified corporate emails as CSV or JSON.",
)
def export_contacts(
    vc_slug: Optional[str] = Query(None, description="Filter export by specific VC firm"),
    format: str = Query("csv", pattern="^(csv|json)$"),
    service: VCIntelligenceService = Depends(get_vc_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    contacts = service.export_contacts(vc_slug=vc_slug)

    if format == "json":
        return contacts

    # Generate CSV stream
    output = io.StringIO()
    if contacts:
        fieldnames = list(contacts[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(contacts)
    else:
        writer = csv.writer(output)
        writer.writerow(["No founder contact leads available for export."])

    filename = f"vc_founder_contacts_{vc_slug or 'all'}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- CONTINUOUS 50-FOUNDER BATCH HARVESTER ENDPOINTS ---

@router.get(
    "/continuous/status",
    summary="Get continuous batch runner status",
    description="Telemetry for continuous scraping and founder batch harvesting.",
)
def get_continuous_status():
    from src.vc_intelligence.continuous_runner import ContinuousVCBatchRunner
    runner = ContinuousVCBatchRunner.get_instance()
    return runner.get_status()


@router.post(
    "/continuous/run-batch-now",
    summary="Trigger immediate 50-founder batch harvesting",
    description="Harvests a single batch of up to 50 verified founders immediately.",
)
def run_batch_now():
    from src.vc_intelligence.continuous_runner import ContinuousVCBatchRunner
    runner = ContinuousVCBatchRunner.get_instance()
    res = runner.run_batch_synchronous()
    return res


@router.post(
    "/continuous/start",
    summary="Start continuous background batch harvester",
    description="Starts autonomous loop harvesting 50-founder batches.",
)
async def start_continuous(
    batch_size: int = Query(50, ge=5, le=100),
    max_batches: Optional[int] = Query(None, ge=1),
    interval_seconds: float = Query(2.0, ge=0.5, le=60.0),
):
    import asyncio
    from src.vc_intelligence.continuous_runner import ContinuousVCBatchRunner

    runner = ContinuousVCBatchRunner.get_instance()
    if runner.is_running:
        return {"status": "already_running", "message": "Continuous batch harvester is already running."}

    # Start loop in background task
    asyncio.create_task(
        runner.start_continuous_loop(
            batch_size=batch_size,
            max_batches=max_batches,
            delay_seconds=interval_seconds,
        )
    )
    return {"status": "started", "batch_size": batch_size, "interval_seconds": interval_seconds}


@router.post(
    "/continuous/stop",
    summary="Stop continuous batch harvester",
    description="Sends graceful stop signal to the background batch harvester.",
)
def stop_continuous():
    from src.vc_intelligence.continuous_runner import ContinuousVCBatchRunner
    runner = ContinuousVCBatchRunner.get_instance()
    runner.stop()
    return {"status": "stopping", "message": "Stop signal dispatched to continuous batch harvester."}

