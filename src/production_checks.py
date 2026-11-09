"""Refuse to start the API in production with unsafe or missing settings.

Called from main.py at import. Each problem is one line naming the env var to fix, so a
bad deploy fails fast in the platform's logs instead of serving traffic half-configured.
Workers import src.tasks (not main) and are not blocked by API-only settings.
"""

from __future__ import annotations

from typing import Any


def production_problems(s: Any) -> list[str]:
    """Empty list = safe to serve. Only meaningful when ENV=production."""
    problems: list[str] = []

    def need(cond: bool, msg: str) -> None:
        if not cond:
            problems.append(msg)

    url = (s.database_url or "").lower()
    need(not url.startswith("sqlite"), "DATABASE_URL must be Postgres in production (SQLite is not durable/concurrent)")
    need(bool(s.multi_tenant_enabled), "MULTI_TENANT_ENABLED must be true (false lets anonymous requests act as the admin user)")
    need(not s.allow_dev_auth_tokens, "ALLOW_DEV_AUTH_TOKENS must be false")
    need(not s.seed_dev_admin, "SEED_DEV_ADMIN must be false")
    need(bool(s.clerk_issuer or s.clerk_jwks_url), "CLERK_ISSUER or CLERK_JWKS_URL is required (Clerk session verification)")
    need(bool((s.clerk_authorized_parties or "").strip()), "CLERK_AUTHORIZED_PARTIES must list the Jobify origin(s) (azp check)")
    need(bool(s.clerk_webhook_secret), "CLERK_WEBHOOK_SECRET is required (unsigned webhooks are rejected only when it is set)")
    need(bool(s.token_encryption_key), "TOKEN_ENCRYPTION_KEY is required (encrypts stored OAuth refresh tokens)")
    origins = [o.strip() for o in (s.cors_origins or "").split(",") if o.strip()]
    need(bool(origins) and all(o.startswith("https://") for o in origins),
         "CORS_ORIGINS must list only https:// origins (e.g. https://app.yourdomain.com)")
    need((s.frontend_url or "").startswith("https://"), "FRONTEND_URL must be the https:// Jobify URL")
    need(not getattr(s, "auto_send_emails", False), "AUTO_SEND_EMAILS must stay false (CLAUDE.md section 1)")
    provider = (getattr(s, "billing_provider", "") or "").lower()
    if provider == "dodo":
        need(bool(getattr(s, "dodo_payments_webhook_secret", None)), "DODO_PAYMENTS_WEBHOOK_SECRET is required (unsigned payment webhooks are rejected)")
    if provider == "stripe":
        need(bool(getattr(s, "stripe_webhook_secret", None)), "STRIPE_WEBHOOK_SECRET is required (unsigned payment webhooks are rejected)")
    need(provider != "mock", "BILLING_PROVIDER=mock is not allowed in production")
    if getattr(s, "inbox_domain", None):
        need(bool(getattr(s, "inbound_webhook_secret", None)), "INBOUND_WEBHOOK_SECRET is required when INBOX_DOMAIN is set")
    return problems
