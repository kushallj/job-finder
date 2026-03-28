"""
src/feedback — Self-Improving Feedback Loop & Analytics (Task 7)

Closes the loop between outreach outcomes and pipeline behavior:

  Collect  →  Mine  →  Learn  →  Adapt  →  Digest

Components:
  MetricsCollector   — reads OutreachRecord / Application from DB, computes funnel stats
  PatternMiner       — DP-based pattern mining: which feature combos predict replies/interviews
  AdaptiveOptimizer  — writes learned weights back to pipeline (hooks, send times, templates)
  DigestGenerator    — weekly markdown + structured report
  FeedbackLoop       — nightly orchestrator; exposes get_recommendations() to other modules
"""

from .models import (
    OutreachMetrics,
    SuccessPattern,
    Recommendation,
    RecommendationType,
    LearningSnapshot,
)
from .metrics_collector import MetricsCollector
from .pattern_miner import PatternMiner
from .adaptive_optimizer import AdaptiveOptimizer
from .digest_generator import DigestGenerator
from .feedback_loop import FeedbackLoop, get_loop

__all__ = [
    "OutreachMetrics",
    "SuccessPattern",
    "Recommendation",
    "RecommendationType",
    "LearningSnapshot",
    "MetricsCollector",
    "PatternMiner",
    "AdaptiveOptimizer",
    "DigestGenerator",
    "FeedbackLoop",
    "get_loop",
]
