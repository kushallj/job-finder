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
}

export interface Application {
  id: number;
  job_id: number;
  match_score: number | null;
  skills_matched: string | null;
  skills_missing: string | null;
  resume_version: string | null;
  cover_letter: string | null;
  status: 'pending' | 'applied' | 'rejected' | 'interview';
  applied_at: string | null;
  created_at: string;
  updated_at: string;
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

