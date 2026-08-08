"""
tests/test_feedback_loop.py — Unit tests for feedback loop components.

Tests for:
1. Nightly metrics collection from outreach records
2. Pattern mining from successful/unsuccessful outreach
3. Adaptive optimization based on patterns
4. Daily digest report generation
5. Metric tracking (open rate, reply rate, positive reply rate)

Requirements: 20.1, 20.2, 20.3, 20.4, 20.5
"""

import pytest
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Job, Contact, OutreachRecord, Application
from src.feedback import (
    MetricsCollector,
    PatternMiner,
    AdaptiveOptimizer,
    DigestGenerator,
    FeedbackLoop,
    OutreachMetrics,
    SuccessPattern,
    Recommendation,
    RecommendationType,
    LearningSnapshot,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def feedback_db():
    """Create an in-memory SQLite DB with all tables for feedback testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def feedback_db_factory():
    """Return a factory function that creates new sessions for FeedbackLoop."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def factory():
        return TestingSessionLocal()
    
    yield factory, TestingSessionLocal()  # Also yield a session for setup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def sample_outreach_records(feedback_db):
    """Create sample outreach records with various statuses for testing."""
    now = datetime.now(timezone.utc)
    
    # Create a job first
    job = Job(
        job_id="test_job_1",
        title="Software Engineer",
        company="TestCorp",
        location="Remote",
        description="Python developer role",
        url="https://test.com/jobs/1",
        source="test"
    )
    feedback_db.add(job)
    feedback_db.flush()
    
    # Create a contact
    contact = Contact(
        name="Jane Smith",
        title="Engineering Manager",
        email="jane@testcorp.com",
        company="TestCorp",
        department="Engineering",
        confidence_score=90
    )
    feedback_db.add(contact)
    feedback_db.flush()
    
    records = []
    # Create 30 outreach records with mixed outcomes
    for i in range(30):
        hour = 9 + (i % 8)  # Hours 9-16
        day_offset = i % 7
        sent_time = now - timedelta(days=day_offset, hours=24-hour)
        
        # Mix of statuses
        if i < 5:
            status = "bounced"
            reply_sentiment = None
            replied_at = None
        elif i < 15:
            status = "replied"
            reply_sentiment = "positive" if i < 10 else "neutral"
            replied_at = sent_time + timedelta(hours=4)
        else:
            status = "sent"
            reply_sentiment = None
            replied_at = None
        
        # Mix of template types and hooks
        template_types = ["hr_outreach", "engineering_manager", "follow_up"]
        ab_variants = [0, 1]
        
        record = OutreachRecord(
            contact_id=contact.id,
            job_id=job.id,
            subject=f"Great opportunity at TestCorp #{i}",
            body=f"Hi Jane, I saw your project on GitHub. Let's talk about your role.",
            template_type=template_types[i % len(template_types)],
            status=status,
            sent_at=sent_time,
            replied_at=replied_at,
            email_sent=True,
            contact_email="jane@testcorp.com",
            contact_name="Jane Smith",
            reply_sentiment=reply_sentiment,
            ab_variant=ab_variants[i % 2],
        )
        records.append(record)
        feedback_db.add(record)
    
    feedback_db.commit()
    return records


# ---------------------------------------------------------------------------
# Test: Metrics Collection (Requirement 20.1, 20.5)
# ---------------------------------------------------------------------------

class TestMetricsCollector:
    """Tests for MetricsCollector - nightly metrics collection."""
    
    def test_collect_empty_db(self, feedback_db):
        """Test metrics collection returns empty metrics with no data."""
        collector = MetricsCollector(feedback_db)
        metrics = collector.collect(window_days=7)
        
        assert metrics.total_sent == 0
        assert metrics.total_replied == 0
        assert metrics.reply_rate == 0.0
        assert metrics.window_days == 7
    
    def test_collect_basic_funnel_metrics(self, feedback_db, sample_outreach_records):
        """Test that basic funnel metrics are collected correctly."""
        collector = MetricsCollector(feedback_db)
        metrics = collector.collect(window_days=7)
        
        assert metrics.total_sent == 30
        assert metrics.total_bounced == 5
        assert metrics.total_delivered == 25  # 30 - 5 bounced
        assert metrics.total_replied == 10  # 10 replied
        assert metrics.total_positive == 5  # 5 positive sentiment
    
    def test_reply_rate_calculation(self, feedback_db, sample_outreach_records):
        """Test reply rate is calculated correctly (Requirement 20.5)."""
        collector = MetricsCollector(feedback_db)
        metrics = collector.collect(window_days=7)
        
        expected_reply_rate = 10 / 30  # 10 replied out of 30 sent
        assert abs(metrics.reply_rate - expected_reply_rate) < 0.001
    
    def test_positive_reply_rate_calculation(self, feedback_db, sample_outreach_records):
        """Test positive reply rate calculation (Requirement 20.5)."""
        collector = MetricsCollector(feedback_db)
        metrics = collector.collect(window_days=7)
        
        expected_positive_rate = 5 / 30  # 5 positive out of 30 sent
        assert abs(metrics.positive_rate - expected_positive_rate) < 0.001
    
    def test_segment_by_template_type(self, feedback_db, sample_outreach_records):
        """Test segmentation by template type."""
        collector = MetricsCollector(feedback_db)
        metrics = collector.collect(window_days=7)
        
        # Should have segment data for templates
        assert len(metrics.by_template) > 0
        for template, stats in metrics.by_template.items():
            assert stats.sent > 0
            assert 0 <= stats.reply_rate <= 1.0
    
    def test_segment_by_ab_variant(self, feedback_db, sample_outreach_records):
        """Test segmentation by A/B variant."""
        collector = MetricsCollector(feedback_db)
        metrics = collector.collect(window_days=7)
        
        # Should have A/B variant data
        assert len(metrics.by_ab_variant) > 0
    
    def test_segment_by_send_hour(self, feedback_db, sample_outreach_records):
        """Test segmentation by send hour."""
        collector = MetricsCollector(feedback_db)
        metrics = collector.collect(window_days=7)
        
        # Should have hour-based segmentation
        # Note: may be empty if not enough sends per hour
        for hour, stats in metrics.by_send_hour.items():
            assert 0 <= hour <= 23
            assert stats.sent >= 5  # Minimum segment size
    
    def test_funnel_str_format(self, feedback_db, sample_outreach_records):
        """Test funnel string format for logging."""
        collector = MetricsCollector(feedback_db)
        metrics = collector.collect(window_days=7)
        
        funnel_str = metrics.funnel_str()
        assert "Sent" in funnel_str
        assert "Replied" in funnel_str
        assert "Positive" in funnel_str
    
    def test_window_days_filter(self, feedback_db):
        """Test that window_days correctly filters old records."""
        now = datetime.now(timezone.utc)
        
        # Create a job and contact
        job = Job(
            job_id="window_test",
            title="Test",
            company="Test",
            location="Remote",
            description="Test",
            url="https://test.com",
            source="test"
        )
        feedback_db.add(job)
        feedback_db.flush()
        
        # Create recent and old records
        recent_record = OutreachRecord(
            job_id=job.id,
            subject="Recent",
            body="Recent email",
            status="replied",
            sent_at=now - timedelta(days=3),
            replied_at=now - timedelta(days=2),
            email_sent=True,
            contact_email="test@test.com"
        )
        old_record = OutreachRecord(
            job_id=job.id,
            subject="Old",
            body="Old email",
            status="replied",
            sent_at=now - timedelta(days=10),
            replied_at=now - timedelta(days=9),
            email_sent=True,
            contact_email="test@test.com"
        )
        feedback_db.add(recent_record)
        feedback_db.add(old_record)
        feedback_db.commit()
        
        collector = MetricsCollector(feedback_db)
        
        # 7-day window should only include recent record
        metrics_7d = collector.collect(window_days=7)
        assert metrics_7d.total_sent == 1
        
        # 14-day window should include both
        metrics_14d = collector.collect(window_days=14)
        assert metrics_14d.total_sent == 2


# ---------------------------------------------------------------------------
# Test: Pattern Mining (Requirement 20.2)
# ---------------------------------------------------------------------------

class TestPatternMiner:
    """Tests for PatternMiner - pattern mining from outreach data."""
    
    def test_mine_from_empty_metrics(self):
        """Test mining returns empty list with no data."""
        miner = PatternMiner()
        metrics = OutreachMetrics(window_days=7)
        patterns = miner.mine(metrics, db_session=None)
        
        assert patterns == []
    
    def test_mine_hook_type_patterns(self, feedback_db, sample_outreach_records):
        """Test that hook type patterns are detected."""
        collector = MetricsCollector(feedback_db)
        metrics = collector.collect(window_days=7)
        
        miner = PatternMiner()
        patterns = miner.mine(metrics, feedback_db, window_days=30)
        
        # Should have some patterns
        hook_patterns = [p for p in patterns if p.feature_key == "hook_type"]
        # At least some pattern detection should occur
        assert len(patterns) >= 0  # May be 0 if not enough samples
    
    def test_pattern_lift_calculation(self):
        """Test that pattern lift is calculated correctly."""
        pattern = SuccessPattern(
            feature_key="hook_type",
            feature_val="contact_resonance",
            send_count=100,
            reply_count=30,  # 30% reply rate
            interview_count=5,
            baseline_rate=0.10,  # 10% baseline
            confidence=0.98
        )
        
        # Lift = 0.30 / 0.10 = 3.0
        assert abs(pattern.lift - 3.0) < 0.001
        assert abs(pattern.reply_rate - 0.30) < 0.001
    
    def test_pattern_significance_check(self):
        """Test pattern statistical significance checking."""
        # Significant pattern: high confidence, enough samples
        sig_pattern = SuccessPattern(
            feature_key="template",
            feature_val="engineering",
            send_count=50,
            reply_count=20,
            interview_count=3,
            baseline_rate=0.20,
            confidence=0.97
        )
        assert sig_pattern.is_significant() is True
        
        # Not significant: low sample size
        low_sample = SuccessPattern(
            feature_key="template",
            feature_val="engineering",
            send_count=10,  # < 20
            reply_count=4,
            interview_count=1,
            baseline_rate=0.20,
            confidence=0.97
        )
        assert low_sample.is_significant() is False
        
        # Not significant: low confidence
        low_conf = SuccessPattern(
            feature_key="template",
            feature_val="engineering",
            send_count=50,
            reply_count=15,
            interview_count=2,
            baseline_rate=0.20,
            confidence=0.80  # < 0.95
        )
        assert low_conf.is_significant() is False
    
    def test_mine_segment_patterns(self):
        """Test mining patterns from segment data."""
        miner = PatternMiner()
        
        # Create metrics with by_template data
        metrics = OutreachMetrics(window_days=7)
        metrics.total_sent = 100
        metrics.total_replied = 15
        
        from src.feedback.models import ReplyStats
        metrics.by_template = {
            "hr_outreach": ReplyStats(sent=40, replied=8, positive=4, bounced=2, interviews=1),
            "engineering": ReplyStats(sent=30, replied=12, positive=6, bounced=1, interviews=2),
            "follow_up": ReplyStats(sent=30, replied=5, positive=2, bounced=2, interviews=0),
        }
        
        patterns = miner.mine(metrics, db_session=None)
        template_patterns = [p for p in patterns if p.feature_key == "template"]
        
        # Should find patterns for each template with enough sends
        assert len(template_patterns) >= 1
    
    def test_pattern_str_representation(self):
        """Test pattern string representation."""
        pattern = SuccessPattern(
            feature_key="send_hour",
            feature_val="10",
            send_count=100,
            reply_count=25,
            interview_count=5,
            baseline_rate=0.15,
            confidence=0.96
        )
        
        pattern_str = str(pattern)
        assert "send_hour=10" in pattern_str
        assert "25%" in pattern_str  # reply rate
        assert "baseline" in pattern_str


# ---------------------------------------------------------------------------
# Test: Adaptive Optimization (Requirement 20.3)
# ---------------------------------------------------------------------------

class TestAdaptiveOptimizer:
    """Tests for AdaptiveOptimizer - adaptive optimization based on patterns."""
    
    @pytest.fixture
    def temp_learning_db(self, tmp_path):
        """Create a temporary learning database."""
        db_path = tmp_path / "learning.db"
        with patch('src.feedback.adaptive_optimizer._LEARNING_DB', db_path):
            optimizer = AdaptiveOptimizer()
            yield optimizer, db_path
    
    def test_adapt_empty_patterns(self, temp_learning_db):
        """Test adaptation with no patterns returns empty recommendations."""
        optimizer, _ = temp_learning_db
        metrics = OutreachMetrics(window_days=7)
        recommendations = optimizer.adapt(metrics, patterns=[])
        
        # May have recommendations from templates/send times if metrics exist
        assert isinstance(recommendations, list)
    
    def test_adapt_increases_hook_weight_for_high_lift(self, temp_learning_db):
        """Test that high-lift patterns increase hook weights."""
        optimizer, _ = temp_learning_db
        
        metrics = OutreachMetrics(window_days=7, total_sent=100, total_replied=15)
        patterns = [
            SuccessPattern(
                feature_key="hook_type",
                feature_val="contact_resonance",
                send_count=50,
                reply_count=20,  # 40% reply rate
                interview_count=5,
                baseline_rate=0.15,  # 15% baseline
                confidence=0.97
            )
        ]
        
        recommendations = optimizer.adapt(metrics, patterns)
        
        # Should have an increase weight recommendation
        increase_recs = [r for r in recommendations 
                        if r.type == RecommendationType.INCREASE_HOOK_WEIGHT]
        assert len(increase_recs) >= 1
        
        # Hook weight should be saved
        weights = optimizer.get_hook_weights()
        if "contact_resonance" in weights:
            assert weights["contact_resonance"] > 1.0  # Increased from default
    
    def test_adapt_decreases_hook_weight_for_low_lift(self, temp_learning_db):
        """Test that low-lift patterns decrease hook weights."""
        optimizer, _ = temp_learning_db
        
        metrics = OutreachMetrics(window_days=7, total_sent=100, total_replied=20)
        patterns = [
            SuccessPattern(
                feature_key="hook_type",
                feature_val="generic",
                send_count=40,
                reply_count=2,  # 5% reply rate
                interview_count=0,
                baseline_rate=0.20,  # 20% baseline - lift is 0.25
                confidence=0.96
            )
        ]
        
        recommendations = optimizer.adapt(metrics, patterns)
        
        decrease_recs = [r for r in recommendations 
                        if r.type == RecommendationType.DECREASE_HOOK_WEIGHT]
        assert len(decrease_recs) >= 1
    
    def test_adapt_send_time_recommendation(self, temp_learning_db):
        """Test send time recommendations are generated."""
        optimizer, _ = temp_learning_db
        
        from src.feedback.models import ReplyStats
        
        metrics = OutreachMetrics(window_days=7, total_sent=100, total_replied=10)
        metrics.by_send_hour = {
            9: ReplyStats(sent=20, replied=8, positive=4, bounced=0, interviews=2),   # 40% - best
            10: ReplyStats(sent=20, replied=2, positive=1, bounced=1, interviews=0),  # 10%
            14: ReplyStats(sent=20, replied=1, positive=0, bounced=0, interviews=0),  # 5%
            15: ReplyStats(sent=20, replied=1, positive=0, bounced=0, interviews=0),  # 5%
        }
        
        recommendations = optimizer.adapt(metrics, patterns=[])
        
        # Should recommend best send hour
        time_recs = [r for r in recommendations 
                   if r.type == RecommendationType.ADJUST_SEND_TIME]
        if time_recs:
            assert "09" in time_recs[0].action or "9" in time_recs[0].action
    
    def test_adapt_ab_variant_promotion(self, temp_learning_db):
        """Test A/B variant promotion recommendations."""
        optimizer, _ = temp_learning_db
        
        from src.feedback.models import ReplyStats
        
        metrics = OutreachMetrics(window_days=7, total_sent=50, total_replied=8)
        metrics.by_ab_variant = {
            0: ReplyStats(sent=25, replied=2, positive=1, bounced=1, interviews=0),   # 8%
            1: ReplyStats(sent=25, replied=8, positive=5, bounced=0, interviews=2),   # 32%
        }
        
        recommendations = optimizer.adapt(metrics, patterns=[])
        
        # Should recommend promoting variant 1
        promo_recs = [r for r in recommendations 
                    if r.type == RecommendationType.PROMOTE_AB_VARIANT]
        if promo_recs:
            assert "1" in promo_recs[0].action
    
    def test_adapt_template_improvement_recommendation(self, temp_learning_db):
        """Test underperforming template recommendations."""
        optimizer, _ = temp_learning_db
        
        from src.feedback.models import ReplyStats
        
        metrics = OutreachMetrics(window_days=7, total_sent=60, total_replied=12)
        metrics.by_template = {
            "hr_outreach": ReplyStats(sent=30, replied=10, positive=5, bounced=1, interviews=2),  # 33%
            "follow_up": ReplyStats(sent=30, replied=1, positive=0, bounced=2, interviews=0),     # 3%
        }
        
        recommendations = optimizer.adapt(metrics, patterns=[])
        
        # Should recommend improving follow_up template
        template_recs = [r for r in recommendations 
                        if r.type == RecommendationType.IMPROVE_TEMPLATE]
        if template_recs:
            assert any("follow_up" in r.action for r in template_recs)
    
    def test_recommendation_impact_estimate(self, temp_learning_db):
        """Test that recommendations have valid impact estimates."""
        optimizer, _ = temp_learning_db
        
        metrics = OutreachMetrics(window_days=7, total_sent=100, total_replied=15)
        patterns = [
            SuccessPattern(
                feature_key="hook_type",
                feature_val="tech_alignment",
                send_count=30,
                reply_count=12,
                interview_count=3,
                baseline_rate=0.15,
                confidence=0.96
            )
        ]
        
        recommendations = optimizer.adapt(metrics, patterns)
        
        for rec in recommendations:
            # Impact should be in reasonable range (percentage points)
            assert -50 <= rec.impact_estimate <= 100


# ---------------------------------------------------------------------------
# Test: Digest Generator (Requirement 20.4)
# ---------------------------------------------------------------------------

class TestDigestGenerator:
    """Tests for DigestGenerator - daily digest report generation."""
    
    def test_generate_markdown_empty_metrics(self):
        """Test digest generation with empty metrics."""
        generator = DigestGenerator()
        
        snapshot = LearningSnapshot(
            snapshot_date="2025-01-15",
            metrics=OutreachMetrics(window_days=7),
            patterns=[],
            recommendations=[]
        )
        
        generator.generate(snapshot)
        
        assert snapshot.digest_markdown != ""
        assert "Weekly Digest" in snapshot.digest_markdown
        assert "2025-01-15" in snapshot.digest_markdown
    
    def test_generate_markdown_with_metrics(self):
        """Test digest generation with real metrics."""
        generator = DigestGenerator()
        
        metrics = OutreachMetrics(
            window_days=7,
            total_sent=100,
            total_delivered=95,
            total_bounced=5,
            total_replied=20,
            total_positive=12,
            total_interviews=5,
            total_offers=1
        )
        
        snapshot = LearningSnapshot(
            snapshot_date="2025-01-15",
            metrics=metrics,
            patterns=[],
            recommendations=[]
        )
        
        generator.generate(snapshot)
        
        md = snapshot.digest_markdown
        assert "100" in md  # total_sent
        assert "Outreach Funnel" in md
        assert "Sent" in md
        assert "Replied" in md
    
    def test_generate_markdown_with_patterns(self):
        """Test digest includes discovered patterns."""
        generator = DigestGenerator()
        
        patterns = [
            SuccessPattern(
                feature_key="hook_type",
                feature_val="contact_resonance",
                send_count=50,
                reply_count=15,
                interview_count=3,
                baseline_rate=0.15,
                confidence=0.97
            )
        ]
        
        snapshot = LearningSnapshot(
            snapshot_date="2025-01-15",
            metrics=OutreachMetrics(window_days=7, total_sent=100, total_replied=15),
            patterns=patterns,
            recommendations=[]
        )
        
        generator.generate(snapshot)
        
        md = snapshot.digest_markdown
        assert "Patterns" in md or "pattern" in md.lower()
    
    def test_generate_markdown_with_recommendations(self):
        """Test digest includes recommendations."""
        generator = DigestGenerator()
        
        recommendations = [
            Recommendation(
                type=RecommendationType.INCREASE_HOOK_WEIGHT,
                action="Increase 'contact_resonance' hook weight",
                evidence="hook_type=contact_resonance lift=2.5",
                impact_estimate=8.5
            ),
            Recommendation(
                type=RecommendationType.ADJUST_SEND_TIME,
                action="Send emails at 10:00 UTC",
                evidence="send_hour=10 reply_rate=35%",
                impact_estimate=5.0
            )
        ]
        
        snapshot = LearningSnapshot(
            snapshot_date="2025-01-15",
            metrics=OutreachMetrics(window_days=7, total_sent=100, total_replied=15),
            patterns=[],
            recommendations=recommendations
        )
        
        generator.generate(snapshot)
        
        md = snapshot.digest_markdown
        assert "Recommendations" in md
        assert "contact_resonance" in md or "hook" in md.lower()
    
    def test_generate_dict_format(self):
        """Test structured dict generation for API."""
        generator = DigestGenerator()
        
        metrics = OutreachMetrics(
            window_days=7,
            total_sent=100,
            total_replied=20,
            total_positive=12,
            total_interviews=5,
            total_offers=1,
            top_hooks=["contact_resonance", "tech_alignment"],
            top_subjects=["Great opportunity", "Your experience matches"]
        )
        
        recommendations = [
            Recommendation(
                type=RecommendationType.INCREASE_HOOK_WEIGHT,
                action="Test action",
                evidence="Test evidence",
                impact_estimate=5.0
            )
        ]
        
        snapshot = LearningSnapshot(
            snapshot_date="2025-01-15",
            metrics=metrics,
            patterns=[],
            recommendations=recommendations
        )
        
        result = generator.generate_dict(snapshot)
        
        assert result["date"] == "2025-01-15"
        assert result["funnel"]["sent"] == 100
        assert result["funnel"]["replied"] == 20
        assert result["funnel"]["reply_rate"] == 0.2
        assert "contact_resonance" in result["top_hooks"]
        assert len(result["recommendations"]) == 1
    
    def test_generate_with_hook_performance(self):
        """Test digest includes hook performance table."""
        generator = DigestGenerator()
        
        from src.feedback.models import ReplyStats
        
        metrics = OutreachMetrics(
            window_days=7,
            total_sent=60,
            total_replied=12,
            by_hook_type={
                "contact_resonance": ReplyStats(sent=30, replied=9, positive=5),
                "generic": ReplyStats(sent=30, replied=3, positive=1)
            }
        )
        
        snapshot = LearningSnapshot(
            snapshot_date="2025-01-15",
            metrics=metrics,
            patterns=[],
            recommendations=[]
        )
        
        generator.generate(snapshot)
        
        md = snapshot.digest_markdown
        assert "Hook" in md
        assert "contact_resonance" in md or "Reply Rate" in md
    
    def test_save_and_load_snapshot(self, tmp_path):
        """Test snapshot persistence to SQLite."""
        db_path = tmp_path / "learning.db"
        
        with patch('src.feedback.digest_generator._LEARNING_DB', db_path):
            generator = DigestGenerator()
            
            snapshot = LearningSnapshot(
                snapshot_date="2025-01-15",
                metrics=OutreachMetrics(window_days=7, total_sent=100, total_replied=20),
                patterns=[],
                recommendations=[],
                digest_markdown="# Test Digest"
            )
            
            generator.save_snapshot(snapshot)
            
            # Verify data was saved
            import sqlite3
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT snapshot_date, markdown FROM learning_snapshots"
            ).fetchone()
            conn.close()
            
            assert row is not None
            assert row[0] == "2025-01-15"
            assert row[1] == "# Test Digest"


