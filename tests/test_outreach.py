"""
Comprehensive unit tests for outreach sub-modules:
- src.outreach.ab_test (ABTestManager, VariantStats, DEFAULT_VARIANTS)
- src.outreach.domain_rate_limiter (DomainRateLimiter)
- src.outreach.smart_timer (SmartSendTimer)
"""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.outreach.ab_test import ABTestManager, VariantStats, DEFAULT_VARIANTS
from src.outreach.domain_rate_limiter import DomainRateLimiter
from src.outreach.smart_timer import SmartSendTimer


# ===========================================================================
# ABTestManager Tests
# ===========================================================================


class TestABDefaultVariants:
    """Tests for DEFAULT_VARIANTS structure."""

    def test_ab_default_variants_exist(self):
        """Verify all 4 template keys exist with 3 variants each."""
        expected_keys = {"hr_outreach", "engineering_manager", "follow_up_1", "follow_up_2"}
        assert set(DEFAULT_VARIANTS.keys()) == expected_keys
        for key in expected_keys:
            assert len(DEFAULT_VARIANTS[key]) == 3, (
                f"Template '{key}' should have 3 variants, got {len(DEFAULT_VARIANTS[key])}"
            )


class TestVariantStats:
    """Tests for VariantStats dataclass."""

    def test_ab_variant_stats_default(self):
        """New VariantStats has sends=0, replies=0, reply_rate=0.0."""
        stats = VariantStats()
        assert stats.sends == 0
        assert stats.replies == 0
        assert stats.winner is False
        assert stats.reply_rate == 0.0

    def test_ab_reply_rate_calculation(self):
        """5 sends, 2 replies → reply_rate = 0.4."""
        stats = VariantStats(sends=5, replies=2)
        assert stats.reply_rate == pytest.approx(0.4)

    def test_ab_reply_rate_zero_sends(self):
        """Zero sends should yield 0.0 reply rate (no division by zero)."""
        stats = VariantStats(sends=0, replies=0)
        assert stats.reply_rate == 0.0


class TestABTestManager:
    """Tests for ABTestManager functionality."""

    def test_ab_best_variant_returns_tuple(self):
        """best_variant returns (int, str) tuple."""
        mgr = ABTestManager()
        result = mgr.best_variant("hr_outreach", company="Test", skill="Python")
        assert isinstance(result, tuple)
        assert len(result) == 2
        idx, subject = result
        assert isinstance(idx, int)
        assert isinstance(subject, str)
        assert 0 <= idx < 3

    def test_ab_record_send_increments(self):
        """record_send increments the sends counter for the specified variant."""
        mgr = ABTestManager()
        initial_sends = mgr._stats["hr_outreach"][0].sends
        mgr.record_send("hr_outreach", 0)
        assert mgr._stats["hr_outreach"][0].sends == initial_sends + 1

    def test_ab_record_reply_increments(self):
        """record_reply increments the replies counter for the specified variant."""
        mgr = ABTestManager()
        initial_replies = mgr._stats["hr_outreach"][1].replies
        mgr.record_reply("hr_outreach", 1)
        assert mgr._stats["hr_outreach"][1].replies == initial_replies + 1

    def test_ab_promote_winner(self):
        """After promote_winner(template, 1), best_variant always returns index 1."""
        mgr = ABTestManager()
        mgr.promote_winner("hr_outreach", 1)
        # Run multiple times to confirm it's deterministic
        for _ in range(20):
            idx, subject = mgr.best_variant("hr_outreach", company="Acme", skill="Go")
            assert idx == 1

    def test_ab_get_winner_none(self):
        """Before promotion, get_winner returns None."""
        mgr = ABTestManager()
        assert mgr.get_winner("hr_outreach") is None
        assert mgr.get_winner("engineering_manager") is None
        assert mgr.get_winner("follow_up_1") is None
        assert mgr.get_winner("follow_up_2") is None

    def test_ab_get_winner_after_promote(self):
        """After promotion, get_winner returns the promoted index."""
        mgr = ABTestManager()
        mgr.promote_winner("engineering_manager", 2)
        assert mgr.get_winner("engineering_manager") == 2

    def test_ab_best_variant_formats_subject(self):
        """best_variant formats the subject line with provided kwargs."""
        mgr = ABTestManager()
        mgr.promote_winner("hr_outreach", 0)
        idx, subject = mgr.best_variant("hr_outreach", company="Stripe", skill="Python")
        assert "Stripe" in subject

    def test_ab_record_send_invalid_template(self):
        """record_send with unknown template does not raise."""
        mgr = ABTestManager()
        # Should not raise
        mgr.record_send("nonexistent_template", 0)

    def test_ab_record_reply_invalid_template(self):
        """record_reply with unknown template does not raise."""
        mgr = ABTestManager()
        # Should not raise
        mgr.record_reply("nonexistent_template", 0)


