// API Response Types - Mirror backend models

export interface Job {
  id: number;
  job_id: string;
  title: string;
  company: string | null;
  location: string | null;
  description: string | null;
  url: string | null;
  source: string | null;
  posted_date: string | null;
  fetched_at: string;
  match_score?: number | null;
  application_status?: string | null;
  provider_id?: string | null;
  company_website?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  has_remote?: boolean | null;
  work_mode?: string | null;
  experience_level?: string | null;
  tags?: string[];
  provider_sources?: string[];
}

export type LifecycleStatus = 'saved' | 'ready' | 'applied' | 'interview' | 'offer' | 'negotiation' | 'accepted' | 'rejected';

export interface Application {
  id: number;
  job_id: number;
  match_score: number | null;
  skills_matched: string | null;
  skills_missing: string | null;
  resume_version: string | null;
  cover_letter: string | null;
  status: LifecycleStatus | 'pending';
  applied_at: string | null;
  created_at: string;
  updated_at: string;
  ats_detected?: string | null;
  customized_resume_path?: string | null;
  cover_letter_path?: string | null;
  submission_notes?: string | null;
  proof_url?: string | null;
  proof_notes?: string | null;
  job?: Job;
}

export interface Contact {
  id: number;
  name: string;
  title: string | null;
  email: string | null;
  linkedin_url: string | null;
  company: string;
  department: string | null;
  confidence_score: number;
  source: 'linkedin' | 'website' | 'generated' | null;
  found_at: string;
}

export interface OutreachRecord {
  id: number;
  contact_id: number;
  job_id: number;
  subject: string | null;
  body: string | null;
  template_type: 'hr_outreach' | 'engineering_manager' | 'follow_up' | null;
  status: 'sent' | 'bounced' | 'replied' | 'no_response' | 'failed' | 'followed_up';
  sent_at: string | null;
  replied_at: string | null;
  email_sent: boolean;
  contact_email: string | null;
  contact_name: string | null;
  follow_up_scheduled: string | null;
  follow_up_sent: boolean;
  follow_up_count: number;
  last_follow_up_at: string | null;
  contact?: Contact;
  job?: Job;
}

export interface Resume {
  id: number;
  original_content: string;
  skills: string | null;
  experience_years: number | null;
  created_at: string;
  is_active: boolean;
}

// API Request Types
export interface QueryRequest {
  query: string;
  min_score?: number;
}

export interface QueryResponse {
  status: 'success' | 'error';
  trace_id: string;
  query: string;
  jobs_fetched: number;
  resume_used: string;
  min_score_requested: number;
  min_score_applied: boolean;
}

export interface ContactSearchRequest {
  company_name: string;
  job_title?: string;
}

export interface ContactSearchResponse {
  contacts: Contact[];
  total: number;
}

export interface OutreachRequest {
  job_id: number;
  contact_email: string;
  contact_name: string;
  send_immediately?: boolean;
}

export interface OutreachResponse {
  status: 'success' | 'failed' | 'queued';
  trace_id: string;
  job_id: number;
  contact_email: string;
  email_sent: boolean;
  outreach_id: number;
}

export interface FollowUpRequest {
  outreach_id: number;
  follow_up_number?: number;
}

export interface FollowUpResponse {
  status: 'success' | 'failed';
  trace_id: string;
  outreach_id: number;
  follow_up_number: number;
  email_sent: boolean;
}

export interface PendingOutreachJob {
  id: number;
  title: string;
  company: string;
  location: string;
  url: string;
  source: string;
  posted_date: string | null;
  fetched_at: string;
}

export interface PendingOutreachResponse {
  status: 'success' | 'error';
  total_jobs: number;
  jobs: PendingOutreachJob[];
}

export interface OutreachStats {
  total_jobs: number;
  total_contacts: number;
  total_applications: number;
  total_outreach_attempts: number;
  emails_sent: number;
  follow_ups_sent: number;
  success_rate: number;
}

export interface RecentOutreach {
  id: number;
  contact_email: string;
  status: string;
  sent_at: string | null;
}

export interface StatsResponse {
  status: 'success' | 'error';
  source: 'live' | 'db_fallback';
  stats: OutreachStats;
  recent_outreach?: RecentOutreach[];
  timestamp?: string;
}

export interface HealthStatus {
  status: 'healthy';
  timestamp: string;
  subsystems: {
    job_processor: boolean;
    outreach_proc: boolean;
    email_outreach: boolean;
    contact_finder: boolean;
  };
}

export interface RootResponse {
  status: string;
  service: string;
  version: string;
}

export interface JobsResponse {
  status: 'success' | 'error';
  jobs: Job[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export interface OpportunitySignal {
  label: string;
  value: string;
  strength: 'strong' | 'medium' | 'weak' | 'info';
  detail: string;
}

export interface OpportunityPerson {
  id: number;
  name: string;
  title: string | null;
  email: string | null;
  linkedin_url: string | null;
  confidence_score: number;
  relationship_hint: string;
}

export interface OpportunityResume {
  has_master_resume: boolean;
  master_resume_label: string | null;
  has_tailored_resume: boolean;
  tailored_resume_label: string | null;
  cover_letter_preview: string | null;
  missing_keywords: string[];
}

export interface OpportunityOutreach {
  total: number;
  sent: number;
  replied: number;
  pending: number;
  latest_status: string | null;
  recommended_message: string;
}

export interface OpportunityNextAction {
  key: string;
  label: string;
  reason: string;
  priority: 'high' | 'medium' | 'low';
  route?: string | null;
  external?: boolean;
  requires_confirmation?: boolean;
}

export interface OpportunityBrief {
  status: string;
  job: Job;
  fit_score: number;
  fit_label: string;
  fit_reasons: string[];
  company_signals: OpportunitySignal[];
  people: OpportunityPerson[];
  resume: OpportunityResume;
  outreach: OpportunityOutreach;
  next_action: OpportunityNextAction;
  application_id?: number | null;
  application_status?: LifecycleStatus | string | null;
  confirmation_number?: string | null;
  proof_note?: string | null;
  proof_url?: string | null;
  proof_logged_at?: string | null;
  generated_at?: string;
}

export interface ActionQueueItem {
  job_id: number;
  application_id: number | null;
  title: string;
  company: string | null;
  fit_score: number | null;
  stage: LifecycleStatus | string;
  status: LifecycleStatus | string | null;
  action: OpportunityNextAction;
  url: string | null;
  updated_at: string | null;
}

export interface ActionQueueResponse {
  status: string;
  actions: ActionQueueItem[];
  total: number;
  timestamp?: string;
}

export interface ProviderSyncSource {
  provider: string;
  fetched: number;
  inserted: number;
  updated: number;
  failed?: boolean;
  error?: string | null;
}

export interface ProviderSyncResponse {
  status: string;
  total_fetched: number;
  total_inserted: number;
  total_updated: number;
  sources: ProviderSyncSource[];
}

export interface MarketIntelligenceResponse {
  status: string;
  provider: string;
  stale?: boolean;
  error?: string | null;
  data?: Record<string, any>;
}

