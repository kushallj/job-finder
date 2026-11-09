"""
jobify_chat_router.py — Phase 6 of the Jobify MVP: Chat.

  GET    /api/conversations?page&pageSize     {items: Conversation[], total, page, pageSize}, newest first
  POST   /api/conversations {mode}            Conversation
  PATCH  /api/conversations/{id} {title?, mode?}
  DELETE /api/conversations/{id}              204
  POST   /api/conversations/{id}/messages {content, mode}   text/event-stream (see jobify_chat.py)

The reply comes from settings.chat_provider (src/jobify/services/chat_providers.py; "echo" until an
LLM is chosen). Providers never send anything: agent mode returns drafts only.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.api.contract import paginate
from src.api.deps import CURRENT_USER, DB_SESSION
from src.database import SessionLocal
from src.jobify.services import chat as jc
from src.jobify.services.chat_context import build_user_context
from src.jobify.services.chat_providers import (
    ChatProvider,
    ChatProviderError,
    build_prompt,
    get_chat_provider,
)
from src.models import ChatConversation, User

router = APIRouter(prefix="/api/conversations", tags=["Jobify"])

MAX_MESSAGE_CHARS = 8000


def get_session_factory() -> Callable[[], Session]:
    """Sessions for work done while the response streams (overridden in tests)."""
    return SessionLocal


def chat_provider() -> ChatProvider:
    try:
        return get_chat_provider()
    except ChatProviderError as exc:
        raise HTTPException(503, detail={"code": "CHAT_UNAVAILABLE", "message": str(exc)}) from exc


class NewConversation(BaseModel):
    mode: str = Field(default="agent", pattern="^(ask|agent)$")


class ConversationPatch(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    mode: str | None = Field(default=None, pattern="^(ask|agent)$")

    @field_validator("title")
    @classmethod
    def _title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = " ".join(v.split())
        if not v:
            raise ValueError("Title can't be empty")
        return v


class SendBody(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    mode: str = Field(default="agent", pattern="^(ask|agent)$")

    @field_validator("content")
    @classmethod
    def _content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message can't be empty")
        return v.strip()


@router.get("")
def list_conversations(user: User = CURRENT_USER, db: Session = DB_SESSION, page: int = Query(default=1, ge=1), pageSize: int = Query(default=50, ge=1, le=100)) -> dict[str, Any]:
    query = (db.query(ChatConversation).filter(ChatConversation.user_id == user.id)
             .order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc()))
    return paginate(query, page, pageSize, jc.conversation_out)


@router.post("")
def create_conversation(user: User = CURRENT_USER, db: Session = DB_SESSION, body: NewConversation | None = None) -> dict[str, Any]:
    return jc.conversation_out(jc.create(db, user, (body or NewConversation()).mode))


@router.patch("/{conversation_id:int}")
def update_conversation(conversation_id: int, body: ConversationPatch, user: User = CURRENT_USER, db: Session = DB_SESSION) -> dict[str, Any]:
    conv = jc.owned(db, user, conversation_id)
    if body.title is not None:
        conv.title = body.title
    if body.mode is not None:
        conv.mode = body.mode
    db.commit()
    db.refresh(conv)
    return jc.conversation_out(conv)


@router.delete("/{conversation_id:int}", status_code=204)
def delete_conversation(conversation_id: int, user: User = CURRENT_USER, db: Session = DB_SESSION) -> Response:
    db.delete(jc.owned(db, user, conversation_id))
    db.commit()
    return Response(status_code=204)


@router.post("/{conversation_id:int}/messages")
async def send_message(conversation_id: int, body: SendBody, request: Request, user: User = CURRENT_USER, db: Session = DB_SESSION, provider: ChatProvider = Depends(chat_provider), session_factory: Callable[[], Session] = Depends(get_session_factory)) -> StreamingResponse:
    conv = jc.owned(db, user, conversation_id)
    jc.check_rate_limit(db, user)  # 429, before charging
    user_msg = jc.accept_message(db, user, conv, body.content, body.mode)  # 402 before anything is stored
    db.refresh(conv)
    prompt = build_prompt(jc.history(conv), body.mode, context=build_user_context(db, user))
    events = jc.stream_reply(session_factory=session_factory, provider=provider, user_id=user.id,
                             conversation_id=conv.id, user_message=jc.message_out(user_msg), prompt=prompt,
                             mode=body.mode, is_disconnected=request.is_disconnected)
    return StreamingResponse(events, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
