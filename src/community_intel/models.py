from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class IntelSourceType(str, Enum):
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    MEDIUM = "medium"
    SUBSTACK = "substack"
    YOUTUBE = "youtube"


class CommunityIntelItem(BaseModel):
    source: IntelSourceType = Field(..., description="reddit, hackernews, medium, substack, youtube")
    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    author: Optional[str] = Field(default=None)
    published_at: Optional[str] = Field(default=None)
    summary: str = Field(..., description="High-signal summary of interview/company experience")
    relevance_score: float = Field(default=85.0, ge=0.0, le=100.0)
    tags: List[str] = Field(default_factory=list, description="e.g. ['coding_round', 'system_design', 'compensation', 'culture']")


class InterviewLoopBreakdown(BaseModel):
    rounds: List[Dict[str, str]] = Field(default_factory=list, description="Rounds e.g. Recruiter Screen, Technical Coding, System Design, Hiring Manager Fit")
    common_questions: List[str] = Field(default_factory=list, description="Specific questions reported by past candidates")
    system_design_topics: List[str] = Field(default_factory=list, description="Architecture problems typically asked")
    red_flags: List[str] = Field(default_factory=list, description="Culture or process warnings reported by employees/candidates")
    green_flags: List[str] = Field(default_factory=list, description="Positive highlights e.g. engineering autonomy, rapid promotions")
    negotiation_tips: List[str] = Field(default_factory=list, description="Insider compensation negotiation levers")


class CompanyCommunityIntel(BaseModel):
    company: str = Field(..., min_length=1)
    role_category: Optional[str] = Field(default="Software Engineering")
    total_sources_scanned: int = Field(default=0)
    overall_sentiment: str = Field(default="High-Bar / Challenging", description="Positive, Neutral, Challenging, High-Bar")
    interview_debrief: InterviewLoopBreakdown = Field(default_factory=InterviewLoopBreakdown)
    sources: List[CommunityIntelItem] = Field(default_factory=list)
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
