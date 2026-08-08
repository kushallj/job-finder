"""Comprehensive unit tests for the email engine confidence scorer."""

import pytest
from datetime import datetime, timezone, timedelta

from src.email_engine.confidence_scorer import (
    ScoringSignals,
    ScoredEmail,
    ConfidenceScorer,
)


@pytest.fixture
def scorer():
    """Create a ConfidenceScorer instance for tests."""
    return ConfidenceScorer()


def _make_signals(**kwargs):
    """Helper to create ScoringSignals with sensible defaults."""
    defaults = {
        "smtp_verified": None,
        "smtp_catch_all": False,
        "smtp_blocked": False,
        "pattern_confidence": 0.0,
        "matches_top_pattern": False,
        "format_base_score": 0,
        "sources": [],
        "has_first_name": False,
        "has_last_name": False,
        "name_is_unknown": False,
        "discovered_at": None,
    }
    defaults.update(kwargs)
    return ScoringSignals(**defaults)


# =============================================================================
# Integration / End-to-End Scoring Tests
# =============================================================================


class TestScoreIntegration:
    """Tests for overall scoring behavior with combined signals."""

    def test_score_perfect_email(self, scorer):
        """All signals positive → score >= 90, label='high'."""
        signals = _make_signals(
            smtp_verified=True,
            smtp_catch_all=False,
            smtp_blocked=False,
            pattern_confidence=0.95,
            matches_top_pattern=True,
            format_base_score=80,
            sources=["hunter", "apollo", "clearbit", "rocketreach"],
            has_first_name=True,
            has_last_name=True,
            name_is_unknown=False,
            discovered_at=datetime.now(timezone.utc),
        )
        result = scorer.score("perfect@example.com", signals)

        assert result.final_score >= 90
        assert result.label == "high"
        assert result.email == "perfect@example.com"

    def test_score_bounced_email(self, scorer):
        """smtp_verified=False → low score, label='bounced'."""
        signals = _make_signals(
            smtp_verified=False,
            sources=["hunter"],
            has_first_name=True,
            has_last_name=True,
            name_is_unknown=False,
            discovered_at=datetime.now(timezone.utc),
        )
        result = scorer.score("bounced@example.com", signals)

        assert result.label == "bounced"
        assert result.smtp_component == 0

    def test_score_unverified_email(self, scorer):
        """No signals at all → label='unverified'."""
        signals = _make_signals(
            smtp_verified=None,
            smtp_catch_all=False,
            smtp_blocked=False,
            pattern_confidence=0.0,
            matches_top_pattern=False,
            format_base_score=0,
            sources=[],
            has_first_name=False,
            has_last_name=False,
            name_is_unknown=False,
            discovered_at=None,
        )
        result = scorer.score("unknown@example.com", signals)

        assert result.label == "unverified"
        assert result.final_score < 35

    def test_score_medium_confidence(self, scorer):
        """Some positive signals → score 55-75, label='medium'."""
        signals = _make_signals(
            smtp_verified=None,
            pattern_confidence=0.7,
            matches_top_pattern=True,
            format_base_score=50,
            sources=["hunter", "apollo"],
            has_first_name=True,
            has_last_name=True,
            name_is_unknown=False,
            discovered_at=datetime.now(timezone.utc) - timedelta(days=15),
        )
        result = scorer.score("medium@example.com", signals)

        assert 55 <= result.final_score <= 75
        assert result.label == "medium"


# =============================================================================
# SMTP Component Tests
# =============================================================================


class TestSMTPComponent:
    """Tests for SMTP verification scoring component."""

    def test_smtp_verified_component(self, scorer):
        """smtp_verified=True → smtp_component=100."""
        signals = _make_signals(smtp_verified=True)
        result = scorer.score("test@example.com", signals)

        assert result.smtp_component == 100

    def test_smtp_unchecked_component(self, scorer):
        """smtp_verified=None → smtp_component=50."""
        signals = _make_signals(smtp_verified=None)
        result = scorer.score("test@example.com", signals)

        assert result.smtp_component == 50

    def test_smtp_catch_all_component(self, scorer):
        """catch_all=True with smtp_verified=True → smtp_component=40."""
        # smtp_catch_all only triggers when smtp_verified is NOT None
        signals = _make_signals(smtp_verified=True, smtp_catch_all=True)
        result = scorer.score("test@example.com", signals)

        assert result.smtp_component == 40

    def test_smtp_blocked_component(self, scorer):
        """blocked=True → smtp_component=55."""
        signals = _make_signals(smtp_blocked=True)
        result = scorer.score("test@example.com", signals)

        assert result.smtp_component == 55


