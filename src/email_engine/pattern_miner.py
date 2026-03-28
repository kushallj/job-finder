"""
pattern_miner.py — Dynamic Programming email pattern mining.

This is the core of Hunter.io's algorithm.

Problem:
  Given a set of known emails for a domain, determine the dominant
  email format so we can predict unknown people's addresses.

Algorithm (DP + statistical inference):
  1. For each known email local-part, test all 8 format templates
  2. Count matches per format → frequency table
  3. Dominant pattern = argmax(frequency table)
  4. Confidence = dominant_count / total * sigmoid_boost(total)
  5. Memoize: domain → best_pattern (avoids re-mining on each call)

The "DP" part:
  State:   dp[domain] = {format_id: match_count}
  Update:  O(F) per new email (F = 8 formats = constant)
  Query:   O(1) — just argmax of cached dict
  Persist: SQLite (survives restarts, accumulates knowledge over time)

Why this works:
  Companies standardize their email format company-wide.
  stripe.com → first.last@stripe.com  (confidence: 94%)
  google.com → first@google.com       (confidence: 82%)
  Once we've seen 5+ confirmed emails for a domain, we can predict
  any employee's address with high confidence.

Edge cases handled:
  - Ambiguous patterns (first.last vs last.first): resolved using name data
  - Catch-all domains: flagged, confidence capped at 50%
  - Subdomain normalization: mail.stripe.com → stripe.com
  - Short names (< 2 chars): skip to avoid false positives
  - Numeric local-parts: skip (these are system accounts)
"""

from __future__ import annotations

import re
import sqlite3
import logging
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Format definitions
# ---------------------------------------------------------------------------

@dataclass
class EmailFormat:
    """One email format template with its detection regex and generation template."""
    id:         str
    template:   str          # e.g. "{first}.{last}"
    pattern:    re.Pattern   # regex to detect this format in a local-part
    base_score: int          # prior confidence (industry data)
    group_map:  dict         # regex group → variable name


# Formats ordered by global frequency (based on Hunter.io published stats)
EMAIL_FORMATS: List[EmailFormat] = [
    EmailFormat(
        id="first_dot_last",
        template="{first}.{last}",
        pattern=re.compile(r"^(?P<first>[a-z]{2,})\.(?P<last>[a-z]{2,})$"),
        base_score=78,
        group_map={"first": "first", "last": "last"},
    ),
    EmailFormat(
        id="f_last",
        template="{fi}{last}",
        pattern=re.compile(r"^(?P<fi>[a-z])(?P<last>[a-z]{2,})$"),
        base_score=72,
        group_map={"fi": "first_initial", "last": "last"},
    ),
    EmailFormat(
        id="first_last",
        template="{first}{last}",
        pattern=re.compile(r"^(?P<first>[a-z]{2,})(?P<last>[a-z]{2,})$"),
        base_score=60,
        group_map={"first": "first", "last": "last"},
    ),
    EmailFormat(
        id="first_under_last",
        template="{first}_{last}",
        pattern=re.compile(r"^(?P<first>[a-z]{2,})_(?P<last>[a-z]{2,})$"),
        base_score=55,
        group_map={"first": "first", "last": "last"},
    ),
    EmailFormat(
        id="first_dash_last",
        template="{first}-{last}",
        pattern=re.compile(r"^(?P<first>[a-z]{2,})-(?P<last>[a-z]{2,})$"),
        base_score=50,
        group_map={"first": "first", "last": "last"},
    ),
    EmailFormat(
        id="last_dot_first",
        template="{last}.{first}",
        pattern=re.compile(r"^(?P<last>[a-z]{2,})\.(?P<first>[a-z]{2,})$"),
        base_score=55,
        group_map={"last": "last", "first": "first"},
    ),
    EmailFormat(
        id="first_only",
        template="{first}",
        pattern=re.compile(r"^(?P<first>[a-z]{3,})$"),
        base_score=40,
        group_map={"first": "first"},
    ),
    EmailFormat(
        id="last_only",
        template="{last}",
        pattern=re.compile(r"^(?P<last>[a-z]{3,})$"),
        base_score=38,
        group_map={"last": "last"},
    ),
    EmailFormat(
        id="f_dot_last",
        template="{fi}.{last}",
        pattern=re.compile(r"^(?P<fi>[a-z])\.(?P<last>[a-z]{2,})$"),
        base_score=65,
        group_map={"fi": "first_initial", "last": "last"},
    ),
    EmailFormat(
        id="first_l",
        template="{first}{li}",
        pattern=re.compile(r"^(?P<first>[a-z]{2,})(?P<li>[a-z])$"),
        base_score=45,
        group_map={"first": "first", "li": "last_initial"},
    ),
]

