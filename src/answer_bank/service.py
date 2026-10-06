"""
src/answer_bank/service.py

AnswerBankService — check-cache-then-generate workflow for recurring
questions (ATS screening questions, recurring reply objections, etc.)

Mirrors linkedin-ai's flow:
    1. Normalize the question text.
    2. Look for an exact normalized match first.
    3. Fall back to fuzzy matching against stored questions.
    4. If nothing found, generate an answer via job-finder's existing
       UnifiedAIService and persist it for next time.

Usage:

    from src.database import SessionLocal
    from src.answer_bank.service import AnswerBankService

    db = SessionLocal()
    bank = AnswerBankService(db)

    answer = await bank.get_or_generate_answer(
        question_text="Do you now or in the future require visa sponsorship?",
        candidate_context={"name": "Jane Doe", "resume_summary": "..."},
        category="visa_sponsorship",
        context="ats_application",
    )
"""

from __future__ import annotations

import re
import difflib
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.answer_bank.models import AnsweredQuestion
from src.ai.unified_ai_service import UnifiedAIService


# Fuzzy match threshold: 0.0-1.0, tuned conservatively so we don't reuse
# an answer for a meaningfully different question. Raise this if you see
# false-positive reuse; lower it if near-duplicate phrasing isn't matching.
FUZZY_MATCH_THRESHOLD = 0.87


