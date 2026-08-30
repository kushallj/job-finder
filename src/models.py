from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    company = Column(String(500))
    location = Column(String(500))
    description = Column(Text)
    url = Column(Text)
    source = Column(String(100))
    posted_date = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    # External job intelligence metadata (JobDataAPI / AI Dev Jobs)
    provider_id = Column(String(255))
    company_website = Column(Text)
    salary_min = Column(Float)
    salary_max = Column(Float)
    salary_currency = Column(String(10))
    has_remote = Column(Boolean)
    work_mode = Column(String(50))
    experience_level = Column(String(20))
    tags = Column(Text)  # JSON array
    expired_at = Column(DateTime)
    provider_payload = Column(Text)  # JSON provider record for traceability
    provider_sources = Column(Text)  # JSON array of all providers that corroborated this role
    
    # Relationships
    applications = relationship("Application", back_populates="job")

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    
    # Matching
    match_score = Column(Float)
    skills_matched = Column(Text)  # JSON string
    skills_missing = Column(Text)  # JSON string
    
    # Generated content
    resume_version = Column(Text)
    cover_letter = Column(Text)
    
    # Status & Lifecycle
    status = Column(String(50), default="pending")  # saved, ready, applied, interview, offer, negotiation, accepted, rejected
    applied_at = Column(DateTime)

    # Submission packet & proof
    ats_detected = Column(String(100))
    customized_resume_path = Column(Text)
    cover_letter_path = Column(Text)
    submission_notes = Column(Text)
    proof_url = Column(Text)
    proof_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="applications")

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True)
    original_content = Column(Text, nullable=False)
    skills = Column(Text)  # JSON string
    experience_years = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    title = Column(String(255))
    email = Column(String(255))
    linkedin_url = Column(Text)
    company = Column(String(255), nullable=False)
    department = Column(String(255))
    confidence_score = Column(Integer, default=0)
    
    # Source tracking
    source = Column(String(100))  # 'linkedin', 'website', 'generated'
    found_at = Column(DateTime, default=datetime.utcnow)
    
    # Unsubscribe / Do-not-contact tracking (Requirement 17.4)
    do_not_contact = Column(Boolean, default=False)  # True when contact requests unsubscribe
    do_not_contact_reason = Column(String(255))  # e.g., 'unsubscribe_reply', 'bounced'
    do_not_contact_at = Column(DateTime)  # When the do-not-contact flag was set
    
    # Relationships
    outreach_records = relationship("OutreachRecord", back_populates="contact")

class OutreachRecord(Base):
    __tablename__ = "outreach_records"
    
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))
    
    # Email details
    subject = Column(String(500))
    body = Column(Text)
    template_type = Column(String(100))  # 'hr_outreach', 'engineering_manager', 'follow_up'
    
    # Status tracking
    status = Column(String(50), default="sent")  # sent, bounced, replied, no_response
    sent_at = Column(DateTime, default=datetime.utcnow)
    replied_at = Column(DateTime)
    email_sent = Column(Boolean, default=False)
    contact_email = Column(String(255))
    contact_name = Column(String(255))
    
    # Follow-up tracking
    follow_up_scheduled = Column(DateTime)
    follow_up_sent = Column(Boolean, default=False)
    follow_up_count = Column(Integer, default=0)
    last_follow_up_at = Column(DateTime)

    # Outreach intelligence (Task 6)
    reply_sentiment = Column(String(20))        # positive|negative|neutral|unsubscribe|referral
    ab_variant = Column(Integer, default=0)     # which A/B subject variant was used
    send_scheduled_at = Column(DateTime)        # SmartTimer scheduled send time
    timezone_detected = Column(String(100))     # detected recipient timezone
    
    # Relationships
    contact = relationship("Contact", back_populates="outreach_records")
    job = relationship("Job")

class ProcessingResult(Base):
    """Results from async pipeline job processing (Requirement 21.6)."""
    __tablename__ = "processing_results"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), nullable=False)
    
    # Processing status
    status = Column(String(50), nullable=False)  # pending, processing, completed, failed, retrying
    
    # Result data
    data = Column(Text)  # JSON string with processing result data
    error = Column(Text)  # Error message if failed
    error_type = Column(String(100))  # Error type/category
    
    # Metrics
    attempt_count = Column(Integer, default=1)
    processing_time_ms = Column(Float, default=0.0)
    worker_id = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PipelineMetric(Base):
    """Performance metrics for async pipeline execution (Requirement 21.7)."""
    __tablename__ = "pipeline_metrics"
    
    id = Column(Integer, primary_key=True)
    
    # Job metrics
    jobs_queued = Column(Integer, default=0)
    jobs_completed = Column(Integer, default=0)
    jobs_failed = Column(Integer, default=0)
    
    # Queue metrics
    queue_size = Column(Integer, default=0)
    queue_backpressure_events = Column(Integer, default=0)
    queue_wait_time_ms = Column(Float, default=0.0)
    
    # Worker metrics
    workers_active = Column(Integer, default=0)
    workers_total = Column(Integer, default=0)
    worker_utilization_percent = Column(Float, default=0.0)
    
    # Performance metrics
    throughput_jobs_per_second = Column(Float, default=0.0)
    latency_p50_ms = Column(Float, default=0.0)
    latency_p95_ms = Column(Float, default=0.0)
    latency_p99_ms = Column(Float, default=0.0)
    
    # API metrics
    api_rate_limit_waits = Column(Integer, default=0)
    api_rate_limit_wait_time_ms = Column(Float, default=0.0)
    
    # Error metrics
    retry_attempts = Column(Integer, default=0)
    retry_successes = Column(Integer, default=0)
    retry_failures = Column(Integer, default=0)
    
    # Timestamps
    recorded_at = Column(DateTime, default=datetime.utcnow)
    pipeline_start_time = Column(DateTime)
    pipeline_end_time = Column(DateTime)


class XOAuthToken(Base):
    """Stores OAuth 2.0 PKCE access and refresh tokens for connected X accounts."""
    __tablename__ = "x_oauth_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_identifier = Column(String(255), default="default_user", unique=True, index=True)
    x_user_id = Column(String(255), nullable=True)
    x_username = Column(String(255), nullable=True)
    x_name = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String(50), default="bearer")
    expires_at = Column(DateTime, nullable=True)
    scopes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DiscoveredEmailCache(Base):
    """Caches discovered and verified emails, MX records, and corporate patterns."""
    __tablename__ = "discovered_email_cache"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(255), index=True)
    domain = Column(String(255), index=True)
    person_name = Column(String(255))
    email = Column(String(255), index=True)
    title = Column(String(255))
    confidence_score = Column(Float, default=70.0)
    source = Column(String(100))  # dorking, github, hunter, apollo, pattern, clearbit
    mail_provider = Column(String(100))  # Google Workspace, Microsoft 365, Custom
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