# =============================================================================
# Pattern Component Tests
# =============================================================================


class TestPatternComponent:
    """Tests for pattern confidence scoring component."""

    def test_pattern_with_high_confidence(self, scorer):
        """pattern_confidence=0.9, matches_top=True → pattern_component >= 100 (capped at 100)."""
        signals = _make_signals(
            pattern_confidence=0.9,
            matches_top_pattern=True,
        )
        result = scorer.score("test@example.com", signals)

        # 0.9 * 100 = 90, +10 for matches_top = 100
        assert result.pattern_component >= 100

    def test_pattern_with_zero_confidence(self, scorer):
        """pattern_confidence=0 → uses format_base_score."""
        signals = _make_signals(
            pattern_confidence=0.0,
            matches_top_pattern=False,
            format_base_score=45,
        )
        result = scorer.score("test@example.com", signals)

        # With zero pattern confidence, should fall back to format_base_score
        assert result.pattern_component == 45


# =============================================================================
# Source Component Tests
# =============================================================================


class TestSourceComponent:
    """Tests for source quality and corroboration scoring component."""

    def test_source_single_hunter(self, scorer):
        """sources=['hunter'] → source_component = 1.0 × 20 = 20."""
        signals = _make_signals(sources=["hunter"])
        result = scorer.score("test@example.com", signals)

        assert result.source_component == 20

    def test_source_two_providers(self, scorer):
        """sources=['hunter','apollo'] → corroboration=45, quality=1.0 → 45."""
        signals = _make_signals(sources=["hunter", "apollo"])
        result = scorer.score("test@example.com", signals)

        assert result.source_component == 45

    def test_source_three_providers(self, scorer):
        """sources=['hunter','apollo','github_commits'] → corroboration=65 × avg_quality."""
        signals = _make_signals(sources=["hunter", "apollo", "github_commits"])
        result = scorer.score("test@example.com", signals)

        # avg quality = (1.0 + 1.0 + 0.85) / 3 = 0.95
        # source_component = 65 * 0.95 = 61.75 → rounded to nearest int or float
        expected = 65 * ((1.0 + 1.0 + 0.85) / 3)
        assert abs(result.source_component - expected) < 1.5


# =============================================================================
# Name Component Tests
# =============================================================================


class TestNameComponent:
    """Tests for name quality scoring component."""

    def test_name_full(self, scorer):
        """has_first_name + has_last_name, not unknown → 100."""
        signals = _make_signals(
            has_first_name=True,
            has_last_name=True,
            name_is_unknown=False,
        )
        result = scorer.score("test@example.com", signals)

        assert result.name_component == 100

    def test_name_unknown(self, scorer):
        """name_is_unknown=True → 10."""
        signals = _make_signals(
            has_first_name=False,
            has_last_name=False,
            name_is_unknown=True,
        )
        result = scorer.score("test@example.com", signals)

        assert result.name_component == 10

    def test_name_partial(self, scorer):
        """Only first name → 60."""
        signals = _make_signals(
            has_first_name=True,
            has_last_name=False,
            name_is_unknown=False,
        )
        result = scorer.score("test@example.com", signals)

        assert result.name_component == 60


# =============================================================================
# Recency Component Tests
# =============================================================================


class TestRecencyComponent:
    """Tests for recency scoring component based on discovery time."""

    def test_recency_fresh(self, scorer):
        """discovered_at=now → 100."""
        signals = _make_signals(
            discovered_at=datetime.now(timezone.utc),
        )
        result = scorer.score("test@example.com", signals)

        assert result.recency_component == 100

    def test_recency_old(self, scorer):
        """discovered_at=6 months ago → 20."""
        signals = _make_signals(
            discovered_at=datetime.now(timezone.utc) - timedelta(days=180),
        )
        result = scorer.score("test@example.com", signals)

        assert result.recency_component == 20

    def test_recency_week_old(self, scorer):
        """discovered_at=3 days ago → 80."""
        signals = _make_signals(
            discovered_at=datetime.now(timezone.utc) - timedelta(days=3),
        )
        result = scorer.score("test@example.com", signals)

        assert result.recency_component == 80


