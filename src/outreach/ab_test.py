"""
ab_test.py — Subject line A/B testing with statistical significance.

Algorithm:
  Exploration: epsilon-greedy (ε=0.1) — 10% of sends go to a random variant
               to keep collecting data even after a winner emerges.
  Exploitation: pick variant with highest reply rate.
  Significance: chi-square test (p < 0.05, min 30 sends per variant).

Why chi-square, not t-test?
  Reply rate is a binary outcome (replied / didn't reply) → chi-square is
  the correct test for proportions. t-test is for continuous variables.

Data flow:
  record_send(template, variant_idx)    — called when email is sent
  record_reply(template, variant_idx)   — called when reply detected
  best_variant(template)                → returns variant_idx to use
  promote_winner(template)              → locks in the winning variant

Persistence:
  State is in-memory by default. Pass a db_path to enable SQLite persistence.
  This lets stats survive restarts (important for long-running campaigns).
"""

from __future__ import annotations

import json
import logging
import math
import random
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Built-in subject line variants per template type
# ---------------------------------------------------------------------------

DEFAULT_VARIANTS: Dict[str, List[str]] = {
    "hr_outreach": [
        "Experienced SWE interested in {company} — quick intro?",
        "Reaching out about engineering roles at {company}",
        "{company} caught my eye — background in {skill}",
    ],
    "engineering_manager": [
        "Engineer with {skill} experience — open to a chat?",
        "Your {company} engineering team — would love to connect",
        "Worked on {skill} at scale — exploring {company}",
    ],
    "follow_up_1": [
        "Following up — still interested in {company}",
        "Quick follow-up on my earlier note",
        "Circling back — {company} engineering role",
    ],
    "follow_up_2": [
        "One last follow-up — {company}",
        "Still keen on {company} if timing is right",
        "Checking in — {company} opportunity",
    ],
}


@dataclass
class VariantStats:
    sends:     int = 0
    replies:   int = 0
    winner:    bool = False     # locked in as permanent winner

    @property
    def reply_rate(self) -> float:
        return self.replies / self.sends if self.sends > 0 else 0.0


