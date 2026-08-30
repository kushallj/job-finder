"""
API request/response models for FastAPI endpoints.

This module defines Pydantic models for request validation and response serialization
across all API endpoints. Models include field validation, error handling, and proper
typing to ensure data integrity.

Requirements: 23.2 (Validate request parameters), 23.3 (Return processing statistics)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class JobSource(str, Enum):
    """Valid job sources"""
    ADZUNA = "adzuna"
    LINKEDIN = "linkedin"
    NAUKRI = "naukri"
    INDEED = "indeed"
    WELLFOUND = "wellfound"
    HIRIST = "hirist"
    REMOTE_CO = "remote.co"
    INSTAHYRE = "instahyre"
    CLOUDFLARE_CRAWL = "cloudflare_crawl"
    API_SCRAPER = "api_scraper"
    FIRECRAWL_NEWS = "firecrawl_news"
    NEWSAPI = "newsapi"
    OTHER = "other"
    JOBDATAAPI = "jobdataapi"
    AIDEVBOARD = "aidevboard"


class OutreachStatus(str, Enum):
    """Outreach record status"""
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"
    REPLIED = "replied"
    FOLLOWED_UP = "followed_up"


class ProcessingStatus(str, Enum):
    """Pipeline processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ═══════════════════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    """
    Request model for job search and processing pipeline.
    
    Requirements: 23.1 (POST endpoint), 23.2 (Validate request parameters)
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query for job listings (e.g., 'python developer')",
        examples=["python developer", "react frontend engineer"],
    )
    min_score: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Minimum match score threshold (0-100)",
        examples=[50, 70],
    )
    source: Optional[JobSource] = Field(
        default=None,
        description="Optional job source filter",
    )
    location: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional location filter",
        examples=["San Francisco", "Remote"],
    )
    company: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional company name filter",
        examples=["Google", "Stripe"],
    )
    timeout_seconds: Optional[int] = Field(
        default=300,
        ge=10,
        le=3600,
        description="Pipeline execution timeout in seconds (10-3600)",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Ensure query is not empty after stripping"""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()


class ContactSearchRequest(BaseModel):
    """
    Request model for contact discovery.
    
    Requirements: 23.2 (Validate request parameters)
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Company name to search for contacts",
        examples=["Stripe", "OpenAI"],
    )
    job_title: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional job title filter (e.g., 'Engineering Manager')",
        examples=["Engineering Manager", "HR Manager", "Recruiter"],
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of contacts to return (1-50)",
    )
    smtp_verify: bool = Field(
        default=False,
        description="Whether to perform SMTP verification on discovered emails",
    )

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        """Ensure company name is not empty after stripping"""
        if not v or not v.strip():
            raise ValueError("Company name cannot be empty or whitespace only")
        return v.strip()


class OutreachStatusUpdateRequest(BaseModel):
    """
    Request model for updating an outreach record's status.

    Backs PUT /api/outreach/{outreach_id}/status, which the frontend
    (outreachApi.updateStatus) already called but the backend didn't expose.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    status: OutreachStatus = Field(
        ...,
        description="New status for the outreach record",
    )


class OutreachRequest(BaseModel):
    """
    Request model for sending outreach emails.
    
    Requirements: 23.2 (Validate request parameters)
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    job_id: int = Field(
        ...,
        ge=1,
        description="Job ID to send outreach for",
        examples=[123],
    )
    contact_email: str = Field(
        ...,
        min_length=3,
        max_length=254,  # RFC 5321 max email length
        description="Contact email address",
        examples=["hiring@company.com"],
    )
    contact_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Contact name",
        examples=["Jane Smith"],
    )
    send_immediately: bool = Field(
        default=True,
        description="Whether to send immediately or queue for later",
    )
    custom_message: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional custom message to include in outreach",
    )

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email format validation"""
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v

    @field_validator("contact_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty after stripping"""
        if not v or not v.strip():
            raise ValueError("Contact name cannot be empty or whitespace only")
        return v.strip()


class FollowUpRequest(BaseModel):
    """
    Request model for sending follow-up emails.
    
    Requirements: 23.2 (Validate request parameters)
    """
    outreach_id: int = Field(
        ...,
        ge=1,
        description="Outreach record ID to send follow-up for",
        examples=[456],
    )
    follow_up_number: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Follow-up attempt number (1-3)",
        examples=[1, 2, 3],
    )
    custom_message: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional custom message for follow-up",
    )


