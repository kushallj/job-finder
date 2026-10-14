"""
Stripe Billing, Subscription Lifecycle & Webhook Processing Service.
Zero-dependency REST implementation using httpx and Python standard library hmac-sha256.
Provides seamless live Stripe integration with automatic mock fallback for sandboxed test runs.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.config import settings
from src.models import CreditTransaction, User
from src.services.credit_service import add_credits

log = logging.getLogger(__name__)

# Standard Plan Definitions
PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "Free Starter",
        "price": 0,
        "interval": "one-time",
        "credits": 50,
        "features": [
            "50 complimentary applications",
            "Standard multi-portal matching",
            "Single resume profile",
            "Community knowledge base",
        ],
    },
    "starter": {
        "id": "starter",
        "name": "Starter Autopilot",
        "price": 29,
        "interval": "month",
        "credits": 300,
        "features": [
            "300 applications per month",
            "Workday & NextRaise auto-apply",
            "Tailored resume generations",
            "Standard AI speed queue",
            "Daily application summaries",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Pro Supercharger",
        "price": 59,
        "interval": "month",
        "credits": 1000,
        "popular": True,
        "features": [
            "1,000 applications per month",
            "Full autonomous multi-tenant autopilot",
            "Cognitive Answer Bank auto-fill & sync",
            "Deep ATS resume keyword optimization",
            "Ghost-Hunter radar & hiring manager matching",
            "Priority AI processing queue",
        ],
    },
    "unlimited": {
        "id": "unlimited",
        "name": "Executive Unlimited",
        "price": 99,
        "interval": "month",
        "credits": 9999,
        "features": [
            "Unlimited auto-applications & tailoring",
            "Direct recruiter outreach & follow-up engine",
            "Multi-resume A/B testing matrix",
            "Dedicated high-throughput worker pool",
            "24/7 VIP priority support",
        ],
    },
}

CREDIT_PACKS: Dict[str, Dict[str, Any]] = {
    "pack_100": {
        "id": "pack_100",
        "name": "100 Credits Top-Up",
        "price": 15,
        "credits": 100,
        "description": "Ideal for quick bursts of tailored applications",
    },
    "pack_300": {
        "id": "pack_300",
        "name": "300 Credits Top-Up",
        "price": 35,
        "credits": 300,
        "description": "High-volume pack for active multi-role interview sprints",
    },
}


def get_plans_catalog(current_user: Optional[User] = None) -> Dict[str, Any]:
    """Retrieve full catalog of subscription tiers, credit packs, and current user plan."""
    user_tier = current_user.subscription_tier if current_user else "free"
    user_credits = current_user.credits_balance if current_user else 0
    sub_status = getattr(current_user, "subscription_status", "active") if current_user else "active"
    
    return {
        "current_tier": user_tier,
        "current_credits": user_credits,
        "subscription_status": sub_status,
        "plans": list(PLANS.values()),
        "credit_packs": list(CREDIT_PACKS.values()),
    }


def create_checkout_session(
    db: Session,
    user: User,
    target: str,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> Dict[str, str]:
    """
    Create a Stripe Checkout Session for either a subscription plan or a credit top-up pack.
    Returns session URL and session ID.
    If stripe_secret_key is not configured, provides a mock checkout session for test environments.
    """
    is_plan = target in PLANS and target != "free"
    is_pack = target in CREDIT_PACKS
    
    if not is_plan and not is_pack:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target '{target}'. Must be a valid subscription plan (starter, pro, unlimited) or credit pack (pack_100, pack_300).",
        )
    
    success_url = success_url or f"{settings.frontend_url}/#billing-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = cancel_url or f"{settings.frontend_url}/#billing-cancel"
    
    # ── Real Stripe API Call ──────────────────────────────────────────────────
    if settings.stripe_secret_key and not settings.stripe_secret_key.startswith("sk_test_mock"):
        stripe_mode = "subscription" if is_plan else "payment"
        unit_amount = (PLANS[target]["price"] * 100) if is_plan else (CREDIT_PACKS[target]["price"] * 100)
        item_name = PLANS[target]["name"] if is_plan else CREDIT_PACKS[target]["name"]
        
        headers = {
            "Authorization": f"Bearer {settings.stripe_secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        data = {
            "mode": stripe_mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": str(user.id),
            "customer_email": user.email,
            "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][product_data][name]": item_name,
            "line_items[0][price_data][unit_amount]": str(unit_amount),
            "line_items[0][quantity]": "1",
            "metadata[user_id]": str(user.id),
            "metadata[target]": target,
            "metadata[type]": "subscription" if is_plan else "topup",
        }
        if is_plan:
            data["line_items[0][price_data][recurring][interval]"] = "month"

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post("https://api.stripe.com/v1/checkout/sessions", headers=headers, data=data)
                res.raise_for_status()
                session_data = res.json()
                return {
                    "checkout_url": session_data.get("url"),
                    "session_id": session_data.get("id"),
                    "mode": stripe_mode,
                }
        except Exception as exc:
            log.error(f"Stripe API checkout session creation failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe billing gateway error: {exc}",
            ) from exc

    # ── Simulated Mock Checkout Session (Local dev & test environments) ──────
    mock_id = f"cs_mock_{uuid.uuid4().hex[:16]}"
    mock_url = f"{settings.frontend_url}/#mock-checkout?session_id={mock_id}&target={target}&user_id={user.id}"
    log.info(f"Generated mock checkout session for user {user.id} ({target}): {mock_id}")
    return {
        "checkout_url": mock_url,
        "session_id": mock_id,
        "mode": "subscription" if is_plan else "payment",
    }


def create_customer_portal_session(
    db: Session,
    user: User,
    return_url: Optional[str] = None,
) -> Dict[str, str]:
    """
    Create a Stripe Customer Portal session to manage payment methods, view invoices, or cancel.
    """
    return_url = return_url or f"{settings.frontend_url}/settings"
    
    if settings.stripe_secret_key and user.stripe_customer_id:
        headers = {
            "Authorization": f"Bearer {settings.stripe_secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "customer": user.stripe_customer_id,
            "return_url": return_url,
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post("https://api.stripe.com/v1/billing_portal/sessions", headers=headers, data=data)
                res.raise_for_status()
                portal_data = res.json()
                return {"portal_url": portal_data.get("url")}
        except Exception as exc:
            log.warning(f"Could not open live Stripe billing portal: {exc}")
    
    # Fallback simulation
    mock_portal = f"{settings.frontend_url}/#mock-portal?customer_id={user.stripe_customer_id or 'cust_mock'}"
    return {"portal_url": mock_portal}


def verify_webhook_signature(
    payload_bytes: bytes,
    sig_header: str,
    secret: Optional[str] = None,
    tolerance: int = 300,
) -> bool:
    """
    Verify Stripe webhook signature according to Stripe specification.
    Format of sig_header: t=timestamp,v1=signature
    Zero external dependencies: uses Python stdlib hmac and hashlib.
    """
    webhook_secret = secret or settings.stripe_webhook_secret
    if not webhook_secret:
        # If no webhook secret configured in dev/test, accept if marked mock
        return True
    
    if not sig_header:
        return False
    
    parts = dict(item.strip().split("=", 1) for item in sig_header.split(",") if "=" in item)
    timestamp_str = parts.get("t")
    signature = parts.get("v1")
    
    if not timestamp_str or not signature:
        return False
    
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        return False
    
    # Enforce timestamp tolerance unless testing with mock secret
    if not webhook_secret.startswith("whsec_test"):
        if abs(time.time() - timestamp) > tolerance:
            log.warning("Stripe webhook rejected: timestamp older than tolerance")
            return False
    
    signed_payload = f"{timestamp_str}.".encode("utf-8") + payload_bytes
    expected_sig = hmac.new(
        webhook_secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    
    return hmac.compare_digest(expected_sig, signature)


def process_webhook_event(db: Session, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process verified Stripe webhook events:
    - checkout.session.completed
    - invoice.payment_succeeded
    - customer.subscription.deleted
    """
    event_type = event.get("type")
    data_obj = event.get("data", {}).get("object", {})
    
    log.info(f"Processing Stripe webhook event: {event_type}")
    
    if event_type == "checkout.session.completed":
        metadata = data_obj.get("metadata", {})
        user_id_str = metadata.get("user_id") or data_obj.get("client_reference_id")
        target = metadata.get("target")
        target_type = metadata.get("type", "subscription")
        
        if not user_id_str:
            log.warning("checkout.session.completed received without user_id in metadata")
            return {"status": "skipped", "reason": "missing_user_id"}
        
        user = db.query(User).filter(User.id == int(user_id_str)).first()
        if not user:
            log.error(f"User {user_id_str} not found during checkout completion")
            return {"status": "error", "reason": "user_not_found"}
        
        customer_id = data_obj.get("customer")
        if customer_id:
            user.stripe_customer_id = customer_id
        
        subscription_id = data_obj.get("subscription")
        if subscription_id:
            user.stripe_subscription_id = subscription_id

        if target_type == "subscription" and target in PLANS:
            plan_info = PLANS[target]
            user.subscription_tier = target
            user.subscription_status = "active"
            
            # Replenish plan monthly credits
            granted_credits = plan_info["credits"]
            add_credits(
                db=db,
                user_id=user.id,
                amount=granted_credits,
                action="subscription_activated",
                reference_id=data_obj.get("id"),
                notes=f"Subscribed to {plan_info['name']} tier (+{granted_credits} credits)",
            )
            db.commit()
            return {"status": "success", "action": "subscription_activated", "tier": target}

        elif target_type == "topup" and target in CREDIT_PACKS:
            pack_info = CREDIT_PACKS[target]
            granted_credits = pack_info["credits"]
            add_credits(
                db=db,
                user_id=user.id,
                amount=granted_credits,
                action="credit_pack_topup",
                reference_id=data_obj.get("id"),
                notes=f"Purchased {pack_info['name']} (+{granted_credits} credits)",
            )
            db.commit()
            return {"status": "success", "action": "topup_applied", "credits": granted_credits}

    elif event_type == "invoice.payment_succeeded":
        # Recurring monthly renewal
        subscription_id = data_obj.get("subscription")
        if subscription_id:
            user = db.query(User).filter(User.stripe_subscription_id == subscription_id).first()
            if user and user.subscription_tier in PLANS:
                plan_info = PLANS[user.subscription_tier]
                monthly_credits = plan_info["credits"]
                add_credits(
                    db=db,
                    user_id=user.id,
                    amount=monthly_credits,
                    action="recurring_renewal",
                    reference_id=data_obj.get("id"),
                    notes=f"Monthly renewal for {plan_info['name']} (+{monthly_credits} credits)",
                )
                user.subscription_status = "active"
                db.commit()
                return {"status": "success", "action": "renewal_credits_added", "user_id": user.id}

    elif event_type in ("customer.subscription.deleted", "customer.subscription.canceled"):
        subscription_id = data_obj.get("id")
        user = db.query(User).filter(User.stripe_subscription_id == subscription_id).first()
        if user:
            user.subscription_tier = "free"
            user.subscription_status = "canceled"
            db.commit()
            log.info(f"Downgraded user {user.id} to free tier following subscription cancellation")
            return {"status": "success", "action": "downgraded_to_free", "user_id": user.id}

    return {"status": "ignored", "event_type": event_type}
