"""
src/outreach — Multi-channel outreach orchestration package.

Components:
    smart_timer         — Timezone-aware optimal send window calculator
    reply_detector      — IMAP-based reply detection (runs in ThreadPoolExecutor)
    followup_scheduler  — Async background scheduler for Day-5/12/21 sequences
    sentiment           — Two-tier reply sentiment classifier
    ab_test             — Subject line A/B testing with chi-square significance
    domain_rate_limiter — Per-domain + global daily rate limiting
"""

from .smart_timer import SmartSendTimer
from .reply_detector import ReplyDetector
from .followup_scheduler import FollowUpScheduler
from .sentiment import SentimentClassifier, SentimentLabel
from .ab_test import ABTestManager
from .domain_rate_limiter import DomainRateLimiter

__all__ = [
    "SmartSendTimer",
    "ReplyDetector",
    "FollowUpScheduler",
    "SentimentClassifier",
    "SentimentLabel",
    "ABTestManager",
    "DomainRateLimiter",
]
