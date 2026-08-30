from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class XProfile(BaseModel):
    """Normalized profile schema for an X (Twitter) user."""
    model_config = ConfigDict(str_strip_whitespace=True)

    x_user_id: str = Field(..., description="Unique X user ID")
    username: str = Field(..., description="X handle (without @)")
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Bio / description")
    company: Optional[str] = Field(None, description="Inferred or stated company")
    title: Optional[str] = Field(None, description="Inferred role or occupation")
    location: Optional[str] = Field(None, description="Stated location")
    followers_count: int = Field(default=0, ge=0)
    following_count: int = Field(default=0, ge=0)
    tweet_count: int = Field(default=0, ge=0)
    verified: bool = Field(default=False)
    profile_image_url: Optional[str] = Field(None)
    x_url: Optional[str] = Field(None, description="Profile URL: https://x.com/username")
    source: str = Field(default="api", description="Source: 'api', 'csv', or 'cache'")

    def model_post_init(self, __context: Any) -> None:
        if not self.x_url and self.username:
            clean = self.username.lstrip("@")
            self.x_url = f"https://x.com/{clean}"


class XTweet(BaseModel):
    """Schema representing an X tweet / post."""
    model_config = ConfigDict(str_strip_whitespace=True)

    tweet_id: str = Field(..., description="Unique Tweet ID")
    author_id: Optional[str] = Field(None)
    author_username: Optional[str] = Field(None)
    author_name: Optional[str] = Field(None)
    text: str = Field(..., description="Tweet text")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    like_count: int = Field(default=0, ge=0)
    retweet_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)
    is_hiring_tweet: bool = Field(default=False)
    tweet_url: Optional[str] = Field(None)

    def model_post_init(self, __context: Any) -> None:
        if not self.tweet_url and self.author_username and self.tweet_id:
            clean = self.author_username.lstrip("@")
            self.tweet_url = f"https://x.com/{clean}/status/{self.tweet_id}"


class XContext(BaseModel):
    """Candidate context passed to AI message generators."""
    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(default="", description="Target company")
    role_title: str = Field(default="", description="Target position")
    job_link: Optional[str] = Field(None, description="Link to job posting")
    candidate_bio: Optional[str] = Field(None, description="Brief 1-line candidate summary")
    highlight: Optional[str] = Field(None, description="Standout technical project or metric")
    sender_name: str = Field(default="Candidate", description="Sender's name")
    target_topic: Optional[str] = Field(None, description="Specific tech topic or tweet context")


class XEngagementAction(BaseModel):
    """Record of an automated engagement action taken on X."""
    action_type: Literal["follow", "like", "repost", "reply", "dm", "quote"] = Field(...)
    target_username: str = Field(...)
    target_user_id: Optional[str] = Field(None)
    tweet_id: Optional[str] = Field(None)
    message_text: Optional[str] = Field(None)
    status: str = Field(default="success")
    intent_url: Optional[str] = Field(None, description="Direct web intent URL fallback")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