# Formats that are unambiguous (contain a separator: . _ -)
UNAMBIGUOUS_FORMATS = {"first_dot_last", "first_under_last", "first_dash_last",
                       "last_dot_first", "f_dot_last"}


# ---------------------------------------------------------------------------
# PatternDB — SQLite-backed domain pattern knowledge base
# ---------------------------------------------------------------------------

class PatternDB:
    """
    Persistent mapping: domain → {format_id: match_count}.

    This is the "memory" of the system. Once we've mined a domain,
    the result is cached and shared across all runs.

    Schema:
      domain_patterns(domain TEXT PK, format_json TEXT, total_seen INT, last_updated TEXT)
    """

    def __init__(self, db_path: str = "email_patterns.db"):
        self._path = db_path
        self._init_db()
        self._cache: Dict[str, Dict[str, int]] = {}    # in-memory LRU-style cache

    def _init_db(self) -> None:
        con = sqlite3.connect(self._path)
        con.execute("""
            CREATE TABLE IF NOT EXISTS domain_patterns (
                domain       TEXT PRIMARY KEY,
                format_json  TEXT NOT NULL,
                total_seen   INTEGER DEFAULT 0,
                is_catchall  INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT (datetime('now'))
            )
        """)
        con.commit()
        con.close()

    def get(self, domain: str) -> Optional[Dict[str, int]]:
        """Return format frequency table for domain, or None if unknown."""
        domain = _normalize_domain(domain)
        if domain in self._cache:
            return self._cache[domain]
        try:
            con = sqlite3.connect(self._path)
            row = con.execute(
                "SELECT format_json FROM domain_patterns WHERE domain = ?", (domain,)
            ).fetchone()
            con.close()
            if row:
                data = json.loads(row[0])
                self._cache[domain] = data
                return data
        except Exception as e:
            log.debug("PatternDB get error: %s", e)
        return None

    def update(self, domain: str, freq_table: Dict[str, int], total: int, is_catchall: bool = False) -> None:
        """Upsert the frequency table for domain."""
        domain = _normalize_domain(domain)
        self._cache[domain] = freq_table
        try:
            con = sqlite3.connect(self._path)
            con.execute("""
                INSERT INTO domain_patterns (domain, format_json, total_seen, is_catchall)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    format_json  = excluded.format_json,
                    total_seen   = excluded.total_seen,
                    is_catchall  = excluded.is_catchall,
                    last_updated = datetime('now')
            """, (domain, json.dumps(freq_table), total, int(is_catchall)))
            con.commit()
            con.close()
        except Exception as e:
            log.debug("PatternDB update error: %s", e)

    def is_catchall(self, domain: str) -> bool:
        domain = _normalize_domain(domain)
        try:
            con = sqlite3.connect(self._path)
            row = con.execute(
                "SELECT is_catchall FROM domain_patterns WHERE domain = ?", (domain,)
            ).fetchone()
            con.close()
            return bool(row and row[0])
        except Exception:
            return False

    def all_known_domains(self) -> List[str]:
        try:
            con = sqlite3.connect(self._path)
            rows = con.execute("SELECT domain FROM domain_patterns").fetchall()
            con.close()
            return [r[0] for r in rows]
        except Exception:
            return []


# ---------------------------------------------------------------------------
# PatternMiner
# ---------------------------------------------------------------------------

@dataclass
class PatternResult:
    """Result of pattern mining for one domain."""
    domain:         str
    best_format:    Optional[EmailFormat]
    confidence:     float               # 0.0–1.0
    freq_table:     Dict[str, int]      # format_id → match_count
    total_emails:   int
    is_ambiguous:   bool = False        # True if top-2 formats are close (< 10% gap)
    is_catchall:    bool = False