class CrawlRequest(BaseModel):
    """
    Request model for Cloudflare web crawling.
    
    Requirements: 23.2 (Validate request parameters)
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    url: str = Field(
        ...,
        min_length=10,
        max_length=2048,
        description="URL to crawl (must be https://)",
        examples=["https://stripe.com/jobs"],
    )
    company_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Company name for crawled jobs",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of pages to crawl (1-500)",
    )
    depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum crawl depth (1-5)",
    )
    query: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional keyword filter for crawled pages",
    )
    include_patterns: Optional[List[str]] = Field(
        default=None,
        description="URL patterns to include (regex)",
        examples=[[".*jobs.*", ".*careers.*"]],
    )
    exclude_patterns: Optional[List[str]] = Field(
        default=None,
        description="URL patterns to exclude (regex)",
        examples=[[".*pdf$", ".*\\.zip$"]],
    )
    feed_pipeline: bool = Field(
        default=False,
        description="Whether to feed crawled jobs through the processing pipeline",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL is valid HTTPS"""
        v = v.strip()
        if not v.startswith("https://"):
            raise ValueError("URL must start with https://")
        return v

    @field_validator("include_patterns", "exclude_patterns")
    @classmethod
    def validate_patterns(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Ensure patterns are not empty strings"""
        if v is None:
            return v
        return [p.strip() for p in v if p.strip()]


# ═══════════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════════

class PipelineStatistics(BaseModel):
    """
    Pipeline execution statistics.
    
    Requirements: 23.3 (Return processing statistics in response)
    """
    jobs_fetched: int = Field(..., ge=0, description="Number of jobs fetched from source")
    jobs_processed: int = Field(..., ge=0, description="Number of jobs processed")
    jobs_completed: int = Field(..., ge=0, description="Number of jobs successfully completed")
    jobs_failed: int = Field(..., ge=0, description="Number of jobs that failed processing")
    processing_time_seconds: float = Field(..., ge=0, description="Total processing time in seconds")
    throughput_jobs_per_second: float = Field(..., ge=0, description="Processing throughput (jobs/sec)")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.jobs_processed == 0:
            return 0.0
        return round((self.jobs_completed / self.jobs_processed) * 100, 2)


class QueryResponse(BaseModel):
    """
    Response model for job query and processing.
    
    Requirements: 23.3 (Return processing statistics in response)
    """
    status: str = Field(..., description="Request status")
    trace_id: str = Field(..., description="Request trace ID for debugging")
    query: str = Field(..., description="Search query used")
    resume_used: str = Field(..., description="Resume file path used")
    min_score_requested: int = Field(..., ge=0, le=100, description="Minimum score threshold requested")
    statistics: Optional[PipelineStatistics] = Field(None, description="Processing statistics")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class AsyncPipelineResponse(BaseModel):
    """
    Response model for async pipeline execution.
    
    Requirements: 23.3 (Return processing statistics in response)
    """
    status: str = Field(..., description="Pipeline execution status")
    trace_id: str = Field(..., description="Request trace ID for debugging")
    query: str = Field(..., description="Search query used")
    statistics: PipelineStatistics = Field(..., description="Processing statistics")
    resume_used: str = Field(..., description="Resume file path used")
    min_score_requested: int = Field(..., ge=0, le=100, description="Minimum score threshold")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ContactData(BaseModel):
    """Contact information"""
    id: Optional[int] = Field(None, description="Contact database ID")
    name: str = Field(..., description="Contact name")
    title: Optional[str] = Field(None, description="Job title")
    email: str = Field(..., description="Email address")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    company: str = Field(..., description="Company name")
    department: Optional[str] = Field(None, description="Department")
    confidence_score: float = Field(..., ge=0, le=100, description="Discovery confidence score")
    source: str = Field(..., description="Discovery source")
    found_at: Optional[datetime] = Field(None, description="Discovery timestamp")


class ContactSearchResponse(BaseModel):
    """
    Response model for contact search.
    
    Requirements: 23.3 (Return processing statistics)
    """
    status: str = Field(..., description="Request status")
    company: str = Field(..., description="Company name searched")
    contacts_found: int = Field(..., ge=0, description="Total contacts discovered")
    contacts_saved: int = Field(..., ge=0, description="New contacts saved to database")
    contacts: List[ContactData] = Field(default_factory=list, description="List of discovered contacts")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class OutreachResponse(BaseModel):
    """Response model for outreach send"""
    status: str = Field(..., description="Outreach status")
    trace_id: str = Field(..., description="Request trace ID")
    job_id: int = Field(..., description="Job ID")
    contact_email: str = Field(..., description="Contact email")
    email_sent: bool = Field(..., description="Whether email was successfully sent")
    outreach_id: Optional[int] = Field(None, description="Outreach record ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class FollowUpResponse(BaseModel):
    """Response model for follow-up send"""
    status: str = Field(..., description="Follow-up status")
    trace_id: str = Field(..., description="Request trace ID")
    outreach_id: int = Field(..., description="Outreach record ID")
    follow_up_number: int = Field(..., description="Follow-up attempt number")
    email_sent: bool = Field(..., description="Whether email was successfully sent")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class JobData(BaseModel):
    """Job listing information"""
    id: int = Field(..., description="Job database ID")
    job_id: str = Field(..., description="External job ID")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: Optional[str] = Field(None, description="Job location")
    description: Optional[str] = Field(None, description="Job description")
    url: Optional[str] = Field(None, description="Job posting URL")
    source: str = Field(..., description="Job source")
    posted_date: Optional[datetime] = Field(None, description="Job posting date")
    fetched_at: Optional[datetime] = Field(None, description="Fetch timestamp")
    match_score: Optional[float] = Field(None, ge=0, le=100, description="AI match score")
    application_status: Optional[str] = Field(None, description="Current application pipeline status")
    provider_id: Optional[str] = None
    company_website: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    has_remote: Optional[bool] = None
    work_mode: Optional[str] = None
    experience_level: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    provider_sources: List[str] = Field(default_factory=list)


class PaginationData(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, description="Items per page")
    total: int = Field(..., ge=0, description="Total items")
    pages: int = Field(..., ge=0, description="Total pages")


class JobsResponse(BaseModel):
    """Response model for jobs list"""
    status: str = Field(..., description="Request status")
    jobs: List[JobData] = Field(default_factory=list, description="List of jobs")
    pagination: PaginationData = Field(..., description="Pagination information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ContactsResponse(BaseModel):
    """Response model for contacts list"""
    status: str = Field(..., description="Request status")
    contacts: List[ContactData] = Field(default_factory=list, description="List of contacts")
    pagination: PaginationData = Field(..., description="Pagination information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class CrawlResponse(BaseModel):
    """Response model for Cloudflare crawl"""
    status: str = Field(..., description="Crawl status")
    trace_id: str = Field(..., description="Request trace ID")
    url: str = Field(..., description="Crawled URL")
    pages_crawled: int = Field(..., ge=0, description="Number of pages crawled")
    jobs_stored: int = Field(..., ge=0, description="Number of jobs stored")
    pages: List[Dict[str, Any]] = Field(default_factory=list, description="Crawled pages data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class StartupDiscoveryRequest(BaseModel):
    """Request model for startup discovery"""
    provider: str = Field("firecrawl", description="Discovery provider: 'firecrawl' or 'newsapi'")
    target_count: int = Field(50, ge=1, le=1000, description="Target number of startups to find")
    duration_hours: float = Field(0.0, ge=0, le=24, description="Duration to run in hours (0 for single iteration)")
    location: str = Field("India", description="Geographic location to search")


class StartupDiscoveryResponse(BaseModel):
    """Response model for startup discovery"""
    status: str = Field(..., description="Discovery status")
    trace_id: str = Field(..., description="Request trace ID")
    startups_found: int = Field(..., description="Number of unique startups found")
    new_startups_added: int = Field(..., description="Number of new startups added to scraping list")
    companies: List[str] = Field(default_factory=list, description="List of company names found")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class HealthComponentStatus(BaseModel):
    """Health check component status"""
    status: str = Field(..., description="Component status")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class HealthResponse(BaseModel):
    """Response model for health check endpoint"""
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    components: Dict[str, HealthComponentStatus] = Field(..., description="Component health statuses")
    summary: Optional[Dict[str, Any]] = Field(None, description="Health summary")
    issues: Optional[List[str]] = Field(None, description="Critical issues")
    warnings: Optional[List[str]] = Field(None, description="Warnings")


# ═══════════════════════════════════════════════════════════════════════════
# Error Response Models
# ═══════════════════════════════════════════════════════════════════════════

class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    type: Optional[str] = Field(None, description="Error type")


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    
    Requirements: 23.2 (Comprehensive error responses), 23.5 (Request tracing)
    """
    status: str = Field(default="error", description="Response status")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    trace_id: Optional[str] = Field(None, description="Request trace ID for debugging")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "error",
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": [
                {
                    "field": "min_score",
                    "message": "Value must be between 0 and 100",
                    "type": "value_error"
                }
            ],
            "trace_id": "a4f8-123",
            "timestamp": "2024-03-03T10:15:23.123456"
        }
    })


