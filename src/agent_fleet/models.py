from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AgentFleetConfig(BaseModel):
    google_gemini_api_key: Optional[str] = Field(default=None, description="User's personal Google AI Studio free-tier API key")
    autonomous_mode: bool = Field(default=False, description="Enable automatic 24/7 background agent execution")
    execution_interval_hours: int = Field(default=6, ge=1, le=48)
    enabled_agents: List[str] = Field(
        default_factory=lambda: [
            "signal_scout",
            "resume_tailor",
            "outreach_composer",
            "offer_guardian",
        ]
    )
    target_roles: List[str] = Field(default_factory=lambda: ["Senior Software Engineer", "Backend Engineer", "Full Stack Engineer"])
    target_locations: List[str] = Field(default_factory=lambda: ["Remote Worldwide", "India (Bangalore / NCR / Hyderabad)", "US / EU Remote"])
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FleetAgentRunResult(BaseModel):
    agent_name: str = Field(...)
    display_title: str = Field(...)
    avatar: str = Field(default="🤖")
    status: str = Field(default="success")
    summary: str = Field(...)
    actions_taken: int = Field(default=0)
    deliverables: List[Dict[str, Any]] = Field(default_factory=list)
    duration_seconds: float = Field(default=0.5)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FleetCycleResult(BaseModel):
    fleet_id: str = Field(...)
    cycle_id: str = Field(...)
    is_active: bool = Field(default=True)
    has_api_key: bool = Field(...)
    total_actions_executed: int = Field(...)
    agent_runs: List[FleetAgentRunResult] = Field(default_factory=list)
    execution_time_seconds: float = Field(...)
    completed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
