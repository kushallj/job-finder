"""
VC Intelligence Repository Implementation
Database operations, caching, and deduplication logic adhering to Repository Pattern.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session, joinedload, selectinload

from src.models import VCFirm, PortfolioCompany, CompanyFounder
from src.vc_intelligence.interfaces import IVCRepository
from src.vc_intelligence.models import RawPortfolioCompany, RawFounder

log = logging.getLogger("vc_intelligence.repository")



# Column order of founder contact exports (CSV header even when there are no rows).
EXPORT_CONTACT_FIELDS = ["vc_firm", "company_name", "company_domain", "company_website", "batch_or_year",
                         "funding_stage", "founder_name", "founder_title", "founder_email", "email_confidence",
                         "linkedin_url", "twitter_handle", "source", "last_verified_at"]

class VCIntelligenceRepository(IVCRepository):
    """
    SQLAlchemy repository for VC firms, portfolio companies, and founders.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_firm_by_slug(self, slug: str) -> Optional[VCFirm]:
        """Fetch VC firm by unique slug."""
        return self.db.query(VCFirm).filter(VCFirm.slug == slug).first()

    def list_firms(self, region: Optional[str] = None) -> List[VCFirm]:
        """List all tracked VC firms with eager loaded relationships to avoid N+1 queries, optionally filtered by region."""
        query = (
            self.db.query(VCFirm)
            .options(selectinload(VCFirm.companies).selectinload(PortfolioCompany.founders))
        )
        if region and region.lower() != "all":
            query = query.filter(VCFirm.region.ilike(f"%{region}%"))
        return query.order_by(VCFirm.name.asc()).all()

    def seed_100_firms(self) -> int:
        """
        Seed or update all 100 global VC firms from canonical JSON dataset.
        Returns the count of firms seeded or updated.
        """
        import os
        from pathlib import Path

        json_path = Path(__file__).parent / "data" / "vc_100_firms.json"
        if not json_path.exists():
            log.error(f"100 VC firms JSON file not found at {json_path}")
            return 0

        with open(json_path, "r", encoding="utf-8") as f:
            firms_data = json.load(f)

        seeded_count = 0
        now = datetime.utcnow()

        for item in firms_data:
            existing = self.db.query(VCFirm).filter(VCFirm.slug == item["slug"]).first()
            if existing:
                existing.name = item["name"]
                existing.region = item.get("region", "US & Global")
                existing.website = item.get("website") or existing.website
                existing.portfolio_url = item.get("portfolio_url") or existing.portfolio_url
                existing.country_focus = item.get("country_focus") or existing.country_focus
            else:
                new_firm = VCFirm(
                    name=item["name"],
                    slug=item["slug"],
                    region=item.get("region", "US & Global"),
                    website=item.get("website"),
                    portfolio_url=item.get("portfolio_url"),
                    country_focus=item.get("country_focus", "Global"),
                    created_at=now,
                )
                self.db.add(new_firm)
            seeded_count += 1

        self.db.commit()
        log.info(f"Successfully seeded/updated {seeded_count} VC firms into database.")
        return seeded_count

    def save_companies(
        self, vc_firm_id: int, companies: List[RawPortfolioCompany]
    ) -> Tuple[int, int]:
        """
        Upsert portfolio companies for a given VC firm.
        Deduplicates based on (vc_firm_id, slug).
        Returns: (created_count, updated_count)
        """
        created = 0
        updated = 0
        now = datetime.utcnow()

        for c in companies:
            existing = (
                self.db.query(PortfolioCompany)
                .filter(
                    PortfolioCompany.vc_firm_id == vc_firm_id,
                    PortfolioCompany.slug == c.slug,
                )
                .first()
            )

            tags_json = json.dumps(c.industry_tags or [])

            if existing:
                existing.name = c.name
                existing.domain = c.domain or existing.domain
                existing.website = c.website or existing.website
                existing.description = c.description or existing.description
                existing.batch_or_year = c.batch_or_year or existing.batch_or_year
                existing.funding_stage = c.funding_stage or existing.funding_stage
                existing.industry_tags = tags_json
                existing.careers_url = c.careers_url or existing.careers_url
                existing.last_scraped_at = now
                updated += 1
            else:
                new_comp = PortfolioCompany(
                    vc_firm_id=vc_firm_id,
                    name=c.name,
                    slug=c.slug,
                    domain=c.domain,
                    website=c.website,
                    description=c.description,
                    batch_or_year=c.batch_or_year,
                    funding_stage=c.funding_stage,
                    industry_tags=tags_json,
                    careers_url=c.careers_url,
                    last_scraped_at=now,
                    created_at=now,
                )
                self.db.add(new_comp)
                created += 1

        # Update VC firm last_synced_at
        firm = self.db.query(VCFirm).filter(VCFirm.id == vc_firm_id).first()
        if firm:
            firm.last_synced_at = now

        self.db.commit()
        return created, updated

    def get_company_by_id(self, company_id: int) -> Optional[PortfolioCompany]:
        """Fetch portfolio company by ID."""
        return self.db.query(PortfolioCompany).filter(PortfolioCompany.id == company_id).first()

    def get_company_by_slug(self, vc_firm_id: int, slug: str) -> Optional[PortfolioCompany]:
        """Fetch company by VC firm ID and slug."""
        return (
            self.db.query(PortfolioCompany)
            .filter(
                PortfolioCompany.vc_firm_id == vc_firm_id,
                PortfolioCompany.slug == slug,
            )
            .first()
        )

    def list_companies(
        self,
        vc_slug: Optional[str] = None,
        stage: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PortfolioCompany]:
        """Query portfolio companies with eager loaded VC firm and founders to eliminate N+1 queries."""
        query = self.db.query(PortfolioCompany).options(
            joinedload(PortfolioCompany.vc_firm),
            selectinload(PortfolioCompany.founders),
        )

        if vc_slug:
            firm = self.get_firm_by_slug(vc_slug)
            if firm:
                query = query.filter(PortfolioCompany.vc_firm_id == firm.id)
            else:
                return []

        if stage:
            query = query.filter(PortfolioCompany.funding_stage.ilike(f"%{stage}%"))

        if search:
            query = query.filter(
                (PortfolioCompany.name.ilike(f"%{search}%"))
                | (PortfolioCompany.description.ilike(f"%{search}%"))
                | (PortfolioCompany.domain.ilike(f"%{search}%"))
            )

        return query.order_by(PortfolioCompany.last_scraped_at.desc()).offset(offset).limit(limit).all()

    def save_founders(self, company_id: int, founders: List[RawFounder]) -> int:
        """
        Upsert discovered founders for a specific company.
        Deduplicates on (company_id, full_name).
        """
        if not founders:
            return 0

        now = datetime.utcnow()
        saved = 0

        for f in founders:
            existing = (
                self.db.query(CompanyFounder)
                .filter(
                    CompanyFounder.company_id == company_id,
                    CompanyFounder.full_name == f.full_name,
                )
                .first()
            )

            if existing:
                if f.email and (not existing.email or f.email_confidence >= existing.email_confidence):
                    existing.email = f.email
                    existing.email_confidence = f.email_confidence
                existing.title = f.title or existing.title
                existing.linkedin_url = f.linkedin_url or existing.linkedin_url
                existing.twitter_handle = f.twitter_handle or existing.twitter_handle
                existing.bio = f.bio or existing.bio
                existing.source = f.source or existing.source
                existing.last_verified_at = now
            else:
                new_f = CompanyFounder(
                    company_id=company_id,
                    full_name=f.full_name,
                    title=f.title or "Co-Founder",
                    email=f.email,
                    email_confidence=f.email_confidence,
                    linkedin_url=f.linkedin_url,
                    twitter_handle=f.twitter_handle,
                    bio=f.bio,
                    source=f.source,
                    last_verified_at=now,
                    created_at=now,
                )
                self.db.add(new_f)
            saved += 1

        self.db.commit()
        return saved

    def should_enrich_company(self, company_id: int, max_age_days: int = 30) -> bool:
        """
        Deduplication guard:
        If company already has founders enriched within max_age_days, return False.
        This prevents redundant, costly Firecrawl or Playwright scraping.
        """
        founders = (
            self.db.query(CompanyFounder)
            .filter(CompanyFounder.company_id == company_id)
            .all()
        )
        if not founders:
            return True

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        # Check if any founder was verified recently
        has_recent_data = any(
            f.last_verified_at and f.last_verified_at > cutoff for f in founders
        )
        return not has_recent_data

    def get_founders_by_company(self, company_id: int) -> List[CompanyFounder]:
        """Fetch all founders for a given company."""
        return (
            self.db.query(CompanyFounder)
            .filter(CompanyFounder.company_id == company_id)
            .order_by(CompanyFounder.email_confidence.desc())
            .all()
        )

    def export_contacts(self, vc_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Export all founder contacts and corporate emails as a flat list
        suitable for CSV/JSON outreach export.
        """
        query = (
            self.db.query(CompanyFounder, PortfolioCompany, VCFirm)
            .join(PortfolioCompany, CompanyFounder.company_id == PortfolioCompany.id)
            .join(VCFirm, PortfolioCompany.vc_firm_id == VCFirm.id)
        )
        if vc_slug:
            query = query.filter(VCFirm.slug == vc_slug)

        rows = query.order_by(CompanyFounder.email_confidence.desc()).all()
        results: List[Dict[str, Any]] = []

        for founder, company, firm in rows:
            results.append({
                "vc_firm": firm.name,
                "company_name": company.name,
                "company_domain": company.domain,
                "company_website": company.website,
                "batch_or_year": company.batch_or_year,
                "funding_stage": company.funding_stage,
                "founder_name": founder.full_name,
                "founder_title": founder.title,
                "founder_email": founder.email or "",
                "email_confidence": founder.email_confidence,
                "linkedin_url": founder.linkedin_url or "",
                "twitter_handle": founder.twitter_handle or "",
                "source": founder.source,
                "last_verified_at": founder.last_verified_at.isoformat() if founder.last_verified_at else "",
            })

        return results
