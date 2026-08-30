from __future__ import annotations

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from .models import (
    InterviewerPersona,
    TurnDialogue,
    InterviewSessionConfig,
    InterviewDiagnosticScorecard,
)
from .engine import hiregram_engine, HiregramVoiceEngine

_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
_COMPLETED_SCORECARDS: Dict[str, InterviewDiagnosticScorecard] = {}


class HiregramService:
    """Manages multi-persona Hiregram live voice interview sessions and scorecards."""

    def __init__(self, engine: Optional[HiregramVoiceEngine] = None):
        self.engine = engine or hiregram_engine

    def start_session(
        self,
        company: str,
        role_title: str,
        persona: InterviewerPersona = InterviewerPersona.RECRUITER_SARA,
        job_description: Optional[str] = None,
        candidate_resume_summary: Optional[str] = None,
        total_questions_target: int = 4,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        s_id = session_id or f"hg-{uuid.uuid4().hex[:8]}"
        config = InterviewSessionConfig(
            session_id=s_id,
            company=company,
            role_title=role_title,
            persona=persona,
            job_description=job_description,
            candidate_resume_summary=candidate_resume_summary,
            total_questions_target=total_questions_target,
            created_at=datetime.utcnow().isoformat(),
        )

        cfg, first_turn = self.engine.start_session(config)

        _ACTIVE_SESSIONS[s_id] = {
            "config": cfg,
            "turns": [first_turn],
            "current_turn_index": 1,
            "is_finished": False,
        }

        return {
            "session_id": s_id,
            "company": cfg.company,
            "role_title": cfg.role_title,
            "persona": cfg.persona,
            "total_questions": cfg.total_questions_target,
            "current_turn": first_turn.model_dump(),
        }

    def submit_turn(
        self,
        session_id: str,
        answer_text: str,
        duration_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        if session_id not in _ACTIVE_SESSIONS:
            raise KeyError(f"Session {session_id} not found or expired.")

        sess = _ACTIVE_SESSIONS[session_id]
        config: InterviewSessionConfig = sess["config"]
        turns: List[TurnDialogue] = sess["turns"]
        idx = sess["current_turn_index"]

        current_turn = turns[-1]
        evaluated_turn = self.engine.evaluate_turn(
            turn=current_turn,
            answer_text=answer_text,
            duration_seconds=duration_seconds,
            company=config.company,
            role=config.role_title,
        )

        next_turn = self.engine.generate_next_turn(
            config=config,
            current_turn_index=idx,
            previous_answer=answer_text,
        )

        if next_turn:
            turns.append(next_turn)
            sess["current_turn_index"] = idx + 1
            is_finished = False
        else:
            is_finished = True
            sess["is_finished"] = True

        return {
            "session_id": session_id,
            "evaluated_turn": evaluated_turn.model_dump(),
            "next_turn": next_turn.model_dump() if next_turn else None,
            "is_finished": is_finished,
            "current_question_number": sess["current_turn_index"],
            "total_questions": config.total_questions_target,
        }

    def finalize_session(self, session_id: str) -> InterviewDiagnosticScorecard:
        if session_id not in _ACTIVE_SESSIONS:
            if session_id in _COMPLETED_SCORECARDS:
                return _COMPLETED_SCORECARDS[session_id]
            raise KeyError(f"Session {session_id} not found.")

        sess = _ACTIVE_SESSIONS[session_id]
        config: InterviewSessionConfig = sess["config"]
        turns: List[TurnDialogue] = [t for t in sess["turns"] if t.completed]

        scorecard = self.engine.finalize_scorecard(config, turns)
        _COMPLETED_SCORECARDS[session_id] = scorecard
        return scorecard

    def get_scorecard(self, session_id: str) -> Optional[InterviewDiagnosticScorecard]:
        return _COMPLETED_SCORECARDS.get(session_id)


hiregram_service = HiregramService()
