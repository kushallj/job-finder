"""Career lifecycle state machine.

The lifecycle deliberately separates reversible internal state changes from
external side effects. The application queue can therefore recommend exactly
one next action without ever pretending an email/application was sent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

ACTIVE_STATUSES = {
    "saved", "ready", "applied", "interview", "offer", "negotiation",
}
TERMINAL_STATUSES = {"accepted", "rejected"}
KNOWN_STATUSES = ACTIVE_STATUSES | TERMINAL_STATUSES

# Manual state transitions. External actions (submit application/send outreach)
# are intentionally not encoded as automatic status jumps here.
ALLOWED_TRANSITIONS = {
    "saved": {"ready", "rejected"},
    "ready": {"applied", "rejected"},
    "applied": {"interview", "rejected"},
    "interview": {"offer", "rejected"},
    "offer": {"negotiation", "rejected"},
    "negotiation": {"accepted", "rejected"},
    "accepted": set(),
    "rejected": set(),
}

@dataclass(frozen=True)
class LifecycleAction:
    key: str
    label: str
    reason: str
    priority: str
    route: Optional[str] = None
    external: bool = False
    requires_confirmation: bool = False


def normalize_status(status: Optional[str]) -> str:
    return "saved" if not status or status == "pending" else status


def can_transition(current: Optional[str], target: str) -> bool:
    current = normalize_status(current)
    return target in ALLOWED_TRANSITIONS.get(current, set())


def require_transition(current: Optional[str], target: str) -> None:
    current = normalize_status(current)
    if target not in KNOWN_STATUSES:
        raise ValueError(f"Unknown lifecycle status: {target}")
    if not can_transition(current, target):
        raise ValueError(f"Invalid lifecycle transition: {current} -> {target}")


def next_action(
    status: Optional[str],
    *,
    has_reply: bool = False,
    has_contacts: bool = False,
    has_outreach: bool = False,
    followup_due: bool = False,
    has_application_proof: bool = False,
) -> LifecycleAction:
    """Return exactly one recommended action for an opportunity."""
    current = normalize_status(status)

    if current == "saved":
        return LifecycleAction(
            "prepare_application", "Prepare application",
            "Your opportunity is saved but the application packet is not ready yet.",
            "high",
        )
    if current == "ready":
        return LifecycleAction(
            "apply", "Apply",
            "Your submission packet is ready. Review it and submit on the employer site.",
            "high", external=True,
        )
    if current == "applied":
        if has_reply:
            return LifecycleAction(
                "respond", "Respond to reply",
                "A contact replied. Human follow-through is the highest-value next move.",
                "high", route="/outreach", external=True,
            )
        if followup_due:
            return LifecycleAction(
                "followup", "Review follow-up",
                "An outreach thread is waiting for a follow-up.",
                "high", route="/outreach", external=True,
            )
        if has_contacts and not has_outreach:
            return LifecycleAction(
                "outreach", "Start outreach",
                "You have relevant people available; add context around the application while the role is fresh.",
                "high", route="/outreach", external=True,
            )
        return LifecycleAction(
            "interview_prep", "Prepare for interview",
            "The application is submitted. Spend the next block of time preparing rather than creating more application work.",
            "high",
        )
    if current == "interview":
        return LifecycleAction(
            "interview_prep", "Prepare for interview",
            "You are in the interview stage. Review the role, your strongest evidence, and likely questions.",
            "high",
        )
    if current == "offer":
        return LifecycleAction(
            "negotiate", "Review negotiation",
            "You have an offer. Review compensation, scope, level, and constraints before accepting.",
            "high",
        )
    if current == "negotiation":
        return LifecycleAction(
            "accept_offer", "Finalize offer",
            "Negotiation is active. Confirm the outcome before accepting the offer.",
            "high", requires_confirmation=True,
        )
    if current in TERMINAL_STATUSES:
        return LifecycleAction("complete", "No action", "This opportunity is closed.", "low")
    return LifecycleAction("prepare_application", "Prepare application", "Move this opportunity into the application-ready stage.", "medium")


def sort_actions(actions: Iterable[dict]) -> list[dict]:
    rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(actions, key=lambda x: (rank.get(x.get("priority"), 9), -(x.get("fit_score") or 0), x.get("updated_at") or ""))
