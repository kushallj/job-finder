"""
Domain Entity: OutreachRecord
Tracks outgoing multi-channel communication attempts, delivery state, and replies.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from src.domain.value_objects.email_address import EmailAddress


class OutreachStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"


@dataclass
class OutreachRecord:
    """
    Domain entity tracking individual outreach messages sent to hiring contacts.

    Time Complexity:
        Lifecycle transitions: O(1)
    Space Complexity:
        O(1)
    """

    job_id: int
    contact_email: EmailAddress
    channel: str = "email"
    status: OutreachStatus = OutreachStatus.PENDING
    subject: str = ""
    body: str = ""
    email_sent: bool = False
    follow_up_count: int = 0
    id: Optional[int] = None
    sent_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def mark_sent(self) -> None:
        """Mark record as successfully dispatched."""
        self.status = OutreachStatus.SENT
        self.email_sent = True
        self.sent_at = datetime.now(timezone.utc)

    def mark_replied(self) -> None:
        """Record candidate response reception."""
        self.status = OutreachStatus.REPLIED

    def increment_follow_up(self) -> None:
        """Track scheduled follow-up iteration."""
        self.follow_up_count += 1
