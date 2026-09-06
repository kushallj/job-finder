"""
models.py — Data models for the Godfather Telegram Bot.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InlineButton(BaseModel):
    text: str
    callback_data: Optional[str] = None
    url: Optional[str] = None


class BotMessageResponse(BaseModel):
    text: str
    parse_mode: str = "HTML"
    reply_markup: Optional[Dict[str, Any]] = None
    action_type: str = "text"
    agent_invoked: Optional[str] = None


class UserInteractionRequest(BaseModel):
    message: str
    user_id: Optional[str] = "web_user"
    chat_id: Optional[str] = "web_chat"
    user_name: Optional[str] = "Sovereign Engineer"


class BotStatusResponse(BaseModel):
    status: str
    is_running: bool
    is_configured: bool
    bot_username: Optional[str] = "GodfatherCopilotBot"
    uptime_seconds: float = 0.0
    total_commands_executed: int = 0
    autopilot_enabled: bool = True
    active_monitors_count: int = 13
    last_active_timestamp: Optional[str] = None