class TimeoutErrorResponse(BaseModel):
    """Response for timeout errors"""
    status: str = Field(default="error", description="Response status")
    error: str = Field(default="TimeoutError", description="Error type")
    message: str = Field(..., description="Timeout error message")
    timeout_seconds: int = Field(..., description="Timeout threshold that was exceeded")
    trace_id: Optional[str] = Field(None, description="Request trace ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class RateLimitErrorResponse(BaseModel):
    """Response for rate limit errors"""
    status: str = Field(default="error", description="Response status")
    error: str = Field(default="RateLimitError", description="Error type")
    message: str = Field(..., description="Rate limit error message")
    retry_after_seconds: Optional[int] = Field(None, description="Seconds to wait before retrying")
    trace_id: Optional[str] = Field(None, description="Request trace ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


# ═══════════════════════════════════════════════════════════════════════════
# Query Parameter Models (for GET endpoint validation)
# Requirements: 23.2 (Validate request parameters)
# ═══════════════════════════════════════════════════════════════════════════

class PaginationParams(BaseModel):
    """
    Pagination query parameters for list endpoints.
    
    Requirements: 23.2 (Input validation)
    """
    page: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Page number (1-indexed)",
        examples=[1, 2, 10],
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Number of items per page (1-500)",
        examples=[10, 50, 100],
    )


class JobsQueryParams(PaginationParams):
    """
    Query parameters for jobs list endpoint.
    
    Requirements: 23.2 (Input validation)
    """
    source: Optional[JobSource] = Field(
        default=None,
        description="Filter by job source",
    )
    company: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Filter by company name (partial match)",
    )
    min_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Filter by minimum match score",
    )


