from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DiscoveredContact(BaseModel):
    """Normalized schema for an extracted and verified contact."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., description="Full name of the decision maker")
    first_name: Optional[str] = Field(None)
    last_name: Optional[str] = Field(None)
    title: str = Field(default="Engineering Leader", description="Position or headline")
    company: str = Field(..., description="Company name")
    domain: Optional[str] = Field(None, description="Corporate root domain")
    email: str = Field(..., description="Discovered corporate or personal email")
    confidence_score: float = Field(default=70.0, ge=0.0, le=100.0)
    persona_score: int = Field(default=50, ge=0, le=100, description="Hiring impact score (EM=100, Head=90)")
    source: str = Field(default="waterfall", description="Discovery source (dorking, hunter, github, pattern)")
    mail_provider: Optional[str] = Field(None, description="Google Workspace, Microsoft 365, Custom")
    verified: bool = Field(default=False)
    is_deliverable: bool = Field(default=True)
    linkedin_url: Optional[str] = Field(None)
    github_username: Optional[str] = Field(None)
    sources: List[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if not self.first_name and self.name:
            parts = self.name.split()
            self.first_name = parts[0] if parts else ""
            self.last_name = parts[-1] if len(parts) > 1 else ""
        if self.source and self.source not in self.sources:
            self.sources.append(self.source)


class EmailVerificationResult(BaseModel):
    """Detailed deliverability and DNS MX check result."""
    email: str
    is_valid_syntax: bool
    is_disposable: bool
    is_free_mail: bool
    has_mx_records: bool
    mx_records: List[str] = Field(default_factory=list)
    mail_provider: str = Field(default="Unknown")
    confidence_score: float = Field(default=50.0)
    status: str = Field(default="valid")  # valid, risky, invalid, disposable
    reason: Optional[str] = Field(None)


class SearchDork(BaseModel):
    """Google Boolean Search Dork specification."""
    dork_type: str = Field(..., description="email_leak, linkedin_em, github_author, email_pattern")
    query: str = Field(..., description="Exact Google Boolean query string")
    target_role: Optional[str] = Field(None)
    description: str = Field(default="")
    url: Optional[str] = Field(None, description="Direct Google Search URL")


class EmailPermutation(BaseModel):
    """A generated email pattern permutation."""
    pattern_name: str  # first.last, flast, first, etc.
    email: str
    domain: str
    confidence_score: float = Field(default=60.0)
    has_mx: bool = Field(default=False)