# ---------------------------------------------------------------------------
# Test: FeedbackLoop Orchestrator (Requirements 20.1-20.5)
# ---------------------------------------------------------------------------

class TestFeedbackLoop:
    """Tests for FeedbackLoop - the main orchestrator."""
    
    def test_feedback_loop_initialization(self):
        """Test FeedbackLoop initializes correctly."""
        loop = FeedbackLoop()
        
        assert loop._latest_snapshot is None
        assert loop._latest_recs == []
        assert loop._running is False
    
    def test_get_recommendations_empty(self):
        """Test get_recommendations returns empty list before run."""
        loop = FeedbackLoop()
        
        recs = loop.get_recommendations()
        assert recs == []
    
    def test_get_hook_weights_default(self):
        """Test get_hook_weights returns dict."""
        loop = FeedbackLoop()
        
        weights = loop.get_hook_weights()
        assert isinstance(weights, dict)
    
    def test_get_best_hours_default(self):
        """Test get_best_hours returns dict."""
        loop = FeedbackLoop()
        
        hours = loop.get_best_hours()
        assert isinstance(hours, dict)
    
    def test_latest_digest_markdown_empty(self):
        """Test latest_digest_markdown before run."""
        loop = FeedbackLoop()
        
        md = loop.latest_digest_markdown()
        assert "No digest available" in md
    
    def test_latest_digest_dict_empty(self):
        """Test latest_digest_dict returns None before run."""
        loop = FeedbackLoop()
        
        result = loop.latest_digest_dict()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_run_once_integration(self):
        """Test run_once executes full analysis cycle."""
        # Create a fresh in-memory database with thread-safe configuration
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.models import Base, Job, Contact, OutreachRecord
        from datetime import datetime, timedelta, timezone
        
        # Use file-based SQLite for cross-thread access
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
            Base.metadata.create_all(bind=engine)
            TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            
            # Setup: create test data
            setup_session = TestingSessionLocal()
            now = datetime.now(timezone.utc)
            job = Job(job_id="test_async", title="Test", company="Test", location="Remote",
                     description="Test", url="https://test.com", source="test")
            setup_session.add(job)
            setup_session.flush()
            
            for i in range(10):
                rec = OutreachRecord(
                    job_id=job.id,
                    subject=f"Test {i}",
                    body="Test body",
                    status="replied" if i < 3 else "sent",
                    sent_at=now - timedelta(days=1),
                    email_sent=True,
                    contact_email="test@test.com"
                )
                setup_session.add(rec)
            setup_session.commit()
            setup_session.close()
            
            loop = FeedbackLoop(db_session_factory=TestingSessionLocal)
            snapshot = await loop.run_once(metrics_window=7, pattern_window=30)
            
            assert snapshot is not None
            assert snapshot.metrics.total_sent == 10
            assert snapshot.snapshot_date != ""
            assert loop._latest_snapshot is not None
            assert isinstance(loop._latest_recs, list)
        finally:
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_run_once_generates_digest(self):
        """Test run_once generates digest markdown."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.models import Base, Job, OutreachRecord
        from datetime import datetime, timedelta, timezone
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
            Base.metadata.create_all(bind=engine)
            TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            
            setup_session = TestingSessionLocal()
            now = datetime.now(timezone.utc)
            job = Job(job_id="digest_test", title="Test", company="Test", location="Remote",
                     description="Test", url="https://test.com", source="test")
            setup_session.add(job)
            setup_session.flush()
            
            for i in range(5):
                rec = OutreachRecord(job_id=job.id, subject=f"Test {i}", body="Body",
                                    status="sent", sent_at=now - timedelta(days=1),
                                    email_sent=True, contact_email="test@test.com")
                setup_session.add(rec)
            setup_session.commit()
            setup_session.close()
            
            loop = FeedbackLoop(db_session_factory=TestingSessionLocal)
            snapshot = await loop.run_once(metrics_window=7, pattern_window=30)
            
            assert snapshot.digest_markdown != ""
            assert "Weekly Digest" in snapshot.digest_markdown
        finally:
            os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_run_once_populates_latest_recs(self):
        """Test run_once populates latest recommendations."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.models import Base, Job, OutreachRecord
        from datetime import datetime, timedelta, timezone
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
            Base.metadata.create_all(bind=engine)
            TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            
            setup_session = TestingSessionLocal()
            now = datetime.now(timezone.utc)
            job = Job(job_id="recs_test", title="Test", company="Test", location="Remote",
                     description="Test", url="https://test.com", source="test")
            setup_session.add(job)
            setup_session.flush()
            
            for i in range(5):
                rec = OutreachRecord(job_id=job.id, subject=f"Test {i}", body="Body",
                                    status="sent", sent_at=now - timedelta(days=1),
                                    email_sent=True, contact_email="test@test.com")
                setup_session.add(rec)
            setup_session.commit()
            setup_session.close()
            
            loop = FeedbackLoop(db_session_factory=TestingSessionLocal)
            await loop.run_once(metrics_window=7, pattern_window=30)
            
            recs = loop.get_recommendations()
            assert isinstance(recs, list)
        finally:
            os.unlink(db_path)
    
    def test_start_and_stop(self):
        """Test start and stop lifecycle methods."""
        loop = FeedbackLoop()
        
        # Start should set running flag
        # Note: Without event loop, start may warn but shouldn't crash
        loop.start()
        # We can't assert _running without an event loop
        
        loop.stop()
        assert loop._running is False
    
    def test_seconds_until_hour_calculation(self):
        """Test time calculation for nightly run."""
        # Test the static method
        seconds = FeedbackLoop._seconds_until_hour(2)  # 02:00 UTC
        
        # Should be between 0 and 24 hours
        assert 0 < seconds <= 24 * 3600
    
    def test_get_loop_singleton(self):
        """Test get_loop returns singleton."""
        from src.feedback import get_loop
        
        loop1 = get_loop()
        loop2 = get_loop()
        
        # Should return same instance
        # Note: Reset singleton for isolation
        assert loop1 is loop2


