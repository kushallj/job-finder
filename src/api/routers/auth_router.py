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

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
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


@router.post("/login", response_model=AuthResponse)
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
