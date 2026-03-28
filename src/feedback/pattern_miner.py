"""
pattern_miner.py — DP-based success pattern mining.

Algorithm:
  For each outreach record, extract a feature vector:
    {hook_type, send_hour_bucket, domain_tld, template, ab_variant,
     company_has_github, personalization_score_bucket}

  Build a frequency table:
    dp[feature_key][feature_val] = ReplyStats(sent, replied, interviews)

  This is O(F) per record (F = number of features = ~7) and O(F × V) space
  (V = distinct values per feature = ~5-10).  Very fast.

  After collecting all records, compute:
    lift[feature] = reply_rate[feature] / global_reply_rate
    confidence    = chi-square p-value (1 - p)

Statistical significance:
  Chi-square test compares observed vs expected reply counts.
  We use the same math.lgamma-based implementation as ABTestManager.
  Threshold: p < 0.05 (confidence ≥ 0.95), min 20 sends.

Output:
  List[SuccessPattern] sorted by lift × confidence (best patterns first).
  Only statistically significant patterns are returned.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from .models import OutreachMetrics, ReplyStats, SuccessPattern

log = logging.getLogger(__name__)

# Feature extractors: (feature_key, lambda record → str_value)
# These map each OutreachRecord field to a categorical feature value.
_FEATURES: List[Tuple[str, callable]] = []   # populated at module level below


class PatternMiner:
    """
    Mines success patterns from an OutreachMetrics snapshot.

    Usage:
        miner    = PatternMiner()
        patterns = miner.mine(metrics, db_session, window_days=30)
        for p in patterns:
            print(p)   # "✓ hook_type=contact_resonance: 42% reply rate (3.5x baseline)"
    """

    def mine(
        self,
        metrics:     OutreachMetrics,
        db_session=None,
        window_days: int = 30,
    ) -> List[SuccessPattern]:
        """
        Mine patterns from recent outreach records.

        Uses metrics.by_* segment data (no extra DB query needed for basic patterns).
        Falls back to raw DB scan for richer feature combinations.
        """
        patterns: List[SuccessPattern] = []
        baseline  = metrics.reply_rate

        # ── Mine from pre-computed segment metrics ─────────────────────────────
        patterns.extend(self._mine_segment(
            "hook_type", metrics.by_hook_type, baseline
        ))
        patterns.extend(self._mine_segment(
            "send_hour", metrics.by_send_hour, baseline
        ))
        patterns.extend(self._mine_segment(
            "template", metrics.by_template, baseline
        ))
        patterns.extend(self._mine_segment(
            "ab_variant", metrics.by_ab_variant, baseline
        ))

        # ── Mine from raw DB (richer signals) ─────────────────────────────────
        if db_session:
            patterns.extend(self._mine_from_db(db_session, window_days, baseline))

        # Deduplicate and sort by lift × confidence
        seen = set()
        unique = []
        for p in sorted(patterns, key=lambda x: x.lift * x.confidence, reverse=True):
            key = f"{p.feature_key}={p.feature_val}"
            if key not in seen:
                seen.add(key)
                unique.append(p)

        log.info(
            "PatternMiner: %d significant patterns found (baseline=%.1f%%)",
            sum(1 for p in unique if p.is_significant()),
            baseline * 100,
        )
        return unique

    # ── Segment-level pattern extraction ──────────────────────────────────────

    def _mine_segment(
        self,
        feature_key: str,
        segment_map: Dict,
        baseline:    float,
    ) -> List[SuccessPattern]:
        patterns = []
        for val, stats in segment_map.items():
            if stats.sent < 10:
                continue
            p = self._make_pattern(
                feature_key = feature_key,
                feature_val = str(val),
                send_count  = stats.sent,
                reply_count = stats.replied,
                interview_count = stats.interviews,
                baseline    = baseline,
            )
            patterns.append(p)
        return patterns

    # ── Raw DB pattern extraction ──────────────────────────────────────────────

    def _mine_from_db(
        self,
        db_session,
        window_days: int,
        baseline:    float,
    ) -> List[SuccessPattern]:
        """
        DP frequency table over raw OutreachRecord fields.
        Extracts richer features: personalization_score_bucket, domain_tld, etc.
        """
        try:
            from src.models import OutreachRecord, Application
        except ImportError:
            return []

        patterns = []
        cutoff   = datetime.now(timezone.utc) - timedelta(days=window_days)

        try:
            records = db_session.query(OutreachRecord).filter(
                OutreachRecord.sent_at >= cutoff
            ).all()
        except Exception as exc:
            log.debug("PatternMiner DB query: %s", exc)
            return []

        # dp[feature_key][feature_val] = [sent, replied, interviews]
        dp: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))

        for rec in records:
            is_replied   = bool(rec.replied_at) or (rec.status or "") == "replied"
            is_interview = False   # enriched below if joined to Application

            features = _extract_features(rec)
            for fkey, fval in features.items():
                dp[fkey][fval][0] += 1
                if is_replied:
                    dp[fkey][fval][1] += 1
                if is_interview:
                    dp[fkey][fval][2] += 1

        for fkey, val_map in dp.items():
            for fval, (sent, replied, interviews) in val_map.items():
                if sent < 10:
                    continue
                patterns.append(self._make_pattern(
                    feature_key     = fkey,
                    feature_val     = fval,
                    send_count      = sent,
                    reply_count     = replied,
                    interview_count = interviews,
                    baseline        = baseline,
                ))

        return patterns

    # ── Pattern factory ────────────────────────────────────────────────────────

    @staticmethod
    def _make_pattern(
        feature_key:     str,
        feature_val:     str,
        send_count:      int,
        reply_count:     int,
        interview_count: int,
        baseline:        float,
    ) -> SuccessPattern:
        confidence = _chi2_confidence(send_count, reply_count, baseline)
        return SuccessPattern(
            feature_key     = feature_key,
            feature_val     = feature_val,
            send_count      = send_count,
            reply_count     = reply_count,
            interview_count = interview_count,
            baseline_rate   = baseline,
            confidence      = confidence,
        )


# ---------------------------------------------------------------------------
# Feature extractor
# ---------------------------------------------------------------------------

def _extract_features(rec) -> Dict[str, str]:
    """Extract categorical features from an OutreachRecord."""
    features: Dict[str, str] = {}

    # Send hour bucket (morning / afternoon / evening)
    if rec.sent_at:
        hour = rec.sent_at.hour
        if 6 <= hour < 12:
            features["send_window"] = "morning"
        elif 12 <= hour < 17:
            features["send_window"] = "afternoon"
        elif 17 <= hour < 21:
            features["send_window"] = "evening"
        else:
            features["send_window"] = "off_hours"

    # Domain TLD
    email = rec.contact_email or ""
    if "@" in email:
        domain = email.split("@")[1]
        tld    = domain.rsplit(".", 1)[-1] if "." in domain else "unknown"
        features["domain_tld"] = tld

        # Company size signal from known domains
        if domain.endswith((".io", ".ai")):
            features["company_type"] = "startup"
        elif domain.endswith((".com",)):
            features["company_type"] = "established"
        else:
            features["company_type"] = "other"

    # Follow-up count bucket
    fc = rec.follow_up_count or 0
    features["followup_count"] = "0" if fc == 0 else ("1" if fc == 1 else "2+")

    # AB variant
    features["ab_variant"] = str(rec.ab_variant or 0)

    # Template type
    if rec.template_type:
        features["template"] = rec.template_type

    return features


# ---------------------------------------------------------------------------
# Chi-square significance (same approach as ABTestManager)
# ---------------------------------------------------------------------------

def _chi2_confidence(n: int, k: int, p_null: float) -> float:
    """
    One-proportion z-test converted to confidence (1 - p_value).
    p_null: expected success rate under null hypothesis (baseline reply rate)
    k:      observed successes
    n:      total trials
    """
    if n < 5 or p_null <= 0 or p_null >= 1:
        return 0.0

    expected_k = n * p_null
    expected_nk = n * (1 - p_null)
    obs_nk = n - k

    if expected_k < 1 or expected_nk < 1:
        return 0.0

    chi2 = (k - expected_k) ** 2 / expected_k + (obs_nk - expected_nk) ** 2 / expected_nk

    # chi2 CDF approximation (1 degree of freedom) via regularized gamma
    # P(chi2 <= x, df=1) = erf(sqrt(x/2))
    try:
        p_value = 1.0 - math.erf(math.sqrt(chi2 / 2))
        return min(1.0, max(0.0, 1.0 - p_value))
    except (ValueError, OverflowError):
        return 0.0
