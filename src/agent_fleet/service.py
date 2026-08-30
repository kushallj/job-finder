from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime

from .models import (
    AgentFleetConfig,
    FleetCycleResult,
)
from .orchestrator import personal_fleet_orchestrator, PersonalFleetOrchestrator

_FLEET_CONFIG: AgentFleetConfig = AgentFleetConfig()
_LAST_CYCLE_RESULT: Optional[FleetCycleResult] = None


class AgentFleetService:
    """Manages user's personal Google AI fleet configuration and cycles."""

    def __init__(self, orchestrator: Optional[PersonalFleetOrchestrator] = None):
        self.orchestrator = orchestrator or personal_fleet_orchestrator

    def get_config(self) -> AgentFleetConfig:
        return _FLEET_CONFIG

    def update_config(self, new_config: AgentFleetConfig) -> AgentFleetConfig:
        global _FLEET_CONFIG
        _FLEET_CONFIG = new_config
        _FLEET_CONFIG.last_updated = datetime.utcnow().isoformat()
        return _FLEET_CONFIG

    async def run_cycle(self, custom_config: Optional[AgentFleetConfig] = None) -> FleetCycleResult:
        global _LAST_CYCLE_RESULT
        cfg = custom_config or _FLEET_CONFIG
        result = await self.orchestrator.run_cycle(cfg)
        _LAST_CYCLE_RESULT = result
        return result

    def get_last_cycle(self) -> Optional[FleetCycleResult]:
        return _LAST_CYCLE_RESULT


agent_fleet_service = AgentFleetService()