class ContactsQueryParams(PaginationParams):
    """
    Query parameters for contacts list endpoint.
    
    Requirements: 23.2 (Input validation)
    """
    company: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Filter by company name (partial match)",
    )
    min_confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Filter by minimum confidence score",
    )


class PendingOutreachParams(BaseModel):
    """
    Query parameters for pending outreach endpoint.
    
    Requirements: 23.2 (Input validation)
    """
    min_score: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Minimum match score threshold",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of jobs to return",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Additional Response Models
# Requirements: 23.3 (Return processing statistics)
# ═══════════════════════════════════════════════════════════════════════════

class StatsData(BaseModel):
    """Statistics data structure"""
    total_jobs: int = Field(..., ge=0, description="Total jobs in database")
    total_contacts: int = Field(..., ge=0, description="Total contacts discovered")
    total_applications: int = Field(..., ge=0, description="Total job applications")
    total_outreach_attempts: int = Field(..., ge=0, description="Total outreach attempts")
    emails_sent: int = Field(..., ge=0, description="Emails successfully sent")
    follow_ups_sent: int = Field(..., ge=0, description="Follow-up emails sent")
    success_rate: float = Field(..., ge=0, le=100, description="Email send success rate percentage")


class RecentOutreach(BaseModel):
    """Recent outreach record summary"""
    id: int = Field(..., description="Outreach record ID")
    contact_email: str = Field(..., description="Contact email")
    status: str = Field(..., description="Outreach status")
    sent_at: Optional[datetime] = Field(None, description="Send timestamp")


