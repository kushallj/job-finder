"""
gmail_sync.py — Real Gmail connection for the Jobify Applications board (read-only).

Flow: POST /api/gmail/connect -> Google consent (gmail.readonly) -> GET /api/gmail/callback
-> encrypted refresh token on MailboxAccount -> POST /api/gmail/sync (and a daily Celery
beat job) reads recent mail, matches it to *this user's* applications, classifies it with
InboundEmailIntentClassifier and advances cards.

Privacy rules:
  - Scope is gmail.readonly. Nothing is ever sent or modified in the user's mailbox.
  - Only messages that match one of the user's applications are stored; everything
    else is read for matching and discarded.
  - The refresh token is Fernet-encrypted at rest and never returned by the API.
  - Disconnect revokes the token at Google and clears stored message bodies.
"""

from __future__ import annotations

import base64
import re
import secrets
import time
from datetime import datetime, timedelta
from email.utils import parseaddr
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy.orm import Session

from src.api.contract import iso_utc
from src.config import settings
from src.models import Application, InboundRecruiterMessage, MailboxAccount, User
from src.services.inbound_email_classifier import InboundEmailIntentClassifier
from src.services.mail_ingest import ParsedMessage, ingest_message, match_application  # noqa: F401  (re-exported)

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
SCOPES = f"openid email {GMAIL_SCOPE}"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
STATE_TTL_SECONDS = 600
SYNC_INTERVAL = timedelta(days=1)
MAX_BODY_CHARS = 20_000

class GmailError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def configured() -> bool:
    return bool(settings.google_oauth_client_id and settings.google_oauth_client_secret and settings.token_encryption_key)


# --- token encryption -----------------------------------------------------------------

def _fernet():
    from cryptography.fernet import Fernet

    if not settings.token_encryption_key:
        raise GmailError("GMAIL_NOT_CONFIGURED", "Gmail is not configured on this server", 503)
    return Fernet(settings.token_encryption_key.encode())


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(blob: str) -> str:
    return _fernet().decrypt(blob.encode()).decode()


# --- OAuth state ------------------------------------------------------------------------

def make_state(user: User) -> str:
    now = int(time.time())
    return jwt.encode({"uid": user.id, "purpose": "gmail_connect", "nonce": secrets.token_urlsafe(8),
                       "iat": now, "exp": now + STATE_TTL_SECONDS}, settings.jwt_secret_key, algorithm="HS256")


