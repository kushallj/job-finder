/**
 * frontend/src/api/endpoints/nextraise.ts — NextRaise Auto-Apply & High-Volume Dispatch API Client.
 * Configured for account canaby007@gmail.com with 200–300 daily applications target.
 */
import api from '../axios';

export interface NextRaiseAccountConfig {
  account_email: string;
  oauth_connected: boolean;
  has_token: boolean;
  mode: string;
  daily_target: number;
  min_fit_score: number;
  auto_batch_enabled: boolean;
  batch_concurrency: number;
  enabled_ats: string[];
  api_url: string;
  updated_at: string | null;
}

export interface NextRaiseQuotaInfo {
  daily_used: number;
  daily_limit: number;
  daily_remaining: number;
  daily_progress_percent: number;
  total_submitted: number;
  total_failed: number;
  active_tier: string;
  last_reset_date: string;
}

export interface NextRaiseSubmissionItem {
  id: number;
  job_id: number;
  ats_type: string;
  status: 'applied' | 'queued' | 'processing' | 'review_ready' | 'failed';
  receipt_id: string | null;
  proof_url: string | null;
  account_email: string;
  company_name: string | null;
  job_title: string | null;
  match_score: number;
  answers_count: number;
  tailored_resume_path: string | null;
  has_cover_letter: boolean;
  error_detail: string | null;
  execution_time_ms: number;
  created_at: string | null;
  submitted_at: string | null;
  submission_packet?: Record<string, any>;
  answers?: Array<{ question: string; answer: string }>;
}

export interface NextRaiseStatusResponse {
  account: NextRaiseAccountConfig;
  quota: NextRaiseQuotaInfo;
  recent_submissions: NextRaiseSubmissionItem[];
}

export interface NextRaiseBatchApplyResponse {
  status: 'completed' | 'quota_reached' | 'no_jobs_found';
  account_email: string;
  jobs_targeted?: number;
  successful_submissions?: number;
  failed_submissions?: number;
  daily_progress: string;
  daily_percent?: number;
  recent_receipts?: string[];
  message?: string;
  daily_used?: number;
  daily_limit?: number;
}

export interface NextRaiseSingleApplyResponse {
  success: boolean;
  job_id?: number;
  job_title?: string;
  company?: string;
  ats_type?: string;
  receipt_id?: string;
  proof_url?: string;
  daily_progress?: string;
  already_applied?: boolean;
  message?: string;
  error?: string;
}

export const nextraiseApi = {
  getStatus: async (): Promise<NextRaiseStatusResponse> => {
    const res = await api.get<NextRaiseStatusResponse>('/api/nextraise/status');
    return res.data;
  },

  batchApply: async (
    targetCount: number = 250,
    minFitScore: number = 50.0
  ): Promise<NextRaiseBatchApplyResponse> => {
    const res = await api.post<NextRaiseBatchApplyResponse>('/api/nextraise/batch-apply', {
      target_count: targetCount,
      min_fit_score: minFitScore,
    });
    return res.data;
  },

  applySingle: async (jobId: number): Promise<NextRaiseSingleApplyResponse> => {
    const res = await api.post<NextRaiseSingleApplyResponse>(`/api/nextraise/apply/${jobId}`);
    return res.data;
  },

  getSubmissions: async (
    limit: number = 50,
    status?: string
  ): Promise<{ total_count: number; submissions: NextRaiseSubmissionItem[] }> => {
    const res = await api.get('/api/nextraise/submissions', {
      params: { limit, status },
    });
    return res.data;
  },

  getConfig: async (): Promise<NextRaiseAccountConfig> => {
    const res = await api.get<NextRaiseAccountConfig>('/api/nextraise/config');
    return res.data;
  },

  updateConfig: async (
    config: Partial<NextRaiseAccountConfig>
  ): Promise<{ status: string; config: NextRaiseAccountConfig }> => {
    const res = await api.post('/api/nextraise/config', config);
    return res.data;
  },

  authorizeOAuth: async (data: {
    account_email: string;
    oauth_access_token: string;
    oauth_refresh_token?: string;
    session_token?: string;
  }): Promise<{ status: string; account_email: string; message: string }> => {
    const res = await api.post('/api/nextraise/oauth/authorize', data);
    return res.data;
  },
};
