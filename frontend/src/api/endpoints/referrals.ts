import api from '../axios';
import type {
  ReferralSearchResponse,
  ReferralNoteGenerateRequest,
  ReferralNoteGenerateResponse,
  ReferralActionLogRequest,
  JobCaptureRequest,
  JobCaptureResponse,
} from '../types';

export const referralsApi = {
  getTargets: async (limit: number = 30) => {
    const res = await api.get<{ status: string; total_targets: number; targets: any[] }>(`/api/referrals/targets?limit=${limit}`);
    return res.data;
  },

  search: async (company: string, limit: number = 10) => {
    const res = await api.post<ReferralSearchResponse>('/api/referrals/search', { company, limit });
    return res.data;
  },

  sync: async (profiles: any[]) => {
    const res = await api.post<{ status: string; synced_count: number; new_contacts_count: number }>('/api/referrals/sync', { profiles });
    return res.data;
  },

  generateNote: async (payload: ReferralNoteGenerateRequest) => {
    const res = await api.post<ReferralNoteGenerateResponse>('/api/referrals/generate-note', payload);
    return res.data;
  },

  logAction: async (payload: ReferralActionLogRequest) => {
    const res = await api.post<{ status: string; outreach_id: number; message: string }>('/api/referrals/log-action', payload);
    return res.data;
  },

  captureJob: async (payload: JobCaptureRequest) => {
    const res = await api.post<JobCaptureResponse>('/api/jobs/capture', payload);
    return res.data;
  },
};
