from __future__ import annotations

from typing import Optional
from .models import VoiceFeedbackResult
from .analyzer import voice_interview_analyzer, VoiceInterviewAnalyzer


class VoiceInterviewService:
    """Orchestrates real-time speech delivery analysis and mock interview coaching."""

    def __init__(self, analyzer: Optional[VoiceInterviewAnalyzer] = None):
        self.analyzer = analyzer or voice_interview_analyzer

    def analyze_spoken_response(
        self,
        transcript: str,
        duration_seconds: float,
        target_focus: str = "Distributed Systems",
    ) -> VoiceFeedbackResult:
        return self.analyzer.analyze_spoken_response(
            transcript=transcript,
            duration_seconds=duration_seconds,
            target_focus=target_focus,
        )


voice_interview_service = VoiceInterviewService()
