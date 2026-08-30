"""
src/answer_bank/models.py

Persistent memory of previously-answered screening/outreach questions.

Ported concept from linkedin-ai's `search_answered_questions_db()` /
"train your AI to answer like you" feature — reworked for job-finder's
domain (cold outreach + ATS screening questions) instead of LinkedIn
Easy Apply forms.

Import Base from the existing models module so this table registers on
the same metadata/engine — no changes to src/models.py required.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from datetime import datetime

from src.models import Base


class AnsweredQuestion(Base):
    """
    A canonical (question -> answer) pair the system has produced or been
    given before. Keyed by a normalized version of the question text so
    that near-duplicate phrasings ("Do you require visa sponsorship?" vs
    "Will you now or in the future require sponsorship?") can still hit
    the cache via fuzzy matching in the service layer.
    """
    __tablename__ = "answered_questions"

    id = Column(Integer, primary_key=True)

    # Original question text, as encountered (e.g. from an ATS form field
    # label, or a recurring objection raised in an email reply).
    question_text = Column(Text, nullable=False)

    # Normalized form used for exact/fuzzy lookups (lowercased, punctuation
    # stripped, whitespace collapsed). Indexed for fast lookup.
    normalized_question = Column(String(500), nullable=False, index=True)

    # The answer to reuse verbatim next time this question is seen.
    answer_text = Column(Text, nullable=False)

    # Where the answer came from: "ai_generated", "user_provided", "edited"
    source = Column(String(50), default="ai_generated")

    # Optional context tags, e.g. "visa_sponsorship", "salary_expectation",
    # "notice_period" — lets you group/report on question categories.
    category = Column(String(100), nullable=True)

    # Which context this was answered in: "ats_application", "email_reply",
    # "outreach_followup". Useful since job-finder spans multiple channels.
    context = Column(String(50), default="ats_application")

    # Has a human reviewed/approved this answer? AI-generated answers
    # should probably be reviewed before being auto-reused at scale.
    approved = Column(Boolean, default=False)

    # How many times this cached answer has been reused.
    times_used = Column(Integer, default=0)

    # Confidence score from the matcher when this was retrieved via fuzzy
    # match rather than an exact hit (1.0 = exact match).
    match_confidence = Column(Float, default=1.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
