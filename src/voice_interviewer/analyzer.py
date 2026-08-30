from __future__ import annotations

import re
from datetime import datetime
from typing import List, Dict, Any

from .models import FillerWordStats, CadenceStats, StarEvaluation, VoiceFeedbackResult

FILLER_WORDS = [
    "um", "uh", "like", "you know", "actually", "basically",
    "sort of", "kind of", "literally", "i mean", "right", "so yeah"
]


class VoiceInterviewAnalyzer:
    """
    Analyzes spoken mock interview transcripts for verbal fluency,
    filler word density, cadence/WPM, and STAR structure completeness.
    """

    def analyze_spoken_response(
        self,
        transcript: str,
        duration_seconds: float,
        target_focus: str = "Distributed Systems",
    ) -> VoiceFeedbackResult:
        low_text = transcript.lower().strip()
        words = re.findall(r"\b\w+\b", low_text)
        word_count = len(words)
        duration_sec = max(5.0, duration_seconds)

        # 1. Filler Words Analysis
        filler_counts: Dict[str, int] = {}
        total_fillers = 0

        for filler in FILLER_WORDS:
            pattern = rf"\b{re.escape(filler)}\b"
            matches = len(re.findall(pattern, low_text))
            if matches > 0:
                filler_counts[filler] = matches
                total_fillers += matches

        filler_pct = round((total_fillers / max(1, word_count)) * 100.0, 1)

        # 2. Cadence / WPM
        wpm = round((word_count / duration_sec) * 60.0, 1)
        if 125.0 <= wpm <= 165.0:
            cadence_rating = "Optimal Cadence (130-160 WPM) 🎯"
            cadence_score = 100.0
        elif wpm > 165.0:
            cadence_rating = "Too Fast (>165 WPM) 🏃"
            cadence_score = max(50.0, 100.0 - ((wpm - 165.0) * 1.5))
        else:
            cadence_rating = "Too Slow (<125 WPM) 🐢"
            cadence_score = max(50.0, 100.0 - ((125.0 - wpm) * 1.5))

        # 3. STAR Structure Completeness Check
        # Situation
        has_sit = bool(re.search(r"\b(when i was at|in my previous role|we were facing|at company|the situation was|project)\b", low_text))
        sit_score = 22.0 if has_sit else 10.0

        # Task
        has_task = bool(re.search(r"\b(my goal was|my task was|needed to|was responsible for|objective was|challenge)\b", low_text))
        task_score = 23.0 if has_task else 12.0

        # Action
        has_action = bool(re.search(r"\b(i designed|i built|i implemented|i led|i decided to|refactored|optimized|architected)\b", low_text))
        action_score = 25.0 if has_action else 14.0

        # Result
        has_result = bool(re.search(r"\b(result was|reduced|improved|increased|by \d+%|saved|scaled to|latency dropped)\b", low_text))
        res_score = 25.0 if has_result else 10.0

        overall_star = round(sit_score + task_score + action_score + res_score, 1)

        # 4. Overall Verbal Delivery Score (40% STAR, 35% Fillers, 25% Cadence)
        filler_score = max(0.0, 100.0 - (filler_pct * 12.0))
        speech_score = round(
            (overall_star * 0.40) + (filler_score * 0.35) + (cadence_score * 0.25),
            1
        )

        tips = []
        if filler_pct > 3.5:
            tips.append(f"High filler word ratio ({filler_pct}% of speech). Practice taking brief 1-second silent pauses instead of saying '{list(filler_counts.keys())[0]}'.")
        if wpm > 165.0:
            tips.append(f"Speech rate ({wpm} WPM) is rapid. Slow down slightly to emphasize key technical architectural decisions.")
        elif wpm < 120.0:
            tips.append(f"Speech rate ({wpm} WPM) is slow. Aim for more continuous flow without prolonged hesitations.")
        if not has_result:
            tips.append("Missing quantifiable Result. Conclude your answer with a concrete metric (e.g. 'reduced latency by 35%').")
        if not tips:
            tips.append("Executive-level verbal delivery: Excellent cadence, minimal filler words, and clean STAR framework execution.")

        return VoiceFeedbackResult(
            speech_delivery_score=speech_score,
            filler_stats=FillerWordStats(
                total_fillers=total_fillers,
                filler_percentage=filler_pct,
                fillers_by_word=filler_counts,
            ),
            cadence_stats=CadenceStats(
                wpm=wpm,
                duration_seconds=round(duration_sec, 1),
                cadence_rating=cadence_rating,
            ),
            star_eval=StarEvaluation(
                situation_score=sit_score,
                task_score=task_score,
                action_score=action_score,
                result_score=res_score,
                overall_star_score=overall_star,
            ),
            delivery_tips=tips,
            timestamp=datetime.utcnow().isoformat(),
        )


voice_interview_analyzer = VoiceInterviewAnalyzer()
