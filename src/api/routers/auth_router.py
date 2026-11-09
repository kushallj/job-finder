"""
Authentication & User Account API Router for Commercial Multi-Tenant SaaS.
Provides registration, login, profile inspection, and credit balance tracking.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from svix.webhooks import Webhook, WebhookVerificationError

from src.config import settings
from src.database import get_db
from src.models import (
    Application,
    CandidateProfile,
    Contact,
    CreditTransaction,
    MailboxAccount,
    OutreachRecord,
    Resume,
    TelegramConnector,
    User,
)
from src.auth.crypto import hash_password, verify_password
from src.auth.jwt_handler import create_access_token
from src.auth.dependencies import get_current_user, require_admin
from src.services.credit_service import add_credits, get_credit_history

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication & User Management"])


# --- Schemas ---

class RegisterRequest(BaseModel):
    email: str = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, description="User password (min 6 characters)")
    full_name: Optional[str] = Field(None, description="User's display or full name")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    subscription_tier: str
    credits_balance: int
    is_superuser: bool

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TopupRequest(BaseModel):
    amount: int = Field(..., gt=0, le=1000, description="Amount of credits to add")


# --- Endpoints ---

def legacy_password_auth_guard() -> None:
    """Clerk is the only customer login in production (CLAUDE.md section 8). The legacy
    password routes 404 there unless LEGACY_PASSWORD_AUTH_ENABLED=true."""
    from src.config import settings

    if settings.is_production and not settings.legacy_password_auth_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(legacy_password_auth_guard)])
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new candidate user account.
    Automatically assigns 50 complimentary starting credits.
    """
    clean_email = req.email.strip().lower()
    if "@" not in clean_email or "." not in clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format",
        )
    
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )
    
    initial_credits = settings.default_signup_credits
    new_user = User(
        email=clean_email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name or clean_email.split("@")[0].title(),
        subscription_tier="free",
        credits_balance=initial_credits,
        is_active=True,
        is_superuser=False,
    )
    db.add(new_user)
    db.flush()

    # Welcome bonus transaction
    welcome_tx = CreditTransaction(
        user_id=new_user.id,
        amount=initial_credits,
        balance_after=initial_credits,
        action="welcome_bonus",
        notes="Complimentary registration credits",
    )
    db.add(welcome_tx)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )


KNOWN_DEFAULT_PASSWORDS = frozenset({"admin123"})


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(legacy_password_auth_guard)])
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user credentials and issue an access token.
    """
    clean_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    # Databases initialised before 2026-11-05 contain admin@jobfinder.ai / admin123 (a public
    # default). Refuse it everywhere until the password is changed.
    if req.password in KNOWN_DEFAULT_PASSWORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Default credentials are disabled. Set a new password for this account.",
        )

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: User = Depends(get_current_user)):
    """
    Get the authenticated user's current profile, subscription tier, and credit balance.
    """
    return UserResponse.model_validate(user)


@router.get("/credits/history")
def get_user_credits_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """
    Get audit history of credit deductions and additions for the current user.
    """
    history = get_credit_history(db=db, user_id=user.id, limit=limit)
    return {
        "user_id": user.id,
        "credits_balance": user.credits_balance,
        "subscription_tier": user.subscription_tier,
        "history": history,
    }


@router.post("/credits/topup")
def topup_user_credits(
    req: TopupRequest,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Administrative credit top-up endpoint (Restricted to superusers).
    Adds credits to the user balance and records transaction.
    """
    new_balance = add_credits(
        db=db,
        user_id=user.id,
        amount=req.amount,
        action="credit_purchase",
        notes=f"Purchased {req.amount} platform credits",
    )
    return {
        "success": True,
        "added": req.amount,
        "credits_balance": new_balance,
    }


