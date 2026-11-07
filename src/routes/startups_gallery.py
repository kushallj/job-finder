"""
src/routes/startups_gallery.py — REST API Endpoints for startups.gallery Founder Discovery & Batch Mining
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.database import SessionLocal
from src.models import Contact, StartupsGalleryCompanyRecord
from src.company_sources.miners.startups_gallery_miner import startups_gallery_miner
from src.company_sources.registries.startups_gallery_registry import get_category_breakdown

router = APIRouter(prefix="/api/startups-gallery", tags=["startups-gallery"])


class MineBatchRequest(BaseModel):
    batch_size: int = Field(default=100, ge=1, le=500, description="Number of unmined companies to process")
    category: Optional[str] = Field(default=None, description="Filter by sector (e.g. AI, Fintech)")
    auto_send: bool = Field(default=False, description="Auto-send outreach email within rate limits")
    extract_twitter: bool = Field(default=True, description="Attempt X (Twitter) profile discovery")


@router.get("/status")
def get_mining_status():
    """Retrieve aggregate mining statistics and progress across all 1,369 companies."""
    return startups_gallery_miner.get_status()


@router.get("/categories")
def get_categories():
    """List available industry categories and their company counts."""
    return get_category_breakdown()


@router.get("/companies")
def list_companies(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    category: Optional[str] = None,
    mined: Optional[bool] = None,
):
    """Retrieve paginated list of companies from startups.gallery."""
    startups_gallery_miner._ensure_database_seeded()
    with SessionLocal() as db:
        query = db.query(StartupsGalleryCompanyRecord)
        if category:
            query = query.filter(StartupsGalleryCompanyRecord.category.ilike(f"%{category}%"))
        if mined is not None:
            query = query.filter(StartupsGalleryCompanyRecord.mined == mined)

        total = query.count()
        records = query.offset((page - 1) * limit).limit(limit).all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "companies": [
                {
                    "slug": r.slug,
                    "name": r.name,
                    "domain": r.domain,
                    "category": r.category,
                    "funding": r.funding,
                    "location": r.location,
                    "mined": r.mined,
                    "mined_at": r.mined_at.isoformat() if r.mined_at else None,
                    "founders_count": r.founders_count,
                }
                for r in records
            ],
        }


@router.post("/mine-batch")
async def trigger_mine_batch(req: MineBatchRequest):
    """Trigger an on-demand batch mining execution."""
    result = await startups_gallery_miner.batch_mine(
        batch_size=req.batch_size,
        category=req.category,
        auto_send=req.auto_send,
        extract_twitter=req.extract_twitter,
    )
    return result


@router.get("/founders")
def list_mined_founders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    company: Optional[str] = None,
    has_twitter: Optional[bool] = None,
):
    """Retrieve paginated list of extracted founders with LinkedIn, X, and Email."""
    with SessionLocal() as db:
        query = db.query(Contact).filter(Contact.source == "startups_gallery")
        if company:
            query = query.filter(Contact.company.ilike(f"%{company}%"))
        if has_twitter is True:
            query = query.filter(Contact.twitter_url.isnot(None))

        total = query.count()
        records = query.order_by(Contact.found_at.desc()).offset((page - 1) * limit).limit(limit).all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "founders": [
                {
                    "id": c.id,
                    "name": c.name,
                    "title": c.title,
                    "company": c.company,
                    "category": c.department,
                    "email": c.email,
                    "linkedin_url": c.linkedin_url,
                    "twitter_url": c.twitter_url,
                    "confidence_score": c.confidence_score,
                    "found_at": c.found_at.isoformat() if c.found_at else None,
                }
                for c in records
            ],
        }
