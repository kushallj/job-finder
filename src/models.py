from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    """Multi-tenant User account for SaaS commercialization."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    clerk_user_id = Column(String(255), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(500), nullable=True)
    full_name = Column(String(255), nullable=True)
    subscription_tier = Column(String(50), default="free")  # free, starter, pro, unlimited
    credits_balance = Column(Integer, default=50)  # Complimentary starting credits
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), default="active")  # active, past_due, canceled
    current_period_end = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applications = relationship("Application", back_populates="user")
    resumes = relationship("Resume", back_populates="user")
    credit_transactions = relationship("CreditTransaction", back_populates="user")
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    outreach_records = relationship("OutreachRecord", back_populates="user", cascade="all, delete-orphan")

class CreditTransaction(Base):
    """Audit log of credit additions, purchases, and AI generation/application deductions."""
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # e.g. -1 for tailor, +100 for top-up
    balance_after = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)  # "welcome_bonus", "resume_tailor", "workday_apply", "nextraise_apply", "topup"
    reference_id = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="credit_transactions")

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

class UserJob(Base):
    """Per-user state on a shared Job row (Jobify saved / applied). Jobs stay a shared catalog."""
    __tablename__ = "user_jobs"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_jobs_user_job"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    saved_at = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
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

    # Jobify card fields (jobify/src/services/applicationService.js). Manual cards have no
    # job_id, so company/position live here; events/offer are JSON the UI replaces wholesale.
    company = Column(String(500), nullable=True)
    position = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)  # manual | job | email
    events_json = Column(Text, nullable=True)   # [{id, title, at}]
    offer_json = Column(Text, nullable=True)    # {salary, deadline} or null

    # Kanban Board & Priority Positioning
    kanban_stage = Column(String(50), default="applied", index=True)
    kanban_order = Column(Integer, default=0)

    # Next Action & Countdown Timers (Amber, Blue, Red alerts)
    next_action_type = Column(String(50), nullable=True)
    next_action_title = Column(String(255), nullable=True)
    next_action_due_at = Column(DateTime, nullable=True)

    # Recruiter Email Thread Provenance
    recruiter_name = Column(String(255), nullable=True)
    recruiter_email = Column(String(255), nullable=True)
    recruiter_company = Column(String(255), nullable=True)
    email_subject = Column(String(500), nullable=True)
    email_thread_id = Column(String(255), nullable=True)
    last_email_received_at = Column(DateTime, nullable=True)

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
    user = relationship("User", back_populates="applications")

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    original_content = Column(Text, nullable=False)
    skills = Column(Text)  # JSON string
    experience_years = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="resumes")

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    title = Column(String(255))
    email = Column(String(255))
    linkedin_url = Column(Text)
    twitter_url = Column(Text, nullable=True)
    company = Column(String(255), nullable=False)
    department = Column(String(255))
    confidence_score = Column(Integer, default=0)
    
    # Source tracking
    source = Column(String(100))  # 'linkedin', 'website', 'generated', 'startups_gallery'
    found_at = Column(DateTime, default=datetime.utcnow)
    
    # Unsubscribe / Do-not-contact tracking (Requirement 17.4)
    do_not_contact = Column(Boolean, default=False)  # True when contact requests unsubscribe
    do_not_contact_reason = Column(String(255))  # e.g., 'unsubscribe_reply', 'bounced'
    do_not_contact_at = Column(DateTime)  # When the do-not-contact flag was set
    
    # Relationships
    user = relationship("User", back_populates="contacts")
    outreach_records = relationship("OutreachRecord", back_populates="contact")


class StartupsGalleryCompanyRecord(Base):
    """Catalog of startups.gallery companies tracking continuous mining progress."""
    __tablename__ = "startups_gallery_companies"

    id = Column(Integer, primary_key=True)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    funding = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    founded_year = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    ats_url = Column(Text, nullable=True)
    investors = Column(Text, nullable=True)  # JSON-encoded list of VC investors
    jobs = Column(Text, nullable=True)  # JSON-encoded list of active open jobs
    jobs_count = Column(Integer, default=0)

    mined = Column(Boolean, default=False, index=True)
    mined_at = Column(DateTime, nullable=True)
    founders_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class OutreachRecord(Base):
    __tablename__ = "outreach_records"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
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
    user = relationship("User", back_populates="outreach_records")
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


class CandidateProfile(Base):
    """Multi-user candidate profile model to replace singleton config/profile.yml."""
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_identifier = Column(String(255), default="default_user", unique=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=True)  # Public slug e.g. "kushal"
    full_name = Column(String(255), nullable=False)
    headline = Column(String(500), nullable=True)  # e.g. "Staff AI / Frontend Engineer — Distributed Systems & LLM Tooling"
    email = Column(String(255), nullable=False)
    phone = Column(String(100), nullable=True)
    location = Column(String(255), default="Remote")
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    github_username = Column(String(100), nullable=True)  # e.g. "kushalljain"
    portfolio_url = Column(String(500), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    custom_domain = Column(String(255), nullable=True)
    is_public = Column(Boolean, default=True)
    years_of_experience = Column(Float, default=3.0)
    current_title = Column(String(255), nullable=True)
    bio_summary = Column(Text, nullable=True)
    skills = Column(Text, default="[]")  # JSON array of skills e.g. ["Python", "FastAPI", "React"]
    target_roles = Column(Text, default="[]")  # JSON array of desired titles
    target_locations = Column(Text, default="[]")  # JSON array
    min_desired_salary = Column(Float, nullable=True)
    resume_raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships for Public Portfolio & RAG
    experiences = relationship("CandidateExperience", back_populates="profile", cascade="all, delete-orphan")
    projects = relationship("CandidateProject", back_populates="profile", cascade="all, delete-orphan")
    knowledge_chunks = relationship("CandidateKnowledgeChunk", back_populates="profile", cascade="all, delete-orphan")
    chat_logs = relationship("PortfolioChatLog", back_populates="profile", cascade="all, delete-orphan")


class TargetCompanyRecord(Base):
    """Database-backed target company list to replace singleton config/target_companies.yml."""
    __tablename__ = "target_companies"

    id = Column(Integer, primary_key=True, index=True)
    user_identifier = Column(String(255), default="default_user", index=True)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=False)
    tier = Column(String(50), default="tier1")  # tier1, fintech, ai_ml, accelerator, gcc, enterprise
    industry = Column(String(100), nullable=True)
    headquarters = Column(String(255), nullable=True)
    funding_stage = Column(String(100), nullable=True)
    signal_score = Column(Float, default=85.0)
    signal_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OutreachFunnelEvent(Base):
    """Tracks conversion events from lead discovery to interview/offer."""
    __tablename__ = "outreach_funnel_events"

    id = Column(Integer, primary_key=True, index=True)
    user_identifier = Column(String(255), default="default_user", index=True)
    event_type = Column(String(50), nullable=False)  # lead_discovered, packet_generated, review_approved, email_sent, reply_received, interview_scheduled, offer_received
    company = Column(String(255), index=True)
    role_title = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    channel = Column(String(50), default="email")  # email, linkedin, x_twitter, ats
    match_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class VCFirm(Base):
    """Venture Capital Firm entity (e.g. Y Combinator, Accel, Blume, Tiger Global, India Accelerator)."""
    __tablename__ = "vc_firms"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    website = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    country_focus = Column(String(100), default="Global")
    region = Column(String(100), default="US & Global", index=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    companies = relationship("PortfolioCompany", back_populates="vc_firm", cascade="all, delete-orphan")


class PortfolioCompany(Base):
    """Funded Portfolio Company under a specific VC firm."""
    __tablename__ = "portfolio_companies"

    id = Column(Integer, primary_key=True)
    vc_firm_id = Column(Integer, ForeignKey("vc_firms.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True, index=True)
    website = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    batch_or_year = Column(String(100), nullable=True)  # e.g. "W24", "Series A 2023"
    funding_stage = Column(String(100), nullable=True)  # Seed, Early Stage, Series A, Growth
    industry_tags = Column(Text, default="[]")  # JSON array string
    careers_url = Column(String(500), nullable=True)
    last_scraped_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    vc_firm = relationship("VCFirm", back_populates="companies")
    founders = relationship("CompanyFounder", back_populates="company", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("vc_firm_id", "slug", name="uq_vc_company_slug"),
    )


class CompanyFounder(Base):
    """Founder / Co-Founder of a portfolio company with enriched contact details."""
    __tablename__ = "company_founders"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("portfolio_companies.id"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=True)  # Co-Founder & CEO, Founder & CTO, etc.
    email = Column(String(255), nullable=True, index=True)
    email_confidence = Column(Float, default=0.0)  # 0.0 to 1.0 confidence
    linkedin_url = Column(String(500), nullable=True)
    twitter_handle = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    source = Column(String(50), default="firecrawl")  # firecrawl, playwright, heuristic
    last_verified_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("PortfolioCompany", back_populates="founders")

    __table_args__ = (
        UniqueConstraint("company_id", "full_name", name="uq_company_founder_name"),
    )


class MailboxAccount(Base):
    """Connected user mailbox (Gmail / Outlook) for incoming recruiter message synchronization."""
    __tablename__ = "mailbox_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    provider = Column(String(50), default="gmail")  # gmail, outlook, custom
    email_address = Column(String(255), nullable=False, unique=True, index=True)
    imap_host = Column(String(255), default="imap.gmail.com")
    imap_port = Column(Integer, default=993)
    use_ssl = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=True)
    auto_advance_pipeline = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    total_messages_scanned = Column(Integer, default=0)
    total_advancements = Column(Integer, default=0)
    # Jobify Gmail OAuth (read-only). Refresh token is Fernet-encrypted; never returned by the API.
    oauth_refresh_token_enc = Column(Text, nullable=True)
    sync_status = Column(String(30), nullable=True)  # connected | syncing | failed | disconnected
    last_error = Column(Text, nullable=True)
    next_scan_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = relationship("InboundRecruiterMessage", back_populates="mailbox", cascade="all, delete-orphan")


class InboundRecruiterMessage(Base):
    """Audit log of incoming recruiter messages classified and auto-advanced through the pipeline."""
    __tablename__ = "inbound_recruiter_messages"

    id = Column(Integer, primary_key=True)
    mailbox_id = Column(Integer, ForeignKey("mailbox_accounts.id"), nullable=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    
    sender_email = Column(String(255), nullable=False, index=True)
    sender_name = Column(String(255), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=False)
    snippet = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    
    # Classification & Auto-Advancement
    classified_intent = Column(String(50), nullable=False)  # INTERVIEW_INVITATION, ASSESSMENT, OFFER, REJECTION, FOLLOW_UP_REQUIRED
    confidence_score = Column(Float, default=0.90)
    previous_kanban_stage = Column(String(50), nullable=True)
    new_kanban_stage = Column(String(50), nullable=True)
    auto_advanced = Column(Boolean, default=True)
    
    message_id = Column(String(255), nullable=True)
    thread_id = Column(String(255), nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    mailbox = relationship("MailboxAccount", back_populates="messages")
    application = relationship("Application")
    job = relationship("Job")


class CandidateExperience(Base):
    """Work experience history item for public candidate portfolio."""
    __tablename__ = "candidate_experiences"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255), default="Remote")
    employment_type = Column(String(50), default="Full-time")  # Full-time, Contract, Founding
    start_date = Column(String(50), nullable=False)  # e.g. "Jan 2022"
    end_date = Column(String(50), default="Present")  # e.g. "Present" or "Nov 2024"
    is_current = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    technologies = Column(Text, default="[]")  # JSON array of tech chips e.g. ["React", "FastAPI", "TypeScript"]
    achievements = Column(Text, default="[]")  # JSON array of verified bullet accomplishments
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("CandidateProfile", back_populates="experiences")


class CandidateProject(Base):
    """Verified project showcase for public candidate portfolio."""
    __tablename__ = "candidate_projects"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    tagline = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    github_repo_url = Column(String(500), nullable=True)
    demo_url = Column(String(500), nullable=True)
    tech_stack = Column(Text, default="[]")  # JSON array of chips e.g. ["Python", "HNSW", "Vector DB"]
    stars_count = Column(Integer, default=0)
    is_verified = Column(Boolean, default=True)
    readme_content = Column(Text, nullable=True)  # Full markdown README content for RAG indexing
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("CandidateProfile", back_populates="projects")


class CandidateKnowledgeChunk(Base):
    """Chunked and embedded semantic knowledge from resumes, GitHub READMEs, and projects for RAG."""
    __tablename__ = "candidate_knowledge_chunks"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False)  # resume, github_readme, project, experience
    source_title = Column(String(255), nullable=False)  # e.g. "Resume: Senior Frontend Engineer", "GitHub: vector-indexer README"
    source_url = Column(String(500), nullable=True)
    embedding = Column(Text, nullable=False)  # JSON-serialized float array (128-dim)
    metadata_json = Column(Text, default="{}")  # JSON extra metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("CandidateProfile", back_populates="knowledge_chunks")


class PortfolioChatLog(Base):
    """Audit log of recruiter Q&A sessions with the candidate's interactive RAG chatbot."""
    __tablename__ = "portfolio_chat_logs"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    recruiter_question = Column(Text, nullable=False)
    ai_answer = Column(Text, nullable=False)
    citations_json = Column(Text, default="[]")  # JSON list of cited source chunks
    confidence_score = Column(Float, default=0.95)
    recruiter_ip_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("CandidateProfile", back_populates="chat_logs")


