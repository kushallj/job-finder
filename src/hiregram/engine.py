from __future__ import annotations

import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .models import (
    InterviewerPersona,
    TurnDialogue,
    InterviewSessionConfig,
    InterviewDiagnosticScorecard,
)
from .persona import get_persona_profile

FILLER_WORDS = [
    "um", "uh", "like", "you know", "basically", "actually", "sort of",
    "kind of", "i mean", "right", "literally", "honestly"
]


class HiregramVoiceEngine:
    """
    Simulates realistic turn-by-turn Voice AI interviews, evaluates audio cadence,
    STAR structure, and produces comprehensive diagnostic scorecards.
    """

    def start_session(self, config: InterviewSessionConfig) -> Tuple[InterviewSessionConfig, TurnDialogue]:
        profile = get_persona_profile(config.persona)
        questions = profile.get("question_bank", [])
        first_q_raw = questions[0] if questions else "Can you introduce yourself and your technical background?"
        first_q = first_q_raw.format(company=config.company, role=config.role_title)

        first_turn = TurnDialogue(
            turn_index=1,
            question=first_q,
            interviewer_persona=f"{profile['name']} ({profile['title']})",
            completed=False,
        )
        return config, first_turn

    def evaluate_turn(
        self,
        turn: TurnDialogue,
        answer_text: str,
        duration_seconds: float,
        company: str,
        role: str,
    ) -> TurnDialogue:
        words = re.findall(r'\b[a-zA-Z0-9_\-\']+\b', answer_text)
        word_count = len(words)

        # 1. Cadence & WPM
        effective_duration = max(duration_seconds, 1.0)
        wpm = round((word_count / effective_duration) * 60.0, 1) if duration_seconds > 0 else 140.0

        # 2. Filler words
        lower_answer = answer_text.lower()
        found_fillers = []
        for filler in FILLER_WORDS:
            pattern = rf'\b{re.escape(filler)}\b'
            matches = re.findall(pattern, lower_answer)
            if matches:
                found_fillers.extend([filler] * len(matches))

        # 3. STAR Breakdown
        star_scores = self._score_star(answer_text)
        star_total = sum(star_scores.values()) # 0 to 100

        # 4. Delivery penalty / bonus
        cadence_score = 25.0
        if wpm < 90 or wpm > 200:
            cadence_score -= 8.0
        elif 120 <= wpm <= 165:
            cadence_score += 0.0

        filler_ratio = len(found_fillers) / max(word_count, 1)
        if filler_ratio > 0.08:
            cadence_score -= 10.0
        elif filler_ratio > 0.04:
            cadence_score -= 5.0

        cadence_score = max(5.0, min(25.0, cadence_score))

        # Turn score
        total_turn_score = round(min(100.0, (star_total * 0.75) + cadence_score), 1)

        # 5. Strengths & Improvements
        strengths, improvements = self._extract_feedback(
            answer_text, wpm, found_fillers, star_scores, total_turn_score
        )

        # 6. Gold Standard Ideal Answer Synthesis
        gold_standard = self._synthesize_gold_standard(turn.question, company, role)

        turn.candidate_answer = answer_text
        turn.duration_seconds = duration_seconds
        turn.wpm = wpm
        turn.filler_words_detected = found_fillers
        turn.star_breakdown = star_scores
        turn.turn_score = total_turn_score
        turn.strengths = strengths
        turn.areas_for_improvement = improvements
        turn.gold_standard_ideal_answer = gold_standard
        turn.completed = True

        return turn

    def generate_next_turn(
        self,
        config: InterviewSessionConfig,
        current_turn_index: int,
        previous_answer: str,
    ) -> Optional[TurnDialogue]:
        if current_turn_index >= config.total_questions_target:
            return None

        profile = get_persona_profile(config.persona)
        questions = profile.get("question_bank", [])
        next_idx = current_turn_index
        if next_idx < len(questions):
            q_raw = questions[next_idx]
        else:
            q_raw = "How do you handle technical debt while continuously shipping new features at {company}?"

        next_q = q_raw.format(company=config.company, role=config.role_title)
        return TurnDialogue(
            turn_index=current_turn_index + 1,
            question=next_q,
            interviewer_persona=f"{profile['name']} ({profile['title']})",
            completed=False,
        )

    def finalize_scorecard(
        self,
        config: InterviewSessionConfig,
        completed_turns: List[TurnDialogue],
    ) -> InterviewDiagnosticScorecard:
        if not completed_turns:
            avg_score = 50.0
            tech_depth = 50.0
            star_score = 50.0
            cadence_score = 50.0
            lead_score = 50.0
        else:
            avg_score = round(sum(t.turn_score for t in completed_turns) / len(completed_turns), 1)
            star_score = round(sum(sum(t.star_breakdown.values()) for t in completed_turns) / len(completed_turns), 1)
            cadence_score = round(min(100.0, sum(t.wpm for t in completed_turns) / len(completed_turns) * 0.65), 1)
            tech_depth = round(min(100.0, avg_score * 1.05), 1)
            lead_score = round(min(100.0, avg_score * 0.95), 1)

        if avg_score >= 84.0:
            verdict = "Strong Hire (Exceeds Bar)"
        elif avg_score >= 72.0:
            verdict = "Lean Hire (Meets Bar)"
        elif avg_score >= 60.0:
            verdict = "Needs Polish (Borderline)"
        else:
            verdict = "High Risk (Significant Gaps)"

        key_strengths = [
            f"Crisp technical articulation aligning with {config.role_title} requirements.",
            "Evidenced ownership and structured situational context provided.",
            "Strong communication cadence within the optimal 130–160 WPM interview window.",
        ]

        improvements = [
            "Quantify results with hard production metrics (e.g. latency dropped by 35%, throughput scaled 5x).",
            "Be explicit about alternative architectural tradeoffs evaluated before settling on the chosen solution.",
            "Minimize pause fillers during transitions between the Task and Action phases.",
        ]

        practice_drills = [
            f"Practice 2-minute timed STAR elevator pitches for {config.company}.",
            "Run 3 back-of-the-envelope capacity estimations for distributed caches and message queues.",
            "Drill the 'Tell me about a failure' response using the 70/30 Action-to-Reflection ratio.",
        ]

        return InterviewDiagnosticScorecard(
            session_id=config.session_id,
            company=config.company,
            role_title=config.role_title,
            persona=config.persona,
            overall_score=avg_score,
            readiness_verdict=verdict,
            technical_depth_score=tech_depth,
            star_structure_score=star_score,
            delivery_cadence_score=cadence_score,
            leadership_impact_score=lead_score,
            turns=completed_turns,
            key_strengths=key_strengths,
            high_priority_improvements=improvements,
            practice_drills_recommended=practice_drills,
            created_at=datetime.utcnow().isoformat(),
        )

    def _score_star(self, text: str) -> Dict[str, float]:
        lower = text.lower()
        has_situation = any(k in lower for k in ["when", "at my previous", "in my role", "we were facing", "the context", "the problem was"])
        has_task = any(k in lower for k in ["my goal", "my responsibility", "tasked with", "needed to", "objective was"])
        has_action = any(k in lower for k in ["i designed", "i implemented", "i led", "i refactored", "i architected", "i resolved", "i created"])
        has_result = any(k in lower for k in ["as a result", "reduced by", "increased by", "improved", "%", "ms", "rps", "delivered", "outcome"])

        return {
            "situation": 25.0 if has_situation else 12.0,
            "task": 25.0 if has_task else 14.0,
            "action": 25.0 if has_action else 15.0,
            "result": 25.0 if has_result else 10.0,
        }

    def _extract_feedback(
        self,
        text: str,
        wpm: float,
        fillers: List[str],
        star: Dict[str, float],
        score: float,
    ) -> Tuple[List[str], List[str]]:
        strengths = []
        improvements = []

        if star.get("action", 0) >= 20.0:
            strengths.append("Clear description of direct personal engineering actions ('I built/designed').")
        if star.get("result", 0) >= 20.0:
            strengths.append("Highlighted measurable business impact and performance outcomes.")
        if 120 <= wpm <= 165:
            strengths.append(f"Ideal speaking cadence at {wpm} words per minute.")
        if not strengths:
            strengths.append("Direct answer that addressed the core interviewer prompt.")

        if star.get("result", 0) < 20.0:
            improvements.append("Strengthen the Result phase: state quantifiable metrics (e.g. latency, cost, uptime).")
        if star.get("situation", 0) < 20.0:
            improvements.append("Provide crisper context in the first 15 seconds to set up the problem.")
        if len(fillers) >= 4:
            improvements.append(f"Detected {len(fillers)} verbal fillers ({', '.join(set(fillers))}). Replace with deliberate pauses.")
        if wpm < 100:
            improvements.append(f"Cadence was a bit slow ({wpm} WPM). Aim for brisk, energetic delivery.")
        elif wpm > 185:
            improvements.append(f"Cadence was quite rapid ({wpm} WPM). Pace your explanation to ensure clarity.")

        return strengths, improvements

    def _synthesize_gold_standard(self, question: str, company: str, role: str) -> str:
        return (
            f"\"In my recent role as a {role}, our distributed payment pipeline experienced intermittent 400ms latency spikes under peak load. "
            f"My objective was to eliminate tail latency while preserving strict idempotency and zero data loss. "
            f"I decoupled the synchronous database write path by introducing an asynchronous write-behind cache with Redis Cluster, "
            f"implemented exponential backoff with jitter on transient network failures, and instrumented distributed OpenTelemetry tracing. "
            f"As a result, p99 latency dropped from 420ms to 18ms, throughput scaled 4.5x to 85,000 RPS, and we maintained 99.999% availability during peak traffic.\""
        )


hiregram_engine = HiregramVoiceEngine()
