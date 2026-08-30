from __future__ import annotations

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import (
    BooleanDorkResult,
    ChatMessage,
    ChatTurnRequest,
    ChatTurnResponse,
    DorkGenerateRequest,
    DorkGenerateResponse,
)
from .engine import osint_boolean_engine, OSINTBooleanEngine

# In-memory session store for multi-turn conversations
_CHAT_SESSIONS: Dict[str, List[ChatMessage]] = {}


class CopilotService:
    """Manages conversational multi-turn sessions and OSINT Boolean query synthesis."""

    def __init__(self, engine: Optional[OSINTBooleanEngine] = None):
        self.engine = engine or osint_boolean_engine

    def get_starters(self) -> List[Dict[str, str]]:
        return [
            {
                "title": "Find Unindexed Notion & Google Docs JDs",
                "prompt": "Write a Google Boolean Dork to find unlisted Notion and Google Docs job descriptions for Senior Backend Engineers.",
            },
            {
                "title": "Discover Hiring Managers on LinkedIn & X",
                "prompt": "Generate a boolean search string to find Engineering Managers and Directors of Engineering who tweeted or posted that they are hiring.",
            },
            {
                "title": "Uncover Leaked Salary & Leveling Spreadsheets",
                "prompt": "How can I find public Google Spreadsheets with crowdsourced compensation and equity benchmarks for Stripe, OpenAI, and Anthropic?",
            },
            {
                "title": "Search GitHub for Past Take-Home Challenges",
                "prompt": "Write a query to find candidate take-home assignment repositories and solution submissions on GitHub for top tech companies.",
            },
        ]

    def generate_dorks(self, req: DorkGenerateRequest) -> DorkGenerateResponse:
        dorks = self.engine.generate_dorks(
            role=req.role_title,
            company=req.company,
            intent=req.intent or "all",
        )
        return DorkGenerateResponse(
            status="success",
            total_dorks=len(dorks),
            dorks=dorks,
        )

    async def chat(self, req: ChatTurnRequest) -> ChatTurnResponse:
        session_id = req.session_id or str(uuid.uuid4())
        if session_id not in _CHAT_SESSIONS:
            _CHAT_SESSIONS[session_id] = []

        history = [{"role": m.role, "content": m.content} for m in _CHAT_SESSIONS[session_id]]

        # Record user message
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            role="user",
            content=req.message,
            timestamp=datetime.utcnow().isoformat(),
        )
        _CHAT_SESSIONS[session_id].append(user_msg)

        # Generate response
        result = await self.engine.answer_chat(
            message=req.message,
            history=history,
            company=req.target_company,
            role=req.role_title,
        )

        dorks_obj = [d if isinstance(d, BooleanDorkResult) else BooleanDorkResult(**d) for d in result.get("dorks", [])]

        assistant_msg = ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=result["reply"],
            dorks=dorks_obj,
            suggested_followups=result.get("suggested_followups", []),
            timestamp=datetime.utcnow().isoformat(),
        )
        _CHAT_SESSIONS[session_id].append(assistant_msg)

        return ChatTurnResponse(
            status="success",
            session_id=session_id,
            reply=assistant_msg.content,
            dorks=assistant_msg.dorks,
            suggested_followups=assistant_msg.suggested_followups,
        )


copilot_service = CopilotService()
