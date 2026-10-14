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
    verify_webhook_signature,
    process_webhook_event,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["Stripe Billing & Subscriptions"])


# --- Schemas ---

class CheckoutSessionRequest(BaseModel):
    target: str = Field(..., description="Target plan ('starter', 'pro', 'unlimited') or credit pack ('pack_100', 'pack_300')")
    success_url: Optional[str] = Field(None, description="Redirect URL upon successful payment")
    cancel_url: Optional[str] = Field(None, description="Redirect URL if customer cancels checkout")


class PortalSessionRequest(BaseModel):
    return_url: Optional[str] = Field(None, description="URL to return to after customer finishes with portal")


# --- Endpoints ---

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
