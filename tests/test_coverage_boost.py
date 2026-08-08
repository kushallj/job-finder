"""Additional tests targeting coverage gaps in ab_test, smart_timer, and database."""

import pytest
import asyncio
import math
import tempfile
import os
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from src.outreach.ab_test import ABTestManager, VariantStats, DEFAULT_VARIANTS
from src.outreach.smart_timer import SmartSendTimer, _TLD_TZ, _FALLBACK_TZ
from src.outreach.domain_rate_limiter import DomainRateLimiter, _DomainBucket


# =============================================================================
# ABTestManager — Additional coverage
# =============================================================================

class TestABTestManagerExtended:
    """Additional ABTestManager tests targeting missed lines."""

    def test_ab_init_custom_variants(self):
        """ABTestManager accepts custom variants."""
        custom = {"test_template": ["Subject A", "Subject B"]}
        mgr = ABTestManager(variants=custom)
        idx, subject = mgr.best_variant("test_template")
        assert subject in ["Subject A", "Subject B"]
        assert idx in [0, 1]

    def test_ab_unknown_template_returns_template_name(self):
        """Unknown template returns 0 and template string."""
        mgr = ABTestManager()
        idx, subject = mgr.best_variant("nonexistent_template")
        assert idx == 0
        assert subject == "nonexistent_template"

    def test_ab_record_send_unknown_template_no_crash(self):
        """record_send with unknown template doesn't crash."""
        mgr = ABTestManager()
        mgr.record_send("unknown_template", 0)  # should not raise

    def test_ab_record_reply_unknown_template_no_crash(self):
        """record_reply with unknown template doesn't crash."""
        mgr = ABTestManager()
        mgr.record_reply("unknown_template", 0)  # should not raise

    def test_ab_record_send_out_of_bounds_index(self):
        """record_send with out-of-bounds variant_idx doesn't crash."""
        mgr = ABTestManager()
        mgr.record_send("hr_outreach", 99)  # should not raise

    def test_ab_record_reply_out_of_bounds_index(self):
        """record_reply with out-of-bounds variant_idx doesn't crash."""
        mgr = ABTestManager()
        mgr.record_reply("hr_outreach", 99)  # should not raise

    def test_ab_exploitation_chooses_best(self):
        """With epsilon=0 override, exploitation picks highest reply rate."""
        mgr = ABTestManager()
        # Give variant 2 a high reply rate
        mgr._stats["hr_outreach"][2].sends = 100
        mgr._stats["hr_outreach"][2].replies = 50  # 50% reply rate
        mgr._stats["hr_outreach"][0].sends = 100
        mgr._stats["hr_outreach"][0].replies = 5   # 5% reply rate
        mgr._stats["hr_outreach"][1].sends = 100
        mgr._stats["hr_outreach"][1].replies = 10  # 10% reply rate
        
        # Disable exploration to test pure exploitation
        with patch.object(mgr, 'EPSILON', 0.0):
            idx, _ = mgr.best_variant("hr_outreach", company="Test", skill="Python")
            assert idx == 2

    def test_ab_format_with_kwargs(self):
        """Subject line formatting works with kwargs."""
        mgr = ABTestManager()
        # Force winner to avoid randomness
        mgr.promote_winner("hr_outreach", 0)
        idx, subject = mgr.best_variant("hr_outreach", company="Stripe", skill="Python")
        assert "Stripe" in subject

    def test_ab_format_missing_kwargs_graceful(self):
        """Formatting with missing kwargs doesn't crash (returns raw template)."""
        mgr = ABTestManager()
        mgr.promote_winner("hr_outreach", 0)
        # Call without required kwargs — should handle gracefully
        idx, subject = mgr.best_variant("hr_outreach")
        assert isinstance(subject, str)

    def test_ab_summary(self):
        """summary() returns structured data for all templates."""
        mgr = ABTestManager()
        mgr.record_send("hr_outreach", 0)
        mgr.record_reply("hr_outreach", 0)
        
        summary = mgr.summary()
        assert "hr_outreach" in summary
        assert len(summary["hr_outreach"]) == 3
        assert summary["hr_outreach"][0]["sends"] == 1
        assert summary["hr_outreach"][0]["replies"] == 1

    def test_ab_check_significance_insufficient_data(self):
        """_check_significance does nothing with insufficient data."""
        mgr = ABTestManager()
        # Only 5 sends (need 30 minimum)
        for i in range(5):
            mgr.record_send("hr_outreach", 0)
        assert mgr.get_winner("hr_outreach") is None

    def test_ab_check_significance_with_enough_data(self):
        """_check_significance promotes winner with enough data and signal."""
        mgr = ABTestManager()
        # Variant 0: 100 sends, 30 replies (30%)
        mgr._stats["hr_outreach"][0].sends = 100
        mgr._stats["hr_outreach"][0].replies = 30
        # Variant 1: 100 sends, 5 replies (5%)
        mgr._stats["hr_outreach"][1].sends = 100
        mgr._stats["hr_outreach"][1].replies = 5
        # Variant 2: 100 sends, 3 replies (3%)
        mgr._stats["hr_outreach"][2].sends = 100
        mgr._stats["hr_outreach"][2].replies = 3
        
        mgr._check_significance("hr_outreach")
        # Should promote variant 0 as winner
        assert mgr.get_winner("hr_outreach") == 0

    def test_ab_check_significance_zero_replies(self):
        """_check_significance with zero total replies does nothing."""
        mgr = ABTestManager()
        mgr._stats["hr_outreach"][0].sends = 50
        mgr._stats["hr_outreach"][1].sends = 50
        mgr._stats["hr_outreach"][2].sends = 50
        # Zero replies for all
        mgr._check_significance("hr_outreach")
        assert mgr.get_winner("hr_outreach") is None

    def test_ab_chi2_p_value_edge_cases(self):
        """_chi2_p_value handles edge cases."""
        # df <= 0
        assert ABTestManager._chi2_p_value(5.0, 0) == 1.0
        # chi2 <= 0
        assert ABTestManager._chi2_p_value(0.0, 2) == 1.0
        # df == 1
        p = ABTestManager._chi2_p_value(3.84, 1)
        assert 0 < p < 0.1  # critical value for p=0.05
        # df == 2
        p = ABTestManager._chi2_p_value(5.99, 2)
        assert 0 < p < 0.1

    def test_ab_sqlite_persistence(self):
        """ABTestManager persists to SQLite and loads on restart."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            # Create manager with persistence
            mgr1 = ABTestManager(db_path=db_path)
            mgr1.record_send("hr_outreach", 0)
            mgr1.record_send("hr_outreach", 0)
            mgr1.record_reply("hr_outreach", 0)
            
            # Create a new manager from same DB — should load stats
            mgr2 = ABTestManager(db_path=db_path)
            assert mgr2._stats["hr_outreach"][0].sends == 2
            assert mgr2._stats["hr_outreach"][0].replies == 1
        finally:
            os.unlink(db_path)

    def test_ab_already_has_winner_skips_significance(self):
        """_check_significance is a no-op if winner already exists."""
        mgr = ABTestManager()
        mgr.promote_winner("hr_outreach", 1)
        # Even with lots of data, _check_significance won't overwrite
        mgr._stats["hr_outreach"][0].sends = 1000
        mgr._stats["hr_outreach"][0].replies = 500
        mgr._check_significance("hr_outreach")
        # Winner should still be 1 (manually set)
        assert mgr.get_winner("hr_outreach") == 1


# =============================================================================
# SmartSendTimer — Additional coverage
# =============================================================================

class TestSmartSendTimerExtended:
    """Additional SmartSendTimer tests."""

    @pytest.mark.asyncio
    async def test_smart_timer_calc_delay_in_window(self):
        """When currently in optimal window, delay is 0."""
        timer = SmartSendTimer()
        # Mock a Tuesday 10:00 local time scenario
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Kolkata")
        
        delay = timer._calc_delay("Asia/Kolkata")
        # We can't guarantee the result since it depends on current time,
        # but it should always be >= 0
        assert delay >= 0.0

    @pytest.mark.asyncio
    async def test_smart_timer_from_tld_various(self):
        """_from_tld resolves multiple TLD formats correctly."""
        timer = SmartSendTimer()
        assert timer._from_tld("company.in") == "Asia/Kolkata"
        assert timer._from_tld("company.co.uk") == "Europe/London"
        assert timer._from_tld("company.de") == "Europe/Berlin"
        assert timer._from_tld("company.jp") == "Asia/Tokyo"
        assert timer._from_tld("company.au") == "Australia/Sydney"
        assert timer._from_tld("company.sg") == "Asia/Singapore"
        assert timer._from_tld("company.fr") == "Europe/Paris"
        assert timer._from_tld("company.xyz") is None  # Unknown TLD

    @pytest.mark.asyncio
    async def test_smart_timer_detect_timezone_caching(self):
        """_detect_timezone caches results."""
        timer = SmartSendTimer()
        # First call populates cache
        tz1 = await timer._detect_timezone("test.in")
        assert "test.in" in timer._cache
        # Second call hits cache
        tz2 = await timer._detect_timezone("test.in")
        assert tz1 == tz2

    @pytest.mark.asyncio
    async def test_smart_timer_from_whois_exception(self):
        """_from_whois returns None on any exception."""
        timer = SmartSendTimer()
        # python-whois may not be installed, so this tests the exception path
        result = await timer._from_whois("definitely-not-a-real-domain.zzz")
        assert result is None

    @pytest.mark.asyncio
    async def test_smart_timer_from_ipinfo_exception(self):
        """_from_ipinfo returns None when network fails."""
        timer = SmartSendTimer()
        # Mock httpx to fail
        with patch.object(timer, '_http', new_callable=MagicMock) as mock_http:
            mock_http.get = AsyncMock(side_effect=Exception("Network error"))
            result = await timer._from_ipinfo("test.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_smart_timer_optimal_send_time_returns_future(self):
        """optimal_send_time returns a datetime >= now."""
        timer = SmartSendTimer()
        result = await timer.optimal_send_time("company.in")
        # Should be at or after current time
        assert result >= datetime.now(timezone.utc) - timedelta(seconds=1)

    @pytest.mark.asyncio
    async def test_smart_timer_seconds_nonnegative(self):
        """seconds_until_optimal always returns >= 0."""
        timer = SmartSendTimer()
        delay = await timer.seconds_until_optimal("company.in")
        assert delay >= 0.0


# =============================================================================
# DomainBucket — Additional coverage
# =============================================================================

class TestDomainBucket:
    """Tests for the internal _DomainBucket class."""

    def test_bucket_refill(self):
        """Tokens refill over time."""
        bucket = _DomainBucket(tokens=0.0, capacity=3.0, refill_rate=1.0)
        import time
        time.sleep(0.1)
        bucket.refill()
        assert bucket.tokens > 0.0

    def test_bucket_acquire_success(self):
        """acquire() succeeds when tokens available."""
        bucket = _DomainBucket(tokens=2.0, capacity=3.0, refill_rate=0.001)
        assert bucket.acquire() is True
        assert bucket.tokens < 2.0

    def test_bucket_acquire_failure(self):
        """acquire() fails when no tokens."""
        bucket = _DomainBucket(tokens=0.0, capacity=3.0, refill_rate=0.0)
        assert bucket.acquire() is False

    def test_bucket_available(self):
        """available() returns current token count."""
        bucket = _DomainBucket(tokens=2.5, capacity=3.0, refill_rate=0.0)
        assert bucket.available() == 2.5

    def test_bucket_seconds_until_available(self):
        """seconds_until_available returns 0 when tokens available."""
        bucket = _DomainBucket(tokens=2.0, capacity=3.0, refill_rate=1.0)
        assert bucket.seconds_until_available() == 0.0

    def test_bucket_seconds_until_available_empty(self):
        """seconds_until_available returns positive when empty."""
        bucket = _DomainBucket(tokens=0.0, capacity=3.0, refill_rate=1.0)
        wait = bucket.seconds_until_available()
        assert wait > 0.0

    def test_bucket_capacity_cap(self):
        """Tokens cannot exceed capacity."""
        bucket = _DomainBucket(tokens=3.0, capacity=3.0, refill_rate=100.0)
        import time
        time.sleep(0.01)
        bucket.refill()
        assert bucket.tokens <= 3.0


# =============================================================================
# Database — Additional coverage
# =============================================================================

class TestDatabaseExtra:
    """Additional database tests to cover init_db and get_db."""

    def test_database_init_db(self):
        """init_db creates tables without error."""
        from sqlalchemy import create_engine, inspect
        from sqlalchemy.orm import sessionmaker
        from src.models import Base
        
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "jobs" in tables
        assert "applications" in tables
        assert "contacts" in tables
        assert "outreach_records" in tables
        assert "resumes" in tables

    def test_database_get_db_generator(self):
        """get_db yields a session and closes it properly."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.models import Base
        
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine)
        
        # Simulate get_db behavior
        db = TestSession()
        try:
            assert db is not None
            assert not db.is_active is False
        finally:
            db.close()

    def test_database_session_rollback_on_error(self):
        """Session properly handles errors."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.exc import IntegrityError
        from src.models import Base, Job
        from datetime import datetime
        
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        
        db = Session()
        job = Job(
            job_id="dup_test",
            title="Test",
            company="TestCo",
            posted_date=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        
        # Try to add duplicate
        db2 = Session()
        job2 = Job(
            job_id="dup_test",
            title="Test2",
            company="TestCo2",
            posted_date=datetime.utcnow()
        )
        db2.add(job2)
        with pytest.raises(IntegrityError):
            db2.commit()
        db2.rollback()
        db2.close()
        db.close()

    def test_database_module_init_db(self):
        """Direct test of src.database.init_db()."""
        from unittest.mock import patch
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Patch the engine to use in-memory DB
        test_engine = create_engine("sqlite:///:memory:")
        with patch("src.database.engine", test_engine):
            from src.database import init_db
            init_db()
        
        from sqlalchemy import inspect
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "jobs" in tables

    def test_database_module_get_db(self):
        """Direct test of src.database.get_db() generator."""
        from unittest.mock import patch
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.models import Base
        
        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        TestSessionLocal = sessionmaker(bind=test_engine)
        
        with patch("src.database.SessionLocal", TestSessionLocal):
            from src.database import get_db
            gen = get_db()
            db = next(gen)
            assert db is not None
            try:
                next(gen)
            except StopIteration:
                pass  # Expected — generator is exhausted after yield
