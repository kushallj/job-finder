from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import List, Optional

class Settings(BaseSettings):
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow",
    )
    # AI - Gemini
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"

    # AI - Ollama (local LLM)
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_keep_alive: str = "5m"
    
    # Google Sheets
    google_sheet_title: Optional[str] = None
    google_sheet_id: Optional[str] = None
    google_sheet_worksheet: Optional[str] = None
    
    # Job APIs
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    jobdata_api_key: Optional[str] = None
    aidevboard_api_key: Optional[str] = None
    fantastic_jobs_api_key: Optional[str] = None
    fantasticjobs_api_key: Optional[str] = None
    careerjet_api_key: Optional[str] = None
    careerjet_locale_code: str = "en_US"
    usajobs_api_key: Optional[str] = None
    usajobs_email: Optional[str] = None
    provider_sync_limit: int = 50
    provider_sync_max_age_days: int = 30



    
    # Database
    database_url: str = "sqlite:///./jobs.db"
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Google
    google_credentials_path: str = "config/google-service-account.json"
    gmail_address: Optional[str] = "outreach@jobfinder.ai"
    gmail_password: Optional[str] = None
    
    # Email Discovery APIs
    hunter_api_key: Optional[str] = None
    apollo_api_key: Optional[str] = None
    signalhire_api_key: Optional[str] = None
    signalhire_callback_url: Optional[str] = None  # Your ngrok URL + /api/signalhire/callback

    # Boolean/X-ray lead sourcing (src/agents/agent_11_query_hunter.py) —
    # ToS-compliant search backends only, never raw scraping of Google/
    # LinkedIn/X results pages. Configure ONE of the three below.
    google_cse_api_key: Optional[str] = None   # Google Custom Search JSON API key
    google_cse_id: Optional[str] = None        # Programmable Search Engine ID (cx=)
    serper_api_key: Optional[str] = None       # serper.dev — alternative to Google CSE
    serpapi_api_key: Optional[str] = None      # serpapi.com — Google search API
    serp_api_key: Optional[str] = None         # serpapi.com alias
    
    # Cloudflare Browser Rendering
    cloudflare_account_id: Optional[str] = None
    cloudflare_api_token: Optional[str] = None

    # Firecrawl — used by src/scrapers/firecrawl_scraper.py to crawl
    # startup career pages directly (get key: https://www.firecrawl.dev/app/api-keys)
    firecrawl_api_key: Optional[str] = None

    # GitHub
    github_token: Optional[str] = None

    # News API
    news_api_key: Optional[str] = None

    # Resume Evaluation & Parsing (ApyHub / SharpAPI)
    apyhub_token: Optional[str] = None
    apyhub_api_key: Optional[str] = None
    sharpapi_api_key: Optional[str] = None

    # Email provider — "smtp" | "sendgrid" | "ses"
    email_provider: str = "smtp"
    sendgrid_api_key: Optional[str] = None

    # AWS SES
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_ses_source_arn: Optional[str] = None  # verified SES identity ARN (optional)

    # Job processing
    email_delay_seconds: float = 30.0
    job_concurrency: int = 5
    min_score: int = 50
    max_contacts: int = 3
    db_chunk_size: int = 100

    # App
    env: str = "development"
    log_level: str = "INFO"
    auto_send_emails: bool = False  # Human-in-the-loop review gate by default
    # Shared Jobify job catalog (src/tasks.refresh_job_catalog). Celery beat runs it at
    # minute catalog_refresh_minute of each hour in catalog_refresh_hours_utc (crontab
    # syntax). Default 02:30 + 14:30 UTC = 08:00 + 20:00 IST.
    catalog_refresh_hours_utc: str = "2,14"
    catalog_refresh_minute: int = 30
    # Comma-separated job-board title searches; empty = the defaults in src/tasks.py.
    catalog_queries: str = ""
    # GET /api/admin/catalog-runs reports stale when no run succeeded within this window.
    catalog_stale_after_hours: int = 26
    # Jobify chat (src/jobify/services/chat_providers.py). Comma-separated fallback chain, tried in
    # order until one starts replying, e.g. "ollama" (dev) or "openrouter,hf". "echo" = stub.
    chat_provider: str = "echo"
    chat_echo_delay_ms: int = 40  # per streamed word, so Stop is testable against the stub
    # Per-user send limits: protect shared free-tier quotas (OpenRouter :free is per account).
    chat_rate_per_minute: int = 6
    chat_rate_per_day: int = 150
    # Let thinking models reason before answering (always hidden from users). Off = fast but weaker at
    # maths and at refusing "add a fake claim" requests (measured with scripts/chat_eval.py on qwen3:8b).
    # Turn on for hosted GPU providers; reasoning tokens count against chat_reasoning_max_tokens.
    chat_reasoning: bool = False
    chat_reasoning_max_tokens: int = 4096
    chat_max_tokens: int = 1024
    chat_temperature: float = 0.4
    chat_timeout_s: float = 60.0  # max wait for the next chunk
    chat_ollama_base_url: str = "http://localhost:11434/v1"
    chat_ollama_model: str = "qwen3:8b"
    openrouter_api_key: Optional[str] = None
    chat_openrouter_model: str = ""  # e.g. a ":free" Qwen/Kimi id from openrouter.ai/models
    hf_token: Optional[str] = None
    chat_hf_model: str = ""  # Hugging Face router model id
    # Any other OpenAI-compatible API (Alibaba Qwen, Moonshot Kimi, MiniMax, NVIDIA NIM...)
    chat_custom_base_url: str = ""
    chat_custom_api_key: Optional[str] = None
    chat_custom_model: str = ""


    # Sender identity (used in outreach emails, cover letters, etc.)
    sender_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    tagline: Optional[str] = None

    # Tsenta Auto-Apply Agent (YC S26)
    tsenta_api_key: Optional[str] = None
    tsenta_api_url: str = "https://api.tsenta.com/v1"
    tsenta_mode: str = "review_required"  # "review_required" | "full_auto"
    tsenta_auto_submit: bool = False
    tsenta_min_fit_score: int = 75

    # Multi-Tenant SaaS & Auth (Production Commercialization)
    multi_tenant_enabled: bool = True
    jwt_secret_key: str = "job-finder-super-secret-production-key-2026-change-in-env"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    default_signup_credits: int = 50

    # Clerk Authentication Bridge & Webhooks
    clerk_issuer: Optional[str] = None
    clerk_jwks_url: Optional[str] = None
    clerk_webhook_secret: Optional[str] = None
    clerk_secret_key: Optional[str] = None
    # Comma-separated frontend origins allowed in the token's azp claim, e.g.
    # "https://app.jobify.com,http://localhost:3000". Empty = azp not checked.
    clerk_authorized_parties: str = ""
    allow_dev_auth_tokens: bool = False  # enables dev_token_admin when ENV=development
    # Local-only superuser seed. Never runs in production; needs both flags (no default password).
    seed_dev_admin: bool = False
    dev_admin_password: Optional[str] = None

    # Gmail (Jobify Applications sync). Read-only scope; refresh tokens are Fernet-encrypted
    # with TOKEN_ENCRYPTION_KEY. Redirect URI must be registered on the Google OAuth client.
    google_oauth_client_id: Optional[str] = None
    google_oauth_client_secret: Optional[str] = None
    google_oauth_redirect_uri: str = "http://localhost:8000/api/gmail/callback"
    token_encryption_key: Optional[str] = None
    gmail_sync_lookback_days: int = 30
    gmail_sync_max_messages: int = 50

    # Jobify job-hunt inbox: every user gets name.xxxx@INBOX_DOMAIN. Inbound mail arrives via a
    # Cloudflare Email Worker (infra/cloudflare/inbox-worker) that POSTs the raw message to
    # /api/inbound/email signed with INBOUND_WEBHOOK_SECRET. Replies go out over plain SMTP
    # (any provider's free tier: Brevo, Resend, SES...).
    inbox_domain: Optional[str] = None
    inbound_webhook_secret: Optional[str] = None
    inbound_max_bytes: int = 10 * 1024 * 1024
    inbox_smtp_host: Optional[str] = None
    inbox_smtp_port: int = 587
    inbox_smtp_username: Optional[str] = None
    inbox_smtp_password: Optional[str] = None
    inbox_smtp_starttls: bool = True
    inbox_daily_send_limit: int = 50

    @property
    def clerk_authorized_parties_list(self) -> List[str]:
        return [p.strip().rstrip("/") for p in self.clerk_authorized_parties.split(",") if p.strip()]

    # Stripe Billing & Subscriptions
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_starter: str = "price_starter_mock"
    stripe_price_pro: str = "price_pro_mock"
    stripe_price_unlimited: str = "price_unlimited_mock"
    stripe_price_pack_100: str = "price_pack_100_mock"
    stripe_price_pack_300: str = "price_pack_300_mock"

    # Dodo Payments (Merchant of Record - India UPI & Global Cards)
    dodo_payments_api_key: Optional[str] = None
    dodo_payments_webhook_secret: Optional[str] = None
    dodo_payments_environment: str = "test_mode"  # "test_mode" | "live_mode"
    billing_provider: str = "dodo"  # "dodo" | "stripe" | "mock"

    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.env.lower() == "production":
            default_placeholder = "job-finder-super-secret-production-key-2026-change-in-env"
            if not self.jwt_secret_key or self.jwt_secret_key == default_placeholder:
                raise ValueError(
                    "FATAL: Running with ENV=production requires setting a secure, unique JWT_SECRET_KEY in environment variables."
                )
        return self

settings = Settings()