def read_state(state: str) -> int:
    try:
        claims = jwt.decode(state, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise GmailError("INVALID_STATE", f"Invalid or expired connect link: {exc}") from exc
    if claims.get("purpose") != "gmail_connect" or not isinstance(claims.get("uid"), int):
        raise GmailError("INVALID_STATE", "Invalid connect link")
    return claims["uid"]


def auth_url(user: User) -> str:
    if not configured():
        raise GmailError("GMAIL_NOT_CONFIGURED", "Gmail is not configured on this server", 503)
    return AUTH_URL + "?" + urlencode({
        "client_id": settings.google_oauth_client_id, "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code", "scope": SCOPES, "access_type": "offline", "prompt": "consent",
        "include_granted_scopes": "true", "state": make_state(user),
    })


# --- Google HTTP (one class so tests can swap it) ------------------------------------------

class GoogleClient:
    def __init__(self, timeout: float = 20.0):
        self.http = httpx.Client(timeout=timeout)

    def _check(self, res: httpx.Response, what: str) -> Dict[str, Any]:
        if res.status_code >= 400:
            if res.status_code in (400, 401) and "invalid_grant" in res.text:
                raise GmailError("GMAIL_REAUTH_REQUIRED", "Gmail access was revoked or expired. Connect again.", 409)
            raise GmailError("GMAIL_API_ERROR", f"Google {what} failed ({res.status_code})", 502)
        return res.json() if res.content else {}

    def exchange_code(self, code: str) -> Dict[str, Any]:
        return self._check(self.http.post(TOKEN_URL, data={
            "code": code, "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "redirect_uri": settings.google_oauth_redirect_uri, "grant_type": "authorization_code"}), "token exchange")

    def refresh(self, refresh_token: str) -> str:
        data = self._check(self.http.post(TOKEN_URL, data={
            "refresh_token": refresh_token, "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret, "grant_type": "refresh_token"}), "token refresh")
        return data["access_token"]

    def userinfo(self, access_token: str) -> Dict[str, Any]:
        return self._check(self.http.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}), "userinfo")

    def list_messages(self, access_token: str, query: str, limit: int) -> List[str]:
        data = self._check(self.http.get(f"{GMAIL_API}/messages", params={"q": query, "maxResults": limit},
                                         headers={"Authorization": f"Bearer {access_token}"}), "message list")
        return [m["id"] for m in data.get("messages", [])]

    def get_message(self, access_token: str, msg_id: str) -> Dict[str, Any]:
        return self._check(self.http.get(f"{GMAIL_API}/messages/{msg_id}", params={"format": "full"},
                                         headers={"Authorization": f"Bearer {access_token}"}), "message read")

    def revoke(self, token: str) -> None:
        try:
            self.http.post(REVOKE_URL, data={"token": token})
        except httpx.HTTPError:
            pass  # best effort; local token is deleted regardless


def get_client() -> GoogleClient:
    return GoogleClient()


# --- connection state (shape: applicationService.getConnection) -------------------------

def mailbox_for(db: Session, user: User) -> Optional[MailboxAccount]:
    return (db.query(MailboxAccount).filter(MailboxAccount.user_id == user.id, MailboxAccount.provider == "gmail")
            .order_by(MailboxAccount.id.desc()).first())


def connection_state(mb: Optional[MailboxAccount]) -> Dict[str, Any]:
    if mb is None or not mb.sync_status:
        return {"status": "not_connected", "email": None, "lastSync": None, "nextScan": None}
    live = mb.sync_status in ("connected", "syncing", "failed")
    return {
        "status": mb.sync_status,
        "email": mb.email_address if live else None,
        "lastSync": iso_utc(mb.last_sync_at) if live else None,
        "nextScan": iso_utc(mb.next_scan_at) if live else None,
        **({"error": mb.last_error} if mb.sync_status == "failed" and mb.last_error else {}),
    }


def complete_connect(db: Session, code: str, state: str, client: GoogleClient) -> MailboxAccount:
    user = db.query(User).filter(User.id == read_state(state)).first()
    if user is None:
        raise GmailError("INVALID_STATE", "Account not found")
    tokens = client.exchange_code(code)
    if GMAIL_SCOPE not in (tokens.get("scope") or ""):
        raise GmailError("GMAIL_SCOPE_DENIED", "Gmail read access was not granted")
    refresh = tokens.get("refresh_token")
    if not refresh:
        raise GmailError("GMAIL_NO_REFRESH_TOKEN", "Google did not return offline access. Try connecting again.")
    email = (client.userinfo(tokens["access_token"]).get("email") or "").lower()
    if not email:
        raise GmailError("GMAIL_API_ERROR", "Google did not return the account email", 502)

    taken = db.query(MailboxAccount).filter(MailboxAccount.email_address == email).first()
    if taken and taken.user_id != user.id:
        raise GmailError("GMAIL_IN_USE", "This Gmail account is connected to another Jobify account", 409)
    mb = taken or mailbox_for(db, user) or MailboxAccount(user_id=user.id, provider="gmail")
    mb.user_id, mb.provider, mb.email_address = user.id, "gmail", email
    mb.imap_host, mb.is_connected, mb.auto_advance_pipeline = None, True, True
    mb.oauth_refresh_token_enc = encrypt_token(refresh)
    mb.sync_status, mb.last_error = "connected", None
    mb.next_scan_at = datetime.utcnow()
    db.add(mb)
    db.commit()
    return mb


def disconnect(db: Session, user: User, client: GoogleClient) -> MailboxAccount | None:
    mb = mailbox_for(db, user)
    if mb is None:
        return None
    if mb.oauth_refresh_token_enc:
        try:
            client.revoke(decrypt_token(mb.oauth_refresh_token_enc))
        except Exception:  # noqa: BLE001  undecryptable token: still wipe it locally
            pass
    mb.oauth_refresh_token_enc = None
    mb.sync_status, mb.is_connected, mb.last_error, mb.next_scan_at = "disconnected", False, None, None
    for msg in db.query(InboundRecruiterMessage).filter(InboundRecruiterMessage.mailbox_id == mb.id):
        msg.body_text, msg.snippet = None, None
    db.commit()
    return mb


# --- message parsing ----------------------------------------------------------------------

def _header(msg: Dict[str, Any], name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _body_text(part: Dict[str, Any]) -> str:
    mime = part.get("mimeType", "")
    data = part.get("body", {}).get("data")
    if data and mime in ("text/plain", "text/html"):
        raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
        return re.sub(r"<[^>]+>", " ", raw) if mime == "text/html" else raw
    texts = [_body_text(p) for p in part.get("parts", []) or []]
    plain = [t for p, t in zip(part.get("parts", []) or [], texts) if p.get("mimeType") == "text/plain" and t]
    return (plain or [t for t in texts if t] or [""])[0]


def parse_message(raw: Dict[str, Any]) -> ParsedMessage:
    name, addr = parseaddr(_header(raw, "From"))
    ts = int(raw.get("internalDate", "0") or 0) / 1000
    return ParsedMessage(
        id=raw["id"], thread_id=raw.get("threadId", ""), sender_email=addr.lower(), sender_name=name,
        subject=_header(raw, "Subject")[:500], snippet=(raw.get("snippet") or "")[:500],
        body=_body_text(raw.get("payload", {}))[:MAX_BODY_CHARS],
        received_at=datetime.utcfromtimestamp(ts) if ts else datetime.utcnow(),
    )


# --- sync -------------------------------------------------------------------------------------

def sync_mailbox(db: Session, mb: MailboxAccount, client: GoogleClient, now: Optional[datetime] = None) -> Dict[str, int]:
    now = now or datetime.utcnow()
    if not mb.oauth_refresh_token_enc:
        raise GmailError("GMAIL_NOT_CONNECTED", "Gmail is not connected", 409)
    mb.sync_status = "syncing"
    db.commit()
    try:
        access = client.refresh(decrypt_token(mb.oauth_refresh_token_enc))
        since = mb.last_sync_at or (now - timedelta(days=settings.gmail_sync_lookback_days))
        query = f"after:{int(since.timestamp())} -category:promotions -category:social"
        ids = client.list_messages(access, query, settings.gmail_sync_max_messages)
        seen = {m for (m,) in db.query(InboundRecruiterMessage.message_id)
                .filter(InboundRecruiterMessage.mailbox_id == mb.id, InboundRecruiterMessage.message_id.in_(ids)).all()} if ids else set()
        apps = (db.query(Application).filter(Application.user_id == mb.user_id)
                .order_by(Application.updated_at.desc()).all())
        classifier = InboundEmailIntentClassifier()
        stored = advanced = 0
        for msg_id in ids:
            if msg_id in seen:
                continue
            row = ingest_message(db, mb, parse_message(client.get_message(access, msg_id)), apps, classifier,
                                 store_unmatched=False)  # personal inbox: unrelated mail is never stored
            if row is not None:
                stored += 1
                advanced += int(bool(row.auto_advanced))
        mb.total_messages_scanned = (mb.total_messages_scanned or 0) + len(ids)
        mb.total_advancements = (mb.total_advancements or 0) + advanced
        mb.last_sync_at, mb.next_scan_at = now, now + SYNC_INTERVAL
        mb.sync_status, mb.last_error = "connected", None
        db.commit()
        return {"scanned": len(ids), "stored": stored, "advanced": advanced}
    except GmailError as exc:
        db.rollback()
        mb.sync_status = "disconnected" if exc.code == "GMAIL_REAUTH_REQUIRED" else "failed"
        mb.last_error = exc.message
        if exc.code == "GMAIL_REAUTH_REQUIRED":
            mb.oauth_refresh_token_enc = None
        db.commit()
        raise
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        mb.sync_status, mb.last_error = "failed", "Sync failed. Try again later."
        db.commit()
        raise GmailError("GMAIL_SYNC_FAILED", "Sync failed. Try again later.", 502) from exc
