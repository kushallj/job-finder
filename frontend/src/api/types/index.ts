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
  source: 'linkedin' | 'website' | 'generated' | 'linkedin_referral' | string | null;
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
  message?: string;
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

export interface JobQueryParams {
  page?: number;
  limit?: number;
  search?: string;
  region?: string;
  experience_level?: string;
  years_of_experience?: number;
  date_posted?: string;
  tech_stack?: string;
  source?: string;
  has_remote?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
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

export interface JobCaptureRequest {
  title: string;
  company?: string;
  location?: string;
  description?: string;
  url: string;
  source?: string;
  score?: boolean;
}

export interface JobCaptureResponse {
  status: string;
  job: Job;
  already_existed: boolean;
  match_score?: number | null;
  matched_skills?: string[] | null;
  missing_skills?: string[] | null;
  score_error?: string | null;
}

export interface ReferralProfile {
  full_name: string;
  first_name?: string;
  last_name?: string;
  headline?: string;
  company?: string;
  title?: string;
  location?: string;
  linkedin_url?: string;
  mutual_connections?: number;
  source?: string;
}

export interface ReferralSearchResponse {
  status: string;
  company: string;
  source: string;
  count: number;
  profiles: ReferralProfile[];
}

export interface ReferralNoteGenerateRequest {
  full_name: string;
  company: string;
  first_name?: string;
  title?: string;
  headline?: string;
  job_title?: string;
  job_link?: string;
  short_bio?: string;
  highlight?: string;
  reason?: string;
  sender_name?: string;
  max_length?: number;
}

export interface ReferralNoteGenerateResponse {
  status: string;
  connection_note: string;
  full_letter: string;
  char_count: number;
  is_under_limit: boolean;
}

export interface ReferralActionLogRequest {
  contact_name: string;
  company: string;
  action_type: 'connection_sent' | 'message_sent' | 'replied';
  linkedin_url?: string;
  contact_email?: string;
  message_body?: string;
  job_id?: number;
}

export interface XProfile {
  x_user_id: string;
  username: string;
  name: string;
  description?: string | null;
  company?: string | null;
  title?: string | null;
  location?: string | null;
  followers_count: number;
  following_count?: number;
  tweet_count?: number;
  verified: boolean;
  profile_image_url?: string | null;
  x_url?: string;
  source?: string;
}

export interface XTweet {
  tweet_id: string;
  author_id?: string | null;
  author_username?: string | null;
  author_name?: string | null;
  text: string;
  created_at?: string;
  like_count: number;
  retweet_count: number;
  reply_count?: number;
  is_hiring_tweet?: boolean;
  tweet_url?: string;
}

export interface XSearchResponse {
  status: string;
  company: string;
  role?: string | null;
  source: string;
  count: number;
  profiles: XProfile[];
}

export interface XTweetSearchResponse {
  status: string;
  company: string;
  role?: string | null;
  count: number;
  tweets: XTweet[];
}

export interface XMessageGenerateRequest {
  action_type: 'dm' | 'reply' | 'quote';
  username: string;
  company: string;
  name?: string;
  title?: string;
  role_title?: string;
  job_link?: string;
  candidate_bio?: string;
  highlight?: string;
  target_topic?: string;
  sender_name?: string;
  tweet_id?: string;
  tweet_text?: string;
  max_length?: number;
}

export interface XMessageGenerateResponse {
  status: string;
  action_type: string;
  message: string;
  char_count: number;
  is_under_limit: boolean;
  intent_url?: string | null;
}

export interface XEngageRequest {
  action_type: 'follow' | 'like' | 'repost' | 'reply' | 'dm' | 'quote';
  target_username: string;
  company: string;
  target_user_id?: string;
  tweet_id?: string;
  message_text?: string;
  job_id?: number;
}

export interface XEngageResponse {
  status: string;
  outreach_id: number;
  action_type: string;
  target: string;
  intent_url?: string | null;
  mode: string;
  daily_usage?: Record<string, any>;
}

export interface XAuthStatusResponse {
  connected: boolean;
  username?: string | null;
  expires_at?: string | null;
  scopes?: string[];
}


// ── Agents (src/agents/, 15-agent target-company system) ──────────────────

export interface CompanySignal { type: string; detail: string; source: string; date: string; }
export interface CompBenchmark { min?: number; median?: number; max?: number; source?: string; as_of?: string; }
export interface TargetCompany {
  name: string; aka?: string[]; domain: string; industry: string; hq: string; tier: number;
  hiring_probability: 'High' | 'Medium-High' | 'Medium' | 'Low-Medium' | 'Low';
  ats_hint: string; signals: CompanySignal[]; comp_benchmark_inr_lpa: CompBenchmark; why_target_now: string;
}
export interface CompaniesResponse { companies: TargetCompany[]; sector_context: Record<string, { note: string }>; }

export interface AgentResult<T = Record<string, unknown>> {
  agent: string; ok: boolean; summary: string; data: T; warnings: string[]; duration_ms: number;
}

export interface DailyPipelineResult {
  signals: Record<string, unknown>;
  roles_found: number;
  scored: Record<string, unknown>;
  queue: Array<{ company: string; title: string; url: string; priority_score: number; recommendation: string }>;
  drafts: Array<{
    company: string; title: string; url: string; priority_score: number; headline: string;
    top_contact: Record<string, unknown>; subject: string; body: string;
  }>;
  report_path: string;
}

export interface BooleanQuery { id: string; category: string; query: string; purpose: string; }
export interface LeadsResult {
  executed: boolean;
  leads: Array<{ query_id: string; category: string; title: string; url: string; snippet: string }>;
  rendered_queries: BooleanQuery[];
}
export interface BooleanLead {
  id: number; query_id: string; category: string; title: string; url: string; snippet: string;
  status: 'new' | 'reviewed' | 'converted'; discovered_at: number;
}

export interface NetworkerResult {
  challenge: {
    identified_challenge: string; evidence: string[]; matched_proof_points: string[]; solution_sketch: string;
  };
  content_drafts: { platform_drafts: { linkedin: string; x: string }; reminder: string };
}

export interface PitchResult { win_markdown: string; problem: string; solution_points: string[]; narrative: string; }

export interface InterviewQuestion {
  id: string; text: string; type: 'company_specific' | 'technical' | 'behavioral'; focus_area: string;
}
export interface InterviewScore {
  star_scores: { situation: number; task: number; action: number; result: number };
  specificity_score: number; overall: number; feedback: string; used_llm: boolean;
}

export interface NegotiateBenchmark { band: CompBenchmark; suggested_ask_lpa: number | null; position: string; }
export interface NegotiateCounter {
  position_in_band: string; counter_ask_lpa: number; script: string; confidence_note: string;
}

export interface OutreachDraftResult {
  tailor: AgentResult<{ headline: string; ordered_bullets: string[]; used_llm: boolean }>;
  contacts: AgentResult<{ top_contact: Record<string, unknown> | null; outreach_order: unknown[] }>;
  outreach: AgentResult<{ subject: string; body: string; hooks_used: string[]; used_full_stack: boolean }>;
}




