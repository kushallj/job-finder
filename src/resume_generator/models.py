from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ResumeGenerateRequest(BaseModel):
    candidate_name: Optional[str] = Field(default="Candidate", max_length=255)
    candidate_email: Optional[str] = Field(default="candidate@example.com", max_length=255)
    candidate_phone: Optional[str] = Field(default="+1 (555) 019-2834", max_length=50)
    candidate_location: Optional[str] = Field(default="San Francisco, CA / Remote", max_length=255)
    candidate_linkedin: Optional[str] = Field(default="linkedin.com/in/candidate", max_length=255)
    candidate_github: Optional[str] = Field(default="github.com/candidate", max_length=255)
    role_title: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    job_description: Optional[str] = Field(default=None)
    custom_bullets: Optional[List[str]] = Field(default=None)


class CoverLetterGenerateRequest(BaseModel):
    candidate_name: Optional[str] = Field(default="Candidate")
    candidate_email: Optional[str] = Field(default="candidate@example.com")
    company: str = Field(..., min_length=1)
    role_title: str = Field(..., min_length=1)
    hiring_manager_name: Optional[str] = Field(default="Engineering Leadership Team")
    job_description: Optional[str] = Field(default=None)


class ResumeDocumentResponse(BaseModel):
    status: str = Field(default="success")
    document_type: str = Field(..., description="ats_resume, cover_letter")
    company: str = Field(...)
    role_title: str = Field(...)
    ats_match_score: float = Field(...)
    html_content: str = Field(..., description="Clean printable ATS HTML")
    plain_text: str = Field(...)
    suggested_keywords: List[str] = Field(default_factory=list)
    timestamp: str