class TelegramConnector(Base):
    """Stores Telegram bot pairing, chat IDs, preferences, and alert statistics for candidate."""
    __tablename__ = "telegram_connectors"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_identifier = Column(String(255), default="default_user", index=True)
    
    # Telegram Auth & Connection
    telegram_chat_id = Column(String(100), nullable=True, index=True)
    telegram_username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    pairing_code = Column(String(64), unique=True, index=True, nullable=True)
    pairing_expires_at = Column(DateTime, nullable=True)
    is_connected = Column(Boolean, default=False)
    paired_at = Column(DateTime, nullable=True)
    
    # Push Alert Preferences
    min_match_score = Column(Float, default=90.0)  # High-match alert threshold (>= 90%)
    notify_high_match_jobs = Column(Boolean, default=True)
    notify_interview_requests = Column(Boolean, default=True)
    notify_status_changes = Column(Boolean, default=True)
    
    # Metrics
    alerts_sent_count = Column(Integer, default=0)
    actions_taken_count = Column(Integer, default=0)
    last_alert_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    alert_logs = relationship("TelegramPushAlertLog", back_populates="connector", cascade="all, delete-orphan")


class TelegramPushAlertLog(Base):
    """Audit log of dispatched push alerts and 1-click button actions."""
    __tablename__ = "telegram_push_alert_logs"

    id = Column(Integer, primary_key=True)
    connector_id = Column(Integer, ForeignKey("telegram_connectors.id"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # high_match_job, interview_request, assessment, offer
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    
    title = Column(String(255), nullable=False)
    message_text = Column(Text, nullable=False)
    telegram_message_id = Column(String(100), nullable=True)
    
    # 1-Click Action callbacks
    action_taken = Column(String(50), nullable=True)  # apply_now, draft_pitch, draft_reply, view_posting, none
    action_taken_at = Column(DateTime, nullable=True)
    action_result_summary = Column(Text, nullable=True)
    
    status = Column(String(50), default="sent")  # sent, delivered, failed, simulated
    created_at = Column(DateTime, default=datetime.utcnow)

    connector = relationship("TelegramConnector", back_populates="alert_logs")
    job = relationship("Job")
    application = relationship("Application")

