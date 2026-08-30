from __future__ import annotations

import base64
import hashlib
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import httpx
from sqlalchemy.orm import Session

from src.models import XOAuthToken

X_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"

DEFAULT_SCOPES = [
    "tweet.read",
    "tweet.write",
    "users.read",
    "follows.read",
    "follows.write",
    "dm.read",
    "dm.write",
    "like.write",
    "offline.access",
]


class XOAuthHandler:
    """Handles OAuth 2.0 PKCE authentication flow for X (Twitter) API v2."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        self.client_id = (client_id or os.getenv("X_CLIENT_ID", "")).strip()
        self.client_secret = (client_secret or os.getenv("X_CLIENT_SECRET", "")).strip()
        self.redirect_uri = (redirect_uri or os.getenv("X_REDIRECT_URI", "http://localhost:8000/api/x/auth/callback")).strip()
        self._in_memory_states: Dict[str, str] = {}  # state -> code_verifier

    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generates a high-entropy code_verifier and SHA256 code_challenge."""
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return code_verifier, code_challenge

    def get_authorization_url(self, scopes: Optional[list[str]] = None) -> Dict[str, str]:
        """Builds the OAuth 2.0 PKCE authorization link."""
        code_verifier, code_challenge = self.generate_pkce_pair()
        state = secrets.token_urlsafe(24)
        self._in_memory_states[state] = code_verifier

        scope_str = " ".join(scopes or DEFAULT_SCOPES)
        params = {
            "response_type": "code",
            "client_id": self.client_id or "MOCK_X_CLIENT_ID",
            "redirect_uri": self.redirect_uri,
            "scope": scope_str,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        url = f"{X_AUTH_URL}?{urllib.parse.urlencode(params)}"
        return {
            "authorization_url": url,
            "state": state,
            "code_verifier": code_verifier,
        }

    async def exchange_code_for_tokens(
        self,
        code: str,
        state: str,
        verifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exchanges authorization code for access and refresh tokens."""
        code_verifier = verifier or self._in_memory_states.pop(state, None)
        if not code_verifier:
            code_verifier = "mock_verifier_for_testing"

        # Mock fallback for test/dev when no client_id configured
        if not self.client_id:
            return {
                "access_token": f"mock_x_access_token_{secrets.token_hex(16)}",
                "refresh_token": f"mock_x_refresh_token_{secrets.token_hex(16)}",
                "token_type": "bearer",
                "expires_in": 7200,
                "scope": " ".join(DEFAULT_SCOPES),
            }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.client_secret:
            auth_str = f"{self.client_id}:{self.client_secret}"
            b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {b64_auth}"

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(X_TOKEN_URL, data=data, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"X token exchange failed ({resp.status_code}): {resp.text}")
            return resp.json()

    def save_token(
        self,
        db: Session,
        token_data: Dict[str, Any],
        user_identifier: str = "default_user",
        x_user_id: Optional[str] = None,
        x_username: Optional[str] = None,
        x_name: Optional[str] = None,
    ) -> XOAuthToken:
        """Persists or updates OAuth token in SQLite database."""
        token_rec = db.query(XOAuthToken).filter(XOAuthToken.user_identifier == user_identifier).first()
        expires_in = token_data.get("expires_in", 7200)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        if not token_rec:
            token_rec = XOAuthToken(
                user_identifier=user_identifier,
                x_user_id=x_user_id,
                x_username=x_username,
                x_name=x_name,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "bearer"),
                expires_at=expires_at,
                scopes=token_data.get("scope"),
            )
            db.add(token_rec)
        else:
            token_rec.access_token = token_data["access_token"]
            if token_data.get("refresh_token"):
                token_rec.refresh_token = token_data["refresh_token"]
            token_rec.expires_at = expires_at
            if x_user_id:
                token_rec.x_user_id = x_user_id
            if x_username:
                token_rec.x_username = x_username
            if x_name:
                token_rec.x_name = x_name
            if token_data.get("scope"):
                token_rec.scopes = token_data["scope"]

        db.commit()
        db.refresh(token_rec)
        return token_rec

    def get_token(self, db: Session, user_identifier: str = "default_user") -> Optional[XOAuthToken]:
        """Retrieves stored token from SQLite."""
        return db.query(XOAuthToken).filter(XOAuthToken.user_identifier == user_identifier).first()


x_oauth = XOAuthHandler()
