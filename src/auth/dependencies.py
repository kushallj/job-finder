"""
FastAPI authentication and current user dependency injection.
Supports:
- Clerk session JWTs (RS256) with auto-provisioning
- Backend JWTs (HS256)
- Global router-level auth enforcement with public allowlist
- Admin role-gated dependencies
"""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any, Dict, Optional, Set

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.models import CreditTransaction, User
from src.auth.jwt_handler import decode_access_token

log = logging.getLogger(__name__)

security_bearer = HTTPBearer(auto_error=False)

# Explicitly allowlisted public endpoints
PUBLIC_EXACT_PATHS: Set[str] = {
    "/",
    "/health",
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/api/billing/webhook",
    "/api/billing/webhook/stripe",
    "/api/billing/plans",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/auth/webhook/clerk",
    "/api/auth/clerk/webhook",
}

PUBLIC_PREFIXES = (
    "/static/",
    "/assets/",
)


def is_public_path(path: str, method: str = "GET") -> bool:
    """Check if the given request path and method are public."""
    if method == "OPTIONS":
        return True

    clean_path = path.rstrip("/") if path != "/" else "/"
    if clean_path in PUBLIC_EXACT_PATHS or path in PUBLIC_EXACT_PATHS:
        return True

    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True

    # Public portfolio viewing & GitHub heatmap (excluding administrative /seed)
    if method == "GET" and path.startswith("/api/portfolio/") and not path.endswith("/seed"):
        return True

    # Public startups.gallery exploration & status endpoints
    if method == "GET" and path.startswith("/api/startups-gallery"):
        return True

    # Public recruiter chatbot on hosted candidate portfolio
    if method == "POST" and path.startswith("/api/portfolio/") and path.endswith("/chat"):
        return True

    return False


