from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SpamWordMatch(BaseModel):
    word: str = Field(..., description="Spam word or trigger phrase found")
    category: str = Field(..., description="urgency, financial_hype, aggressive_cta, spam_formatting")
    severity: str = Field(default="warning", description="warning, critical")
    suggested_alternatives: List[str] = Field(default_factory=list, description="Safe professional replacements")
    position: int = Field(default=0, description="Character index in draft")


class DeliverabilityAnalysisResult(BaseModel):
    spam_score: float = Field(..., ge=0.0, le=100.0, description="0% = Clean/Primary Inbox, 100% = Guaranteed Spam")
    deliverability_tier: str = Field(..., description="Primary Inbox 🛡️, Promotions Tab ⚠️, Spam Folder 🚨")
    is_safe: bool = Field(..., description="True if spam_score < 40.0")
    flesch_kincaid_grade: float = Field(..., description="Grade level (Target: 5.0 - 7.5)")
    reading_time_seconds: int = Field(..., description="Estimated read time (Target: <45s)")
    word_count: int = Field(...)
    char_count: int = Field(...)
    link_count: int = Field(...)
    uppercase_ratio: float = Field(...)
    spam_matches: List[SpamWordMatch] = Field(default_factory=list)
    subject_score: float = Field(..., ge=0.0, le=100.0)
    subject_advice: str = Field(...)
    deliverability_recommendations: List[str] = Field(default_factory=list)
    timestamp: str
