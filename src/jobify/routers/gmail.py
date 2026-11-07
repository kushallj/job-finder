"""
jobify_gmail_router.py — Phase 3 of the Jobify MVP: real Gmail connection (read-only).

Contract (jobify/docs/INTEGRATION.md): GET /gmail, POST /gmail/connect (returns an OAuth
URL; never fakes success), POST /gmail/sync, DELETE /gmail. State shape:
{ status, email, lastSync, nextScan }. Logic lives in src/jobify/services/gmail_sync.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user
from src.config import settings
from src.database import get_db
from src.models import User
from src.jobify.services import gmail_sync as gs

router = APIRouter(prefix="/api/gmail", tags=["Jobify"])


def _raise(exc: gs.GmailError):
    raise HTTPException(exc.status, {"code": exc.code, "message": exc.message})


def _back_to_app(**params: str) -> RedirectResponse:
    base = settings.frontend_url.rstrip("/")
    return RedirectResponse(f"{base}/app/applications?{urlencode(params)}", status_code=302)


@router.get("")
def get_connection(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    # `available`: whether this server can offer Gmail at all (OAuth client configured).
    return {**gs.connection_state(gs.mailbox_for(db, user)), "available": gs.configured()}


@router.post("/connect")
def connect(user: User = Depends(get_current_user)) -> Dict[str, str]:
    try:
        return {"url": gs.auth_url(user)}
    except gs.GmailError as exc:
        _raise(exc)


@router.get("/callback", include_in_schema=False)
def callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = Query(default=None),
             db: Session = Depends(get_db)) -> RedirectResponse:
    """Public (Google redirects here without our bearer token); trust comes from the signed state."""
    if error:
        return _back_to_app(gmail="error", reason="ACCESS_DENIED" if error == "access_denied" else "GOOGLE_ERROR")
    if not code or not state:
        return _back_to_app(gmail="error", reason="INVALID_CALLBACK")
    try:
        gs.complete_connect(db, code, state, gs.get_client())
    except gs.GmailError as exc:
        return _back_to_app(gmail="error", reason=exc.code)
    return _back_to_app(gmail="connected")


@router.post("/sync")
def sync(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    mb = gs.mailbox_for(db, user)
    if mb is None or not mb.oauth_refresh_token_enc:
        _raise(gs.GmailError("GMAIL_NOT_CONNECTED", "Connect Gmail first", 409))
    stale = mb.updated_at is None or mb.updated_at < datetime.utcnow() - timedelta(minutes=10)
    if mb.sync_status == "syncing" and not stale:  # a crashed sync must not block retries forever
        _raise(gs.GmailError("SYNC_IN_PROGRESS", "A sync is already running", 409))
    try:
        result = gs.sync_mailbox(db, mb, gs.get_client())
    except gs.GmailError as exc:
        _raise(exc)
    return {**gs.connection_state(mb), "result": result}


@router.delete("")
def disconnect(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    return gs.connection_state(gs.disconnect(db, user, gs.get_client()))