def _decode_unverified_jwt(token: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Decode header and payload of a JWT token without signature verification."""
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format: must consist of 3 dot-separated segments")

    def _b64_decode(segment: str) -> Dict[str, Any]:
        padding_needed = (4 - len(segment) % 4) % 4
        padded = segment + ("=" * padding_needed)
        raw = base64.urlsafe_b64decode(padded)
        return json.loads(raw.decode("utf-8"))

    header = _b64_decode(parts[0])
    payload = _b64_decode(parts[1])
    return header, payload


_clerk_jwks_client: Optional[PyJWKClient] = None


def get_clerk_jwks_client() -> Optional[PyJWKClient]:
    """Retrieve or initialize the PyJWKClient for Clerk cryptographic RS256 token verification."""
    global _clerk_jwks_client
    jwks_url = settings.clerk_jwks_url
    if not jwks_url and settings.clerk_issuer:
        jwks_url = f"{settings.clerk_issuer.rstrip('/')}/.well-known/jwks.json"
    if jwks_url:
        if _clerk_jwks_client is None:
            _clerk_jwks_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
        return _clerk_jwks_client
    return _clerk_jwks_client


def set_clerk_jwks_client(client: Optional[PyJWKClient]) -> None:
    """Set or reset the Clerk PyJWKClient singleton (used for testing and mock injection)."""
    global _clerk_jwks_client
    _clerk_jwks_client = client


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Strict dependency: Requires a valid Bearer JWT token in Authorization header.
    Supports both Clerk session tokens (RS256) and local backend tokens (HS256).
    Returns the authenticated User model.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    # Developer convenience bypass for local automated testing
    if settings.env.lower() == "development" and token in ("dev_token_admin", "test_admin_token"):
        admin_user = db.query(User).filter(User.is_superuser == True).first()
        if admin_user:
            return admin_user

    # Determine JWT algorithm from header
    try:
        header, payload = _decode_unverified_jwt(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Malformed token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    alg = header.get("alg", "HS256")

    # 1. Clerk session token (RS256)
    if alg == "RS256" or (isinstance(payload.get("sub"), str) and payload.get("sub", "").startswith("user_")):
        jwks_client = get_clerk_jwks_client()
        if jwks_client is not None:
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                decode_kwargs: Dict[str, Any] = {
                    "algorithms": ["RS256"],
                    "options": {"verify_aud": False},
                }
                if settings.clerk_issuer:
                    decode_kwargs["issuer"] = settings.clerk_issuer
                payload = jwt.decode(token, signing_key.key, **decode_kwargs)
            except jwt.PyJWTError as exc:
                log.warning(f"Clerk RS256 token verification failed: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid Clerk token: {exc}",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc
        else:
            # Offline / unconfigured fallback: Validate expiration and time-based claims
            now_ts = int(time.time())
            exp = payload.get("exp")
            if exp is not None and now_ts > exp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Clerk token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            nbf = payload.get("nbf")
            if nbf is not None and now_ts < nbf:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Clerk token not valid yet",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        clerk_user_id = str(payload.get("sub", "")).strip()
        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clerk token missing 'sub' subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Lookup by clerk_user_id
        user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()

        # Lookup by email if clerk_user_id not yet linked
        email = (
            payload.get("email")
            or payload.get("primary_email")
            or payload.get("primary_email_address")
            or payload.get("email_address")
        )
        if email and isinstance(email, str):
            email = email.strip().lower()

        if not user and email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.clerk_user_id = clerk_user_id
                db.commit()
                db.refresh(user)

        # Auto-provision user on first request
        if not user:
            user_email = email or f"{clerk_user_id}@clerk.user"
            full_name = (
                payload.get("name")
                or payload.get("full_name")
                or f"{payload.get('first_name', '')} {payload.get('last_name', '')}".strip()
                or user_email.split("@")[0].replace(".", " ").title()
            )
            initial_credits = settings.default_signup_credits
            user = User(
                clerk_user_id=clerk_user_id,
                email=user_email,
                full_name=full_name,
                hashed_password="",
                subscription_tier="free",
                credits_balance=initial_credits,
                is_active=True,
                is_superuser=False,
            )
            db.add(user)
            db.flush()

            # Record initial welcome bonus
            welcome_tx = CreditTransaction(
                user_id=user.id,
                amount=initial_credits,
                balance_after=initial_credits,
                action="welcome_bonus",
                notes="Complimentary Clerk signup credits",
            )
            db.add(welcome_tx)
            db.commit()
            db.refresh(user)
            log.info(f"Auto-provisioned new Clerk user {clerk_user_id} ({user_email}) with {initial_credits} credits")

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )
        return user

    # 2. Local backend JWT token (HS256)
    try:
        verified_payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = verified_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        uid = int(user_id)
        user = db.query(User).filter(User.id == uid).first()
    except (ValueError, TypeError):
        user = db.query(User).filter(User.clerk_user_id == str(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Optional dependency: If a valid Bearer token is present, returns that user.
    Returns None when unauthenticated.
    """
    if credentials and credentials.credentials:
        try:
            return get_current_user(credentials=credentials, db=db)
        except HTTPException:
            return None
    return None


async def enforce_auth_unless_public(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Global FastAPI dependency: Enforces authentication across all routes
    unless explicitly present in the public allowlist or in single-tenant dev mode.
    """
    if request.method == "OPTIONS":
        return None

    path = request.url.path

    if is_public_path(path, request.method):
        return None

    # Single-tenant local development fallback
    if not settings.multi_tenant_enabled and settings.env.lower() != "production":
        user = None
        if credentials and credentials.credentials:
            try:
                user = get_current_user(credentials=credentials, db=db)
            except HTTPException:
                pass
        if not user:
            user = db.query(User).filter(User.email == "admin@jobfinder.ai").first()
            if not user:
                user = db.query(User).order_by(User.id.asc()).first()
        request.state.user = user
        return user

    user = get_current_user(credentials=credentials, db=db)
    request.state.user = user
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Enforce administrative privileges. Raises 403 Forbidden for non-admin users.
    """
    if not (current_user.is_superuser or current_user.email == "admin@jobfinder.ai"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to perform this action",
        )
    return current_user
