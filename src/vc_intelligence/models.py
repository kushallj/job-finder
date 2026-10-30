"""
VC Intelligence Domain Schemas & DTOs
Strict Pydantic v2 domain schemas for portfolio companies, venture capital firms,
and enriched founder contacts.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RawFounder(BaseModel):
    """Raw founder data extracted from Firecrawl or Playwright scraping."""
    model_config = ConfigDict(from_attributes=True)

    full_name: str = Field(..., description="Full legal or professional name of the founder")
    title: Optional[str] = Field("Co-Founder", description="Designation (e.g. Co-Founder & CEO, CTO)")
    email: Optional[str] = Field(None, description="Direct verified or synthesized corporate email")
    email_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score of email discovery (0.0 to 1.0)")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    twitter_handle: Optional[str] = Field(None, description="Twitter / X profile handle or URL")
    bio: Optional[str] = Field(None, description="Founder biography or summary from team/about page")
    source: str = Field("firecrawl", description="Source provider: firecrawl, playwright, or heuristic")


class RawPortfolioCompany(BaseModel):
    """Raw portfolio company extracted from a VC directory."""
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Official company / startup name")
    slug: str = Field(..., description="Unique URL slug or identifier")
    domain: Optional[str] = Field(None, description="Primary domain e.g. stripe.com")
    website: Optional[str] = Field(None, description="Full website URL")
    description: Optional[str] = Field(None, description="Company mission / product description")
    batch_or_year: Optional[str] = Field(None, description="Batch, vintage, or funding year (e.g. W24, 2023)")
    funding_stage: Optional[str] = Field(None, description="Investment stage (e.g. Seed, Series A, Growth)")
    industry_tags: List[str] = Field(default_factory=list, description="Industry or sector tags")
    careers_url: Optional[str] = Field(None, description="Careers or job board URL")
    founders: List[RawFounder] = Field(default_factory=list, description="Associated founders if extracted directly")


class CompanyFounderDTO(BaseModel):
    """Founder data transfer object for API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    full_name: str
    title: Optional[str] = None
    email: Optional[str] = None
    email_confidence: float = 0.0
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    bio: Optional[str] = None
    source: str = "firecrawl"
    last_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class PortfolioCompanyDTO(BaseModel):
    """Portfolio company data transfer object."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    vc_firm_id: int
    vc_firm_name: Optional[str] = None
    name: str
    slug: str
    domain: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    batch_or_year: Optional[str] = None
    funding_stage: Optional[str] = None
    industry_tags: List[str] = Field(default_factory=list)
    careers_url: Optional[str] = None
    last_scraped_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    founders: List[CompanyFounderDTO] = Field(default_factory=list)


class VCFirmDTO(BaseModel):
    """Venture Capital Firm summary data transfer object."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    website: Optional[str] = None
    portfolio_url: Optional[str] = None
    country_focus: str = "Global"
    companies_count: int = 0
    founders_count: int = 0
    last_synced_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class VCSyncRequest(BaseModel):
    """Request payload to initiate portfolio synchronization."""
    max_companies: int = Field(50, ge=1, le=500, description="Max portfolio companies to extract")
    enrich_contacts: bool = Field(True, description="Whether to also trigger founder email & contact enrichment")


class VCSyncResponse(BaseModel):
    """Response payload following a VC synchronization run."""
    vc_slug: str
    vc_name: str
    companies_synced: int
    companies_updated: int
    founders_discovered: int
    status: str = "success"
    message: str
