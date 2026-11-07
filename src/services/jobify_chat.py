"""
jobify_chat.py — Jobify Phase 6: conversations, messages, and the streamed reply.

Contract (jobify/docs/INTEGRATION.md, jobify/src/services/chatService.js):
  Conversation = { id, title, mode: ask|agent, updatedAt, messages[] }
  Message      = { id, role: user|assistant, content, at, mode, status: complete|stopped, provider }

Send = POST /api/conversations/:id/messages { content, mode } -> text/event-stream:
  event: user   data: Message            (the saved user turn)
  event: delta  data: { text }           (zero or more reply chunks)
  event: done   data: { message, creditsCharged }
  event: error  data: { code, message, refunded }
Errors found before streaming starts (404, 422, 402 CREDITS_REQUIRED, 503) are normal JSON
error responses, so the client can handle them like any other API call.

Credits: CREDIT_COSTS["chat_message"] is charged when the send is accepted. It is refunded
only if the provider fails before producing any text. Stopping keeps the charge (the model
did the work) and stores the partial reply with status "stopped".
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.api.contract import iso_utc
from src.models import ChatConversation, ChatMessage, User
from src.services.chat_providers import ChatProvider, ChatProviderError, build_prompt
from src.services.credit_service import CREDIT_COSTS, add_credits, deduct_credits

log = logging.getLogger(__name__)

CHAT_ACTION = "chat_message"
MODES = ("ask", "agent")
TITLE_LEN = 48


def chat_cost() -> int:
    return int(CREDIT_COSTS.get(CHAT_ACTION, 5))


# --- shapes ------------------------------------------------------------------------

def message_out(m: ChatMessage) -> Dict[str, Any]:
    return {"id": str(m.id), "role": m.role, "content": m.content, "at": iso_utc(m.created_at), "mode": m.mode,
            "status": m.status, "provider": m.provider}


def conversation_out(c: ChatConversation) -> Dict[str, Any]:
    return {"id": str(c.id), "title": c.title, "mode": c.mode, "updatedAt": iso_utc(c.updated_at),
            "messages": [message_out(m) for m in c.messages]}


def sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# --- conversations -----------------------------------------------------------------

def owned(db: Session, user: User, conversation_id: int) -> ChatConversation:
    conv = (db.query(ChatConversation)
            .filter(ChatConversation.id == conversation_id, ChatConversation.user_id == user.id).first())
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    return conv


def create(db: Session, user: User, mode: str) -> ChatConversation:
    now = datetime.utcnow()
    conv = ChatConversation(user_id=user.id, title="New chat", mode=mode, created_at=now, updated_at=now)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


# --- sending -----------------------------------------------------------------------

def accept_message(db: Session, user: User, conv: ChatConversation, content: str, mode: str) -> ChatMessage:
    """Charge, then store the user turn. Raises 402 before anything is stored."""
    deduct_credits(db, user.id, chat_cost(), CHAT_ACTION, reference_id=f"conversation:{conv.id}",
                   notes="Chat message")
    now = datetime.utcnow()
    if not conv.messages and conv.title == "New chat":
        conv.title = " ".join(content.split())[:TITLE_LEN] or "New chat"
    conv.mode = mode
    conv.updated_at = now
    msg = ChatMessage(conversation_id=conv.id, role="user", content=content, mode=mode, created_at=now)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def history(conv: ChatConversation) -> List[Dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in conv.messages
            if m.role in ("user", "assistant") and m.content]


async def stream_reply(
    *,
    session_factory: Callable[[], Session],
    provider: ChatProvider,
    user_id: int,
    conversation_id: int,
    user_message: Dict[str, Any],
    prompt: List[Dict[str, str]],
    mode: str,
    is_disconnected: Callable[[], Any],
) -> AsyncIterator[str]:
    """SSE body. Persists the assistant turn however the stream ends (done, stopped, error).

    Writes go through a fresh session from `session_factory`, not the request's session, so
    this keeps working if FastAPI closes request dependencies before the body is streamed.
    """
    parts: List[str] = []
    state = {"saved": False}

    def persist(status: str) -> Optional[Dict[str, Any]]:
        if state["saved"]:
            return None
        state["saved"] = True
        content = "".join(parts)
        if not content:
            return None  # nothing to show; a failed send is refunded by the caller
        db = session_factory()
        try:
            now = datetime.utcnow()
            msg = ChatMessage(conversation_id=conversation_id, role="assistant", content=content, mode=mode,
                              status=status, provider=provider.name, created_at=now)
            db.add(msg)
            conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
            if conv is not None:
                conv.updated_at = now
            db.commit()
            db.refresh(msg)
            return message_out(msg)
        finally:
            db.close()

    def refund() -> None:
        db = session_factory()
        try:
            add_credits(db, user_id, chat_cost(), action="chat_message_refund",
                        reference_id=f"conversation:{conversation_id}", notes="Assistant failed to reply")
        finally:
            db.close()

    yield sse("user", user_message)
    try:
        async for chunk in provider.stream(prompt, mode=mode):
            if not chunk:
                continue
            if await is_disconnected():
                persist("stopped")
                return
            parts.append(chunk)
            yield sse("delta", {"text": chunk})
    except (asyncio.CancelledError, GeneratorExit):
        persist("stopped")  # client went away (Stop button / closed tab)
        raise
    except ChatProviderError as exc:
        return_error = (str(exc) or "The assistant could not reply.", "PROVIDER_ERROR")
    except Exception:  # never leak provider internals to the browser
        log.exception("chat provider %s failed", provider.name)
        return_error = ("The assistant could not reply. Try again.", "PROVIDER_ERROR")
    else:
        return_error = None if parts else ("The assistant returned an empty reply. Try again.", "EMPTY_REPLY")

    if return_error is not None:
        if parts:  # partial reply: keep it, keep the charge
            saved = persist("stopped")
            yield sse("error", {"code": return_error[1], "message": return_error[0], "refunded": False,
                                "partial": saved})
        else:
            state["saved"] = True
            refund()
            yield sse("error", {"code": return_error[1], "message": return_error[0], "refunded": True})
        return

    saved = persist("complete")
    yield sse("done", {"message": saved, "creditsCharged": chat_cost()})