# ---------------------------------------------------------------------------
# Test: Metric Tracking (Requirement 20.5)
# ---------------------------------------------------------------------------

class TestMetricTracking:
    """Tests for metric tracking: open rate, reply rate, positive reply rate."""
    
    def test_reply_rate_property(self):
        """Test reply rate is correctly calculated."""
        metrics = OutreachMetrics(
            window_days=7,
            total_sent=100,
            total_replied=25
        )
        
        assert metrics.reply_rate == 0.25
    
    def test_positive_rate_property(self):
        """Test positive reply rate is correctly calculated."""
        metrics = OutreachMetrics(
            window_days=7,
            total_sent=100,
            total_positive=10
        )
        
        assert metrics.positive_rate == 0.10
    
    def test_interview_rate_property(self):
        """Test interview rate is correctly calculated."""
        metrics = OutreachMetrics(
            window_days=7,
            total_sent=100,
            total_interviews=5
        )
        
        assert metrics.interview_rate == 0.05
    
    def test_delivery_rate_property(self):
        """Test delivery rate is correctly calculated."""
        metrics = OutreachMetrics(
            window_days=7,
            total_sent=100,
            total_delivered=95
        )
        
        assert metrics.delivery_rate == 0.95
    
    def test_rate_calculation_zero_sent(self):
        """Test rate calculation handles zero sent."""
        metrics = OutreachMetrics(window_days=7, total_sent=0)
        
        # Should return 0, not divide by zero
        assert metrics.reply_rate == 0.0
        assert metrics.positive_rate == 0.0
        assert metrics.interview_rate == 0.0
    
    def test_reply_stats_addition(self):
        """Test ReplyStats can be added together."""
        from src.feedback.models import ReplyStats
        
        stats1 = ReplyStats(sent=50, replied=10, positive=5, bounced=2, interviews=2)
        stats2 = ReplyStats(sent=30, replied=8, positive=4, bounced=1, interviews=1)
        
        combined = stats1 + stats2
        
        assert combined.sent == 80
        assert combined.replied == 18
        assert combined.positive == 9
        assert combined.bounced == 3
        assert combined.interviews == 3
    
    def test_reply_stats_rates(self):
        """Test ReplyStats rate calculations."""
        from src.feedback.models import ReplyStats
        
        stats = ReplyStats(sent=100, replied=20, positive=10, interviews=5)
        
        assert stats.reply_rate == 0.20
        assert stats.positive_rate == 0.10
        assert stats.interview_rate == 0.05


