from __future__ import annotations

from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class InterviewerPersona(str, Enum):
    RECRUITER_SARA = "recruiter_sara"
    ARCHITECT_ALEX = "architect_alex"
    BAR_RAISER_MARCUS = "bar_raiser_marcus"
    STARTUP_CTO_ELENA = "startup_cto_elena"


class TurnDialogue(BaseModel):
    turn_index: int = Field(..., ge=1)
    question: str = Field(..., min_length=1)
    interviewer_persona: str = Field(...)
    candidate_answer: str = Field(default="")
    duration_seconds: float = Field(default=0.0)
    wpm: float = Field(default=0.0)
    filler_words_detected: List[str] = Field(default_factory=list)
    star_breakdown: Dict[str, float] = Field(default_factory=dict, description="S, T, A, R scores 0-25 each")
    turn_score: float = Field(default=0.0, ge=0.0, le=100.0)
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    gold_standard_ideal_answer: str = Field(default="")
    completed: bool = Field(default=False)


class InterviewSessionConfig(BaseModel):
    session_id: str = Field(...)
    company: str = Field(..., min_length=1)
    role_title: str = Field(..., min_length=1)
    persona: InterviewerPersona = Field(default=InterviewerPersona.RECRUITER_SARA)
    job_description: Optional[str] = Field(default=None)
    candidate_resume_summary: Optional[str] = Field(default=None)
    total_questions_target: int = Field(default=4, ge=2, le=8)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class InterviewDiagnosticScorecard(BaseModel):
    session_id: str = Field(...)
    company: str = Field(...)
    role_title: str = Field(...)
    persona: InterviewerPersona = Field(...)
    overall_score: float = Field(..., ge=0.0, le=100.0)
    readiness_verdict: str = Field(..., description="Strong Hire, Lean Hire, Needs Polish, High Risk")
    technical_depth_score: float = Field(..., ge=0.0, le=100.0)
    star_structure_score: float = Field(..., ge=0.0, le=100.0)
    delivery_cadence_score: float = Field(..., ge=0.0, le=100.0)
    leadership_impact_score: float = Field(..., ge=0.0, le=100.0)
    turns: List[TurnDialogue] = Field(default_factory=list)
    key_strengths: List[str] = Field(default_factory=list)
    high_priority_improvements: List[str] = Field(default_factory=list)
    practice_drills_recommended: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
