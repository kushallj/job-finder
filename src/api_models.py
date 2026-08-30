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
    email: Optional[str] = Field(None, description="Email address")
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


# ═══════════════════════════════════════════════════════════════════════════
# Job Capture & LinkedIn Referral Automator Models
# ═══════════════════════════════════════════════════════════════════════════

class JobCaptureRequest(BaseModel):
    """Request model for 1-click capturing job postings from LinkedIn/Indeed."""
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=500, description="Job title")
    company: str = Field(default="", max_length=500, description="Company name")
    location: Optional[str] = Field(default=None, max_length=500, description="Job location")
    description: str = Field(default="", max_length=20000, description="Job description text")
    url: str = Field(..., min_length=1, max_length=2000, description="Job posting URL")
    source: str = Field(default="linkedin_extension", max_length=100, description="Capture source")
    score: bool = Field(
        default=False,
        description="If true, score this job against the configured resume using AI",
    )


class JobCaptureResponse(BaseModel):
    """Response model for a captured job, optionally including an AI match score."""
    status: str = Field(..., description="Request status")
    job: JobData = Field(..., description="The saved or pre-existing job")
    already_existed: bool = Field(default=False, description="True if this URL was already saved")
    match_score: Optional[float] = Field(default=None, description="AI match score (0-100), if scored")
    matched_skills: Optional[List[str]] = Field(default=None, description="Skills the resume covers")
    missing_skills: Optional[List[str]] = Field(default=None, description="Skills the resume is missing")
    score_error: Optional[str] = Field(default=None, description="Error message if scoring failed")


class ReferralTargetsResponse(BaseModel):
    """Response model for active referral targets from the job pipeline."""
    status: str = Field(..., description="Request status")
    total_targets: int = Field(..., description="Total active targets")
    targets: List[Dict[str, Any]] = Field(default_factory=list, description="Active target companies and roles")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReferralSearchRequest(BaseModel):
    """Request model for searching LinkedIn referral contacts by company."""
    company: str = Field(..., min_length=1, max_length=255, description="Target company name")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum profiles to return")
    job_title: Optional[str] = Field(default=None, max_length=255, description="Optional target job title")


class ReferralSearchResponse(BaseModel):
    """Response model for LinkedIn referral contacts search."""
    status: str = Field(..., description="Request status")
    company: str = Field(..., description="Target company")
    source: str = Field(..., description="Data source: 'proxycurl', 'csv', or 'disk_cache'")
    count: int = Field(..., description="Number of profiles returned")
    profiles: List[Dict[str, Any]] = Field(default_factory=list, description="Discovered profiles")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReferralProfileSyncRequest(BaseModel):
    """Request model for batch syncing discovered LinkedIn profiles into Contacts CRM."""
    profiles: List[Dict[str, Any]] = Field(..., min_length=1, description="List of profile objects to ingest")


class ReferralProfileSyncResponse(BaseModel):
    """Response model for referral profile ingestion."""
    status: str = Field(..., description="Request status")
    synced_count: int = Field(..., description="Total profiles processed")
    new_contacts_count: int = Field(..., description="Newly inserted contacts")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReferralNoteGenerateRequest(BaseModel):
    """Request model for generating personalized referral connection notes & letters."""
    full_name: str = Field(..., min_length=1, max_length=255, description="Contact full name")
    company: str = Field(..., min_length=1, max_length=255, description="Target company")
    first_name: Optional[str] = Field(default=None, max_length=100)
    title: Optional[str] = Field(default=None, max_length=255)
    headline: Optional[str] = Field(default=None, max_length=500)
    job_title: Optional[str] = Field(default=None, max_length=255)
    job_link: Optional[str] = Field(default=None, max_length=2000)
    short_bio: Optional[str] = Field(default=None, max_length=500)
    highlight: Optional[str] = Field(default=None, max_length=500)
    reason: Optional[str] = Field(default=None, max_length=500)
    sender_name: Optional[str] = Field(default="Candidate", max_length=100)
    max_length: Optional[int] = Field(default=200, ge=50, le=2000, description="Max character length for connection note")


