from __future__ import annotations

from typing import Optional
from .models import MarketRadarResponse
from .engine import market_radar_engine, MarketRadarEngine


class MarketRadarService:
    """Manages global remote arbitrage calculations and GCC hiring radar."""

    def __init__(self, engine: Optional[MarketRadarEngine] = None):
        self.engine = engine or market_radar_engine

    def get_market_radar(self) -> MarketRadarResponse:
        return self.engine.get_market_radar()


market_radar_service = MarketRadarService()
