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

# Standard Plan Definitions (2-Tier Model: Free Tier + Pro at ~$3 / ₹249)
PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "Free Starter",
        "badge": "FREE FOREVER",
        "description": "Essential job discovery and tracking to organize your search.",
        "price": 0,
        "monthly": 0,
        "yearly": 0,
        "price_monthly_usd": 0,
        "price_yearly_usd": 0,
        "price_monthly_inr": 0,
        "price_yearly_inr": 0,
        "interval": "forever",
        "credits": 50,
        "is_popular": False,
        "features": [
            "50 complimentary AI credits",
            "Job discovery & smart portal search",
            "Application tracking & Kanban board",
            "Single resume profile storage",
            "Public candidate portfolio",
        ],
        "limits": [
            "No automated background submissions",
            "No founder direct outreach drafts",
        ],
        "cta": "Get Started Free",
    },
    "pro": {
        "id": "pro",
        "name": "Pro Autopilot",
        "badge": "MOST POPULAR",
        "description": "Full AI application autopilot, tailored resumes, and founder outreach.",
        "price": 3,
        "monthly": 3,
        "yearly": 29,
        "price_monthly_usd": 3.0,
        "price_yearly_usd": 2.41,  # $29/year billed annually
        "price_monthly_inr": 249,
        "price_yearly_inr": 199,   # ₹2,388/year billed annually
        "yearly_inr": 2388,
        "interval": "month",
        "credits": 1000,
        "is_popular": True,
        "features": [
            "1,000 AI credits every month",
            "Workday & NextRaise autopilot assistance",
            "AI tailored resumes & cover letters",
            "Cold email drafts to startup founders",
            "Recruiter email sync & auto-advancement",
            "Cognitive Answer Bank auto-fill",
            "Priority AI worker queue & 24/7 support",
        ],
        "limits": [],
        "cta": "Upgrade to Pro",
    },
}

CREDIT_PACKS: Dict[str, Dict[str, Any]] = {
    "pack_100": {
        "id": "pack_100",
        "name": "100 Credits Top-Up",
        "price": 1,
        "price_usd": 1,
        "price_inr": 89,
        "credits": 100,
        "description": "Quick burst of tailored applications and founder emails",
    },
}


def get_plans_catalog(current_user: Optional[User] = None) -> Dict[str, Any]:
    """Retrieve canonical 2-tier catalog of subscription plans, credit packs, and user entitlements."""
    user_tier = current_user.subscription_tier if current_user else "free"
    user_credits = current_user.credits_balance if current_user else 0
    sub_status = getattr(current_user, "subscription_status", "active") if current_user else "active"
    
    return {
        "current_tier": user_tier,
        "current_credits": user_credits,
        "subscription_status": sub_status,
        "default_currency": "USD",
        "supported_currencies": ["USD", "INR"],
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
    Create a Checkout Session for either a subscription plan or a credit top-up pack.
    Supports Dodo Payments (MoR for India UPI & Global Cards), Stripe, and mock fallback.
    Returns session URL and session ID.
    """
    target_clean = "pro" if target in ("starter", "basic", "pro") else target
    is_plan = target_clean in PLANS and target_clean != "free"
    is_pack = target_clean in CREDIT_PACKS
    
    if not is_plan and not is_pack:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target '{target}'. Must be a valid subscription plan ('pro') or credit pack ('pack_100').",
        )
    
    success_url = success_url or f"{settings.frontend_url}/#billing-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = cancel_url or f"{settings.frontend_url}/#billing-cancel"
    
    # ── Dodo Payments (Primary Merchant of Record for India & Global) ──────────
    if settings.billing_provider == "dodo" and settings.dodo_payments_api_key and not settings.dodo_payments_api_key.startswith("mock_"):
        dodo_base = "https://api.dodopayments.com/v1" if settings.dodo_payments_environment == "live_mode" else "https://test.dodopayments.com/v1"
        item = PLANS[target_clean] if is_plan else CREDIT_PACKS[target_clean]
        payload = {
            "customer": {
                "email": user.email,
                "name": user.full_name or user.email.split("@")[0].title(),
            },
            "product_cart": [
                {
                    "product_id": target_clean,
                    "quantity": 1,
                    "amount": int(item["price"] * 100),
                }
            ],
            "return_url": success_url,
            "metadata": {
                "user_id": str(user.id),
                "target": target_clean,
                "type": "subscription" if is_plan else "topup",
            },
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    f"{dodo_base}/checkouts",
                    headers={"Authorization": f"Bearer {settings.dodo_payments_api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                res.raise_for_status()
                dodo_data = res.json()
                return {
                    "checkout_url": dodo_data.get("checkout_url") or dodo_data.get("url"),
                    "session_id": dodo_data.get("session_id") or dodo_data.get("id"),
                    "mode": "subscription" if is_plan else "payment",
                    "provider": "dodo",
                }
        except Exception as exc:
            log.error(f"Dodo Payments checkout creation error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Dodo Payments billing gateway error: {exc}",
            ) from exc

    # ── Real Stripe API Call ──────────────────────────────────────────────────
    if settings.billing_provider == "stripe" and settings.stripe_secret_key and not settings.stripe_secret_key.startswith("sk_test_mock"):
        stripe_mode = "subscription" if is_plan else "payment"
        unit_amount = (PLANS[target_clean]["price"] * 100) if is_plan else (CREDIT_PACKS[target_clean]["price"] * 100)
        item_name = PLANS[target_clean]["name"] if is_plan else CREDIT_PACKS[target_clean]["name"]
        
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
            "metadata[target]": target_clean,
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
                    "provider": "stripe",
                }
        except Exception as exc:
            log.error(f"Stripe API checkout session creation failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Stripe billing gateway error: {exc}",
            ) from exc

    # ── Simulated Mock Checkout Session (Local dev & test environments) ──────
    mock_id = f"cs_mock_{uuid.uuid4().hex[:16]}"
    mock_url = f"{settings.frontend_url}/#mock-checkout?session_id={mock_id}&target={target_clean}&user_id={user.id}&provider={settings.billing_provider}"
    log.info(f"Generated mock checkout session for user {user.id} ({target_clean}) via {settings.billing_provider}: {mock_id}")
    return {
        "checkout_url": mock_url,
        "session_id": mock_id,
        "mode": "subscription" if is_plan else "payment",
        "provider": settings.billing_provider,
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


def unsigned_webhooks_allowed() -> bool:
    return settings.env.lower() in ("development", "dev", "local", "test")


def verify_dodo_signature(payload_bytes: bytes, headers: Dict[str, str], secret: Optional[str] = None) -> bool:
    """Dodo Payments signs webhooks with the Standard Webhooks scheme (webhook-id,
    webhook-timestamp, webhook-signature; HMAC-SHA256, 5-minute tolerance). The svix
    library verifies that scheme, including the timestamp window and constant-time compare."""
    webhook_secret = secret or settings.dodo_payments_webhook_secret
    if not webhook_secret:
        return unsigned_webhooks_allowed()
    from svix.webhooks import Webhook, WebhookVerificationError

    try:
        Webhook(webhook_secret).verify(payload_bytes, {k.lower(): v for k, v in headers.items()})
    except (WebhookVerificationError, ValueError):
        return False
    return True


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
        # Unsigned events are accepted only for local development/tests. Anywhere else a
        # missing secret would let anyone POST a fake payment and grant themselves a plan.
        return unsigned_webhooks_allowed()
    
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
