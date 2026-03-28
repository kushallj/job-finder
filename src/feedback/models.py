"""
models.py — Dataclasses for the Feedback & Learning system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class ReplyStats:
    """Aggregated stats for a specific segment (hook type, send hour, etc.)."""
    sent:        int   = 0
    replied:     int   = 0
    positive:    int   = 0
    bounced:     int   = 0
    interviews:  int   = 0

    @property
    def reply_rate(self) -> float:
        return self.replied / self.sent if self.sent > 0 else 0.0

    @property
    def positive_rate(self) -> float:
        return self.positive / self.sent if self.sent > 0 else 0.0

    @property
    def interview_rate(self) -> float:
        return self.interviews / self.sent if self.sent > 0 else 0.0

    def __add__(self, other: "ReplyStats") -> "ReplyStats":
        return ReplyStats(
            sent       = self.sent + other.sent,
            replied    = self.replied + other.replied,
            positive   = self.positive + other.positive,
            bounced    = self.bounced + other.bounced,
            interviews = self.interviews + other.interviews,
        )


@dataclass
class OutreachMetrics:
    """Full funnel metrics for a time window."""
    window_days:        int
    total_sent:         int                          = 0
    total_delivered:    int                          = 0
    total_bounced:      int                          = 0
    total_replied:      int                          = 0
    total_positive:     int                          = 0
    total_interviews:   int                          = 0
    total_offers:       int                          = 0

    # Segment breakdowns
    by_hook_type:       Dict[str, ReplyStats]        = field(default_factory=dict)
    by_send_hour:       Dict[int, ReplyStats]         = field(default_factory=dict)
    by_company_domain:  Dict[str, ReplyStats]         = field(default_factory=dict)
    by_template:        Dict[str, ReplyStats]         = field(default_factory=dict)
    by_ab_variant:      Dict[int, ReplyStats]         = field(default_factory=dict)

    top_subjects:       List[str]                    = field(default_factory=list)
    top_hooks:          List[str]                    = field(default_factory=list)

    @property
    def reply_rate(self) -> float:
        return self.total_replied / max(self.total_sent, 1)

    @property
    def positive_rate(self) -> float:
        return self.total_positive / max(self.total_sent, 1)

    @property
    def interview_rate(self) -> float:
        return self.total_interviews / max(self.total_sent, 1)

    @property
    def delivery_rate(self) -> float:
        return self.total_delivered / max(self.total_sent, 1)

    def funnel_str(self) -> str:
        return (
            f"Sent {self.total_sent} → "
            f"Replied {self.total_replied} ({self.reply_rate:.0%}) → "
            f"Positive {self.total_positive} ({self.positive_rate:.0%}) → "
            f"Interviews {self.total_interviews} ({self.interview_rate:.0%})"
        )


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

@dataclass
class SuccessPattern:
    """
    A mined pattern that correlates with higher reply/interview rates.

    Example:
        feature_key   = "hook_type"
        feature_val   = "contact_resonance"
        reply_rate    = 0.42
        baseline_rate = 0.12
        lift          = 3.5   (3.5x better than average)
        sample_size   = 47
        confidence    = 0.97
    """
    feature_key:   str
    feature_val:   str
    send_count:    int
    reply_count:   int
    interview_count: int
    baseline_rate: float   = 0.0    # overall average reply rate
    confidence:    float   = 0.0    # statistical confidence (0-1)

    @property
    def reply_rate(self) -> float:
        return self.reply_count / max(self.send_count, 1)

    @property
    def lift(self) -> float:
        """How much better than baseline (1.0 = same, 2.0 = 2x better)."""
        if self.baseline_rate <= 0:
            return 1.0
        return self.reply_rate / self.baseline_rate

    def is_significant(self) -> bool:
        """Statistically significant: p < 0.05, min 20 samples."""
        return self.confidence >= 0.95 and self.send_count >= 20

    def __str__(self) -> str:
        sig = "✓" if self.is_significant() else "~"
        return (
            f"{sig} {self.feature_key}={self.feature_val}: "
            f"{self.reply_rate:.0%} reply rate "
            f"({self.lift:.1f}x baseline, n={self.send_count})"
        )


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class RecommendationType(str, Enum):
    INCREASE_HOOK_WEIGHT  = "increase_hook_weight"
    DECREASE_HOOK_WEIGHT  = "decrease_hook_weight"
    ADJUST_SEND_TIME      = "adjust_send_time"
    TARGET_COMPANY_TYPE   = "target_company_type"
    AVOID_COMPANY_TYPE    = "avoid_company_type"
    PROMOTE_AB_VARIANT    = "promote_ab_variant"
    IMPROVE_TEMPLATE      = "improve_template"
    INCREASE_FOLLOWUP     = "increase_followup"


@dataclass
class Recommendation:
    type:             RecommendationType
    action:           str           # human-readable action
    evidence:         str           # the data point driving this
    impact_estimate:  float         # expected reply rate improvement (percentage points)
    pattern:          Optional[SuccessPattern] = None

    def __str__(self) -> str:
        return f"[{self.type.value}] {self.action} (est. +{self.impact_estimate:.1f}pp)"


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

@dataclass
class LearningSnapshot:
    """A complete weekly learning report."""
    snapshot_date:   str
    metrics:         OutreachMetrics
    patterns:        List[SuccessPattern]
    recommendations: List[Recommendation]
    digest_markdown: str             = ""
    digest_html:     str             = ""
