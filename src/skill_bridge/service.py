from __future__ import annotations

from typing import Dict, Any, Optional
from .models import ProjectGenerateRequest, ProjectGenerateResponse
from .engine import skill_bridge_engine, SkillBridgeEngine


class SkillBridgeService:
    """Manages skill gap evaluation and Proof-of-Work project generation."""

    def __init__(self, engine: Optional[SkillBridgeEngine] = None):
        self.engine = engine or skill_bridge_engine

    def generate_project(self, req: ProjectGenerateRequest) -> ProjectGenerateResponse:
        return self.engine.generate_project(req)


skill_bridge_service = SkillBridgeService()
