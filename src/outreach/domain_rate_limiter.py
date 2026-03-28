"""
domain_rate_limiter.py — Per-domain + global daily rate limiting.

Rules (configurable):
  Global:      max 50 emails / day
  Per company: max 3 emails / 7 days  (avoid spamming same company)
  Per contact: max 1 email / 7 days   (no double-sends to same person)

Implementation:
  - Two-level token buckets:
      global_bucket  — replenishes 50 tokens every 24 hours
      domain_buckets — per-domain, replenishes 3 tokens every 7 days
  - Contact-level dedup: set of (email, week_number) tuples
  - TTL eviction: domain buckets older than 14 days are dropped
  - Thread-safe: asyncio.Lock on all mutations
  - Builds on existing TokenBucket from src.async_pipeline.rate_limiter

Why per-domain, not per-company?
  Companies can have multiple domains (stripe.com, stripe.io, etc.).
  We key on the root domain extracted from the contact email.
  This is more precise than company name matching (which is fuzzy).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple

log = logging.getLogger(__name__)


@dataclass
class _DomainBucket:
    """Token bucket + last-used timestamp for TTL eviction."""
    tokens:     float
    capacity:   float
    refill_rate: float          # tokens per second
    last_refill: float = field(default_factory=time.monotonic)
    last_used:   float = field(default_factory=time.monotonic)

    def refill(self) -> None:
        now     = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def acquire(self) -> bool:
        self.refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            self.last_used = time.monotonic()
            return True
        return False

    def available(self) -> float:
        self.refill()
        return self.tokens

    def seconds_until_available(self) -> float:
        self.refill()
        if self.tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self.tokens
        return deficit / self.refill_rate


class DomainRateLimiter:
    """
    Two-level rate limiter: global daily cap + per-domain weekly cap.

    Usage:
        limiter = DomainRateLimiter()

        allowed, reason = await limiter.check("john@stripe.com")
        if not allowed:
            print(f"Blocked: {reason}")
        else:
            limiter.consume("john@stripe.com")   # deduct token
    """

    def __init__(
        self,
        global_daily_limit:   int   = 50,
        domain_weekly_limit:  int   = 3,
        contact_weekly_limit: int   = 1,
        bucket_ttl_days:      float = 14.0,
    ):
        # Global: 50 tokens / 86400 seconds (1 day)
        self._global = _DomainBucket(
            tokens      = float(global_daily_limit),
            capacity    = float(global_daily_limit),
            refill_rate = global_daily_limit / 86_400.0,
        )
        self._domain_weekly_limit   = domain_weekly_limit
        self._contact_weekly_limit  = contact_weekly_limit
        # Weekly refill: 3 tokens / 604800 seconds (7 days)
        self._domain_refill_rate  = domain_weekly_limit  / 604_800.0
        self._contact_refill_rate = contact_weekly_limit / 604_800.0

        self._domain_buckets:  Dict[str, _DomainBucket] = {}
        self._contact_buckets: Dict[str, _DomainBucket] = {}

        self._bucket_ttl_secs = bucket_ttl_days * 86_400.0
        self._lock = asyncio.Lock()

        # Stats
        self._total_allowed = 0
        self._total_blocked = 0

    # ── Public API ────────────────────────────────────────────────────────────

    async def check(self, contact_email: str) -> Tuple[bool, str]:
        """
        Check if sending to `contact_email` is allowed right now.

        Returns:
            (True, "")               — allowed
            (False, reason_string)   — blocked with human-readable reason
        """
        domain  = self._extract_domain(contact_email)
        email   = contact_email.lower().strip()

        async with self._lock:
            self._evict_stale()

            # Check global daily bucket
            if self._global.available() < 1.0:
                wait = self._global.seconds_until_available()
                reason = f"Global daily limit reached. Next slot in {wait/3600:.1f}h"
                self._total_blocked += 1
                return False, reason

            # Check per-domain weekly bucket
            d_bucket = self._get_or_create_domain_bucket(domain)
            if d_bucket.available() < 1.0:
                wait   = d_bucket.seconds_until_available()
                reason = f"Domain limit for @{domain} reached. Next slot in {wait/3600:.1f}h"
                self._total_blocked += 1
                return False, reason

            # Check per-contact weekly bucket
            c_bucket = self._get_or_create_contact_bucket(email)
            if c_bucket.available() < 1.0:
                wait   = c_bucket.seconds_until_available()
                reason = f"Contact {email} already emailed this week. Next slot in {wait/3600:.1f}h"
                self._total_blocked += 1
                return False, reason

            return True, ""

    async def consume(self, contact_email: str) -> bool:
        """
        Deduct one token from all relevant buckets.
        Call ONLY after check() returns True and you actually send.
        Returns False if tokens ran out between check and consume (race).
        """
        domain = self._extract_domain(contact_email)
        email  = contact_email.lower().strip()

        async with self._lock:
            g_ok = self._global.acquire()
            d_ok = self._get_or_create_domain_bucket(domain).acquire()
            c_ok = self._get_or_create_contact_bucket(email).acquire()

            if g_ok and d_ok and c_ok:
                self._total_allowed += 1
                log.debug("Token consumed for %s (domain=%s)", email, domain)
                return True

            log.warning("Token race-condition for %s — tokens ran out between check and consume", email)
            return False

    def stats(self) -> dict:
        return {
            "total_allowed":   self._total_allowed,
            "total_blocked":   self._total_blocked,
            "global_remaining": self._global.available(),
            "active_domains":  len(self._domain_buckets),
            "active_contacts": len(self._contact_buckets),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_create_domain_bucket(self, domain: str) -> _DomainBucket:
        if domain not in self._domain_buckets:
            self._domain_buckets[domain] = _DomainBucket(
                tokens      = float(self._domain_weekly_limit),
                capacity    = float(self._domain_weekly_limit),
                refill_rate = self._domain_refill_rate,
            )
        return self._domain_buckets[domain]

    def _get_or_create_contact_bucket(self, email: str) -> _DomainBucket:
        if email not in self._contact_buckets:
            self._contact_buckets[email] = _DomainBucket(
                tokens      = float(self._contact_weekly_limit),
                capacity    = float(self._contact_weekly_limit),
                refill_rate = self._contact_refill_rate,
            )
        return self._contact_buckets[email]

    def _evict_stale(self) -> None:
        """Remove domain/contact buckets that haven't been used in TTL window."""
        cutoff = time.monotonic() - self._bucket_ttl_secs
        stale_domains  = [k for k, b in self._domain_buckets.items()  if b.last_used < cutoff]
        stale_contacts = [k for k, b in self._contact_buckets.items() if b.last_used < cutoff]
        for k in stale_domains:
            del self._domain_buckets[k]
        for k in stale_contacts:
            del self._contact_buckets[k]
        if stale_domains or stale_contacts:
            log.debug("Evicted %d domain + %d contact buckets", len(stale_domains), len(stale_contacts))

    @staticmethod
    def _extract_domain(email: str) -> str:
        """Extract root domain from email, e.g. 'john@mail.stripe.com' → 'stripe.com'."""
        email = email.lower().strip()
        if "@" not in email:
            return email
        host = email.split("@", 1)[1]
        parts = host.split(".")
        # Return last two segments (handles mail.stripe.com → stripe.com)
        return ".".join(parts[-2:]) if len(parts) >= 2 else host
