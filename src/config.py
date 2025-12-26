from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow",
    )
    # AI - Gemini (matches ANTHROPIC_API_KEY in .env)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-latest"
    gemini_api_key: Optional[str] = None
    
    # Google Sheets
    google_sheet_title: Optional[str] = None
    google_sheet_id: Optional[str] = None
    
    # Job APIs
    adzuna_app_id: str
    adzuna_app_key: str
    
    # Database
    database_url: str
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # Redis
    redis_url: str
    
    # Google
    google_credentials_path: str
    gmail_address: str
    
    # App
    env: str = "development"
    log_level: str = "INFO"
    
    # Note: Pydantic v2 uses `model_config` above; the old inner `Config` is ignored.

settings = Settings()
