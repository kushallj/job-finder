from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class NotificationConfig(BaseModel):
    telegram_bot_token: Optional[str] = Field(None, description="Telegram Bot Token from @BotFather")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram Chat/Channel ID")
    discord_webhook_url: Optional[str] = Field(None, description="Discord Incoming Webhook URL")
    slack_webhook_url: Optional[str] = Field(None, description="Slack Incoming Webhook URL")
    min_fit_score: float = Field(default=65.0, ge=0.0, le=100.0)
    notify_on_tier1_only: bool = Field(default=False)
    enabled: bool = Field(default=True)


class AlertPayload(BaseModel):
    job_id: Optional[int] = Field(None)
    title: str = Field(..., min_length=1)
    company: str = Field(..., min_length=1)
    location: Optional[str] = Field(default="Remote")
    fit_score: float = Field(..., ge=0.0, le=100.0)
    job_url: str = Field(..., min_length=1)
    top_contact_name: Optional[str] = Field(None)
    top_contact_email: Optional[str] = Field(None)
    summary_hook: Optional[str] = Field(None)


class ChannelDispatchResult(BaseModel):
    channel: str = Field(..., description="telegram, discord, slack, generic")
    status: str = Field(..., description="success, failed, disabled, simulated")
    detail: str = Field(...)


class NotificationDispatchResponse(BaseModel):
    status: str = Field(default="success")
    dispatched_count: int = Field(...)
    results: List[ChannelDispatchResult] = Field(default_factory=list)
    timestamp: str
