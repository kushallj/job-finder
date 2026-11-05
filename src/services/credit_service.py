"""
Credit Metering & Usage Service for Commercial Multi-Tenant SaaS.
Tracks credit balances, executes atomic deductions, logs audit trails,
and enforces HTTP 402 Payment Required guards when credits are depleted.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models import CreditTransaction, User

log = logging.getLogger(__name__)

# Standard operation credit costs
CREDIT_COSTS = {
    "resume_tailor": 1,
    "cover_letter": 1,
    "workday_apply": 2,
    "nextraise_apply": 1,
    "ats_deep_analysis": 1,
    "interview_prep_sprint": 3,
    # Jobify (jobify/src/app/pages/ChatPage.jsx CREDIT_COST, mocks/founders.js UNLOCK_COST)
    "chat_message": 5,
    "founder_unlock": 5,
}


def get_user_credits(db: Session, user_id: int) -> int:
    """Retrieve current credit balance for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user.credits_balance or 0


def deduct_credits(
    db: Session,
    user_id: int,
    amount: int,
    action: str,
    reference_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """
    Atomically deduct credits for an action.
    If credits are insufficient and user is not on 'unlimited' tier / superuser,
    raises HTTP 402 PAYMENT REQUIRED.
    Returns remaining balance.
    """
    if amount <= 0:
        return get_user_credits(db, user_id)
    
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Unlimited tier bypass
    if user.is_superuser or user.subscription_tier == "unlimited":
        new_balance = max(user.credits_balance, 9999)
        user.credits_balance = new_balance
        tx = CreditTransaction(
            user_id=user.id,
            amount=-amount,
            balance_after=new_balance,
            action=action,
            reference_id=reference_id,
            notes=notes or f"Unlimited tier deduction for {action}",
        )
        db.add(tx)
        db.commit()
        return new_balance

    if (user.credits_balance or 0) < amount:
        log.warning(
            f"User {user_id} credit depletion: requested={amount}, balance={user.credits_balance}"
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "INSUFFICIENT_CREDITS",
                "message": f"Insufficient credits. This operation requires {amount} credits, but you have {user.credits_balance}.",
                "balance": user.credits_balance,
                "required": amount,
                "action": action,
            },
        )
    
    user.credits_balance -= amount
    new_balance = user.credits_balance
    
    tx = CreditTransaction(
        user_id=user.id,
        amount=-amount,
        balance_after=new_balance,
        action=action,
        reference_id=reference_id,
        notes=notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(user)
    
    log.info(f"Deducted {amount} credits for user {user_id} ({action}). New balance: {new_balance}")
    return new_balance


def add_credits(
    db: Session,
    user_id: int,
    amount: int,
    action: str = "topup",
    reference_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """Add credits to a user balance (welcome bonus, stripe top-up, refund)."""
    if amount <= 0:
        raise ValueError("Amount to add must be positive")
    
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.credits_balance = (user.credits_balance or 0) + amount
    new_balance = user.credits_balance
    
    tx = CreditTransaction(
        user_id=user.id,
        amount=amount,
        balance_after=new_balance,
        action=action,
        reference_id=reference_id,
        notes=notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(user)
    
    log.info(f"Added {amount} credits to user {user_id} ({action}). New balance: {new_balance}")
    return new_balance


def get_credit_history(
    db: Session,
    user_id: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch recent transaction history for a user."""
    transactions = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user_id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": t.id,
            "amount": t.amount,
            "balance_after": t.balance_after,
            "action": t.action,
            "reference_id": t.reference_id,
            "notes": t.notes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in transactions
    ]
