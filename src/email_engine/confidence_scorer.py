"""
confidence_scorer.py — Multi-factor email confidence scorer.

This is how Hunter.io scores emails before showing them to users.
Each signal contributes a weighted component to the final 0-100 score.

Scoring formula:
  score = (
      smtp_score    × 0.35 +   # SMTP verification — strongest signal
      pattern_score × 0.25 +   # Domain pattern match — structural signal
      source_score  × 0.20 +   # Cross-source corroboration
      name_score    × 0.10 +   # Name quality (first+last known vs "Unknown")
      recency_score × 0.10     # Recency of discovery
  )

Signal details:

  smtp_score (0-100):
    verified=True, catch_all=False  → 100
    not_checked                     → 50  (neutral prior)
    verified=False (bounced)        → 0
    catch_all domain                → 40  (email exists but may be false positive)
    smtp_error (server blocked)     → 55  (inconclusive — many servers block SMTP check)

  pattern_score (0-100):
    pattern_confidence × 100
    If format matches dominant pattern exactly → +10 bonus (capped at 100)
    If no pattern data → base_score from EmailFormat

  source_score (0-100):
    1 source  → 20
    2 sources → 45  (+corroboration boost)
    3 sources → 65
    4+ sources→ 80
    Provider quality weights applied (Hunter > Apollo > web_scrape > generated)

  name_score (0-100):
    first + last known, not "Unknown"  → 100
    first name only                     → 60
    "Unknown"                           → 10
    name derived from email local-part  → 40

  recency_score (0-100):
    found < 1 day ago   → 100
    found < 7 days ago  → 80
    found < 30 days ago → 60
    found < 90 days ago → 40
    older or unknown    → 20

Provider quality weights (for source_score):
  hunter, apollo, clearbit, rocketreach → quality 1.0 (verified APIs)
  snov, skrapp, anymail_finder          → quality 0.9
  github_commits                        → quality 0.85 (real emails but role unknown)
  web_crawler                           → quality 0.6 (scraping, less reliable)
  generated (pattern only)              → quality 0.4 (no verification)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

# Provider quality weights
_PROVIDER_QUALITY: Dict[str, float] = {
    "hunter":         1.0,
    "apollo":         1.0,
    "clearbit":       1.0,
    "rocketreach":    1.0,
    "snov":           0.9,
    "skrapp":         0.9,
    "anymail_finder": 0.9,
    "voilanorbert":   0.85,
    "github_commits": 0.85,
    "dropcontact":    0.85,
    "kaspr":          0.85,
    "signalhire":     0.80,
    "web_crawler":    0.60,
    "generated":      0.40,
    "dns_pattern":    0.35,
}

# Source count → corroboration boost (0-100)
_SOURCE_CORROBORATION: Dict[int, int] = {
    0: 0,
    1: 20,
    2: 45,
    3: 65,
    4: 75,
    5: 82,
}


@dataclass
class ScoringSignals:
    """All signals used to compute final confidence score."""

    # SMTP verification result
    smtp_verified:    Optional[bool]  = None    # True=verified, False=bounce, None=unchecked
    smtp_catch_all:   bool            = False
    smtp_blocked:     bool            = False    # server blocked our check (inconclusive)

    # Pattern mining
    pattern_confidence: float         = 0.0     # 0.0–1.0 from PatternResult.confidence
    matches_top_pattern: bool         = False    # does this email match the domain's dominant pattern?
    format_base_score:   int          = 50       # base_score from EmailFormat

    # Source provenance
    sources: List[str]                = field(default_factory=list)

    # Name quality
    has_first_name: bool              = False
    has_last_name:  bool              = False
    name_is_unknown: bool             = True

    # Recency (when this email was first discovered)
    discovered_at: Optional[datetime] = None


@dataclass
class ScoredEmail:
    """Final scored email with breakdown."""
    email:           str
    final_score:     int          # 0-100
    smtp_component:  float
    pattern_component: float
    source_component:  float
    name_component:    float
    recency_component: float
    label:           str          # "high", "medium", "low", "unverified"

    @property
    def is_high_confidence(self) -> bool:
        return self.final_score >= 75

    @property
    def is_usable(self) -> bool:
        return self.final_score >= 40


class ConfidenceScorer:
    """
    Computes a final confidence score for an email address
    given multiple evidence signals.

    Usage:
        scorer  = ConfidenceScorer()
        signals = ScoringSignals(
            smtp_verified=True,
            smtp_catch_all=False,
            pattern_confidence=0.9,
            matches_top_pattern=True,
            sources=["hunter", "github_commits"],
            has_first_name=True,
            has_last_name=True,
            name_is_unknown=False,
            discovered_at=datetime.now(timezone.utc),
        )
        result = scorer.score("john.doe@stripe.com", signals)
        print(result.final_score)   # e.g. 92
        print(result.label)         # "high"
    """

    WEIGHTS = {
        "smtp":    0.35,
        "pattern": 0.25,
        "source":  0.20,
        "name":    0.10,
        "recency": 0.10,
    }

    def score(self, email: str, signals: ScoringSignals) -> ScoredEmail:
        smtp_c    = self._smtp_score(signals)
        pattern_c = self._pattern_score(signals)
        source_c  = self._source_score(signals)
        name_c    = self._name_score(signals)
        recency_c = self._recency_score(signals)

        raw = (
            smtp_c    * self.WEIGHTS["smtp"]    +
            pattern_c * self.WEIGHTS["pattern"] +
            source_c  * self.WEIGHTS["source"]  +
            name_c    * self.WEIGHTS["name"]    +
            recency_c * self.WEIGHTS["recency"]
        )
        final = max(0, min(100, int(round(raw))))
        label = self._label(final, signals)

        return ScoredEmail(
            email             = email,
            final_score       = final,
            smtp_component    = smtp_c,
            pattern_component = pattern_c,
            source_component  = source_c,
            name_component    = name_c,
            recency_component = recency_c,
            label             = label,
        )

    def bulk_score(
        self,
        emails: List[str],
        signals_map: Dict[str, ScoringSignals],
    ) -> List[ScoredEmail]:
        """Score a list of emails and return sorted by final_score desc."""
        results = []
        for email in emails:
            signals = signals_map.get(email, ScoringSignals())
            results.append(self.score(email, signals))
        return sorted(results, key=lambda x: x.final_score, reverse=True)

    # ── Signal scorers ────────────────────────────────────────────────────────

    @staticmethod
    def _smtp_score(s: ScoringSignals) -> float:
        if s.smtp_verified is None:
            if s.smtp_blocked:
                return 55.0    # server blocked check → inconclusive, slight positive prior
            return 50.0        # unchecked → neutral
        if s.smtp_catch_all:
            return 40.0        # domain accepts all → not meaningful
        if s.smtp_verified:
            return 100.0
        return 0.0             # bounced

    @staticmethod
    def _pattern_score(s: ScoringSignals) -> float:
        if s.pattern_confidence <= 0:
            return float(s.format_base_score)

        base = s.pattern_confidence * 100.0
        if s.matches_top_pattern:
            base = min(100.0, base + 10.0)
        return base

    @staticmethod
    def _source_score(s: ScoringSignals) -> float:
        if not s.sources:
            return 0.0

        # Average quality of sources, weighted by count corroboration
        avg_quality = sum(
            _PROVIDER_QUALITY.get(src, 0.5) for src in s.sources
        ) / len(s.sources)

        count_bonus = _SOURCE_CORROBORATION.get(
            min(len(s.sources), max(_SOURCE_CORROBORATION.keys())),
            80,
        )
        return avg_quality * count_bonus

    @staticmethod
    def _name_score(s: ScoringSignals) -> float:
        if s.name_is_unknown:
            return 10.0
        if s.has_first_name and s.has_last_name:
            return 100.0
        if s.has_first_name or s.has_last_name:
            return 60.0
        return 30.0

    @staticmethod
    def _recency_score(s: ScoringSignals) -> float:
        if s.discovered_at is None:
            return 20.0
        now   = datetime.now(timezone.utc)
        delta = now - s.discovered_at.replace(tzinfo=timezone.utc) if s.discovered_at.tzinfo is None else now - s.discovered_at
        days  = delta.total_seconds() / 86400

        if days < 1:   return 100.0
        if days < 7:   return 80.0
        if days < 30:  return 60.0
        if days < 90:  return 40.0
        return 20.0

    @staticmethod
    def _label(score: int, signals: ScoringSignals) -> str:
        if signals.smtp_verified is False:
            return "bounced"
        if score >= 75:
            return "high"
        if score >= 55:
            return "medium"
        if score >= 35:
            return "low"
        return "unverified"
