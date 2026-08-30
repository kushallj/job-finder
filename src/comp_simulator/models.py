from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class OfferPackage(BaseModel):
    company: str = Field(..., min_length=1)
    role_title: str = Field(..., min_length=1)
    base_salary: float = Field(..., ge=0.0, description="Annual base salary in USD")
    signon_bonus: float = Field(default=0.0, ge=0.0, description="Year 1 sign-on cash bonus")
    target_bonus_pct: float = Field(default=15.0, ge=0.0, le=100.0, description="Target performance bonus %")
    equity_grant_usd: float = Field(default=0.0, ge=0.0, description="Total 4-year equity grant value in USD")
    vesting_schedule: str = Field(default="standard_4yr_25", description="standard_4yr_25, amazon_5_15_40_40, even_quarterly")
    custom_vesting_splits: Optional[List[float]] = Field(None, description="4-year percentage splits e.g. [25, 25, 25, 25]")
    stock_type: str = Field(default="RSU", description="RSU, StockOptions")
    startup_exit_multiple: float = Field(default=1.0, ge=0.1, le=100.0, description="Scenario multiple e.g. 1x, 3x, 5x")
    estimated_tax_rate: float = Field(default=35.0, ge=0.0, le=70.0, description="Combined state + federal tax rate %")


class YearlyCompBreakdown(BaseModel):
    year: int = Field(...)
    base_salary: float = Field(...)
    cash_bonus: float = Field(...)
    equity_vested: float = Field(...)
    total_pre_tax: float = Field(...)
    take_home_post_tax: float = Field(...)


class CompSimulationResult(BaseModel):
    company: str = Field(...)
    role_title: str = Field(...)
    four_year_total_pre_tax: float = Field(...)
    four_year_total_post_tax: float = Field(...)
    average_annual_comp: float = Field(...)
    yearly_breakdowns: List[YearlyCompBreakdown] = Field(default_factory=list)
    negotiation_counter_target: float = Field(..., description="Suggested realistic counter-offer target (10-18% boost)")
    negotiation_advice: str = Field(...)
    timestamp: str