class ABTestManager:
    """
    Manages A/B testing for email subject lines.

    Usage:
        mgr = ABTestManager()

        # Choose variant to use
        idx, subject = mgr.best_variant("hr_outreach", company="Stripe", skill="Python")

        # After sending
        mgr.record_send("hr_outreach", idx)

        # After reply detected
        mgr.record_reply("hr_outreach", idx)

        # Check if we have a winner
        winner = mgr.get_winner("hr_outreach")
    """

    MIN_SENDS_FOR_SIGNIFICANCE = 30    # minimum sends per variant before chi-square
    SIGNIFICANCE_LEVEL         = 0.05  # p-value threshold
    EPSILON                    = 0.10  # 10% random exploration

    def __init__(
        self,
        variants:  Optional[Dict[str, List[str]]] = None,
        db_path:   Optional[str] = None,
    ):
        self._variants = variants or DEFAULT_VARIANTS
        self._stats: Dict[str, List[VariantStats]] = {
            tmpl: [VariantStats() for _ in v]
            for tmpl, v in self._variants.items()
        }
        self._winners: Dict[str, int] = {}   # template → winning variant index
        self._db_path = db_path
        if db_path:
            self._init_db(db_path)
            self._load_from_db()

    # ── Public API ────────────────────────────────────────────────────────────

    def best_variant(
        self,
        template: str,
        **fmt_kwargs,
    ) -> Tuple[int, str]:
        """
        Choose the best subject line variant for `template`.
        Returns (variant_index, formatted_subject).

        Selection strategy:
          1. If a winner is locked in → always use winner
          2. With probability ε → random exploration
          3. Otherwise → highest reply rate (exploitation)
        """
        if template not in self._variants:
            log.warning("Unknown template %s, using key as subject", template)
            return 0, template

        # Locked winner
        if template in self._winners:
            idx = self._winners[template]
            return idx, self._format(template, idx, fmt_kwargs)

        variant_list = self._variants[template]
        stats_list   = self._stats[template]

        # Epsilon-greedy exploration
        if random.random() < self.EPSILON:
            idx = random.randrange(len(variant_list))
            log.debug("A/B explore: template=%s idx=%d", template, idx)
            return idx, self._format(template, idx, fmt_kwargs)

        # Exploitation: highest reply rate (with tie-break: fewer sends = more data needed)
        idx = max(
            range(len(stats_list)),
            key=lambda i: (
                stats_list[i].reply_rate,
                -stats_list[i].sends,   # tie-break: prefer less-tested variant
            ),
        )
        return idx, self._format(template, idx, fmt_kwargs)

    def record_send(self, template: str, variant_idx: int) -> None:
        if template in self._stats and variant_idx < len(self._stats[template]):
            self._stats[template][variant_idx].sends += 1
            self._persist(template, variant_idx)
            self._check_significance(template)

    def record_reply(self, template: str, variant_idx: int) -> None:
        if template in self._stats and variant_idx < len(self._stats[template]):
            self._stats[template][variant_idx].replies += 1
            self._persist(template, variant_idx)
            self._check_significance(template)

    def get_winner(self, template: str) -> Optional[int]:
        return self._winners.get(template)

    def promote_winner(self, template: str, variant_idx: int) -> None:
        """Manually lock in a winner (e.g., after human review)."""
        self._winners[template] = variant_idx
        log.info("Winner manually promoted: template=%s idx=%d", template, variant_idx)

    def summary(self) -> Dict[str, list]:
        """Return stats dict for dashboard display."""
        result = {}
        for tmpl, stats_list in self._stats.items():
            result[tmpl] = [
                {
                    "variant": self._variants[tmpl][i],
                    "sends":      s.sends,
                    "replies":    s.replies,
                    "reply_rate": round(s.reply_rate * 100, 1),
                    "winner":     self._winners.get(tmpl) == i,
                }
                for i, s in enumerate(stats_list)
            ]
        return result

    # ── Chi-square significance test ─────────────────────────────────────────

    def _check_significance(self, template: str) -> None:
        """
        Run chi-square test across all variants for `template`.
        Promotes the best performer if p < SIGNIFICANCE_LEVEL.

        Chi-square for 2×N contingency table:
          O = [[replied_i, not_replied_i] for each variant]
          chi2 = sum((O - E)^2 / E)
        """
        if template in self._winners:
            return     # already decided

        stats = self._stats[template]
        if any(s.sends < self.MIN_SENDS_FOR_SIGNIFICANCE for s in stats):
            return     # not enough data yet

        total_sends   = sum(s.sends   for s in stats)
        total_replies = sum(s.replies for s in stats)
        if total_replies == 0:
            return

        expected_rate = total_replies / total_sends
        chi2 = 0.0
        for s in stats:
            expected_pos = s.sends * expected_rate
            expected_neg = s.sends * (1 - expected_rate)
            if expected_pos == 0 or expected_neg == 0:
                continue
            obs_pos = s.replies
            obs_neg = s.sends - s.replies
            chi2 += (obs_pos - expected_pos) ** 2 / expected_pos
            chi2 += (obs_neg - expected_neg) ** 2 / expected_neg

        df    = len(stats) - 1
        p_val = self._chi2_p_value(chi2, df)

        if p_val < self.SIGNIFICANCE_LEVEL:
            winner_idx = max(range(len(stats)), key=lambda i: stats[i].reply_rate)
            self._winners[template] = winner_idx
            log.info(
                "A/B winner: template=%s idx=%d rate=%.1f%% (chi2=%.2f p=%.4f)",
                template, winner_idx,
                stats[winner_idx].reply_rate * 100,
                chi2, p_val,
            )

    @staticmethod
    def _chi2_p_value(chi2: float, df: int) -> float:
        """
        Approximate p-value for chi-square distribution using incomplete gamma.
        Uses math.lgamma for numerical stability — no scipy required.
        """
        if df <= 0 or chi2 <= 0:
            return 1.0
        # Regularized incomplete gamma Q(df/2, chi2/2)
        # For df=1 (most common case): p = erfc(sqrt(chi2/2))
        if df == 1:
            return math.erfc(math.sqrt(chi2 / 2))
        # For df=2: p = exp(-chi2/2)
        if df == 2:
            return math.exp(-chi2 / 2)
        # General: series expansion (good enough for df 1-5)
        k   = df / 2.0
        x   = chi2 / 2.0
        try:
            log_p = k * math.log(x) - x - math.lgamma(k + 1)
            p     = math.exp(log_p)
            return min(1.0, max(0.0, 1.0 - p))
        except (ValueError, OverflowError):
            return 0.0 if chi2 > 20 else 1.0

    # ── Formatting ────────────────────────────────────────────────────────────

    def _format(self, template: str, idx: int, kwargs: dict) -> str:
        try:
            return self._variants[template][idx].format(**kwargs)
        except KeyError:
            return self._variants[template][idx]

    # ── SQLite persistence ────────────────────────────────────────────────────

    def _init_db(self, db_path: str) -> None:
        con = sqlite3.connect(db_path)
        con.execute("""
            CREATE TABLE IF NOT EXISTS ab_stats (
                template    TEXT,
                variant_idx INTEGER,
                sends       INTEGER DEFAULT 0,
                replies     INTEGER DEFAULT 0,
                PRIMARY KEY (template, variant_idx)
            )
        """)
        con.commit()
        con.close()

    def _load_from_db(self) -> None:
        if not self._db_path:
            return
        try:
            con = sqlite3.connect(self._db_path)
            for row in con.execute("SELECT template, variant_idx, sends, replies FROM ab_stats"):
                tmpl, idx, sends, replies = row
                if tmpl in self._stats and idx < len(self._stats[tmpl]):
                    self._stats[tmpl][idx].sends   = sends
                    self._stats[tmpl][idx].replies = replies
            con.close()
        except Exception as e:
            log.warning("A/B DB load failed: %s", e)

    def _persist(self, template: str, variant_idx: int) -> None:
        if not self._db_path:
            return
        try:
            s   = self._stats[template][variant_idx]
            con = sqlite3.connect(self._db_path)
            con.execute(
                "INSERT OR REPLACE INTO ab_stats VALUES (?, ?, ?, ?)",
                (template, variant_idx, s.sends, s.replies),
            )
            con.commit()
            con.close()
        except Exception as e:
            log.debug("A/B DB persist failed: %s", e)
