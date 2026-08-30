from __future__ import annotations

from typing import List, Optional
from .models import OfferPackage, CompSimulationResult
from .engine import comp_simulator_engine, CompensationSimulatorEngine


class CompSimulatorService:
    """Orchestrates compensation package simulation and competing offer comparisons."""

    def __init__(self, engine: Optional[CompensationSimulatorEngine] = None):
        self.engine = engine or comp_simulator_engine

    def simulate(self, offer: OfferPackage) -> CompSimulationResult:
        return self.engine.simulate_package(offer)

    def compare(self, offers: List[OfferPackage]) -> List[CompSimulationResult]:
        return [self.engine.simulate_package(o) for o in offers]


comp_simulator_service = CompSimulatorService()
