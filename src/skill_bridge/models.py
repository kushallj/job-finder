from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SkillGapAnalysis(BaseModel):
    candidate_skills: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    gap_skills: List[str] = Field(default_factory=list)
    match_percentage: float = Field(..., ge=0.0, le=100.0)


class MicroProjectSpec(BaseModel):
    title: str = Field(..., min_length=1)
    tagline: str = Field(...)
    duration_estimate: str = Field(default="4–6 hours")
    skills_proven: List[str] = Field(default_factory=list)
    architecture_overview: str = Field(...)
    starter_code_files: Dict[str, str] = Field(default_factory=dict, description="Filename -> Source code content")
    demonstration_prompt: str = Field(..., description="Pitch script to include in application linking this repository")


class ProjectGenerateRequest(BaseModel):
    company: str = Field(..., min_length=1)
    role_title: str = Field(..., min_length=1)
    job_description: Optional[str] = Field(default=None)
    candidate_skills: Optional[List[str]] = Field(default=None)


class ProjectGenerateResponse(BaseModel):
    status: str = Field(default="success")
    company: str = Field(...)
    role_title: str = Field(...)
    gap_analysis: SkillGapAnalysis = Field(...)
    project_spec: MicroProjectSpec = Field(...)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
