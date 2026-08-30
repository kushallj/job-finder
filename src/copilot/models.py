from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class BooleanDorkResult(BaseModel):
    title: str = Field(..., description="Short descriptive title of what this dork finds")
    query: str = Field(..., description="Exact Google Boolean Search string")
    explanation: str = Field(..., description="Why this query works and what parameters are matched")
    search_url: str = Field(..., description="Encoded https://www.google.com/search?q= URL")
    category: str = Field(default="unindexed_jds", description="unindexed_jds, hiring_managers, salary_sheets, candidate_pools, engineering_blogs, hidden_repos")


class ChatMessage(BaseModel):
    id: str = Field(...)
    role: str = Field(..., description="user, assistant, system")
    content: str = Field(...)
    dorks: List[BooleanDorkResult] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChatTurnRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = Field(default=None)
    target_company: Optional[str] = Field(default=None)
    role_title: Optional[str] = Field(default=None)


class ChatTurnResponse(BaseModel):
    status: str = Field(default="success")
    session_id: str = Field(...)
    reply: str = Field(...)
    dorks: List[BooleanDorkResult] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DorkGenerateRequest(BaseModel):
    role_title: str = Field(..., min_length=1)
    company: Optional[str] = Field(default=None)
    intent: Optional[str] = Field(default="unindexed_jds", description="unindexed_jds, hiring_managers, salary_sheets, candidate_pools, engineering_blogs, hidden_repos, all")


class DorkGenerateResponse(BaseModel):
    status: str = Field(default="success")
    total_dorks: int = Field(...)
    dorks: List[BooleanDorkResult] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
