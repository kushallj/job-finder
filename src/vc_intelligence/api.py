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
    description="Retrieve all supported VC firms (Y Combinator, Accel, Blume, Tiger Global, India Accelerator) and metrics.",
)
def list_vc_firms(
    service: VCIntelligenceService = Depends(get_vc_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    return service.list_firms()


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
