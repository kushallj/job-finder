"""
FastAPI authentication and current user dependency injection.
Supports both strict JWT Bearer authentication and optional fallback for local dev.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import User
from src.auth.jwt_handler import decode_access_token

log = logging.getLogger(__name__)

security_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Strict dependency: Requires a valid Bearer JWT token in Authorization header.
    Returns the authenticated User model.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
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
    In multi-tenant or production environments, returns None when unauthenticated (never fails open).
    Only in local single-tenant dev mode without multi-tenant enabled does it return local default admin.
    """
    from src.config import settings

    if credentials and credentials.credentials:
        try:
            return get_current_user(credentials=credentials, db=db)
        except HTTPException:
            pass  # Invalid credentials, return None below
    
    # In multi-tenant or production environments, unauthenticated users MUST NOT receive admin privileges.
    if settings.multi_tenant_enabled or settings.env.lower() == "production":
        return None

    # Fallback to default user ONLY in local single-tenant dev environments
    default_user = db.query(User).filter(User.email == "admin@jobfinder.ai").first()
    if not default_user:
        default_user = db.query(User).order_by(User.id.asc()).first()
    return default_user