def normalize_question(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace for stable lookup keys."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


class AnswerBankService:
    def __init__(self, db: Session, ai_service: Optional[UnifiedAIService] = None):
        self.db = db
        self.ai_service = ai_service or UnifiedAIService()

    def _exact_lookup(self, normalized: str) -> Optional[AnsweredQuestion]:
        return (
            self.db.query(AnsweredQuestion)
            .filter(AnsweredQuestion.normalized_question == normalized)
            .order_by(AnsweredQuestion.times_used.desc())
            .first()
        )

    def _fuzzy_lookup(self, normalized: str) -> Optional[tuple[AnsweredQuestion, float]]:
        """
        Compare against all stored normalized questions using difflib's
        SequenceMatcher ratio. Fine for a few thousand rows; if the bank
        grows large, swap this for a proper vector-similarity lookup
        (e.g. embed with the same model used elsewhere in src/ai/).
        """
        candidates = self.db.query(AnsweredQuestion).all()
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            score = difflib.SequenceMatcher(
                None, normalized, candidate.normalized_question
            ).ratio()
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_match and best_score >= FUZZY_MATCH_THRESHOLD:
            return best_match, best_score
        return None

    def find_cached_answer(self, question_text: str) -> Optional[AnsweredQuestion]:
        """Check the bank without generating anything. Returns None on miss."""
        normalized = normalize_question(question_text)

        if hit := self._exact_lookup(normalized):
            return hit

        if fuzzy_result := self._fuzzy_lookup(normalized):
            match, score = fuzzy_result
            match.match_confidence = score
            return match

        return None

    def _record_reuse(self, entry: AnsweredQuestion) -> None:
        entry.times_used += 1
        entry.last_used_at = datetime.utcnow()
        self.db.commit()

    def save_answer(
        self,
        question_text: str,
        answer_text: str,
        source: str = "ai_generated",
        category: Optional[str] = None,
        context: str = "ats_application",
        approved: bool = False,
    ) -> AnsweredQuestion:
        entry = AnsweredQuestion(
            question_text=question_text,
            normalized_question=normalize_question(question_text),
            answer_text=answer_text,
            source=source,
            category=category,
            context=context,
            approved=approved,
            times_used=1,
            last_used_at=datetime.utcnow(),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def save_or_update_answer(
        self,
        question_text: str,
        answer_text: str,
        source: str = "user_edited",
        category: Optional[str] = None,
        context: str = "ats_application",
        approved: bool = True,
    ) -> AnsweredQuestion:
        """
        Bi-directional learning loop upsert.
        If an answer for this question already exists, updates it with user correction.
        Otherwise creates a new approved entry in the Answer Bank.
        """
        normalized = normalize_question(question_text)
        existing = self._exact_lookup(normalized)
        if existing:
            existing.answer_text = answer_text
            existing.source = source
            existing.approved = approved
            existing.times_used = max(existing.times_used, 1) + 1
            existing.last_used_at = datetime.utcnow()
            if category:
                existing.category = category
            self.db.commit()
            self.db.refresh(existing)
            return existing

        return self.save_answer(
            question_text=question_text,
            answer_text=answer_text,
            source=source,
            category=category,
            context=context,
            approved=approved,
        )

    async def get_or_generate_answer(
        self,
        question_text: str,
        candidate_context: Optional[dict] = None,
        category: Optional[str] = None,
        context: str = "ats_application",
        require_approval: bool = False,
    ) -> str:
        """
        Main entry point. Checks the cache first; only calls the AI
        service on a genuine miss. Returns the answer text.

        If require_approval=True and the only hit is an unapproved
        AI-generated answer, it still returns it but flags via
        entry.approved so calling code can decide whether to surface it
        for human review before using it live.
        """
        if cached := self.find_cached_answer(question_text):
            self._record_reuse(cached)
            return cached.answer_text

        # Cache miss — generate via job-finder's existing AI service.
        prompt = self._build_prompt(question_text, candidate_context or {})
        generated = await self.ai_service.generate_text(prompt, max_tokens=200)

        self.save_answer(
            question_text=question_text,
            answer_text=generated.strip(),
            source="ai_generated",
            category=category,
            context=context,
            approved=not require_approval,
        )
        return generated.strip()

    async def get_answer_for_question(
        self,
        question: str,
        job_title: str = "Software Engineer",
        company: str = "Company",
        job_description: str = "",
        category: Optional[str] = None,
        candidate_context: Optional[dict] = None,
    ) -> dict:
        """
        Unified bridge method for ATS & extension question resolution.
        Returns a dict containing answer text, source, and match metadata.
        """
        if cached := self.find_cached_answer(question):
            self._record_reuse(cached)
            return {
                "question": question,
                "answer": cached.answer_text,
                "source": cached.source or "answer_bank_cache",
                "cached": True,
                "confidence": getattr(cached, "match_confidence", 1.0),
            }

        # Contextual prompt with candidate & job specifics
        ctx = candidate_context or {}
        ctx_summary = ctx.get("resume_summary") or f"Experienced software engineer applying for {job_title} at {company}."
        prompt = (
            f"You are answering a job application screening question for {company} ({job_title}).\n"
            f"Candidate background: {ctx_summary}\n"
            f"Role details: {job_description[:400] if job_description else job_title}\n"
            f"Question: {question}\n\n"
            f"Provide a direct, professional, first-person answer in 1-2 sentences:"
        )

        try:
            generated = await self.ai_service.generate_text(prompt, max_tokens=200)
            ans_clean = generated.strip() if generated else "Experienced software engineer with strong domain expertise."
        except Exception:
            ans_clean = f"I have direct experience aligning with {job_title} at {company} and look forward to contributing."

        saved = self.save_answer(
            question_text=question,
            answer_text=ans_clean,
            source="ai_generated",
            category=category,
            context="ats_application",
            approved=True,
        )

        return {
            "question": question,
            "answer": ans_clean,
            "source": "ai_generated",
            "cached": False,
            "confidence": 0.95,
        }


    def _build_prompt(self, question_text: str, candidate_context: dict) -> str:
        resume_summary = candidate_context.get("resume_summary", "")
        name = candidate_context.get("name", "the candidate")
        return (
            f"You are answering a job application screening question on behalf "
            f"of {name}. Answer concisely and honestly in first person, in one "
            f"or two sentences, based on the background below.\n\n"
            f"Background:\n{resume_summary}\n\n"
            f"Question: {question_text}\n\n"
            f"Answer:"
        )

    def list_unapproved(self, limit: int = 50) -> list[AnsweredQuestion]:
        """Surface AI-generated answers awaiting human review."""
        return (
            self.db.query(AnsweredQuestion)
            .filter(AnsweredQuestion.approved == False)  # noqa: E712
            .order_by(AnsweredQuestion.created_at.desc())
            .limit(limit)
            .all()
        )

    def approve(self, answer_id: int, edited_answer_text: Optional[str] = None) -> AnsweredQuestion:
        entry = self.db.query(AnsweredQuestion).filter(AnsweredQuestion.id == answer_id).one()
        entry.approved = True
        if edited_answer_text:
            entry.answer_text = edited_answer_text
            entry.source = "edited"
        self.db.commit()
        self.db.refresh(entry)
        return entry
