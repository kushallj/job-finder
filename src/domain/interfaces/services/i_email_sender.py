"""
Domain Interface: IEmailSender
Port defining contract for SMTP/API email delivery.
"""
from abc import ABC, abstractmethod
from typing import Optional
from src.domain.value_objects.email_address import EmailAddress


class IEmailSender(ABC):
    """Abstract interface for dispatching emails."""

    @abstractmethod
    async def send_email(
        self,
        recipient: EmailAddress,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send single transactional email.

        Returns:
            bool: True if accepted by transport.
        """
        pass