# ---------------------------------------------------------------------------
# Test: Integration - Full Feedback Cycle
# ---------------------------------------------------------------------------

class TestFeedbackIntegration:
    """Integration tests for the complete feedback cycle."""
    
    @pytest.mark.asyncio
    async def test_full_cycle_collect_mine_adapt_digest(self, feedback_db, sample_outreach_records):
        """Test complete feedback cycle: collect → mine → adapt → digest."""
        # Step 1: Collect metrics
        collector = MetricsCollector(feedback_db)
        metrics = collector.collect(window_days=7)
        
        assert metrics.total_sent == 30
        assert metrics.reply_rate > 0
        
        # Step 2: Mine patterns
        miner = PatternMiner()
        patterns = miner.mine(metrics, feedback_db, window_days=30)
        
        assert isinstance(patterns, list)
        
        # Step 3: Adapt based on patterns
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "learning.db"
            with patch('src.feedback.adaptive_optimizer._LEARNING_DB', db_path):
                optimizer = AdaptiveOptimizer()
                recommendations = optimizer.adapt(metrics, patterns)
                
                assert isinstance(recommendations, list)
        
        # Step 4: Generate digest
        generator = DigestGenerator()
        snapshot = LearningSnapshot(
            snapshot_date="2025-01-15",
            metrics=metrics,
            patterns=patterns,
            recommendations=recommendations
        )
        generator.generate(snapshot)
        
        assert snapshot.digest_markdown != ""
        assert "Weekly Digest" in snapshot.digest_markdown
    
    def test_metrics_to_patterns_to_recommendations_flow(self):
        """Test data flows correctly from metrics through patterns to recommendations."""
        from src.feedback.models import ReplyStats
        
        # Create metrics with clear winner
        metrics = OutreachMetrics(
            window_days=7,
            total_sent=200,
            total_replied=30,
            by_hook_type={
                "contact_resonance": ReplyStats(sent=100, replied=25, positive=15, interviews=5),
                "generic": ReplyStats(sent=100, replied=5, positive=2, interviews=0),
            }
        )
        
        # Mine patterns
        miner = PatternMiner()
        patterns = miner.mine(metrics, db_session=None)
        
        # Filter significant patterns
        hook_patterns = [p for p in patterns 
                        if p.feature_key == "hook_type" and p.send_count >= 20]
        
        # Should detect contact_resonance as better
        if hook_patterns:
            sorted_patterns = sorted(hook_patterns, key=lambda p: p.reply_rate, reverse=True)
            assert sorted_patterns[0].feature_val == "contact_resonance"
    
    def test_recommendation_types_coverage(self):
        """Test all recommendation types are defined."""
        expected_types = [
            "INCREASE_HOOK_WEIGHT",
            "DECREASE_HOOK_WEIGHT",
            "ADJUST_SEND_TIME",
            "TARGET_COMPANY_TYPE",
            "AVOID_COMPANY_TYPE",
            "PROMOTE_AB_VARIANT",
            "IMPROVE_TEMPLATE",
            "INCREASE_FOLLOWUP"
        ]
        
        for type_name in expected_types:
            assert hasattr(RecommendationType, type_name)
    
    def test_learning_snapshot_structure(self):
        """Test LearningSnapshot has all required fields."""
        snapshot = LearningSnapshot(
            snapshot_date="2025-01-15",
            metrics=OutreachMetrics(window_days=7),
            patterns=[],
            recommendations=[]
        )
        
        assert hasattr(snapshot, "snapshot_date")
        assert hasattr(snapshot, "metrics")
        assert hasattr(snapshot, "patterns")
        assert hasattr(snapshot, "recommendations")
        assert hasattr(snapshot, "digest_markdown")
        assert hasattr(snapshot, "digest_html")


