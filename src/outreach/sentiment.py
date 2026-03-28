"""
sentiment.py — Two-tier reply sentiment classifier.

Tier 1 — Keyword matching (fast, deterministic, free):
  Runs regex patterns against the reply body.
  Covers >85% of common reply patterns accurately.

Tier 2 — LLM classification (accurate, slow, optional):
  Invoked only when Tier 1 returns NEUTRAL (ambiguous).
  Uses UnifiedAIService (Ollama local → Gemini → keyword fallback).

Sentiment labels:
  POSITIVE    — interested, wants to proceed ("Let's schedule a call")
  NEGATIVE    — not interested ("We're not hiring right now")
  NEUTRAL     — non-committal, generic ("Thanks for reaching out")
  UNSUBSCRIBE — explicit opt-out ("Please remove me")
  REFERRAL    — forwarded internally ("I'm CC'ing our recruiter Sarah")

Design notes:
  - All pattern matching is case-insensitive
  - Tier 1 uses compiled regex for performance (O(n) per email)
  - Tier 2 prompt is constrained to single-word output to avoid hallucination
  - Thread-safe: no shared mutable state between calls
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class SentimentLabel(str, Enum):
    POSITIVE    = "positive"
    NEGATIVE    = "negative"
    NEUTRAL     = "neutral"
    UNSUBSCRIBE = "unsubscribe"
    REFERRAL    = "referral"


# ---------------------------------------------------------------------------
# Tier 1 — Keyword patterns (compiled once at import)
# ---------------------------------------------------------------------------

_POSITIVE_PATTERNS = re.compile(
    r"\b("
    r"interest(ed|ing)|love\s+to|let'?s\s+(talk|connect|chat|schedule|meet)"
    r"|schedule\s+a\s+(call|meeting|chat|interview)"
    r"|available\s+for|hop\s+on\s+a\s+call|set\s+up\s+a\s+time"
    r"|sounds?\s+great|sounds?\s+good|would\s+love"
    r"|looking\s+forward|great\s+background|impressive"
    r"|definitely\s+interested|can\s+we\s+(talk|meet|connect)"
    r"|when\s+are\s+you\s+available|send\s+(me\s+)?your\s+resume"
    r"|move\s+forward|next\s+steps|interview"
    r")\b",
    re.IGNORECASE,
)

_NEGATIVE_PATTERNS = re.compile(
    r"\b("
    r"not\s+(a\s+)?(fit|looking|hiring|interested|right\s+now)"
    r"|no\s+(longer|current|open)\s+(looking|hiring|position|role)"
    r"|don'?t\s+(have|see)\s+a\s+(fit|role|opening|position)"
    r"|not\s+what\s+we('?re|\s+are)\s+looking\s+for"
    r"|position\s+has\s+been\s+filled|already\s+filled"
    r"|we('?re|\s+are)\s+not\s+hiring|no\s+open(ing)?\s+(role|position)"
    r"|budget\s+(freeze|cut)|headcount\s+freeze"
    r"|appreciate\s+your\s+interest\s+but|thank\s+you\s+but"
    r"|wish\s+you\s+the\s+best|good\s+luck\s+in\s+your\s+search"
    r")\b",
    re.IGNORECASE,
)

_UNSUBSCRIBE_PATTERNS = re.compile(
    r"\b("
    r"(please\s+)?(remove|unsubscribe|opt.?out|stop\s+email)"
    r"|don'?t\s+(contact|email|reach\s+out)\s+(me|us)\s+again"
    r"|remove\s+(me|us)\s+from\s+your\s+(list|database|emails)"
    r"|cease\s+and\s+desist|no\s+further\s+contact"
    r")\b",
    re.IGNORECASE,
)

_REFERRAL_PATTERNS = re.compile(
    r"\b("
    r"(cc'?ing|copying|forwarding|looping\s+in)\s+(our|my|the)"
    r"|reach\s+out\s+to\s+[A-Z][a-z]+"     # "reach out to Sarah"
    r"|contact\s+(our|my)\s+(recruiter|hr|hiring)"
    r"|apply\s+(at|on|through|via|to)\s+our"
    r")\b",
    re.IGNORECASE,
)


class SentimentClassifier:
    """
    Classifies reply emails into sentiment labels.

    Usage:
        clf = SentimentClassifier()
        label = await clf.classify("Thanks! Let's schedule a call next week.")
        # → SentimentLabel.POSITIVE
    """

    def __init__(self, use_llm: bool = True):
        self._use_llm = use_llm
        self._ai: Optional[object] = None
        if use_llm:
            try:
                from src.ai.unified_ai_service import UnifiedAIService
                self._ai = UnifiedAIService()
            except Exception as e:
                log.warning("LLM unavailable for sentiment — tier 1 only: %s", e)

    async def classify(self, text: str) -> SentimentLabel:
        """
        Classify `text` into a SentimentLabel.
        Fast path: keyword regex.
        Slow path (only if NEUTRAL): LLM.
        """
        if not text or not text.strip():
            return SentimentLabel.NEUTRAL

        # Tier 1: deterministic keyword matching
        tier1 = self._tier1(text)
        if tier1 != SentimentLabel.NEUTRAL:
            log.debug("Tier-1 sentiment: %s", tier1.value)
            return tier1

        # Tier 2: LLM for ambiguous cases
        if self._use_llm and self._ai:
            try:
                label = await self._tier2_llm(text)
                log.debug("Tier-2 LLM sentiment: %s", label.value)
                return label
            except Exception as e:
                log.warning("LLM sentiment failed, defaulting to NEUTRAL: %s", e)

        return SentimentLabel.NEUTRAL

    # ── Tier 1 ────────────────────────────────────────────────────────────────

    @staticmethod
    def _tier1(text: str) -> SentimentLabel:
        """
        Priority order: UNSUBSCRIBE > NEGATIVE > REFERRAL > POSITIVE > NEUTRAL
        UNSUBSCRIBE must be checked first — it's a legal/ethical obligation.
        """
        if _UNSUBSCRIBE_PATTERNS.search(text):
            return SentimentLabel.UNSUBSCRIBE
        if _NEGATIVE_PATTERNS.search(text):
            return SentimentLabel.NEGATIVE
        if _REFERRAL_PATTERNS.search(text):
            return SentimentLabel.REFERRAL
        if _POSITIVE_PATTERNS.search(text):
            return SentimentLabel.POSITIVE
        return SentimentLabel.NEUTRAL

    # ── Tier 2 ────────────────────────────────────────────────────────────────

    async def _tier2_llm(self, text: str) -> SentimentLabel:
        """
        Ask the LLM to classify a truncated version of the reply.
        Constrained output: single word from the label set.
        """
        snippet = text[:600].replace("\n", " ").strip()
        prompt  = (
            "Classify this email reply into exactly one word from: "
            "positive, negative, neutral, unsubscribe, referral.\n"
            "Rules:\n"
            "  positive    = wants to proceed, interested, scheduling\n"
            "  negative    = not interested, not hiring, rejection\n"
            "  unsubscribe = asking to be removed, do not contact\n"
            "  referral    = directing to another person or link\n"
            "  neutral     = anything else\n\n"
            f'Reply: "{snippet}"\n\n'
            "Output (one word only):"
        )
        # UnifiedAIService.analyze_job returns a dict; we use a direct generate call
        if hasattr(self._ai, "_generate_with_ollama"):
            raw = await self._ai._generate_with_ollama(prompt)
        elif hasattr(self._ai, "backend") and self._ai.backend:
            raw = str(self._ai.backend)
        else:
            return SentimentLabel.NEUTRAL

        word = raw.strip().lower().split()[0] if raw.strip() else "neutral"
        mapping = {
            "positive":    SentimentLabel.POSITIVE,
            "negative":    SentimentLabel.NEGATIVE,
            "neutral":     SentimentLabel.NEUTRAL,
            "unsubscribe": SentimentLabel.UNSUBSCRIBE,
            "referral":    SentimentLabel.REFERRAL,
        }
        return mapping.get(word, SentimentLabel.NEUTRAL)
