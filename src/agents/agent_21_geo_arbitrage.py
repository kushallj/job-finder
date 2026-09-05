"""
agent_21_geo_arbitrage.py — Agent 21: Global Geo-Arbitrage & Cross-Border Engine.

Unlocks high-income relocation & remote tech opportunities across Japan, China/Singapore, and Europe,
with tax-adjusted net take-home and Purchasing Power Parity (PPP) savings calculators.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent, AgentResult, AgentContext
from src.services.geo_arbitrage_service import GeoArbitrageService

logger = logging.getLogger("nexus.agents.geo_arbitrage")


class GeoArbitrageAgent(BaseAgent):
    """Analyzes cross-border relocation compensation, tax arbitrage, and fast-track tech visas."""

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(context=context)
        self.service = GeoArbitrageService()

    def run(
        self,
        gross_annual_salary: float = 16000000.0,
        market_id: str = "japan_tokyo",
        current_inr_ctc_lpa: float = 35.0,
        **kwargs: Any,
    ) -> AgentResult:
        """Runs PPP calculation and visa assessment."""
        try:
            result = self.service.calculate_net_ppp(
                gross_annual_salary=gross_annual_salary,
                market_id=market_id,
                current_inr_ctc_lpa=current_inr_ctc_lpa,
            )
            fin = result["financials"]
            city = result["market"]["city"]
            return AgentResult(
                agent="geo_arbitrage",
                ok=True,
                data=result,
                summary=f"Geo-Arbitrage Analysis ({city}): Net Savings ₹{fin['annual_savings_inr_lakhs']}L/yr ({fin['savings_expansion_multiplier']}x India baseline), PR path: {result['visa_dossier']['permanent_residence_timeline']}.",
            )
        except Exception as exc:
            logger.error(f"Geo-arbitrage execution failed: {exc}")
            return AgentResult(
                agent="geo_arbitrage",
                ok=False,
                error=str(exc),
                data={},
            )
