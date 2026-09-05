"""
agent_24_system_design_whiteboard.py — Agent 24: System Design Whiteboard Co-Pilot.

Generates real-time back-of-the-envelope capacity numbers, Mermaid architecture diagrams,
and defensive failure-mode matrices during System Design interview rounds.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent, AgentResult, AgentContext
from src.services.system_design_whiteboard import SystemDesignWhiteboardService

logger = logging.getLogger("nexus.agents.system_design_whiteboard")


class SystemDesignWhiteboardAgent(BaseAgent):
    """Synthesizes capacity math, architecture diagrams, and failure matrices."""

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(context=context)
        self.service = SystemDesignWhiteboardService()

    def run(
        self,
        archetype_id: str = "realtime_trading_engine",
        dau: int = 10000000,
        actions_per_day: int = 20,
        payload_bytes: int = 1024,
        **kwargs: Any,
    ) -> AgentResult:
        """Runs the system design capacity calculation and diagram synthesis."""
        try:
            result = self.service.estimate_and_diagram(
                archetype_id=archetype_id,
                dau=dau,
                actions_per_day=actions_per_day,
                payload_bytes=payload_bytes,
            )
            qps = result["capacity_estimates"]["peak_qps"]
            storage_tb = result["capacity_estimates"]["annual_storage_tb"]
            return AgentResult(
                agent="system_design_whiteboard",
                ok=True,
                data=result,
                summary=f"System Design Blueprint for '{result['title']}': Peak QPS {qps:,.0f}, Annual Storage {storage_tb} TB, P99 Target {result['p99_sla_target']}.",
            )
        except Exception as exc:
            logger.error(f"System design whiteboard execution failed: {exc}")
            return AgentResult(
                agent="system_design_whiteboard",
                ok=False,
                error=str(exc),
                data={},
            )