# ===========================================================================
# DomainRateLimiter Tests
# ===========================================================================


class TestDomainRateLimiter:
    """Tests for DomainRateLimiter async functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_first_email(self):
        """First email to a new contact should be allowed."""
        limiter = DomainRateLimiter()
        allowed, reason = await limiter.check("user@test.com")
        assert allowed is True
        assert reason == ""

    @pytest.mark.asyncio
    async def test_rate_limiter_global_limit(self):
        """After 50 emails are consumed, the 51st should be blocked (global limit)."""
        limiter = DomainRateLimiter(global_daily_limit=50)
        # Consume 50 emails to different contacts/domains
        for i in range(50):
            email = f"user{i}@domain{i}.com"
            allowed, reason = await limiter.check(email)
            assert allowed is True, f"Email {i} should be allowed"
            await limiter.consume(email)

        # 51st email should be blocked
        allowed, reason = await limiter.check("user51@domain51.com")
        assert allowed is False
        assert "Global daily limit" in reason

    @pytest.mark.asyncio
    async def test_rate_limiter_domain_limit(self):
        """After 3 emails to same domain, the 4th should be blocked."""
        limiter = DomainRateLimiter(domain_weekly_limit=3)
        # Send 3 to same domain, different contacts
        for i in range(3):
            email = f"user{i}@example.com"
            allowed, reason = await limiter.check(email)
            assert allowed is True, f"Email {i} to example.com should be allowed"
            await limiter.consume(email)

        # 4th to same domain should be blocked
        allowed, reason = await limiter.check("user4@example.com")
        assert allowed is False
        assert "Domain limit" in reason

    @pytest.mark.asyncio
    async def test_rate_limiter_contact_limit(self):
        """After 1 email to same contact, the 2nd should be blocked."""
        limiter = DomainRateLimiter(contact_weekly_limit=1)
        email = "john@stripe.com"

        allowed, reason = await limiter.check(email)
        assert allowed is True
        await limiter.consume(email)

        # Same contact again → blocked
        allowed, reason = await limiter.check(email)
        assert allowed is False
        assert "already emailed" in reason

    @pytest.mark.asyncio
    async def test_rate_limiter_consume(self):
        """After consume, available tokens decrease."""
        limiter = DomainRateLimiter()
        email = "dev@company.com"

        # Check global tokens before
        global_before = limiter._global.available()
        await limiter.consume(email)
        global_after = limiter._global.available()

        assert global_after < global_before

    @pytest.mark.asyncio
    async def test_rate_limiter_different_domains_ok(self):
        """Different domains don't interfere with each other's limits."""
        limiter = DomainRateLimiter(domain_weekly_limit=3)

        # Send 3 to domain-a.com (exhaust its limit)
        for i in range(3):
            email = f"user{i}@domain-a.com"
            await limiter.consume(email)

        # domain-a.com should be blocked now
        allowed, _ = await limiter.check("user4@domain-a.com")
        assert allowed is False

        # domain-b.com should still be allowed
        allowed, reason = await limiter.check("user0@domain-b.com")
        assert allowed is True
        assert reason == ""

    @pytest.mark.asyncio
    async def test_rate_limiter_stats(self):
        """Stats tracking works correctly."""
        limiter = DomainRateLimiter()
        email = "test@example.com"
        await limiter.consume(email)
        stats = limiter.stats()
        assert stats["total_allowed"] == 1
        assert stats["active_domains"] >= 1
        assert stats["active_contacts"] >= 1


# ===========================================================================
# SmartSendTimer Tests
# ===========================================================================


class TestSmartSendTimer:
    """Tests for SmartSendTimer async functionality."""

    @pytest.mark.asyncio
    async def test_smart_timer_tld_india(self):
        """Domain 'company.in' should resolve to timezone 'Asia/Kolkata'."""
        timer = SmartSendTimer()
        try:
            tz = timer._from_tld("company.in")
            assert tz == "Asia/Kolkata"
        finally:
            await timer.close()

    @pytest.mark.asyncio
    async def test_smart_timer_tld_uk(self):
        """Domain 'company.co.uk' should resolve to timezone 'Europe/London'."""
        timer = SmartSendTimer()
        try:
            tz = timer._from_tld("company.co.uk")
            assert tz == "Europe/London"
        finally:
            await timer.close()

    @pytest.mark.asyncio
    async def test_smart_timer_tld_com(self):
        """Domain 'stripe.com' should resolve to 'America/New_York'."""
        timer = SmartSendTimer()
        try:
            tz = timer._from_tld("stripe.com")
            assert tz == "America/New_York"
        finally:
            await timer.close()

    @pytest.mark.asyncio
    async def test_smart_timer_returns_non_negative(self):
        """seconds_until_optimal always returns >= 0."""
        timer = SmartSendTimer()
        try:
            with patch.object(timer, "_from_whois", new_callable=AsyncMock, return_value=None):
                with patch.object(timer, "_from_ipinfo", new_callable=AsyncMock, return_value=None):
                    delay = await timer.seconds_until_optimal("company.in")
                    assert delay >= 0.0
        finally:
            await timer.close()

    @pytest.mark.asyncio
    async def test_smart_timer_fallback_timezone(self):
        """Unknown TLD should fall back to 'Asia/Kolkata'."""
        timer = SmartSendTimer()
        try:
            with patch.object(timer, "_from_whois", new_callable=AsyncMock, return_value=None):
                with patch.object(timer, "_from_ipinfo", new_callable=AsyncMock, return_value=None):
                    tz = await timer._detect_timezone("company.xyz")
                    assert tz == "Asia/Kolkata"
        finally:
            await timer.close()

    @pytest.mark.asyncio
    async def test_smart_timer_optimal_send_time_returns_datetime(self):
        """optimal_send_time returns a datetime object."""
        from datetime import datetime

        timer = SmartSendTimer()
        try:
            with patch.object(timer, "_from_whois", new_callable=AsyncMock, return_value=None):
                with patch.object(timer, "_from_ipinfo", new_callable=AsyncMock, return_value=None):
                    result = await timer.optimal_send_time("company.in")
                    assert isinstance(result, datetime)
        finally:
            await timer.close()

    @pytest.mark.asyncio
    async def test_smart_timer_caches_timezone(self):
        """Timezone detection result is cached for subsequent calls."""
        timer = SmartSendTimer()
        try:
            with patch.object(timer, "_from_whois", new_callable=AsyncMock, return_value=None):
                with patch.object(timer, "_from_ipinfo", new_callable=AsyncMock, return_value=None):
                    await timer._detect_timezone("test.in")
                    assert "test.in" in timer._cache
                    assert timer._cache["test.in"] == "Asia/Kolkata"
        finally:
            await timer.close()

    @pytest.mark.asyncio
    async def test_smart_timer_detect_timezone_no_network(self):
        """_detect_timezone works without real network calls when TLD matches."""
        timer = SmartSendTimer()
        try:
            # Mock WHOIS and ipinfo to avoid network
            with patch.object(timer, "_from_whois", new_callable=AsyncMock, return_value=None):
                with patch.object(timer, "_from_ipinfo", new_callable=AsyncMock, return_value=None):
                    tz = await timer._detect_timezone("hello.de")
                    assert tz == "Europe/Berlin"
        finally:
            await timer.close()
