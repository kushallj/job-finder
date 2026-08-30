from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class FillerWordStats(BaseModel):
    total_fillers: int = Field(...)
    filler_percentage: float = Field(..., description="Percentage of spoken words that are fillers")
    fillers_by_word: Dict[str, int] = Field(default_factory=dict)


class CadenceStats(BaseModel):
    wpm: float = Field(..., description="Words per minute")
    duration_seconds: float = Field(...)
    cadence_rating: str = Field(..., description="Optimal (130-160 WPM) ⚡, Too Fast 🏃, Too Slow 🐢")


class StarEvaluation(BaseModel):
    situation_score: float = Field(..., ge=0.0, le=25.0)
    task_score: float = Field(..., ge=0.0, le=25.0)
    action_score: float = Field(..., ge=0.0, le=25.0)
    result_score: float = Field(..., ge=0.0, le=25.0)
    overall_star_score: float = Field(..., ge=0.0, le=100.0)


class VoiceFeedbackResult(BaseModel):
    speech_delivery_score: float = Field(..., ge=0.0, le=100.0, description="Overall verbal delivery score")
    filler_stats: FillerWordStats = Field(...)
    cadence_stats: CadenceStats = Field(...)
    star_eval: StarEvaluation = Field(...)
    delivery_tips: List[str] = Field(default_factory=list)
    timestamp: str
