"""
Inbound Recruiter Email Intent Classifier.

Scans incoming recruiter messages, classifies their intent:
- INTERVIEW_INVITATION -> target stage: technical_interview / recruiter_screen, Next: Technical Interview in 3 days (Amber)
- ASSESSMENT -> target stage: take_home, Next: Take-home assessment in 6 days (Blue)
- OFFER -> target stage: offer, Next: Offer Review in 4 days (Blue)
- REJECTION -> target stage: rejected (Archived)
- FOLLOW_UP_REQUIRED -> maintains stage, Overdue / Follow-up required (Red)
"""

import re
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class IntentClassificationResult:
    """Detailed result of inbound email classification."""
    intent: str
    confidence: float
    target_stage: Optional[str]
    action_title: Optional[str]
    countdown_days: Optional[int]
    explanation: str


class InboundEmailIntentClassifier:
    """Rule-based and heuristic NLP classifier for inbound recruiter emails."""

    # Patterns mapped by intent with weights
    OFFER_PATTERNS = [
        r"\boffer\s+letter\b",
        r"\bformal\s+offer\b",
        r"\bpleased\s+to\s+offer\b",
        r"\bdelighted\s+to\s+offer\b",
        r"\bjob\s+offer\b",
        r"\bcongratulations\s+on\s+your\s+offer\b",
        r"\bwelcome\s+to\s+the\s+team\b",
        r"\boffer\s+of\s+employment\b",
        r"\bemployment\s+agreement\b",
    ]

    REJECTION_PATTERNS = [
        r"\bnot\s+moving\s+forward\b",
        r"\bdecided\s+to\s+pursue\s+other\b",
        r"\bchosen\s+to\s+move\s+forward\s+with\s+other\b",
        r"\bwill\s+not\s+be\s+moving\s+forward\b",
        r"\bunfortunately\b.*\b(not\s+selected|other\s+candidates|not\s+moving)\b",
        r"\bother\s+applicants\s+whose\s+qualifications\b",
        r"\bposition\s+has\s+been\s+filled\b",
        r"\bwe\s+regret\s+to\s+inform\b",
        r"\bwish\s+you\s+(the\s+best|all\s+the\s+best)\s+in\s+your\s+job\s+search\b",
        r"\bkeep\s+your\s+resume\s+on\s+file\b",
    ]

    ASSESSMENT_PATTERNS = [
        r"\btake-?home\b",
        r"\bcoding\s+assessment\b",
        r"\btechnical\s+assessment\b",
        r"\bonline\s+assessment\b",
        r"\bcoding\s+challenge\b",
        r"\btechnical\s+challenge\b",
        r"\bhackerrank\b",
        r"\bcodesignal\b",
        r"\bcoderbyte\b",
        r"\btestgorilla\b",
        r"\bleetcode\b",
        r"\bcomplete\s+the\s+following\s+(test|assignment|assessment|task)\b",
    ]

    INTERVIEW_PATTERNS = [
        r"\binterview\s+invitation\b",
        r"\binvitation\s+to\s+interview\b",
        r"\bschedule\s+(an?|our|the)\s+interview\b",
        r"\bschedule\s+(a\s+)?time\s+to\s+speak\b",
        r"\bphone\s+screen\b",
        r"\brecruiter\s+screen\b",
        r"\btechnical\s+interview\b",
        r"\bchat\s+with\s+(our|the)\s+(team|hiring\s+manager)\b",
        r"\bspeak\s+with\s+(our|the)\s+(team|hiring\s+manager)\b",
        r"\bnext\s+round\s+of\s+interviews\b",
        r"\bavailability\s+for\s+a\s+(quick\s+)?(chat|call|interview)\b",
        r"\bcalendly\.com\b",
        r"\bgoodtime\.io\b",
        r"\bzoom\.us\/j\b",
        r"\bmeet\.google\.com\b",
    ]

    FOLLOW_UP_PATTERNS = [
        r"\baction\s+required\b",
        r"\badditional\s+information\s+(needed|required|requested)\b",
        r"\bplease\s+(provide|send|confirm)\s+your\b",
        r"\bupdate\s+on\s+your\s+application\b",
        r"\bfollow-?up\s+required\b",
        r"\bwaiting\s+on\s+your\s+response\b",
        r"\bplease\s+reply\s+by\b",
    ]

    def classify(self, subject: str, body: str) -> IntentClassificationResult:
        """
        Classifies subject and body text into one of 5 canonical recruiter intents:
        1. OFFER
        2. REJECTION
        3. ASSESSMENT
        4. INTERVIEW_INVITATION
        5. FOLLOW_UP_REQUIRED
        """
        text = f"{subject or ''}\n{body or ''}".lower()
        sub_lower = (subject or "").lower()

        # Check OFFER first (highest priority positive outcome)
        if any(re.search(p, text) for p in self.OFFER_PATTERNS):
            return IntentClassificationResult(
                intent="OFFER",
                confidence=0.98,
                target_stage="offer",
                action_title="Offer Review",
                countdown_days=4,
                explanation="Formal offer / employment agreement detected in recruiter email."
            )

        # Check REJECTION next
        if any(re.search(p, text) for p in self.REJECTION_PATTERNS):
            return IntentClassificationResult(
                intent="REJECTION",
                confidence=0.95,
                target_stage="rejected",
                action_title="Application Closed",
                countdown_days=None,
                explanation="Candidate disposition / rejection noticed in recruiter message."
            )

        # Check ASSESSMENT
        if any(re.search(p, text) for p in self.ASSESSMENT_PATTERNS):
            return IntentClassificationResult(
                intent="ASSESSMENT",
                confidence=0.95,
                target_stage="take_home",
                action_title="Take-home assessment",
                countdown_days=6,
                explanation="Coding challenge or take-home assignment instructions detected."
            )

        # Check INTERVIEW_INVITATION
        if any(re.search(p, text) for p in self.INTERVIEW_PATTERNS):
            # Discern recruiter screen vs technical interview
            is_screen = bool(re.search(r"\b(phone\s+screen|recruiter\s+screen|introductory\s+call|initial\s+chat)\b", text))
            target_stage = "recruiter_screen" if is_screen else "technical_interview"
            action_title = "Recruiter Screen" if is_screen else "Technical Interview"
            return IntentClassificationResult(
                intent="INTERVIEW_INVITATION",
                confidence=0.95,
                target_stage=target_stage,
                action_title=action_title,
                countdown_days=3,
                explanation="Interview invitation and scheduling context identified."
            )

        # Check FOLLOW_UP_REQUIRED
        if any(re.search(p, text) for p in self.FOLLOW_UP_PATTERNS):
            return IntentClassificationResult(
                intent="FOLLOW_UP_REQUIRED",
                confidence=0.88,
                target_stage=None,  # Keep current stage!
                action_title="Follow-up required",
                countdown_days=-1,  # Red alert: Overdue
                explanation="Recruiter requested follow-up action or additional information."
            )

        # Default fallback: If subject mentions "interview", treat as INTERVIEW_INVITATION
        if "interview" in sub_lower:
            return IntentClassificationResult(
                intent="INTERVIEW_INVITATION",
                confidence=0.80,
                target_stage="technical_interview",
                action_title="Technical Interview",
                countdown_days=3,
                explanation="Subject references interview progression."
            )

        # Generic update / follow-up
        return IntentClassificationResult(
            intent="FOLLOW_UP_REQUIRED",
            confidence=0.70,
            target_stage=None,
            action_title="Follow-up required",
            countdown_days=-1,
            explanation="Unclassified recruiter message received requiring review."
        )
