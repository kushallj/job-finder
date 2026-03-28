"""
smart_timer.py — Timezone-aware optimal send window calculator.

Algorithm:
  1. Detect recipient timezone from domain TLD → country WHOIS → IP geolocation
  2. Find next optimal window: 09:00–11:00 recipient local time, Tue–Thu
  3. Return delay_seconds so the caller can schedule precisely

Why optimal windows matter (data from Mailchimp/HubSpot studies):
  - Tuesday 10 AM: 23% higher open rate than Monday 8 AM
  - 9–11 AM local time: professional checks email after morning standup
  - Avoid Monday (busy) and Friday (winding down)

Timezone detection cascade (all free, no API keys required):
  TLD map (.in → IST, .uk → GMT/BST, .de → CET, ...)
    → python-whois registrant country
    → ipinfo.io free API (no key, 50k req/month)
    → fallback: IST (UTC+5:30) since user is India-based
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TLD → IANA timezone (covers ~90% of Indian job postings + global)
# ---------------------------------------------------------------------------
_TLD_TZ: dict[str, str] = {
    "in":  "Asia/Kolkata",
    "io":  "UTC",            # mostly tech startups, treat as UTC
    "ai":  "UTC",
    "com": "America/New_York",   # US-heavy; refined by WHOIS if needed
    "co":  "America/New_York",
    "us":  "America/New_York",
    "uk":  "Europe/London",
    "co.uk": "Europe/London",
    "de":  "Europe/Berlin",
    "fr":  "Europe/Paris",
    "ca":  "America/Toronto",
    "au":  "Australia/Sydney",
    "sg":  "Asia/Singapore",
    "jp":  "Asia/Tokyo",
    "ae":  "Asia/Dubai",
    "nl":  "Europe/Amsterdam",
    "se":  "Europe/Stockholm",
    "no":  "Europe/Oslo",
    "fi":  "Europe/Helsinki",
    "ch":  "Europe/Zurich",
    "nz":  "Pacific/Auckland",
    "hk":  "Asia/Hong_Kong",
    "br":  "America/Sao_Paulo",
    "mx":  "America/Mexico_City",
    "il":  "Asia/Jerusalem",
}

# Country code (from WHOIS) → IANA timezone
_COUNTRY_TZ: dict[str, str] = {
    "IN": "Asia/Kolkata",
    "US": "America/New_York",
    "GB": "Europe/London",
    "DE": "Europe/Berlin",
    "FR": "Europe/Paris",
    "CA": "America/Toronto",
    "AU": "Australia/Sydney",
    "SG": "Asia/Singapore",
    "JP": "Asia/Tokyo",
    "AE": "Asia/Dubai",
    "NL": "Europe/Amsterdam",
    "SE": "Europe/Stockholm",
    "NO": "Europe/Oslo",
    "FI": "Europe/Helsinki",
    "CH": "Europe/Zurich",
    "NZ": "Pacific/Auckland",
    "HK": "Asia/Hong_Kong",
    "BR": "America/Sao_Paulo",
    "MX": "America/Mexico_City",
    "IL": "Asia/Jerusalem",
}

_FALLBACK_TZ = "Asia/Kolkata"   # user is India-based


class SmartSendTimer:
    """
    Calculates the optimal send time for a given recipient domain.

    Usage:
        timer = SmartSendTimer()
        delay = await timer.seconds_until_optimal("stripe.com")
        await asyncio.sleep(delay)
        # send now
    """

    # Optimal local hour range [start_inclusive, end_exclusive)
    OPTIMAL_HOUR_START = 9
    OPTIMAL_HOUR_END   = 11
    # Optimal weekdays: 1=Monday … 5=Friday (avoid 0=Mon if busy, 4=Fri winding down)
    OPTIMAL_WEEKDAYS   = {1, 2, 3}   # Tue, Wed, Thu

    def __init__(self):
        self._http = httpx.AsyncClient(timeout=5.0)
        self._cache: dict[str, str] = {}    # domain → IANA tz string

    # ── Public API ────────────────────────────────────────────────────────────

    async def seconds_until_optimal(self, domain: str) -> float:
        """
        Return seconds to wait before sending to `domain`.
        Returns 0 if we are already inside the optimal window.
        """
        tz_str = await self._detect_timezone(domain)
        return self._calc_delay(tz_str)

    async def optimal_send_time(self, domain: str) -> datetime:
        """Return the next optimal UTC datetime for sending to `domain`."""
        tz_str = await self._detect_timezone(domain)
        delay  = self._calc_delay(tz_str)
        return datetime.now(timezone.utc) + timedelta(seconds=delay)

    # ── Timezone detection cascade ────────────────────────────────────────────

    async def _detect_timezone(self, domain: str) -> str:
        domain = domain.lower().strip()
        if domain in self._cache:
            return self._cache[domain]

        tz = (
            self._from_tld(domain)
            or await self._from_whois(domain)
            or await self._from_ipinfo(domain)
            or _FALLBACK_TZ
        )
        self._cache[domain] = tz
        log.debug("Timezone for %s → %s", domain, tz)
        return tz

    @staticmethod
    def _from_tld(domain: str) -> Optional[str]:
        """Match longest TLD suffix first (e.g. 'co.uk' before 'uk')."""
        parts = domain.split(".")
        for length in range(len(parts), 0, -1):
            tld = ".".join(parts[-length:])
            if tld in _TLD_TZ:
                return _TLD_TZ[tld]
        return None

    async def _from_whois(self, domain: str) -> Optional[str]:
        """Extract country from WHOIS using python-whois (optional dep)."""
        try:
            import whois  # pip install python-whois
            loop   = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: whois.whois(domain))
            country = (result.get("country") or "").upper().strip()
            return _COUNTRY_TZ.get(country)
        except Exception:
            return None

    async def _from_ipinfo(self, domain: str) -> Optional[str]:
        """
        Resolve domain → IP → timezone via ipinfo.io (free, 50k req/month).
        No API key required for basic fields.
        """
        try:
            import socket
            loop = asyncio.get_event_loop()
            ip   = await loop.run_in_executor(None, socket.gethostbyname, domain)
            resp = await self._http.get(f"https://ipinfo.io/{ip}/json")
            if resp.status_code == 200:
                data    = resp.json()
                tz_str  = data.get("timezone", "")
                country = data.get("country", "").upper()
                if tz_str:
                    try:
                        ZoneInfo(tz_str)
                        return tz_str
                    except ZoneInfoNotFoundError:
                        pass
                return _COUNTRY_TZ.get(country)
        except Exception:
            return None

    # ── Delay calculator ─────────────────────────────────────────────────────

    def _calc_delay(self, tz_str: str) -> float:
        """
        Given a timezone string, return seconds until the next optimal send window.
        Returns 0.0 if currently inside window.

        Logic:
          - If current time is in [OPTIMAL_HOUR_START, OPTIMAL_HOUR_END) on an
            optimal weekday → 0 (send now)
          - If current time is before OPTIMAL_HOUR_START on an optimal weekday →
            wait until OPTIMAL_HOUR_START
          - Otherwise → advance to next optimal weekday at OPTIMAL_HOUR_START
        """
        try:
            tz = ZoneInfo(tz_str)
        except ZoneInfoNotFoundError:
            tz = ZoneInfo(_FALLBACK_TZ)

        now_local = datetime.now(tz)

        # Check if currently in window
        if (
            now_local.weekday() in self.OPTIMAL_WEEKDAYS
            and self.OPTIMAL_HOUR_START <= now_local.hour < self.OPTIMAL_HOUR_END
        ):
            return 0.0

        # Find the next slot
        candidate = now_local.replace(
            hour=self.OPTIMAL_HOUR_START, minute=0, second=0, microsecond=0
        )
        if candidate <= now_local:
            candidate += timedelta(days=1)

        # Advance to nearest optimal weekday
        for _ in range(7):
            if candidate.weekday() in self.OPTIMAL_WEEKDAYS:
                break
            candidate += timedelta(days=1)

        now_utc  = datetime.now(timezone.utc)
        send_utc = candidate.astimezone(timezone.utc)
        delay    = (send_utc - now_utc).total_seconds()
        return max(0.0, delay)

    async def close(self):
        await self._http.aclose()
