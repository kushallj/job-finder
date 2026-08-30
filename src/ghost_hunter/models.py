from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class GhostSignal(BaseModel):
    name: str = Field(..., description="Signal identifier e.g. 'stale_posting_date'")
    description: str = Field(..., description="Human readable evidence")
    score_impact: float = Field(..., description="Impact on ghost score (-30 to +40)")
    severity: str = Field(default="neutral", description="positive, warning, critical")


class GhostAnalysisResult(BaseModel):
    ghost_score: float = Field(..., ge=0.0, le=100.0, description="0% = Fresh/High Urgency, 100% = Stale Ghost Job")
    urgency_label: str = Field(..., description="Active Hiring ⚡, Moderate / Evergreen ⚠️, High Ghost Risk 👻")
    is_ghost_risk: bool = Field(..., description="True if ghost_score >= 60")
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    estimated_age_days: Optional[int] = Field(None, description="Estimated age in days")
    signals: List[GhostSignal] = Field(default_factory=list)
    action_recommendation: str = Field(..., description="Actionable advice for candidate")
    timestamp: str
