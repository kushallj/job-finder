/**
 * frontend/src/api/endpoints/workday.ts — Workday Autonomous Profile & Auto-Apply API Client.
 */
import api from '../axios';

export interface WorkdayCandidateProfileData {
  id?: number;
  account_email: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  preferred_name?: string;
  phone: string;
  phone_device_type?: string;
  country: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  state_province: string;
  postal_code: string;
  linkedin_url: string;
  github_url: string;
  portfolio_url?: string;
  twitter_url?: string | null;
  headline: string;
  years_of_experience: number;
  current_company: string;
  current_title: string;
  skills: string[];
  work_history: Array<{
    company: string;
    title: string;
    location: string;
    start_date: string;
    end_date: string;
    is_current: boolean;
    description: string;
  }>;
  education: Array<{
    school: string;
    degree: string;
    field_of_study: string;
    start_date: string;
    end_date: string;
    gpa?: string;
  }>;
  legally_authorized: boolean;
  requires_sponsorship: boolean;
  notice_period_days: number;
  target_salary_min: number;
  target_salary_max: number;
  salary_currency?: string;
  willing_to_relocate: boolean;
  gender: string;
  hispanic_latino?: string;
  race_ethnicity: string;
  veteran_status: string;
  disability_status: string;
  updated_at?: string;
}

export interface WorkdayAccountItem {
  id: number;
  tenant_domain: string;
  career_site_name: string;
  company_name: string;
  account_email: string;
  status: string;
  has_session: boolean;
  last_login_at: string | null;
  created_at: string | null;
}

export interface WorkdaySubmissionItem {
  id: number;
  job_id: number;
  tenant_domain: string;
  company_name: string;
  job_title: string;
  account_email: string;
  status: 'submitted' | 'failed' | 'account_created' | 'resume_tailored';
  receipt_id: string | null;
  proof_url: string | null;
  confirmation_number: string | null;
  match_score: number;
  tailored_resume_path: string | null;
  has_tailored_resume: boolean;
  answers_count: number;
  answers?: Array<{ question: string; answer: string }>;
  error_detail: string | null;
  execution_time_ms: number;
  created_at: string | null;
  submitted_at: string | null;
}

export interface WorkdayConfigData {
  id: number;
  account_email: string;
  auto_apply_enabled: boolean;
  mode: string;
  min_fit_score: number;
  daily_limit: number;
  daily_used: number;
  daily_remaining: number;
  daily_percent: number;
  total_submitted: number;
  total_failed: number;
  tailor_resumes: boolean;
  generate_cover_letters: boolean;
  batch_concurrency: number;
  last_reset_date: string;
  updated_at: string;
}

export interface WorkdayStatusResponse {
  config: WorkdayConfigData;
  profile: WorkdayCandidateProfileData;
  total_accounts_registered: number;
  accounts: WorkdayAccountItem[];
  recent_submissions: WorkdaySubmissionItem[];
}

export interface WorkdaySingleApplyResponse {
  success: boolean;
  job_id?: number;
  job_title?: string;
  company?: string;
  tenant_domain?: string;
  receipt_id?: string;
  proof_url?: string;
  confirmation_number?: string;
  ats_match_score?: number;
  tailored_resume_path?: string;
  answers_count?: number;
  daily_progress?: string;
  already_applied?: boolean;
  message?: string;
  error?: string;
}

export interface WorkdayBatchApplyResponse {
  status: 'completed' | 'quota_reached' | 'no_jobs_found';
  account_email: string;
  jobs_targeted?: number;
  successful_submissions?: number;
  failed_submissions?: number;
  daily_progress?: string;
  recent_receipts?: string[];
  message?: string;
  daily_used?: number;
}

export const workdayApi = {
  getStatus: async (): Promise<WorkdayStatusResponse> => {
    const res = await api.get<WorkdayStatusResponse>('/api/workday/status');
    return res.data;
  },

  getProfile: async (): Promise<WorkdayCandidateProfileData> => {
    const res = await api.get<WorkdayCandidateProfileData>('/api/workday/profile');
    return res.data;
  },

  updateProfile: async (
    profile: Partial<WorkdayCandidateProfileData>
  ): Promise<{ status: string; profile: WorkdayCandidateProfileData; message: string }> => {
    const res = await api.post('/api/workday/profile', profile);
    return res.data;
  },

  applySingle: async (jobId: number): Promise<WorkdaySingleApplyResponse> => {
    const res = await api.post<WorkdaySingleApplyResponse>(`/api/workday/apply/${jobId}`);
    return res.data;
  },

  batchApply: async (
    targetCount: number = 25,
    minFitScore: number = 60.0
  ): Promise<WorkdayBatchApplyResponse> => {
    const res = await api.post<WorkdayBatchApplyResponse>('/api/workday/batch-apply', {
      target_count: targetCount,
      min_fit_score: minFitScore,
    });
    return res.data;
  },

  previewTailor: async (jobId: number): Promise<{
    job_id: number;
    job_title: string;
    company: string;
    ats_match_score: number;
    matched_keywords: string[];
    tailored_resume_path: string;
    tailored_resume_text: string;
    cover_letter_text: string;
  }> => {
    const res = await api.post('/api/workday/preview-tailor', { job_id: jobId });
    return res.data;
  },

  getAccounts: async (limit: number = 50): Promise<{ total_count: number; accounts: WorkdayAccountItem[] }> => {
    const res = await api.get('/api/workday/accounts', { params: { limit } });
    return res.data;
  },

  getSubmissions: async (limit: number = 50, status?: string): Promise<{ total_count: number; submissions: WorkdaySubmissionItem[] }> => {
    const res = await api.get('/api/workday/submissions', { params: { limit, status } });
    return res.data;
  },

  updateConfig: async (
    config: Partial<WorkdayConfigData>
  ): Promise<{ status: string; config: WorkdayConfigData }> => {
    const res = await api.post('/api/workday/config', config);
    return res.data;
  },

  getAnswers: async (params?: { query?: string; category?: string; limit?: number }): Promise<{ total_count: number; answers: AnswerItem[] }> => {
    const res = await api.get('/api/workday/answers', { params });
    return res.data;
  },

  saveAnswer: async (data: { question: string; answer: string; category?: string; source?: string }): Promise<{ status: string; id: number; answer: string; message: string }> => {
    const res = await api.post('/api/workday/save-answer', data);
    return res.data;
  },

  saveAnswersBatch: async (answers: Array<{ question: string; answer: string; category?: string; source?: string }>): Promise<{ status: string; saved_count: number; answers: AnswerItem[] }> => {
    const res = await api.post('/api/workday/save-answers-batch', { answers });
    return res.data;
  },

  deleteAnswer: async (answerId: number): Promise<{ status: string; id: number; message: string }> => {
    const res = await api.delete(`/api/workday/answers/${answerId}`);
    return res.data;
  },
};

export interface AnswerItem {
  id: number;
  question_text: string;
  normalized_question?: string;
  answer_text: string;
  source: string;
  category?: string;
  context?: string;
  approved: boolean;
  times_used: number;
  created_at?: string | null;
  last_used_at?: string | null;
}

