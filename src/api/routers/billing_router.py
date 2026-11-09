"""
Stripe Billing, Subscriptions & Webhook API Router.
Enables self-serve upgrades, credit top-ups, customer portal redirection,
and automated Stripe webhook event processing.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import User
from src.auth.dependencies import get_current_user, get_optional_current_user
from src.services.billing_service import (
    get_plans_catalog,
    create_checkout_session,
    create_customer_portal_session,
    verify_dodo_signature,
    verify_webhook_signature,
    process_webhook_event,
)

from src.services.credit_service import deduct_credits

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["Stripe Billing & Subscriptions"])


# --- Schemas ---

class SpendCreditsRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Credits to deduct")
    action: str = Field(..., description="Action name e.g. ai_chat, founder_unlock")
    reference_id: Optional[str] = Field(None, description="Optional target ID e.g. company or job id")
    notes: Optional[str] = Field(None, description="Optional transaction notes")


class CheckoutSessionRequest(BaseModel):
    target: str = Field(..., description="Target plan ('starter', 'pro', 'unlimited') or credit pack ('pack_100', 'pack_300')")
    success_url: Optional[str] = Field(None, description="Redirect URL upon successful payment")
    cancel_url: Optional[str] = Field(None, description="Redirect URL if customer cancels checkout")


class PortalSessionRequest(BaseModel):
    return_url: Optional[str] = Field(None, description="URL to return to after customer finishes with portal")


# --- Endpoints ---

@router.get("/subscription")
def get_user_subscription(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve active user subscription plan, billing interval, and remaining AI credits.
    """
    if not current_user:
        return {
            "plan": "free",
            "interval": "monthly",
            "status": "none",
            "creditsRemaining": 50,
            "renewsAt": None,
        }
    return {
        "plan": current_user.subscription_tier or "free",
        "interval": "monthly",
        "status": current_user.subscription_status or "active",
        "creditsRemaining": current_user.credits_balance if current_user.credits_balance is not None else 50,
        "renewsAt": current_user.current_period_end.isoformat() if current_user.current_period_end else None,
    }


@router.post("/spend-credits")
def spend_credits_endpoint(
    req: SpendCreditsRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Deduct credits atomically from user account with full audit trail.
    """
    if not current_user:
        return {"success": True, "remaining": 50, "deducted": req.amount}

    remaining = deduct_credits(
        db=db,
        user_id=current_user.id,
        amount=req.amount,
        action=req.action,
        reference_id=req.reference_id,
        notes=req.notes,
    )
    return {"success": True, "remaining": remaining, "deducted": req.amount}


@router.get("/plans")
def get_available_plans(
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Get full catalog of subscription plans, pricing, credit allowances, and features.
    If authenticated, returns current user subscription status and balance.
    """
    return get_plans_catalog(current_user=current_user)


@router.post("/create-checkout-session")
def create_session(
    req: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a Stripe Checkout session URL for subscription upgrade or credit pack purchase.
    """
    return create_checkout_session(
        db=db,
        user=current_user,
        target=req.target,
        success_url=req.success_url,
        cancel_url=req.cancel_url,
    )


@router.post("/create-portal-session")
def create_portal(
    req: PortalSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a Stripe Customer Portal URL for self-serve payment and subscription management.
    """
    return create_customer_portal_session(
        db=db,
        user=current_user,
        return_url=req.return_url,
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """
    Public webhook receiver for asynchronous Stripe events.
    Verifies cryptographic HMAC-SHA256 signature and processes lifecycle changes.
    """
    payload_bytes = await request.body()
    
    # Verify cryptographic signature
    if not verify_webhook_signature(payload_bytes, stripe_signature or ""):
        log.warning("Invalid Stripe webhook signature rejected")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature header",
        )
    
    try:
        event_data = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {exc}",
        ) from exc
    
    result = process_webhook_event(db=db, event=event_data)
    return {"received": True, "result": result}


@router.post("/webhook/dodo")
async def dodo_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public webhook receiver for asynchronous Dodo Payments events (UPI & Cards).
    Activates user Pro subscription (1,000 credits) or adds credit top-ups on successful payments.
    """
    payload_bytes = await request.body()
    # Public route: without a valid signature anyone could grant any user a paid plan.
    if not verify_dodo_signature(payload_bytes, dict(request.headers)):
        log.warning("Invalid or unsigned Dodo webhook rejected")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
    try:
        event_data = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload",
        ) from exc

    data = event_data.get("data", event_data)
    metadata = data.get("metadata", {})
    user_id_str = metadata.get("user_id")

    if user_id_str:
        try:
            uid = int(user_id_str)
            target = metadata.get("target", "pro")
            target_type = metadata.get("type", "subscription")
            user = db.query(User).filter(User.id == uid).first()
            if user:
                if target_type == "subscription" or target in ("pro", "starter", "basic"):
                    user.subscription_tier = "pro"
                    user.subscription_status = "active"
                    from src.services.credit_service import add_credits
                    add_credits(
                        db=db,
                        user_id=user.id,
                        amount=1000,
                        action="subscription_renewal",
                        notes="Dodo Payments Pro subscription activation (1,000 credits)",
                    )
                    db.commit()
                    log.info(f"Dodo webhook: Activated Pro subscription for user {user.id}")
                elif target == "pack_100":
                    from src.services.credit_service import add_credits
                    add_credits(
                        db=db,
                        user_id=user.id,
                        amount=100,
                        action="credit_purchase",
                        notes="Dodo Payments 100 Credits Top-Up pack",
                    )
                    db.commit()
                    log.info(f"Dodo webhook: Added 100 credits for user {user.id}")
                return {"received": True, "status": "processed", "user_id": user.id}
        except Exception as exc:
            log.error(f"Error processing Dodo webhook for user {user_id_str}: {exc}")

    return {"received": True, "status": "ignored"}