class StatsResponse(BaseModel):
    """
    Response model for statistics endpoint.
    
    Requirements: 23.3 (Return processing statistics)
    """
    status: str = Field(..., description="Request status")
    source: str = Field(..., description="Data source (live or db_fallback)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    stats: StatsData = Field(..., description="Statistics data")
    recent_outreach: List[RecentOutreach] = Field(default_factory=list, description="Recent outreach records")
    error: Optional[str] = Field(None, description="Error message if any")


class PendingOutreachJob(BaseModel):
    """Job pending outreach"""
    id: int = Field(..., description="Job ID")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: Optional[str] = Field(None, description="Job location")
    url: Optional[str] = Field(None, description="Job URL")
    source: str = Field(..., description="Job source")
    posted_date: Optional[datetime] = Field(None, description="Posted date")
    fetched_at: Optional[datetime] = Field(None, description="Fetch timestamp")


class PendingOutreachResponse(BaseModel):
    """
    Response model for pending outreach jobs.
    
    Requirements: 23.3 (Return processing statistics)
    """
    status: str = Field(..., description="Request status")
    total_jobs: int = Field(..., ge=0, description="Total jobs pending outreach")
    jobs: List[PendingOutreachJob] = Field(default_factory=list, description="Jobs pending outreach")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class SignalHireCallbackResponse(BaseModel):
    """Response model for SignalHire webhook callback"""
    status: str = Field(..., description="Callback status")
    saved: int = Field(..., ge=0, description="Number of contacts saved")
    total: int = Field(..., ge=0, description="Total items in callback")


class SignalHireResultResponse(BaseModel):
    """Response model for SignalHire result lookup"""
    status: str = Field(..., description="Lookup status")
    contact: Optional[Dict[str, Any]] = Field(None, description="Contact data if found")
    message: Optional[str] = Field(None, description="Status message")


class ApplicationUpdateRequest(BaseModel):
    """Update the user's pipeline status for a job opportunity."""
    status: Literal["saved", "ready", "applied", "interview", "offer", "negotiation", "accepted", "rejected"]


class LifecycleActionData(BaseModel):
    key: str
    label: str
    reason: str
    priority: Literal["high", "medium", "low"]
    route: Optional[str] = None
    external: bool = False
    requires_confirmation: bool = False


class ActionQueueItem(BaseModel):
    job_id: int
    application_id: Optional[int] = None
    title: str
    company: Optional[str] = None
    fit_score: Optional[float] = None
    stage: str
    status: Optional[str] = None
    action: LifecycleActionData
    url: Optional[str] = None
    updated_at: Optional[datetime] = None


class ActionQueueResponse(BaseModel):
    status: str
    actions: List[ActionQueueItem] = Field(default_factory=list)
    total: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LifecycleTransitionRequest(BaseModel):
    status: Literal["ready", "applied", "interview", "offer", "negotiation", "accepted", "rejected"]


class SubmissionProofRequest(BaseModel):
    proof_url: Optional[str] = None
    proof_notes: Optional[str] = None


class OpportunitySignal(BaseModel):
    label: str
    value: str
    strength: str = Field(..., pattern=r"^(strong|medium|weak|info)$")
    detail: str


class OpportunityPerson(BaseModel):
    id: int
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    confidence_score: int = 0
    relationship_hint: str


class OpportunityResume(BaseModel):
    has_master_resume: bool
    master_resume_label: Optional[str] = None
    has_tailored_resume: bool
    tailored_resume_label: Optional[str] = None
    cover_letter_preview: Optional[str] = None
    missing_keywords: List[str] = Field(default_factory=list)


class OpportunityOutreach(BaseModel):
    total: int = 0
    sent: int = 0
    replied: int = 0
    pending: int = 0
    latest_status: Optional[str] = None
    recommended_message: str


class OpportunityNextAction(BaseModel):
    key: str
    label: str
    reason: str
    priority: str = Field(..., pattern=r"^(high|medium|low)$")
    route: Optional[str] = None
    external: bool = False
    requires_confirmation: bool = False


class OpportunityBriefResponse(BaseModel):
    status: str
    job: JobData
    fit_score: float = Field(..., ge=0, le=100)
    fit_label: str
    fit_reasons: List[str] = Field(default_factory=list)
    company_signals: List[OpportunitySignal] = Field(default_factory=list)
    people: List[OpportunityPerson] = Field(default_factory=list)
    resume: OpportunityResume
    outreach: OpportunityOutreach
    next_action: OpportunityNextAction
    application_status: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ProviderSyncRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    max_age_days: int = Field(default=30, ge=1, le=999)
    limit: int = Field(default=50, ge=1, le=100)


class ProviderSyncSource(BaseModel):
    provider: str
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    failed: bool = False
    error: Optional[str] = None


class ProviderSyncResponse(BaseModel):
    status: str
    total_fetched: int
    total_inserted: int
    total_updated: int
    sources: List[ProviderSyncSource] = Field(default_factory=list)


class MarketIntelligenceResponse(BaseModel):
    status: str
    provider: str
    data: Dict[str, Any] = Field(default_factory=dict)
    stale: bool = False
    error: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
