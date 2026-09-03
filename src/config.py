from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

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
    database_url: str
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # Redis
    redis_url: str
    
    # Google
    google_credentials_path: str
    gmail_address: str
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
    auto_send_emails: bool = True  # Automatically send outreach emails after job matching

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
    
    # Note: Pydantic v2 uses `model_config` above; the old inner `Config` is ignored.

settings = Settings()