# =============================================================================
# Bulk Scoring Tests
# =============================================================================


class TestBulkScore:
    """Tests for bulk scoring and sorting behavior."""

    def test_bulk_score_sorted(self, scorer):
        """Pass 3 emails with varying quality → verify sorted descending by score."""
        emails = ["high@ex.com", "medium@ex.com", "low@ex.com"]

        signals_map = {
            "high@ex.com": _make_signals(
                smtp_verified=True,
                pattern_confidence=0.95,
                matches_top_pattern=True,
                sources=["hunter", "apollo", "clearbit", "rocketreach"],
                has_first_name=True,
                has_last_name=True,
                name_is_unknown=False,
                discovered_at=datetime.now(timezone.utc),
            ),
            "medium@ex.com": _make_signals(
                smtp_verified=None,
                pattern_confidence=0.5,
                matches_top_pattern=False,
                sources=["hunter", "apollo"],
                has_first_name=True,
                has_last_name=True,
                name_is_unknown=False,
                discovered_at=datetime.now(timezone.utc) - timedelta(days=20),
            ),
            "low@ex.com": _make_signals(
                smtp_verified=None,
                pattern_confidence=0.1,
                matches_top_pattern=False,
                sources=["generated"],
                has_first_name=False,
                has_last_name=False,
                name_is_unknown=True,
                discovered_at=datetime.now(timezone.utc) - timedelta(days=200),
            ),
        }

        results = scorer.bulk_score(emails, signals_map)

        assert len(results) == 3
        # Verify sorted descending by final_score
        scores = [r.final_score for r in results]
        assert scores == sorted(scores, reverse=True)
        # First should be high, last should be low/unverified
        assert results[0].final_score > results[1].final_score
        assert results[1].final_score > results[2].final_score


# =============================================================================
# ScoredEmail Properties Tests
# =============================================================================


class TestScoredEmailProperties:
    """Tests for ScoredEmail convenience properties."""

    def test_is_high_confidence(self, scorer):
        """is_high_confidence property → True when score >= 75."""
        signals = _make_signals(
            smtp_verified=True,
            pattern_confidence=0.95,
            matches_top_pattern=True,
            sources=["hunter", "apollo", "clearbit", "rocketreach"],
            has_first_name=True,
            has_last_name=True,
            name_is_unknown=False,
            discovered_at=datetime.now(timezone.utc),
        )
        result = scorer.score("high@example.com", signals)

        assert result.final_score >= 75
        assert result.is_high_confidence is True

    def test_is_usable(self, scorer):
        """is_usable property → True when score >= 40."""
        signals = _make_signals(
            smtp_verified=None,
            pattern_confidence=0.5,
            matches_top_pattern=False,
            sources=["hunter"],
            has_first_name=True,
            has_last_name=False,
            name_is_unknown=False,
            discovered_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        result = scorer.score("usable@example.com", signals)

        assert result.final_score >= 40
        assert result.is_usable is True

    def test_not_usable(self, scorer):
        """is_usable property → False when score < 40."""
        signals = _make_signals(
            smtp_verified=None,
            pattern_confidence=0.0,
            matches_top_pattern=False,
            format_base_score=0,
            sources=[],
            has_first_name=False,
            has_last_name=False,
            name_is_unknown=True,
            discovered_at=None,
        )
        result = scorer.score("bad@example.com", signals)

        assert result.final_score < 40
        assert result.is_usable is False

    def test_not_high_confidence(self, scorer):
        """is_high_confidence property → False when score < 75."""
        signals = _make_signals(
            smtp_verified=None,
            pattern_confidence=0.3,
            matches_top_pattern=False,
            sources=["generated"],
            has_first_name=True,
            has_last_name=False,
            name_is_unknown=False,
            discovered_at=datetime.now(timezone.utc) - timedelta(days=100),
        )
        result = scorer.score("low@example.com", signals)

        assert result.final_score < 75
        assert result.is_high_confidence is False
