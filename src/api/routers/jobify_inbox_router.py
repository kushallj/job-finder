"""
jobify_inbox_router.py — the user's job-hunt email address and in-app inbox.

  POST /api/inbound/email            public; Cloudflare Email Worker delivery (HMAC-signed)
  GET  /api/inbox                    { address, receiving, sending, unread }
  GET  /api/inbox/messages           list shape; ?applicationId= filters to one card
  GET  /api/inbox/messages/{id}      full message (marks it read)
  POST /api/inbox/messages/{id}/reply  { body } -> sent message (explicit user action only)

Logic lives in src/services/jobify_inbox.py.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.contract import paginate
from src.auth.dependencies import get_current_user
from src.config import settings
from src.database import get_db
from src.models import InboundRecruiterMessage, MailboxAccount, User
from src.services import jobify_inbox as ib

router = APIRouter(tags=["Jobify"])


def _raise(exc: ib.InboxError):
    raise HTTPException(exc.status, {"code": exc.code, "message": exc.message})


@router.post("/api/inbound/email", status_code=202, include_in_schema=False)
async def inbound_email(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    length = int(request.headers.get("content-length") or 0)
    if length > settings.inbound_max_bytes:
        _raise(ib.InboxError("TOO_LARGE", "Message too large", 413))
    raw = await request.body()
    if len(raw) > settings.inbound_max_bytes:
        _raise(ib.InboxError("TOO_LARGE", "Message too large", 413))
    try:
        ib.verify_signature(request.headers.get("x-jobify-timestamp"), request.headers.get("x-jobify-signature"), raw)
        return ib.receive(db, raw, request.headers.get("x-jobify-envelope-to", ""))
    except ib.InboxError as exc:
        _raise(exc)


@router.get("/api/inbox")
def get_inbox(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        mb = ib.get_or_create_inbox(db, user)
    except ib.InboxError as exc:
        _raise(exc)
    unread = 0
    if mb is not None:
        unread = (db.query(InboundRecruiterMessage)
                  .filter(InboundRecruiterMessage.mailbox_id == mb.id, InboundRecruiterMessage.direction == "in",
                          InboundRecruiterMessage.is_read.isnot(True)).count())
    return {"address": mb.email_address if mb else None, "receiving": ib.receiving_configured(),
            "sending": ib.sending_configured(), "unread": unread}


@router.get("/api/inbox/messages")
def list_messages(applicationId: Optional[int] = None, page: int = Query(default=1, ge=1),
                  pageSize: int = Query(default=50, ge=1, le=100),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    query = (db.query(InboundRecruiterMessage)
             .join(MailboxAccount, InboundRecruiterMessage.mailbox_id == MailboxAccount.id)
             .filter(MailboxAccount.user_id == user.id, MailboxAccount.provider == ib.PROVIDER))
    if applicationId is not None:
        query = query.filter(InboundRecruiterMessage.application_id == applicationId)
    query = query.order_by(InboundRecruiterMessage.received_at.desc(), InboundRecruiterMessage.id.desc())
    return paginate(query, page, pageSize, mapper=ib.to_ui)


@router.get("/api/inbox/messages/{msg_id:int}")
def get_message(msg_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        row = ib.owned_message(db, user, msg_id)
    except ib.InboxError as exc:
        _raise(exc)
    if not row.is_read:
        row.is_read = True
        db.commit()
    return ib.to_ui(row, full=True)


class ReplyBody(BaseModel):
    body: str = Field(min_length=1, max_length=20_000)


@router.post("/api/inbox/messages/{msg_id:int}/reply", status_code=201)
def reply(msg_id: int, payload: ReplyBody, user: User = Depends(get_current_user),
          db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return ib.to_ui(ib.reply(db, user, msg_id, payload.body), full=True)
    except ib.InboxError as exc:
        _raise(exc)
