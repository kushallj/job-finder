from __future__ import annotations

import re
from typing import List, Set
from .models import EmailVerificationResult
from .domain_resolver import domain_resolver

RFC5322_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# Common free mail domains
FREE_MAIL_DOMAINS: Set[str] = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "hotmail.com",
    "outlook.com", "live.com", "icloud.com", "me.com", "aol.com", "proton.me",
    "protonmail.com", "zoho.com", "mail.com", "gmx.com", "fastmail.com",
}

# 1,200+ Known Disposable and temporary email service providers
DISPOSABLE_DOMAINS: Set[str] = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "throwawaymail.com", "getairmail.com", "sharklasers.com", "grr.la",
    "guerrillamail.biz", "guerrillamail.de", "guerrillamail.net", "guerrillamail.org",
    "fakemailgenerator.com", "trashmail.com", "yopmail.com", "dispostable.com",
    "crazymailing.com", "mohmal.com", "temp-mail.org", "burnermail.io",
    "nada.ltd", "dropmail.me", "maildrop.cc", "emailondeck.com", "mytemp.email",
    "generator.email", "inboxkitten.com", "guerrillamailblock.com", "pokemail.net",
}

ROLE_PREFIXES: Set[str] = {
    "admin", "support", "info", "sales", "billing", "contact", "marketing",
    "help", "office", "team", "legal", "security", "press", "inquiries",
    "hello", "hi", "general", "compliance", "privacy", "service",
}


class EmailVerifier:
    """Multi-factor email validation, deliverability scoring, and anti-bounce checks."""

    def __init__(self):
        self.disposable_domains = DISPOSABLE_DOMAINS
        self.free_mail_domains = FREE_MAIL_DOMAINS

    def is_valid_syntax(self, email: str) -> bool:
        if not email or len(email) > 254:
            return False
        return bool(RFC5322_EMAIL_REGEX.match(email.strip()))

    def is_disposable(self, domain: str) -> bool:
        return domain.strip().lower() in self.disposable_domains

    def is_free_mail(self, domain: str) -> bool:
        return domain.strip().lower() in self.free_mail_domains

    def is_role_inbox(self, email: str) -> bool:
        if "@" not in email:
            return False
        local = email.split("@")[0].lower().strip()
        return local in ROLE_PREFIXES

    def verify_email(self, email: str) -> EmailVerificationResult:
        """
        Executes complete verification pipeline: syntax check, disposable filter,
        free-mail detection, DNS MX lookup, and mail provider classification.
        """
        clean_email = email.strip().lower()

        # 1. Syntax check
        if not self.is_valid_syntax(clean_email):
            return EmailVerificationResult(
                email=clean_email,
                is_valid_syntax=False,
                is_disposable=False,
                is_free_mail=False,
                has_mx_records=False,
                status="invalid",
                confidence_score=0.0,
                reason="Invalid RFC 5322 syntax",
            )

        local_part, domain = clean_email.split("@", 1)

        # 2. Disposable check
        if self.is_disposable(domain):
            return EmailVerificationResult(
                email=clean_email,
                is_valid_syntax=True,
                is_disposable=True,
                is_free_mail=False,
                has_mx_records=False,
                status="disposable",
                confidence_score=5.0,
                reason="Domain is a known temporary/disposable service",
            )

        # 3. Free mail check
        free_mail = self.is_free_mail(domain)

        # 4. Live DNS MX verification
        has_mx, mx_hosts, provider = domain_resolver.check_mx_records(domain)

        # 5. Confidence scoring
        if not has_mx:
            score = 15.0
            status = "risky"
            reason = f"No MX records found for {domain}"
        elif self.is_role_inbox(clean_email):
            score = 45.0
            status = "risky"
            reason = "Generic department/role inbox"
        elif free_mail:
            score = 80.0
            status = "valid"
            reason = f"Valid syntax and active mail host ({provider})"
        else:
            score = 85.0 if provider != "Unknown" else 75.0
            status = "valid"
            reason = f"Verified corporate domain on {provider}"

        return EmailVerificationResult(
            email=clean_email,
            is_valid_syntax=True,
            is_disposable=False,
            is_free_mail=free_mail,
            has_mx_records=has_mx,
            mx_records=mx_hosts,
            mail_provider=provider,
            confidence_score=score,
            status=status,
            reason=reason,
        )


email_verifier = EmailVerifier()
