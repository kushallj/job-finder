/**
 * frontend/src/api/endpoints/tsenta.ts — Tsenta Auto-Apply Agent API Client.
 */
import api from '../axios';

export interface TsentaATSItem {
  code: string;
  name: string;
  category: string;
  color_token: string;
  supports_direct_api: boolean;
}

export interface TsentaQuotaInfo {
  id: number;
  daily_used: number;
  daily_limit: number;
  daily_remaining: number;
  total_submitted: number;
  lifetime_free_remaining: number;
  active_tier: string;
  last_reset_at: string | null;
}

export interface TsentaConfigInfo {
  id: number;
  api_key_configured: boolean;
  api_url: string;
  mode: 'review_required' | 'full_auto';
  min_fit_score: number;
  auto_apply_enabled: boolean;
  notification_webhook: string | null;
  updated_at: string | null;
}

export interface TsentaStatusResponse {
  status: string;
  client: {
    connected: boolean;
    engine_status: string;
    agent_version: string;
    supported_ats_count: number;
    free_tier_credits: number;
    subscription_tier: string;
    supported_platforms: string[];
  };
  quota: TsentaQuotaInfo;
  config: TsentaConfigInfo;
  supported_ats: TsentaATSItem[];
}

export interface TsentaQAItem {
  question: string;
  answer: string;
}

export interface TsentaSubmissionData {
  id: number;
  job_id: number;
  ats_type: string;
  status: 'queued' | 'review_ready' | 'submitting' | 'submitted' | 'failed';
  receipt_id: string | null;
  proof_url: string | null;
  match_score: number;
  company_name: string | null;
  job_title: string | null;
  answers: TsentaQAItem[];
  submission_packet: Record<string, any>;
  tailored_resume_text: string | null;
  cover_letter_text: string | null;
  error_detail: string | null;
  execution_time_ms: number;
  created_at: string;
  submitted_at: string | null;
}

export interface TsentaAutoApplyResponse {
  status: 'review_ready' | 'submitted' | 'already_submitted';
  message: string;
  ats_detected?: string;
  ats_code?: string;
  receipt_id?: string;
  proof_url?: string;
  submission: TsentaSubmissionData;
}

export const tsentaApi = {
  getStatus: async (): Promise<TsentaStatusResponse> => {
    const res = await api.get<TsentaStatusResponse>('/api/tsenta/status');
    return res.data;
  },

  autoApply: async (
    jobId: number,
    modeOverride?: 'review_required' | 'full_auto',
    sampleQuestions?: string[]
  ): Promise<TsentaAutoApplyResponse> => {
    const res = await api.post<TsentaAutoApplyResponse>('/api/tsenta/auto-apply', {
      job_id: jobId,
      mode_override: modeOverride,
      sample_questions: sampleQuestions,
    });
    return res.data;
  },

  approveAndSubmit: async (
    submissionId: number,
    customCoverLetter?: string,
    customAnswers?: TsentaQAItem[]
  ): Promise<TsentaAutoApplyResponse> => {
    const res = await api.post<TsentaAutoApplyResponse>('/api/tsenta/review-gate/approve', {
      submission_id: submissionId,
      custom_cover_letter: customCoverLetter,
      custom_answers: customAnswers,
    });
    return res.data;
  },

  batchApply: async (
    jobIds?: number[],
    minScore: number = 80,
    limit: number = 10
  ): Promise<{ total_processed: number; results: any[]; quota: TsentaQuotaInfo }> => {
    const res = await api.post('/api/tsenta/batch-apply', {
      job_ids: jobIds,
      min_score: minScore,
      limit,
    });
    return res.data;
  },

  getSubmissions: async (status?: string, limit: number = 50): Promise<{ total: number; submissions: TsentaSubmissionData[] }> => {
    const res = await api.get('/api/tsenta/submissions', {
      params: { status, limit },
    });
    return res.data;
  },

  getReceipt: async (receiptId: string): Promise<TsentaSubmissionData> => {
    const res = await api.get(`/api/tsenta/receipt/${receiptId}`);
    return res.data;
  },

  updateConfig: async (config: Partial<TsentaConfigInfo & { api_key?: string }>): Promise<{ status: string; config: TsentaConfigInfo }> => {
    const res = await api.post('/api/tsenta/config', config);
    return res.data;
  },
};