@router.post("/webhook/clerk")
@router.post("/clerk/webhook")
async def clerk_webhook_handler(request: Request, db: Session = Depends(get_db)):
    """
    Clerk Svix Webhook endpoint for user synchronization and GDPR account deletion.
    Handles user.created, user.updated, and user.deleted events with signature verification.
    """
    raw_body = await request.body()
    headers = dict(request.headers)

    # 1. Cryptographic Svix signature verification
    if settings.clerk_webhook_secret:
        try:
            wh = Webhook(settings.clerk_webhook_secret)
            wh.verify(raw_body, headers)
        except WebhookVerificationError as exc:
            log.warning(f"Clerk webhook verification failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook signature verification failed",
            )
    else:
        if settings.env.lower() == "production":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Clerk webhook secret not configured in production",
            )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed webhook JSON payload: {exc}",
        )

    event_type = payload.get("type", "")
    data = payload.get("data", {})
    clerk_user_id = data.get("id")

    if not clerk_user_id:
        return {"status": "ignored", "detail": "Missing user ID in event data"}

    # 2. Extract email and display name from Clerk payload structure
    email_addresses = data.get("email_addresses", [])
    primary_email_id = data.get("primary_email_address_id")
    email = None
    for entry in email_addresses:
        if entry.get("id") == primary_email_id:
            email = entry.get("email_address")
            break
    if not email and email_addresses:
        email = email_addresses[0].get("email_address")
    if email:
        email = email.strip().lower()

    first_name = data.get("first_name") or ""
    last_name = data.get("last_name") or ""
    full_name = f"{first_name} {last_name}".strip() or None

    # 3. Handle event types
    if event_type == "user.created":
        existing = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if not existing and email:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                existing.clerk_user_id = clerk_user_id
                if full_name and not existing.full_name:
                    existing.full_name = full_name
                db.commit()
                return {"status": "linked", "user_id": existing.id, "clerk_user_id": clerk_user_id}

        if not existing:
            user_email = email or f"{clerk_user_id}@clerk.user"
            initial_credits = settings.default_signup_credits
            new_user = User(
                clerk_user_id=clerk_user_id,
                email=user_email,
                full_name=full_name or user_email.split("@")[0].replace(".", " ").title(),
                hashed_password="",
                subscription_tier="free",
                credits_balance=initial_credits,
                is_active=True,
                is_superuser=False,
            )
            db.add(new_user)
            db.flush()

            welcome_tx = CreditTransaction(
                user_id=new_user.id,
                amount=initial_credits,
                balance_after=initial_credits,
                action="welcome_bonus",
                notes="Complimentary Clerk signup bonus",
            )
            db.add(welcome_tx)
            db.commit()
            log.info(f"Clerk webhook: created user {clerk_user_id} ({user_email})")
            return {"status": "created", "user_id": new_user.id, "clerk_user_id": clerk_user_id}

        return {"status": "already_exists", "user_id": existing.id}

    elif event_type == "user.updated":
        user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if not user and email:
            user = db.query(User).filter(User.email == email).first()

        if user:
            if clerk_user_id and not user.clerk_user_id:
                user.clerk_user_id = clerk_user_id
            if full_name:
                user.full_name = full_name
            if email and user.email != email:
                user.email = email
            db.commit()
            return {"status": "updated", "user_id": user.id, "clerk_user_id": clerk_user_id}

        return {"status": "ignored", "detail": "User not found to update"}

    elif event_type == "user.deleted":
        # GDPR Right to Erasure cascade purge
        user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if not user:
            return {"status": "ignored", "detail": "User not found for deletion"}

        user_id = user.id
        user_email = user.email

        # 1. Purge tenant-isolated records
        db.query(Application).filter(Application.user_id == user_id).delete(synchronize_session=False)
        db.query(Resume).filter(Resume.user_id == user_id).delete(synchronize_session=False)
        db.query(Contact).filter(Contact.user_id == user_id).delete(synchronize_session=False)
        db.query(OutreachRecord).filter(OutreachRecord.user_id == user_id).delete(synchronize_session=False)
        db.query(CreditTransaction).filter(CreditTransaction.user_id == user_id).delete(synchronize_session=False)

        try:
            db.query(MailboxAccount).filter(MailboxAccount.user_id == user_id).delete(synchronize_session=False)
        except Exception:
            pass

        try:
            db.query(TelegramConnector).filter(TelegramConnector.user_id == user_id).delete(synchronize_session=False)
        except Exception:
            pass

        # 2. Cascade delete CandidateProfile and child collections
        profiles = db.query(CandidateProfile).filter(
            (CandidateProfile.user_identifier == f"user_{user_id}")
            | (CandidateProfile.user_identifier == clerk_user_id)
            | (CandidateProfile.email == user_email)
        ).all()
        for p in profiles:
            db.delete(p)

        # 3. Purge User record
        db.delete(user)
        db.commit()

        log.info(f"GDPR Right to Erasure: Successfully purged user {user_id} ({clerk_user_id}) and all tenant records.")
        return {
            "status": "purged",
            "event": "user.deleted",
            "purged_user_id": user_id,
            "clerk_user_id": clerk_user_id,
        }

    return {"status": "ignored", "event": event_type}

