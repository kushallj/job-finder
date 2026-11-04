"""
JWT (JSON Web Token) encoding and decoding implementation according to RFC 7519.
Zero external dependencies: uses Python standard library hmac, hashlib, base64, and json.
Supports HS256 (HMAC-SHA256) signature verification.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from src.config import settings


def _b64_url_encode(data: bytes) -> str:
    """Base64url encode bytes without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_url_decode(data: str) -> bytes:
    """Base64url decode string with required '=' padding."""
    padding_needed = (4 - len(data) % 4) % 4
    return base64.urlsafe_b64decode(data + ("=" * padding_needed))


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None,
) -> str:
    """
    Generate an HS256-signed JWT token.
    """
    secret = secret_key or settings.jwt_secret_key
    to_encode = data.copy()
    
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_json = json.dumps(to_encode, separators=(",", ":"), sort_keys=True).encode("utf-8")
    
    header_b64 = _b64_url_encode(header_json)
    payload_b64 = _b64_url_encode(payload_json)
    
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(
    token: str,
    secret_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decode and verify an HS256-signed JWT token.
    Raises ValueError on token errors (invalid format, expired, bad signature).
    """
    secret = secret_key or settings.jwt_secret_key
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format: must consist of 3 dot-separated segments")
    
    header_b64, payload_b64, sig_b64 = parts

    # Verify header algorithm
    try:
        header_bytes = _b64_url_decode(header_b64)
        header = json.loads(header_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Malformed JWT header: {exc}") from exc

    if header.get("alg") != "HS256":
        raise ValueError(f"Unsupported JWT algorithm: {header.get('alg')}, expected HS256")

    # Verify signature
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_sig_b64 = _b64_url_encode(expected_sig)
    
    if not hmac.compare_digest(expected_sig_b64, sig_b64):
        raise ValueError("Invalid token signature")
    
    try:
        payload_bytes = _b64_url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Malformed JWT payload: {exc}") from exc
    
    # Verify expiration and not-before claims
    now_ts = int(time.time())
    nbf = payload.get("nbf")
    if nbf is not None and now_ts < nbf:
        raise ValueError("Token is not valid yet (nbf claim in future)")

    exp = payload.get("exp")
    if exp is not None and now_ts > exp:
        raise ValueError("Token has expired")
    
    return payload
