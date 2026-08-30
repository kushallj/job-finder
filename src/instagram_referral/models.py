from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class InstagramProfile(BaseModel):
    username: str = Field(..., min_length=1)
    name: str = Field(...)
    title: Optional[str] = Field(default=None)
    company: str = Field(...)
    bio: str = Field(default="")
    is_founder: bool = Field(default=False)
    profile_url: str = Field(...)
    threads_handle: Optional[str] = Field(default=None)
    verified: bool = Field(default=False)
    followers_count: Optional[int] = Field(default=None)


class InstagramSearchRequest(BaseModel):
    company: str = Field(..., min_length=1)
    role_keyword: Optional[str] = Field(default="Engineering")
    founder_only: bool = Field(default=False)


class InstagramSearchResponse(BaseModel):
    status: str = Field(default="success")
    company: str = Field(...)
    total_found: int = Field(...)
    profiles: List[InstagramProfile] = Field(default_factory=list)


class InstagramMessageRequest(BaseModel):
    action_type: str = Field(default="dm", description="dm, story_reply, comment")
    target_username: str = Field(...)
    company: str = Field(...)
    name: str = Field(...)
    role_title: str = Field(...)
    portfolio_link: Optional[str] = Field(default="https://kushall.in")


class InstagramMessageResponse(BaseModel):
    status: str = Field(default="success")
    target_username: str = Field(...)
    action_type: str = Field(...)
    message: str = Field(...)
    intent_url: str = Field(...)
    character_count: int = Field(...)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
