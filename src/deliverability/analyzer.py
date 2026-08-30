from __future__ import annotations

import re
from datetime import datetime
from typing import List, Dict, Any, Tuple

from .models import SpamWordMatch, DeliverabilityAnalysisResult
from .spam_catalog import SPAM_CATALOG


def count_syllables(word: str) -> int:
    word = word.lower().strip()
    if not word:
        return 1
    word = re.sub(r'(?:[^laeiouy]|ed|es|e)$', '', word)
    word = re.sub(r'^y', '', word)
    matches = re.findall(r'[aeiouy]{1,2}', word)
    return max(1, len(matches))


class DeliverabilityAnalyzer:
    """
    Evaluates cold outreach drafts against deliverability, spam triggers,
    reading grade level, reading time, and subject line effectiveness.
    """

    def analyze_draft(self, subject: str, body: str) -> DeliverabilityAnalysisResult:
        full_text = f"{subject}\n{body}".strip()
        low_text = full_text.lower()

        # 1. Spam Word & Trigger Matching
        spam_matches: List[SpamWordMatch] = []
        base_spam_penalty = 0.0

        for trigger, info in SPAM_CATALOG.items():
            pattern = rf"\b{re.escape(trigger)}\b"
            for m in re.finditer(pattern, low_text):
                penalty = 18.0 if info["severity"] == "critical" else 8.0
                base_spam_penalty += penalty
                spam_matches.append(SpamWordMatch(
                    word=m.group(0),
                    category=info["category"],
                    severity=info["severity"],
                    suggested_alternatives=info["alts"],
                    position=m.start(),
                ))

        # 2. Text Statistics
        words = re.findall(r"\b\w+\b", body)
        word_count = len(words)
        char_count = len(body)
        sentences = [s.strip() for s in re.split(r"[.!?]+", body) if s.strip()]
        sentence_count = max(1, len(sentences))

        # Reading Time (200 words per minute average)
        reading_time_seconds = max(5, round((word_count / 200.0) * 60))

        # 3. Readability: Flesch-Kincaid Grade Level
        # 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
        if word_count > 0:
            total_syllables = sum(count_syllables(w) for w in words)
            fk_grade = (0.39 * (word_count / sentence_count)) + (11.8 * (total_syllables / word_count)) - 15.59
            fk_grade = max(1.0, min(16.0, round(fk_grade, 1)))
        else:
            fk_grade = 6.0

        # 4. Link & Formatting Penalties
        links = re.findall(r"https?://[^\s]+|www\.[^\s]+", body)
        link_count = len(links)
        if link_count > 2:
            base_spam_penalty += (link_count - 2) * 15.0

        # Uppercase ratio (ALL CAPS screaming)
        alpha_chars = [c for c in body if c.isalpha()]
        uppercase_ratio = (sum(1 for c in alpha_chars if c.isupper()) / max(1, len(alpha_chars)))
        if uppercase_ratio > 0.25:
            base_spam_penalty += 25.0

        # Excessive punctuation (e.g. !!! or ???)
        if re.search(r"[!?]{2,}", body):
            base_spam_penalty += 15.0

        # 5. Subject Line Optimization
        subj_words = re.findall(r"\b\w+\b", subject)
        subj_len = len(subj_words)
        subj_score = 90.0
        subj_advice = "Concise and compelling."

        if subj_len < 3:
            subj_score -= 30.0
            subj_advice = "Too short — looks generic or automated."
        elif subj_len > 9:
            subj_score -= 25.0
            subj_advice = "Too long (>9 words) — will be truncated on mobile clients."
        elif any(c in subject for c in ["!", "$", "%"]):
            subj_score -= 20.0
            subj_advice = "Contains special characters (!, $, %) that trigger inbox promo filters."

        # 6. Overall Deliverability Score & Tier
        # Ideal email: 50-125 words, Grade 5-8, 1 link max, 0 spam words
        length_penalty = 0.0
        if word_count > 200:
            length_penalty = 20.0
        elif word_count < 25:
            length_penalty = 10.0

        raw_spam_score = base_spam_penalty + length_penalty + (max(0.0, fk_grade - 9.0) * 5.0)
        final_spam_score = max(0.0, min(100.0, round(raw_spam_score, 1)))

        if final_spam_score < 25.0:
            tier = "Primary Inbox 🛡️"
        elif final_spam_score < 55.0:
            tier = "Promotions Tab ⚠️"
        else:
            tier = "Spam Folder 🚨"

        recommendations = []
        if spam_matches:
            recommendations.append(f"Replace {len(spam_matches)} spam trigger word(s) with suggested professional alternatives.")
        if word_count > 150:
            recommendations.append(f"Trim draft from {word_count} to <120 words for executive mobile reading.")
        if link_count > 1:
            recommendations.append("Limit email to a single hyperlinked portfolio/profile URL to maximize inbox deliverability.")
        if fk_grade > 8.5:
            recommendations.append(f"Reading grade is Grade {fk_grade} — simplify sentence structure for faster scanning.")
        if not recommendations:
            recommendations.append("Excellent deliverability: Clean syntax, optimal word count, and zero spam triggers.")

        return DeliverabilityAnalysisResult(
            spam_score=final_spam_score,
            deliverability_tier=tier,
            is_safe=final_spam_score < 40.0,
            flesch_kincaid_grade=fk_grade,
            reading_time_seconds=reading_time_seconds,
            word_count=word_count,
            char_count=char_count,
            link_count=link_count,
            uppercase_ratio=round(uppercase_ratio, 2),
            spam_matches=spam_matches,
            subject_score=max(0.0, min(100.0, round(subj_score, 1))),
            subject_advice=subj_advice,
            deliverability_recommendations=recommendations,
            timestamp=datetime.utcnow().isoformat(),
        )


deliverability_analyzer = DeliverabilityAnalyzer()