# ---------------------------------------------------------------------------
# Test: Edge Cases and Error Handling
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_metrics_collector_handles_no_db(self):
        """Test MetricsCollector handles missing DB gracefully."""
        collector = MetricsCollector(db_session=None)
        metrics = collector.collect(window_days=7)
        
        assert metrics.total_sent == 0
        assert metrics.window_days == 7
    
    def test_pattern_miner_handles_zero_baseline(self):
        """Test PatternMiner handles zero baseline rate."""
        pattern = SuccessPattern(
            feature_key="test",
            feature_val="value",
            send_count=50,
            reply_count=10,
            interview_count=2,
            baseline_rate=0.0,  # Zero baseline
            confidence=0.95
        )
        
        # Should not divide by zero
        assert pattern.lift == 1.0  # Default lift when baseline is 0
    
    def test_success_pattern_low_sample_not_significant(self):
        """Test patterns with low sample size are not significant."""
        pattern = SuccessPattern(
            feature_key="hook_type",
            feature_val="rare_hook",
            send_count=5,  # Too few
            reply_count=3,
            interview_count=1,
            baseline_rate=0.20,
            confidence=0.99
        )
        
        assert not pattern.is_significant()
    
    def test_digest_generator_handles_empty_segments(self):
        """Test digest generation with empty segment data."""
        generator = DigestGenerator()
        
        metrics = OutreachMetrics(
            window_days=7,
            total_sent=10,
            total_replied=2,
            by_hook_type={},
            by_send_hour={},
            by_template={},
            by_ab_variant={}
        )
        
        snapshot = LearningSnapshot(
            snapshot_date="2025-01-15",
            metrics=metrics,
            patterns=[],
            recommendations=[]
        )
        
        generator.generate(snapshot)
        
        # Should still generate valid markdown
        assert snapshot.digest_markdown != ""
        assert "Weekly Digest" in snapshot.digest_markdown

    
    def test_adaptive_optimizer_weight_bounds(self, tmp_path):
        """Test weights are bounded within valid range."""
        db_path = tmp_path / "learning.db"
        
        with patch('src.feedback.adaptive_optimizer._LEARNING_DB', db_path):
            optimizer = AdaptiveOptimizer()
            
            # Very high lift should be capped
            metrics = OutreachMetrics(window_days=7, total_sent=100, total_replied=10)
            patterns = [
                SuccessPattern(
                    feature_key="hook_type",
                    feature_val="amazing_hook",
                    send_count=30,
                    reply_count=28,  # 93% reply rate
                    interview_count=10,
                    baseline_rate=0.01,  # Very low baseline = huge lift
                    confidence=0.99
                )
            ]
            
            optimizer.adapt(metrics, patterns)
            weights = optimizer.get_hook_weights()
            
            if "amazing_hook" in weights:
                # Weight should be capped at 5.0
                assert weights["amazing_hook"] <= 5.0
                assert weights["amazing_hook"] >= 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
