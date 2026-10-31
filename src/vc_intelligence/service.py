"""
VC Intelligence Orchestration Service
Coordinates portfolio extraction, contact enrichment, deduplication caching,
and lead generation adhering to Dependency Inversion Principle (DIP).
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Any

from src.models import VCFirm, PortfolioCompany, CompanyFounder
from src.vc_intelligence.interfaces import IFounderEnricher
from src.vc_intelligence.models import (
    RawPortfolioCompany,
    VCFirmDTO,
    PortfolioCompanyDTO,
    CompanyFounderDTO,
    VCSyncResponse,
    BatchVCSyncRequest,
    BatchVCSyncResponse,
)
from src.vc_intelligence.repository import VCIntelligenceRepository
from src.vc_intelligence.scrapers.registry import VCScraperRegistry
from src.vc_intelligence.enrichers import CompositeFounderEnricher

log = logging.getLogger("vc_intelligence.service")


class VCIntelligenceService:
    """
    Core Domain Service for VC portfolio company intelligence & founder contact discovery.
    """

    def __init__(
        self,
        repository: VCIntelligenceRepository,
        enricher: Optional[IFounderEnricher] = None,
    ):
        self.repo = repository
        self.enricher = enricher or CompositeFounderEnricher()

    async def sync_vc_firm(
        self,
        slug: str,
        max_companies: int = 50,
        enrich_contacts: bool = True,
    ) -> VCSyncResponse:
        """
        Synchronize portfolio companies and founders for a specific VC firm.
        Applies deduplication caching to avoid redundant scraping.
        """
        firm = self.repo.get_firm_by_slug(slug)
        if not firm:
            return VCSyncResponse(
                vc_slug=slug,
                vc_name=slug,
                companies_synced=0,
                companies_updated=0,
                founders_discovered=0,
                status="error",
                message=f"VC firm '{slug}' is not registered in the database.",
            )

        scraper = VCScraperRegistry.get(slug)
        if not scraper:
            return VCSyncResponse(
                vc_slug=slug,
                vc_name=firm.name,
                companies_synced=0,
                companies_updated=0,
                founders_discovered=0,
                status="error",
                message=f"No scraper strategy registered for slug '{slug}'.",
            )

        log.info(f"Initiating portfolio extraction for {firm.name} ({slug})...")
        raw_companies: List[RawPortfolioCompany] = await scraper.scrape_companies(max_companies=max_companies)

        # 1. Persist portfolio companies
        created_count, updated_count = self.repo.save_companies(firm.id, raw_companies)
        log.info(f"Saved {firm.name} companies: {created_count} created, {updated_count} updated")

        # 2. Enrich founders (with 30-day deduplication cache)
        founders_count = 0
        if enrich_contacts:
            for raw_c in raw_companies:
                saved_comp = self.repo.get_company_by_slug(firm.id, raw_c.slug)
                if not saved_comp:
                    continue

                # Deduplication check: skip if already enriched within 30 days
                if not self.repo.should_enrich_company(saved_comp.id, max_age_days=30):
                    log.debug(f"Skipping enrichment for {saved_comp.name}: cached within 30 days")
                    continue

                try:
                    discovered_founders = await self.enricher.enrich_founders(raw_c)
                    if discovered_founders:
                        n_saved = self.repo.save_founders(saved_comp.id, discovered_founders)
                        founders_count += n_saved
                except Exception as enrich_exc:
                    log.warning(f"Failed to enrich founders for {raw_c.name}: {enrich_exc}")

        return VCSyncResponse(
            vc_slug=slug,
            vc_name=firm.name,
            companies_synced=created_count,
            companies_updated=updated_count,
            founders_discovered=founders_count,
            status="success",
            message=(
                f"Successfully synced {firm.name}: {created_count} new companies, "
                f"{updated_count} updated, {founders_count} founder contacts enriched."
            ),
        )

    async def enrich_company_founders(
        self, company_id: int, force: bool = False
    ) -> List[CompanyFounderDTO]:
        """
        On-demand founder discovery for a single portfolio company.
        """
        company = self.repo.get_company_by_id(company_id)
        if not company:
            return []

        # Deduplication check
        if not force and not self.repo.should_enrich_company(company_id, max_age_days=30):
            log.info(f"Serving cached founders for {company.name}")
            return [self._founder_to_dto(f, company) for f in self.repo.get_founders_by_company(company_id)]

        tags = []
        try:
            tags = json.loads(company.industry_tags or "[]")
        except Exception:
            pass

        raw_c = RawPortfolioCompany(
            name=company.name,
            slug=company.slug,
            domain=company.domain,
            website=company.website,
            description=company.description,
            batch_or_year=company.batch_or_year,
            funding_stage=company.funding_stage,
            industry_tags=tags,
            careers_url=company.careers_url,
        )

        discovered = await self.enricher.enrich_founders(raw_c)
        if discovered:
            self.repo.save_founders(company_id, discovered)

        return [self._founder_to_dto(f, company) for f in self.repo.get_founders_by_company(company_id)]

    def list_firms(self, region: Optional[str] = None) -> List[VCFirmDTO]:
        """List all tracked VC firms with aggregate metrics, optionally filtered by region."""
        firms = self.repo.list_firms(region=region)
        dtos: List[VCFirmDTO] = []
        for firm in firms:
            c_count = len(firm.companies) if firm.companies else 0
            f_count = sum(len(c.founders) for c in firm.companies) if firm.companies else 0
            dtos.append(
                VCFirmDTO(
                    id=firm.id,
                    name=firm.name,
                    slug=firm.slug,
                    website=firm.website,
                    portfolio_url=firm.portfolio_url,
                    country_focus=firm.country_focus or "Global",
                    region=firm.region or "US & Global",
                    companies_count=c_count,
                    founders_count=f_count,
                    last_synced_at=firm.last_synced_at,
                    created_at=firm.created_at,
                )
            )
        return dtos

    def seed_100_firms(self) -> int:
        """Seed all 100 global VC firms into database."""
        return self.repo.seed_100_firms()

    async def batch_sync(self, req: BatchVCSyncRequest) -> BatchVCSyncResponse:
        """
        Synchronize multiple VC firms in batch by region or slug list.
        """
        firms_to_sync: List[str] = []

        if req.slugs:
            firms_to_sync = req.slugs
        else:
            db_firms = self.repo.list_firms(region=req.region)
            firms_to_sync = [f.slug for f in db_firms]

        results: List[VCSyncResponse] = []
        total_companies = 0
        total_founders = 0

        for slug in firms_to_sync:
            try:
                res = await self.sync_vc_firm(
                    slug=slug,
                    max_companies=req.max_companies_per_firm,
                    enrich_contacts=req.enrich_contacts,
                )
                results.append(res)
                total_companies += res.companies_synced
                total_founders += res.founders_discovered
            except Exception as e:
                log.error(f"Batch sync failed for {slug}: {e}")
                results.append(
                    VCSyncResponse(
                        vc_slug=slug,
                        vc_name=slug,
                        companies_synced=0,
                        companies_updated=0,
                        founders_discovered=0,
                        status="error",
                        message=str(e),
                    )
                )

        return BatchVCSyncResponse(
            total_firms_processed=len(firms_to_sync),
            total_companies_synced=total_companies,
            total_founders_discovered=total_founders,
            results=results,
        )

    def list_companies(
        self,
        vc_slug: Optional[str] = None,
        stage: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PortfolioCompanyDTO]:
        """List portfolio companies with founders and metadata."""
        comps = self.repo.list_companies(
            vc_slug=vc_slug, stage=stage, search=search, limit=limit, offset=offset
        )
        results: List[PortfolioCompanyDTO] = []
        for c in comps:
            founders_dtos = [self._founder_to_dto(f, c) for f in c.founders]
            tags = []
            try:
                tags = json.loads(c.industry_tags or "[]")
            except Exception:
                pass

            results.append(
                PortfolioCompanyDTO(
                    id=c.id,
                    vc_firm_id=c.vc_firm_id,
                    vc_firm_name=c.vc_firm.name if c.vc_firm else None,
                    name=c.name,
                    slug=c.slug,
                    domain=c.domain,
                    website=c.website,
                    description=c.description,
                    batch_or_year=c.batch_or_year,
                    funding_stage=c.funding_stage,
                    industry_tags=tags,
                    careers_url=c.careers_url,
                    last_scraped_at=c.last_scraped_at,
                    created_at=c.created_at,
                    founders=founders_dtos,
                )
            )
        return results

    def get_company_founders(self, company_id: int) -> List[CompanyFounderDTO]:
        """Fetch founders of a specific company."""
        company = self.repo.get_company_by_id(company_id)
        if not company:
            return []
        founders = self.repo.get_founders_by_company(company_id)
        return [self._founder_to_dto(f, company) for f in founders]

    def export_contacts(self, vc_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        """Export all founder contacts as a list of dictionaries."""
        return self.repo.export_contacts(vc_slug=vc_slug)

    @staticmethod
    def _founder_to_dto(f: CompanyFounder, c: PortfolioCompany) -> CompanyFounderDTO:
        return CompanyFounderDTO(
            id=f.id,
            company_id=f.company_id,
            company_name=c.name,
            company_domain=c.domain,
            full_name=f.full_name,
            title=f.title,
            email=f.email,
            email_confidence=f.email_confidence,
            linkedin_url=f.linkedin_url,
            twitter_handle=f.twitter_handle,
            bio=f.bio,
            source=f.source or "firecrawl",
            last_verified_at=f.last_verified_at,
            created_at=f.created_at,
        )
