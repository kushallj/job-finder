"""
agent_16_interviewer_profiler.py — Agent 16: Interviewer Cognitive & Bias Profiler.

Profiles scheduled interviewers, extracting architectural stances, open-source footprints,
green lights, red lines, and tailored conversation openers.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent, AgentResult, AgentContext
from src.services.interviewer_profiler import InterviewerProfilerService

logger = logging.getLogger("nexus.agents.interviewer_profiler")


class InterviewerProfilerAgent(BaseAgent):
    """Profiles interviewers to provide candidates with psychological and technical advantages."""

    def __init__(self, context: Optional[AgentContext] = None):
        super().__init__(context=context)
        self.service = InterviewerProfilerService()

    def run(
        self,
        interviewer_name: str = "Engineering Leader",
        company_name: str = "Target Tech Company",
        role: Optional[str] = None,
        github_handle: Optional[str] = None,
        **kwargs: Any
    ) -> AgentResult:
        """Runs the deep cognitive profiling analysis."""
        try:
            dossier = self.service.profile_interviewer(
                name=interviewer_name,
                company=company_name,
                role=role,
                github_handle=github_handle,
            )
            return AgentResult(
                agent="interviewer_profiler",
                ok=True,
                data=dossier,
                summary=f"Generated cognitive profile for {interviewer_name} at {company_name} ({dossier['cognitive_archetype']}).",
            )
        except Exception as exc:
            logger.error(f"Interviewer profiling failed: {exc}")
            return AgentResult(
                agent="interviewer_profiler",
                ok=False,
                error=str(exc),
                data={},
            )
