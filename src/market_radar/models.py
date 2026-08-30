from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RemoteArbitrageRole(BaseModel):
    title: str = Field(...)
    company: str = Field(...)
    country: str = Field(default="United States")
    currency: str = Field(default="USD")
    base_comp_range: str = Field(...)
    inr_equivalent_range: str = Field(...)
    ppp_multiplier: float = Field(default=3.4, description="Purchasing Power Parity value multiplier in India")
    tz_overlap_hours: str = Field(default="3–4 hrs (EST/IST overlap)")
    tax_advantage: str = Field(default="50% Presumptive Tax under Section 44ADA")
    source_url: str = Field(...)
    skills_required: List[str] = Field(default_factory=list)


class GCCHubInsight(BaseModel):
    hub_city: str = Field(...)
    active_openings: int = Field(...)
    top_employers: List[str] = Field(default_factory=list)
    median_senior_ctc: str = Field(...)
    growth_yoy: str = Field(...)


class MarketRadarResponse(BaseModel):
    status: str = Field(default="success")
    usd_to_inr_rate: float = Field(default=87.20)
    eur_to_inr_rate: float = Field(default=94.50)
    remote_global_roles: List[RemoteArbitrageRole] = Field(default_factory=list)
    top_gcc_hubs: List[GCCHubInsight] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