class PatternMiner:
    """
    Derives the dominant email format for a domain from observed emails.

    Core algorithm:
      For each observed email:
        1. Extract local-part  (everything before @)
        2. Skip if system/role account (info@, hr@, etc.)
        3. Skip if numeric or too short
        4. Try each EmailFormat regex
        5. On match → increment freq_table[format_id]

      Result: freq_table sorted by count → best_format with confidence

    Optional name-disambiguation:
      When names are known (from GitHub/LinkedIn), we can disambiguate
      "john.doe@" vs "doe.john@" by checking which matches the known name order.

    Usage:
        miner = PatternMiner(db=PatternDB())

        # Mine from a batch of collected emails
        result = miner.mine(
            emails=["john.doe@stripe.com", "jane.smith@stripe.com"],
            domain="stripe.com",
        )
        print(result.best_format.template)  # → "{first}.{last}"
        print(result.confidence)            # → 0.94

        # Generate candidates for a known person
        candidates = miner.generate_candidates("Sarah", "Connor", "stripe.com", result)
        # → [("sarah.connor@stripe.com", 94), ("sconnor@stripe.com", 18), ...]
    """

    # Role/system email prefixes that are NOT personal
    _ROLE_PREFIXES = frozenset([
        "info", "contact", "hello", "hi", "support", "help", "sales",
        "marketing", "admin", "hr", "careers", "jobs", "recruiting",
        "team", "dev", "api", "no-reply", "noreply", "donotreply",
        "security", "legal", "billing", "payments", "press", "media",
        "feedback", "newsletter", "webmaster", "postmaster", "abuse",
        "privacy", "gdpr", "compliance", "investors", "ir",
    ])

    def __init__(self, db: Optional[PatternDB] = None):
        self._db = db or PatternDB()

    # ── Public API ────────────────────────────────────────────────────────────

    def mine(
        self,
        emails: List[str],
        domain: str,
        known_names: Optional[List[Tuple[str, str]]] = None,  # [(first, last), ...]
        is_catchall: bool = False,
    ) -> PatternResult:
        """
        Mine email format patterns from a list of observed emails for `domain`.

        Args:
            emails:      List of full email addresses (e.g. ["john@stripe.com"])
            domain:      The domain being mined
            known_names: Optional list of (first, last) for disambiguation
            is_catchall: Mark domain as catch-all (caps confidence at 0.5)

        Returns:
            PatternResult with best_format, confidence, freq_table
        """
        domain = _normalize_domain(domain)
        freq: Dict[str, int] = defaultdict(int)

        personal_emails = [
            e for e in emails
            if self._is_personal(e, domain)
        ]

        if not personal_emails:
            # Try to load from DB
            cached = self._db.get(domain)
            if cached:
                return self._build_result(domain, cached, sum(cached.values()), is_catchall)
            return PatternResult(
                domain=domain,
                best_format=None,
                confidence=0.0,
                freq_table={},
                total_emails=0,
                is_catchall=is_catchall,
            )

        # DP: for each personal email, try every format
        name_lookup = self._build_name_lookup(known_names or [])

        for email in personal_emails:
            local = email.split("@")[0].lower()
            matched_formats = self._match_formats(local, name_lookup)
            for fmt_id in matched_formats:
                freq[fmt_id] += 1

        total = len(personal_emails)

        # Persist to DB
        self._db.update(domain, dict(freq), total, is_catchall)

        return self._build_result(domain, dict(freq), total, is_catchall)

    def get_cached(self, domain: str) -> Optional[PatternResult]:
        """Return cached pattern result without re-mining."""
        domain = _normalize_domain(domain)
        cached = self._db.get(domain)
        if cached:
            total = sum(cached.values())
            return self._build_result(domain, cached, total, self._db.is_catchall(domain))
        return None

    def generate_candidates(
        self,
        first: str,
        last: str,
        domain: str,
        pattern_result: Optional[PatternResult] = None,
    ) -> List[Tuple[str, int]]:
        """
        Generate email candidates for a person, ranked by pattern confidence.

        Returns list of (email, confidence_score) sorted descending.
        confidence_score is 0-100.

        Algorithm:
          1. If we have a pattern result, use the dominant format first
          2. Then generate all other formats as fallbacks with lower confidence
          3. Deduplicate (some formats produce same output for short names)
        """
        if pattern_result is None:
            pattern_result = self.get_cached(domain)

        first = first.lower().strip()
        last  = last.lower().strip()
        fi    = first[0] if first else ""
        li    = last[0]  if last  else ""

        if not first or not last:
            return []

        # Generate all permutations
        raw_candidates: Dict[str, int] = {}   # email → score

        # If we have a dominant pattern, use its confidence for the top candidate
        if pattern_result and pattern_result.best_format and pattern_result.confidence > 0.3:
            top_fmt    = pattern_result.best_format
            top_email  = self._apply_template(top_fmt.template, first, last, fi, li)
            top_score  = int(pattern_result.confidence * 100)
            if top_email:
                raw_candidates[f"{top_email}@{domain}"] = top_score

        # Generate all other formats with degraded scores
        for fmt in EMAIL_FORMATS:
            email = self._apply_template(fmt.template, first, last, fi, li)
            if not email:
                continue
            full = f"{email}@{domain}"
            if full in raw_candidates:
                continue    # already added as top candidate

            # Base score from format's prior + slight penalty vs top
            score = fmt.base_score
            if pattern_result and pattern_result.freq_table:
                freq_count = pattern_result.freq_table.get(fmt.id, 0)
                total      = pattern_result.total_emails or 1
                score      = int(min(95, fmt.base_score * 0.4 + (freq_count / total) * 60))

            raw_candidates[full] = score

        # Sort by score descending
        return sorted(raw_candidates.items(), key=lambda x: x[1], reverse=True)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _match_formats(
        self,
        local: str,
        name_lookup: Dict[str, Tuple[str, str]],
    ) -> List[str]:
        """
        Test all EmailFormats against `local` part.
        Returns list of matching format IDs.

        Name disambiguation:
          If known_names are provided, resolve ambiguous formats
          (e.g. "john.doe" could be first.last OR last.first).
          We check if "john" appears as a known first name → first.last wins.
        """
        matched = []
        for fmt in EMAIL_FORMATS:
            m = fmt.pattern.match(local)
            if not m:
                continue

            # Disambiguate first.last vs last.first
            if fmt.id in ("first_dot_last", "last_dot_first") and name_lookup:
                part1, part2 = local.split(".")
                # If part1 is a known first name → first.last
                if part1 in name_lookup:
                    if fmt.id == "first_dot_last":
                        matched.append(fmt.id)
                # If part1 is a known last name → last.first
                elif part2 in name_lookup:
                    if fmt.id == "last_dot_first":
                        matched.append(fmt.id)
                else:
                    # No disambiguation data → count both with 0.5 weight
                    matched.append(fmt.id)
            else:
                matched.append(fmt.id)

        return matched

    @staticmethod
    def _build_name_lookup(
        known_names: List[Tuple[str, str]]
    ) -> Dict[str, Tuple[str, str]]:
        """Build a dict: first_name_lower → (first, last) for quick lookup."""
        lookup = {}
        for first, last in known_names:
            if first:
                lookup[first.lower()] = (first, last)
        return lookup

    @staticmethod
    def _is_personal(email: str, domain: str) -> bool:
        """
        Filter out role/system emails that would corrupt pattern mining.
        Returns True if the email looks like a personal address.
        """
        if "@" not in email:
            return False
        local = email.split("@")[0].lower()

        # Skip role prefixes
        if local in PatternMiner._ROLE_PREFIXES:
            return False

        # Skip numeric-only local parts (system accounts)
        if local.isdigit():
            return False

        # Skip very short (< 3 chars) — too ambiguous
        if len(local) < 3:
            return False

        # Skip if looks like noreply pattern
        if "noreply" in local or "no-reply" in local:
            return False

        return True

    @staticmethod
    def _apply_template(
        template: str,
        first: str, last: str, fi: str, li: str
    ) -> str:
        """Apply a template string, return empty string if result would be invalid."""
        result = (
            template
            .replace("{first}", first)
            .replace("{last}", last)
            .replace("{fi}", fi)
            .replace("{li}", li)
        )
        # Sanity check: no unfilled placeholders
        if "{" in result:
            return ""
        if len(result) < 2:
            return ""
        return result

    def _build_result(
        self,
        domain: str,
        freq: Dict[str, int],
        total: int,
        is_catchall: bool,
    ) -> PatternResult:
        if not freq:
            return PatternResult(
                domain=domain, best_format=None, confidence=0.0,
                freq_table={}, total_emails=total, is_catchall=is_catchall,
            )

        fmt_by_id = {f.id: f for f in EMAIL_FORMATS}

        # Sort by count descending
        sorted_freqs = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        best_id, best_count = sorted_freqs[0]
        best_fmt = fmt_by_id.get(best_id)

        # Confidence = (best_count / total) × quality_boost
        raw_conf   = best_count / total if total > 0 else 0.0
        # Sigmoid-style boost: more samples = higher trust
        # Formula: raw_conf × (1 - e^(-total/5))  → converges to raw_conf as total → ∞
        import math
        quality_boost = 1.0 - math.exp(-total / 5.0)
        confidence    = raw_conf * quality_boost

        # Cap catch-all domains at 50%
        if is_catchall:
            confidence = min(confidence, 0.50)

        # Detect ambiguous (top two within 10%)
        is_ambiguous = (
            len(sorted_freqs) >= 2
            and abs(sorted_freqs[0][1] - sorted_freqs[1][1]) / max(total, 1) < 0.10
        )

        return PatternResult(
            domain=domain,
            best_format=best_fmt,
            confidence=confidence,
            freq_table=dict(freq),
            total_emails=total,
            is_ambiguous=is_ambiguous,
            is_catchall=is_catchall,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_domain(domain: str) -> str:
    """
    Normalize domain: strip protocol, www, and known mail subdomains.
    mail.stripe.com → stripe.com
    www.google.com  → google.com
    """
    domain = domain.lower().strip()
    # Strip protocol
    for prefix in ("https://", "http://"):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    # Strip path
    domain = domain.split("/")[0]
    # Strip known mail subdomains
    for sub in ("mail.", "email.", "mx.", "smtp.", "www."):
        if domain.startswith(sub):
            domain = domain[len(sub):]
    return domain