class ReferralNoteGenerateResponse(BaseModel):
    """Response model for generated referral notes."""
    status: str = Field(..., description="Request status")
    connection_note: str = Field(..., description="Concise connection note constrained by max_length")
    full_letter: str = Field(..., description="Full multi-paragraph referral letter")
    char_count: int = Field(..., description="Connection note character count")
    is_under_limit: bool = Field(..., description="Whether note satisfies max_length")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReferralActionLogRequest(BaseModel):
    """Request model for logging a LinkedIn referral action."""
    contact_name: str = Field(..., min_length=1, max_length=255, description="Contact name")
    company: str = Field(..., min_length=1, max_length=255, description="Company name")
    action_type: str = Field(..., pattern=r"^(connection_sent|message_sent|replied)$", description="Action type")
    linkedin_url: Optional[str] = Field(default=None, max_length=2000, description="LinkedIn profile URL")
    contact_email: Optional[str] = Field(default=None, max_length=255, description="Contact email if known")
    message_body: Optional[str] = Field(default=None, max_length=10000, description="Message text")
    job_id: Optional[int] = Field(default=None, description="Associated job ID if applicable")


class ReferralActionLogResponse(BaseModel):
    """Response model for referral action logging."""
    status: str = Field(..., description="Request status")
    outreach_id: int = Field(..., description="Created OutreachRecord ID")
    message: str = Field(..., description="Confirmation message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# X (Twitter) Referral Automator & Engagement Models
# ═══════════════════════════════════════════════════════════════════════════

class XAuthUrlResponse(BaseModel):
    """Response containing generated X OAuth 2.0 PKCE authorization link."""
    status: str = Field(default="success")
    authorization_url: str = Field(..., description="X OAuth URL")
    state: str = Field(..., description="State parameter for CSRF verification")


class XAuthCallbackRequest(BaseModel):
    """Request model for exchanging OAuth code for tokens."""
    code: str = Field(..., min_length=1, description="Authorization code from X")
    state: str = Field(..., min_length=1, description="State parameter returned by X")
    code_verifier: Optional[str] = Field(None, description="PKCE code verifier if stored by client")


class XAuthCallbackResponse(BaseModel):
    """Response for successful X authentication."""
    status: str = Field(default="success")
    connected: bool = Field(default=True)
    message: str = Field(..., description="Confirmation message")


class XAuthStatusResponse(BaseModel):
    """Status of X account connection."""
    connected: bool = Field(..., description="Whether X account is connected")
    username: Optional[str] = Field(None, description="Connected X handle")
    expires_at: Optional[datetime] = Field(None)
    scopes: Optional[List[str]] = Field(default_factory=list)


class XTargetsResponse(BaseModel):
    """Active target companies for X networking."""
    status: str = Field(default="success")
    total_targets: int = Field(...)
    targets: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class XSearchRequest(BaseModel):
    """Search request for tech employees & leaders on X."""
    company: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = Field(default=None, max_length=255)
    limit: int = Field(default=10, ge=1, le=50)


class XSearchResponse(BaseModel):
    """Search response for X users."""
    status: str = Field(default="success")
    company: str = Field(...)
    role: Optional[str] = Field(None)
    source: str = Field(...)
    count: int = Field(...)
    profiles: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class XTweetSearchRequest(BaseModel):
    """Search request for active hiring tweets."""
    company: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = Field(default=None, max_length=255)
    limit: int = Field(default=10, ge=1, le=50)


class XTweetSearchResponse(BaseModel):
    """Search response for hiring tweets on X."""
    status: str = Field(default="success")
    company: str = Field(...)
    role: Optional[str] = Field(None)
    count: int = Field(...)
    tweets: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class XMessageGenerateRequest(BaseModel):
    """Request model for AI generation of X contextual replies, quote tweets, or DMs."""
    action_type: Literal["dm", "reply", "quote"] = Field(...)
    username: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    role_title: Optional[str] = Field(None, max_length=255)
    job_link: Optional[str] = Field(None, max_length=2000)
    candidate_bio: Optional[str] = Field(None, max_length=500)
    highlight: Optional[str] = Field(None, max_length=500)
    target_topic: Optional[str] = Field(None, max_length=500)
    sender_name: Optional[str] = Field(default="Candidate", max_length=100)
    tweet_id: Optional[str] = Field(None, max_length=100)
    tweet_text: Optional[str] = Field(None, max_length=1000)
    max_length: Optional[int] = Field(default=280, ge=50, le=2000)


class XMessageGenerateResponse(BaseModel):
    """Response model for generated X message/reply."""
    status: str = Field(default="success")
    action_type: str = Field(...)
    message: str = Field(...)
    char_count: int = Field(...)
    is_under_limit: bool = Field(...)
    intent_url: Optional[str] = Field(None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class XEngageRequest(BaseModel):
    """Request to execute an action on X (follow, like, repost, reply, DM)."""
    action_type: Literal["follow", "like", "repost", "reply", "dm", "quote"] = Field(...)
    target_username: str = Field(..., min_length=1, max_length=255)
    company: str = Field(default="Tech Company", max_length=255)
    target_user_id: Optional[str] = Field(None, max_length=100)
    tweet_id: Optional[str] = Field(None, max_length=100)
    message_text: Optional[str] = Field(None, max_length=5000)
    job_id: Optional[int] = Field(None)


class XEngageResponse(BaseModel):
    """Response for executed X action."""
    status: str = Field(default="success")
    outreach_id: int = Field(...)
    action_type: str = Field(...)
    target: str = Field(...)
    intent_url: Optional[str] = Field(None)
    mode: str = Field(default="api")
    daily_usage: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class XProfileSyncRequest(BaseModel):
    """Batch ingest X profiles into Contacts CRM."""
    profiles: List[Dict[str, Any]] = Field(..., min_length=1)


class XProfileSyncResponse(BaseModel):
    """Response for X profile ingestion."""
    status: str = Field(default="success")
    synced_count: int = Field(...)
    new_contacts_count: int = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# Email Intelligence & Google Boolean Dorking API Models
# ═══════════════════════════════════════════════════════════════════════════

class EmailDiscoveryRequest(BaseModel):
    """Request model for waterfall decision-maker and email discovery."""
    company: str = Field(..., min_length=1, max_length=255)
    job_title: Optional[str] = Field(default=None, max_length=255)
    website_hint: Optional[str] = Field(default=None, max_length=2000)
    target_name: Optional[str] = Field(default=None, max_length=255)
    limit: int = Field(default=6, ge=1, le=20)


class EmailDiscoveryResponse(BaseModel):
    """Response model for discovered decision-makers and emails."""
    status: str = Field(default="success")
    company: str = Field(...)
    domain: str = Field(...)
    has_mx: bool = Field(default=True)
    mail_provider: str = Field(default="Unknown")
    total_found: int = Field(...)
    contacts: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_contact: Optional[Dict[str, Any]] = Field(None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EmailVerifyRequest(BaseModel):
    """Request model for live email verification and MX check."""
    email: str = Field(..., min_length=3, max_length=255)


class EmailVerifyResponse(BaseModel):
    """Response model for email verification."""
    status: str = Field(default="success")
    email: str = Field(...)
    is_valid_syntax: bool = Field(...)
    is_disposable: bool = Field(...)
    is_free_mail: bool = Field(...)
    has_mx_records: bool = Field(...)
    mx_records: List[str] = Field(default_factory=list)
    mail_provider: str = Field(...)
    confidence_score: float = Field(...)
    verification_status: str = Field(...)
    reason: Optional[str] = Field(None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EmailDorksRequest(BaseModel):
    """Request model for generating Google Boolean Dorks."""
    company: str = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = Field(default=None, max_length=255)
    person_name: Optional[str] = Field(default=None, max_length=255)
    role_title: Optional[str] = Field(default=None, max_length=255)


class EmailDorksResponse(BaseModel):
    """Response containing generated Google Boolean Dorks."""
    status: str = Field(default="success")
    company: str = Field(...)
    domain: str = Field(...)
    total_dorks: int = Field(...)
    dorks: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EmailPermutationsRequest(BaseModel):
    """Request model for 12 corporate email permutations."""
    full_name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)


class EmailPermutationsResponse(BaseModel):
    """Response model containing 12 corporate permutations with MX score."""
    status: str = Field(default="success")
    full_name: str = Field(...)
    domain: str = Field(...)
    has_mx: bool = Field(...)
    total_permutations: int = Field(...)
    permutations: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# Transformer Q, K, V Attention Architecture API Models
# ═══════════════════════════════════════════════════════════════════════════

class AttentionMatchRequest(BaseModel):
    """Request model for Multi-Head Q,K,V Attention job matching."""
    job_description: str = Field(..., min_length=10)
    custom_bullets: Optional[List[str]] = Field(default=None)


class AttentionMatchResponse(BaseModel):
    """Response model containing 4-head attention scores, matrix, and values."""
    status: str = Field(default="success")
    overall_score: float = Field(...)
    fit_label: str = Field(...)
    heads: Dict[str, Any] = Field(default_factory=dict)
    matrix: Dict[str, Any] = Field(default_factory=dict)
    top_attended_values: List[Dict[str, Any]] = Field(default_factory=list)
    tailored_bullets: List[Dict[str, Any]] = Field(default_factory=list)
    outreach_hooks: List[Dict[str, Any]] = Field(default_factory=list)
    summary_insight: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AttentionTailorRequest(BaseModel):
    """Request model for attention-weighted resume bullet tailoring."""
    job_description: str = Field(..., min_length=10)
    custom_bullets: Optional[List[str]] = Field(default=None)


class AttentionTailorResponse(BaseModel):
    """Response containing tailored bullets ordered by attention weights."""
    status: str = Field(default="success")
    total_bullets: int = Field(...)
    tailored_bullets: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AttentionOutreachRequest(BaseModel):
    """Request model for cross-attention outreach hook generation."""
    contact_name: str = Field(..., min_length=1, max_length=255)
    contact_title: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    job_description: Optional[str] = Field(default=None)


class AttentionOutreachResponse(BaseModel):
    """Response model for cross-attention personalized outreach."""
    status: str = Field(default="success")
    contact_name: str = Field(...)
    contact_title: str = Field(...)
    company: str = Field(...)
    role_type: str = Field(...)
    subject: str = Field(...)
    hook_message: str = Field(...)
    attended_proof_point: str = Field(...)
    impact_metric: Optional[str] = Field(None)
    call_to_action: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# Ghost Job & Stale Listing Detector API Models
# ═══════════════════════════════════════════════════════════════════════════

class GhostAnalysisRequest(BaseModel):
    """Request model for Ghost Job analysis."""
    title: str = Field(..., min_length=1)
    company: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    posted_date: Optional[str] = Field(None)
    has_decision_maker: bool = Field(default=False)


class GhostAnalysisResponse(BaseModel):
    """Response model containing Ghost score and urgency signals."""
    status: str = Field(default="success")
    ghost_score: float = Field(...)
    urgency_label: str = Field(...)
    is_ghost_risk: bool = Field(...)
    confidence_score: float = Field(...)
    estimated_age_days: Optional[int] = Field(None)
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    action_recommendation: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# Cold Email Deliverability Sandbox API Models
# ═══════════════════════════════════════════════════════════════════════════

class DeliverabilityDraftRequest(BaseModel):
    """Request model for analyzing cold email deliverability and spam risk."""
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)


class DeliverabilityDraftResponse(BaseModel):
    """Response model with spam score, reading grade, and synonym suggestions."""
    status: str = Field(default="success")
    spam_score: float = Field(...)
    deliverability_tier: str = Field(...)
    is_safe: bool = Field(...)
    flesch_kincaid_grade: float = Field(...)
    reading_time_seconds: int = Field(...)
    word_count: int = Field(...)
    char_count: int = Field(...)
    link_count: int = Field(...)
    uppercase_ratio: float = Field(...)
    spam_matches: List[Dict[str, Any]] = Field(default_factory=list)
    subject_score: float = Field(...)
    subject_advice: str = Field(...)
    deliverability_recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# Live Voice & Audio AI Mock Interviewer API Models
# ═══════════════════════════════════════════════════════════════════════════

class VoiceFeedbackRequest(BaseModel):
    """Request model for analyzing spoken audio interview transcript."""
    transcript: str = Field(..., min_length=1)
    duration_seconds: float = Field(..., ge=1.0)
    target_focus: Optional[str] = Field(default="Distributed Systems")


class VoiceFeedbackResponse(BaseModel):
    """Response model for verbal delivery, cadence, and STAR fluency."""
    status: str = Field(default="success")
    speech_delivery_score: float = Field(...)
    filler_stats: Dict[str, Any] = Field(...)
    cadence_stats: Dict[str, Any] = Field(...)
    star_eval: Dict[str, Any] = Field(...)
    delivery_tips: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# Instant Multi-Channel Webhook Alerts API Models
# ═══════════════════════════════════════════════════════════════════════════

class NotificationConfigSchema(BaseModel):
    """Configuration model for Telegram, Discord, and Slack alerts."""
    telegram_bot_token: Optional[str] = Field(None)
    telegram_chat_id: Optional[str] = Field(None)
    discord_webhook_url: Optional[str] = Field(None)
    slack_webhook_url: Optional[str] = Field(None)
    min_fit_score: float = Field(default=65.0, ge=0.0, le=100.0)
    notify_on_tier1_only: bool = Field(default=False)
    enabled: bool = Field(default=True)


class NotificationAlertSchema(BaseModel):
    """Alert payload to dispatch to webhooks."""
    job_id: Optional[int] = Field(None)
    title: str = Field(..., min_length=1)
    company: str = Field(..., min_length=1)
    location: Optional[str] = Field(default="Remote")
    fit_score: float = Field(..., ge=0.0, le=100.0)
    job_url: str = Field(..., min_length=1)
    top_contact_name: Optional[str] = Field(None)
    top_contact_email: Optional[str] = Field(None)
    summary_hook: Optional[str] = Field(None)


class NotificationTestRequest(BaseModel):
    """Request model for testing a specific notification channel."""
    channel: str = Field(..., description="telegram, discord, slack")


class NotificationDispatchResponseSchema(BaseModel):
    """Response model summarizing alert dispatch results across channels."""
    status: str = Field(default="success")
    dispatched_count: int = Field(...)
    results: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# 4-Year Total Compensation & Equity Simulator API Models
# ═══════════════════════════════════════════════════════════════════════════

class OfferPackageSchema(BaseModel):
    """Offer package data for compensation modeling."""
    company: str = Field(..., min_length=1)
    role_title: str = Field(..., min_length=1)
    base_salary: float = Field(..., ge=0.0)
    signon_bonus: float = Field(default=0.0, ge=0.0)
    target_bonus_pct: float = Field(default=15.0, ge=0.0, le=100.0)
    equity_grant_usd: float = Field(default=0.0, ge=0.0)
    vesting_schedule: str = Field(default="standard_4yr_25")
    custom_vesting_splits: Optional[List[float]] = Field(None)
    stock_type: str = Field(default="RSU")
    startup_exit_multiple: float = Field(default=1.0, ge=0.1, le=100.0)
    estimated_tax_rate: float = Field(default=35.0, ge=0.0, le=70.0)


class CompSimulationResponse(BaseModel):
    """Response model with 4-year trajectory, yearly breakdowns, and counter targets."""
    status: str = Field(default="success")
    company: str = Field(...)
    role_title: str = Field(...)
    four_year_total_pre_tax: float = Field(...)
    four_year_total_post_tax: float = Field(...)
    average_annual_comp: float = Field(...)
    yearly_breakdowns: List[Dict[str, Any]] = Field(default_factory=list)
    negotiation_counter_target: float = Field(...)
    negotiation_advice: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CompComparisonRequest(BaseModel):
    """Request model for comparing multiple offer packages."""
    offers: List[OfferPackageSchema] = Field(..., min_length=1)


# ═══════════════════════════════════════════════════════════════════════════
# 1-Click ATS Tailored Resume & Cover Letter API Models
# ═══════════════════════════════════════════════════════════════════════════

class ResumeGenerateRequestSchema(BaseModel):
    """Request model for tailored ATS resume generation."""
    candidate_name: Optional[str] = Field(default="Candidate")
    candidate_email: Optional[str] = Field(default="candidate@example.com")
    candidate_phone: Optional[str] = Field(default="+1 (555) 019-2834")
    candidate_location: Optional[str] = Field(default="San Francisco, CA / Remote")
    candidate_linkedin: Optional[str] = Field(default="linkedin.com/in/candidate")
    candidate_github: Optional[str] = Field(default="github.com/candidate")
    role_title: str = Field(..., min_length=1)
    company: str = Field(..., min_length=1)
    job_description: Optional[str] = Field(default=None)
    custom_bullets: Optional[List[str]] = Field(default=None)


class CoverLetterGenerateRequestSchema(BaseModel):
    """Request model for tailored cover letter synthesis."""
    candidate_name: Optional[str] = Field(default="Candidate")
    candidate_email: Optional[str] = Field(default="candidate@example.com")
    company: str = Field(..., min_length=1)
    role_title: str = Field(..., min_length=1)
    hiring_manager_name: Optional[str] = Field(default="Engineering Leadership Team")
    job_description: Optional[str] = Field(default=None)


class ResumeDocumentResponseSchema(BaseModel):
    """Response model with rendered HTML, plain text, and ATS keyword matches."""
    status: str = Field(default="success")
    document_type: str = Field(...)
    company: str = Field(...)
    role_title: str = Field(...)
    ats_match_score: float = Field(...)
    html_content: str = Field(...)
    plain_text: str = Field(...)
    suggested_keywords: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# Community Intel & Interview Debrief Aggregator API Models
# ═══════════════════════════════════════════════════════════════════════════

class CommunityHarvestRequest(BaseModel):
    """Request model to trigger community debrief harvesting for a company."""
    company: str = Field(..., min_length=1)
    role_category: Optional[str] = Field(default="Software Engineer")
    force_refresh: bool = Field(default=False)


class CommunityIntelResponse(BaseModel):
    """Response model with interview rounds, question leaks, and source citations."""
    status: str = Field(default="success")
    company: str = Field(...)
    role_category: str = Field(...)
    total_sources_scanned: int = Field(...)
    overall_sentiment: str = Field(...)
    interview_debrief: Dict[str, Any] = Field(...)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: str = Field(...)


# ═══════════════════════════════════════════════════════════════════════════
# AI OSINT Boolean Query Copilot API Models
# ═══════════════════════════════════════════════════════════════════════════

class CopilotChatRequest(BaseModel):
    """Request model for conversational AI turn with Boolean query detection."""
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = Field(default=None)
    target_company: Optional[str] = Field(default=None)
    role_title: Optional[str] = Field(default=None)


class CopilotChatResponse(BaseModel):
    """Response model with AI reply, targeted boolean dorks, and follow-ups."""
    status: str = Field(default="success")
    session_id: str = Field(...)
    reply: str = Field(...)
    dorks: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    timestamp: str = Field(...)


class CopilotDorksRequest(BaseModel):
    """Request model for generating specific Google Boolean Dork queries."""
    role_title: str = Field(..., min_length=1)
    company: Optional[str] = Field(default=None)
    intent: Optional[str] = Field(default="unindexed_jds")


class CopilotDorksResponse(BaseModel):
    """Response model with generated precision Boolean dorks."""
    status: str = Field(default="success")
    total_dorks: int = Field(...)
    dorks: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(...)











