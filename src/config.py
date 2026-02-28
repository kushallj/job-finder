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
    
    # Google Sheets
    google_sheet_title: Optional[str] = None
    google_sheet_id: Optional[str] = None
    google_sheet_worksheet: Optional[str] = None
    
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
    gmail_password: Optional[str] = None
    
    # Email Discovery APIs
    hunter_api_key: Optional[str] = None
    apollo_api_key: Optional[str] = None
    signalhire_api_key: Optional[str] = None
    signalhire_callback_url: Optional[str] = None  # Your ngrok URL + /api/signalhire/callback
    
    # App
    env: str = "development"
    log_level: str = "INFO"
    auto_send_emails: bool = True  # Automatically send outreach emails after job matching
    
    # Note: Pydantic v2 uses `model_config` above; the old inner `Config` is ignored.

settings = Settings()
