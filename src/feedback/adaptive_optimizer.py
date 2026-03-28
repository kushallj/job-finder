"""
adaptive_optimizer.py — Writes learned weights back to the pipeline.

What gets adapted:
  1. Hook weights    → HookGenerator uses these to rank hooks
                       (stored in data/learning.db :: hook_weights table)
  2. Send time prefs → SmartSendTimer uses learned best hours per TLD
                       (stored in data/learning.db :: send_time_prefs table)
  3. A/B variants    → ABTestManager already has epsilon-greedy; we feed
                       it significant winners to lock in
  4. Template scores → Which templates are underperforming (for digest)

Adaptation rules:
  - Significant pattern (confidence ≥ 0.95, n ≥ 20) with lift > 1.5
    → increase weight proportional to lift
  - Significant pattern with lift < 0.5
    → decrease weight (floor at 0.1 to never fully disable)
  - New patterns with n < 20 accumulate data but don't change weights yet
  - Weights are bounded: [0.1, 5.0]  (prevents runaway amplification)

Weight update formula:
  new_weight = clip(old_weight × (0.5 + 0.5 × lift), 0.1, 5.0)

This exponential moving average smooths out noise:
  lift 2.0 → weight × 1.5 (moderate increase)
  lift 0.5 → weight × 0.75 (moderate decrease)
  lift 4.0 → weight × 2.5 (strong signal)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

from .models import OutreachMetrics, Recommendation, RecommendationType, SuccessPattern

log = logging.getLogger(__name__)

_LEARNING_DB   = Path("data/learning.db")
_WEIGHT_MIN    = 0.10
_WEIGHT_MAX    = 5.00
_LIFT_THRESHOLD = 1.5   # minimum lift to increase weight
_LIFT_FLOOR     = 0.5   # below this → decrease weight


class AdaptiveOptimizer:
    """
    Reads patterns + metrics, writes updated weights to SQLite.
    Other pipeline components read weights at startup (or per-call).

    Usage:
        optimizer = AdaptiveOptimizer()
        recommendations = optimizer.adapt(metrics, patterns)
    """

    def __init__(self):
        self._init_db()

    # ── Public API ─────────────────────────────────────────────────────────────

    def adapt(
        self,
        metrics:  OutreachMetrics,
        patterns: List[SuccessPattern],
    ) -> List[Recommendation]:
        """
        Compute updated weights from patterns, persist to DB,
        and return human-readable recommendations.
        """
        recommendations: List[Recommendation] = []

        sig_patterns = [p for p in patterns if p.is_significant()]

        # ── 1. Hook weights ───────────────────────────────────────────────────
        recommendations.extend(self._adapt_hook_weights(sig_patterns, metrics))

        # ── 2. Send time preferences ──────────────────────────────────────────
        recommendations.extend(self._adapt_send_times(metrics))

        # ── 3. A/B variant promotion ──────────────────────────────────────────
        recommendations.extend(self._adapt_ab_variants(metrics))

        # ── 4. Template recommendations ───────────────────────────────────────
        recommendations.extend(self._adapt_templates(metrics))

        # Sort by impact estimate
        recommendations.sort(key=lambda r: r.impact_estimate, reverse=True)

        log.info(
            "AdaptiveOptimizer: %d recommendations (top: %s)",
            len(recommendations),
            str(recommendations[0]) if recommendations else "none",
        )
        return recommendations

    # ── Hook weight adaptation ─────────────────────────────────────────────────

    def _adapt_hook_weights(
        self,
        patterns:  List[SuccessPattern],
        metrics:   OutreachMetrics,
    ) -> List[Recommendation]:
        recs = []
        current_weights = self._load_hook_weights()
        new_weights     = dict(current_weights)

        for p in patterns:
            if p.feature_key != "hook_type":
                continue

            hook_type   = p.feature_val
            old_weight  = current_weights.get(hook_type, 1.0)
            # Bounded exponential update
            new_weight  = old_weight * (0.5 + 0.5 * p.lift)
            new_weight  = max(_WEIGHT_MIN, min(_WEIGHT_MAX, new_weight))
            new_weights[hook_type] = new_weight

            if p.lift >= _LIFT_THRESHOLD:
                recs.append(Recommendation(
                    type            = RecommendationType.INCREASE_HOOK_WEIGHT,
                    action          = (
                        f"Increase '{hook_type}' hook weight "
                        f"{old_weight:.1f}x → {new_weight:.1f}x "
                        f"(reply rate {p.reply_rate:.0%}, {p.lift:.1f}x baseline)"
                    ),
                    evidence        = str(p),
                    impact_estimate = (p.reply_rate - p.baseline_rate) * 100,
                    pattern         = p,
                ))
            elif p.lift < _LIFT_FLOOR:
                recs.append(Recommendation(
                    type            = RecommendationType.DECREASE_HOOK_WEIGHT,
                    action          = (
                        f"Reduce '{hook_type}' hook usage "
                        f"(only {p.reply_rate:.0%} reply rate, {p.lift:.1f}x baseline)"
                    ),
                    evidence        = str(p),
                    impact_estimate = (p.baseline_rate - p.reply_rate) * 100,
                    pattern         = p,
                ))

        self._save_hook_weights(new_weights)
        return recs

    # ── Send time adaptation ───────────────────────────────────────────────────

    def _adapt_send_times(self, metrics: OutreachMetrics) -> List[Recommendation]:
        recs = []
        if not metrics.by_send_hour:
            return recs

        # Find best and worst hours
        sorted_hours = sorted(
            metrics.by_send_hour.items(),
            key=lambda kv: kv[1].reply_rate,
            reverse=True,
        )

        if not sorted_hours:
            return recs

        best_hour, best_stats = sorted_hours[0]
        worst_hour, worst_stats = sorted_hours[-1]

        # Save preferences
        prefs = {str(h): stats.reply_rate for h, stats in sorted_hours if stats.sent >= 5}
        self._save_send_time_prefs(prefs)

        if best_stats.reply_rate > metrics.reply_rate * 1.5 and best_stats.sent >= 10:
            recs.append(Recommendation(
                type            = RecommendationType.ADJUST_SEND_TIME,
                action          = (
                    f"Prioritize sending at hour {best_hour:02d}:00 "
                    f"({best_stats.reply_rate:.0%} reply rate vs "
                    f"{metrics.reply_rate:.0%} overall)"
                ),
                evidence        = f"send_hour={best_hour} reply_rate={best_stats.reply_rate:.2%}",
                impact_estimate = (best_stats.reply_rate - metrics.reply_rate) * 100,
            ))

        return recs

    # ── A/B variant adaptation ─────────────────────────────────────────────────

    def _adapt_ab_variants(self, metrics: OutreachMetrics) -> List[Recommendation]:
        recs = []
        if not metrics.by_ab_variant:
            return recs

        sorted_variants = sorted(
            metrics.by_ab_variant.items(),
            key=lambda kv: kv[1].reply_rate,
            reverse=True,
        )

        best_v, best_stats = sorted_variants[0]
        if (best_stats.reply_rate > metrics.reply_rate * 1.3
                and best_stats.sent >= 15
                and len(sorted_variants) > 1):
            recs.append(Recommendation(
                type            = RecommendationType.PROMOTE_AB_VARIANT,
                action          = (
                    f"Promote A/B variant {best_v} as primary "
                    f"({best_stats.reply_rate:.0%} reply rate, "
                    f"{best_stats.sent} sends)"
                ),
                evidence        = f"ab_variant={best_v} is {best_stats.reply_rate / max(metrics.reply_rate, 0.001):.1f}x better",
                impact_estimate = (best_stats.reply_rate - metrics.reply_rate) * 100,
            ))

        return recs

    # ── Template adaptation ────────────────────────────────────────────────────

    def _adapt_templates(self, metrics: OutreachMetrics) -> List[Recommendation]:
        recs = []
        if not metrics.by_template:
            return recs

        for template, stats in metrics.by_template.items():
            if stats.sent < 10:
                continue
            if stats.reply_rate < metrics.reply_rate * 0.5:
                recs.append(Recommendation(
                    type            = RecommendationType.IMPROVE_TEMPLATE,
                    action          = (
                        f"Template '{template}' underperforming: "
                        f"{stats.reply_rate:.0%} reply rate "
                        f"(vs {metrics.reply_rate:.0%} overall). "
                        f"Consider rewriting subject/hook."
                    ),
                    evidence        = f"template={template} n={stats.sent}",
                    impact_estimate = (metrics.reply_rate - stats.reply_rate) * 100,
                ))

        return recs

    # ── Public weight getters (used by HookGenerator, SmartSendTimer) ──────────

    def get_hook_weights(self) -> Dict[str, float]:
        """Returns hook type → weight multiplier. Called by HookGenerator."""
        return self._load_hook_weights()

    def get_best_send_hours(self) -> Dict[str, float]:
        """Returns hour → reply_rate. Called by SmartSendTimer as override."""
        return self._load_send_time_prefs()

    # ── SQLite persistence ─────────────────────────────────────────────────────

    def _init_db(self) -> None:
        _LEARNING_DB.parent.mkdir(exist_ok=True)
        with sqlite3.connect(_LEARNING_DB) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS hook_weights (
                    hook_type    TEXT PRIMARY KEY,
                    weight       REAL DEFAULT 1.0,
                    sample_size  INTEGER DEFAULT 0,
                    updated_at   INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS send_time_prefs (
                    hour         TEXT PRIMARY KEY,
                    reply_rate   REAL DEFAULT 0.0,
                    updated_at   INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS recommendations (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    type         TEXT NOT NULL,
                    action       TEXT NOT NULL,
                    evidence     TEXT,
                    impact       REAL,
                    created_at   INTEGER NOT NULL
                );
            """)

    def _load_hook_weights(self) -> Dict[str, float]:
        try:
            with sqlite3.connect(_LEARNING_DB) as conn:
                rows = conn.execute("SELECT hook_type, weight FROM hook_weights").fetchall()
                return {r[0]: r[1] for r in rows}
        except Exception:
            return {}

    def _save_hook_weights(self, weights: Dict[str, float]) -> None:
        try:
            now = int(time.time())
            with sqlite3.connect(_LEARNING_DB) as conn:
                for hook_type, weight in weights.items():
                    conn.execute(
                        """INSERT OR REPLACE INTO hook_weights (hook_type, weight, updated_at)
                           VALUES (?, ?, ?)""",
                        (hook_type, weight, now)
                    )
        except Exception as exc:
            log.debug("Save hook weights: %s", exc)

    def _load_send_time_prefs(self) -> Dict[str, float]:
        try:
            with sqlite3.connect(_LEARNING_DB) as conn:
                rows = conn.execute("SELECT hour, reply_rate FROM send_time_prefs").fetchall()
                return {r[0]: r[1] for r in rows}
        except Exception:
            return {}

    def _save_send_time_prefs(self, prefs: Dict[str, float]) -> None:
        try:
            now = int(time.time())
            with sqlite3.connect(_LEARNING_DB) as conn:
                for hour, rate in prefs.items():
                    conn.execute(
                        """INSERT OR REPLACE INTO send_time_prefs (hour, reply_rate, updated_at)
                           VALUES (?, ?, ?)""",
                        (str(hour), rate, now)
                    )
        except Exception as exc:
            log.debug("Save send time prefs: %s", exc)

    def persist_recommendations(self, recs: List[Recommendation]) -> None:
        """Archive recommendations for audit trail."""
        try:
            now = int(time.time())
            with sqlite3.connect(_LEARNING_DB) as conn:
                for r in recs:
                    conn.execute(
                        """INSERT INTO recommendations (type, action, evidence, impact, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (r.type.value, r.action, r.evidence, r.impact_estimate, now)
                    )
        except Exception as exc:
            log.debug("Persist recommendations: %s", exc)
