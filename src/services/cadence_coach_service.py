"""
cadence_coach_service.py — Real-Time Voice Biomarker & Cadence Telemetry Engine.
Evaluates Words Per Minute (WPM), filler word density, ramble monologues, and STAR structure.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("cadence_coach")

FILLER_PATTERNS = [
    r"\bum\b", r"\buh\b", r"\blike\b", r"\bbasically\b",
    r"\bactually\b", r"\byou know\b", r"\bsort of\b", r"\bkind of\b",
    r"\bto be honest\b", r"\bI mean\b",
]


class CadenceAnalysisRequest(BaseModel):
    transcript: str
    duration_seconds: float
    is_continuous_monologue: bool = True


class VoiceScorecardRequest(BaseModel):
    session_id: str
    total_duration_seconds: float
    transcripts: List[str]


class CadenceCoachService:
    """Evaluates verbal cadence, non-verbal biomarkers, and executive presence."""

    def analyze_cadence(self, transcript: str, duration_seconds: float) -> Dict[str, Any]:
        """
        Analyzes a spoken audio segment in real-time.
        """
        words = re.findall(r"\w+", transcript.strip())
        word_count = len(words)
        duration_minutes = max(duration_seconds / 60.0, 0.01)
        wpm = round(word_count / duration_minutes, 1)

        # WPM Cadence Classification
        if wpm < 110:
            cadence_status = "Too Slow / Hesitant"
            cadence_color = "#00F0FF"
            pacing_advice = "Pick up pace slightly. Aim for 125–140 WPM to sound confident and energetic."
        elif 110 <= wpm <= 155:
            cadence_status = "Golden Executive Range"
            cadence_color = "#00FFA3"
            pacing_advice = "Perfect pacing. Crisp, authoritative, and easy to follow."
        else:
            cadence_status = "Panic Speed / Rushing"
            cadence_color = "#FF0055"
            pacing_advice = "Slow down. Take a diaphragmatic breath and articulate key keywords."

        # Detect Filler Words
        fillers_detected: Dict[str, int] = {}
        total_fillers = 0
        text_lower = transcript.lower()
        for pattern in FILLER_PATTERNS:
            matches = re.findall(pattern, text_lower)
            if matches:
                word_clean = pattern.replace(r"\b", "")
                fillers_detected[word_clean] = len(matches)
                total_fillers += len(matches)

        # Clarity Score (0 - 100%)
        filler_penalty = min(total_fillers * 6.0, 50.0)
        pacing_penalty = 20.0 if wpm > 170 or wpm < 95 else 0.0
        clarity_score = max(0.0, round(100.0 - filler_penalty - pacing_penalty, 1))

        # Ramble Guard: Check if monologue exceeds 75s threshold
        is_ramble_warning = duration_seconds >= 65.0
        ramble_cue = (
            "⚠️ 75s Monologue: Wrap up your point and check in with the interviewer: "
            "'Does this high-level architecture align with what you had in mind?'"
            if duration_seconds >= 70.0 else None
        )

        return {
            "status": "success",
            "word_count": word_count,
            "duration_seconds": round(duration_seconds, 1),
            "wpm": wpm,
            "cadence_status": cadence_status,
            "cadence_color": cadence_color,
            "pacing_advice": pacing_advice,
            "total_fillers_detected": total_fillers,
            "filler_breakdown": fillers_detected,
            "clarity_score": clarity_score,
            "is_ramble_warning": is_ramble_warning,
            "ramble_check_in_cue": ramble_cue,
        }

    def generate_scorecard(self, session_id: str, total_duration_seconds: float, transcripts: List[str]) -> Dict[str, Any]:
        """
        Generates an end-of-interview executive delivery scorecard.
        """
        full_text = " ".join(transcripts)
        analysis = self.analyze_cadence(full_text, total_duration_seconds)

        # Estimate STAR Framework Progression
        has_situation = any(k in full_text.lower() for k in ["situation", "when i was", "at my previous", "in my last role", "faced with"])
        has_task = any(k in full_text.lower() for k in ["task", "goal was", "needed to", "responsible for", "objective"])
        has_action = any(k in full_text.lower() for k in ["action", "i designed", "i built", "i implemented", "i refactored", "optimized"])
        has_result = any(k in full_text.lower() for k in ["result", "reduced by", "increased by", "latency dropped", "saved", "percent", "%", "lpa"])

        star_score = sum([has_situation, has_task, has_action, has_result]) * 25.0

        # Executive Presence Rating
        overall_score = round((analysis["clarity_score"] * 0.6) + (star_score * 0.4), 1)
        if overall_score >= 85:
            executive_rating = "Principal / Staff Ready (Top 5%)"
        elif overall_score >= 70:
            executive_rating = "Senior Engineer (Strong Delivery)"
        else:
            executive_rating = "Developing (Needs Pacing & STAR Focus)"

        return {
            "status": "success",
            "session_id": session_id,
            "overall_executive_score": overall_score,
            "executive_rating": executive_rating,
            "wpm_summary": {
                "average_wpm": analysis["wpm"],
                "status": analysis["cadence_status"],
            },
            "clarity_summary": {
                "clarity_score": analysis["clarity_score"],
                "total_fillers": analysis["total_fillers_detected"],
                "filler_breakdown": analysis["filler_breakdown"],
            },
            "star_framework_adherence": {
                "score": star_score,
                "situation_detected": has_situation,
                "task_detected": has_task,
                "action_detected": has_action,
                "result_metrics_detected": has_result,
            },
        }
