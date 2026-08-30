from __future__ import annotations

from typing import Optional
from .models import DeliverabilityAnalysisResult
from .analyzer import deliverability_analyzer, DeliverabilityAnalyzer


class DeliverabilityService:
    """Orchestrates spam scoring, readability assessment, and inbox placement optimization."""

    def __init__(self, analyzer: Optional[DeliverabilityAnalyzer] = None):
        self.analyzer = analyzer or deliverability_analyzer

    def analyze(self, subject: str, body: str) -> DeliverabilityAnalysisResult:
        return self.analyzer.analyze_draft(subject=subject, body=body)


deliverability_service = DeliverabilityService()
