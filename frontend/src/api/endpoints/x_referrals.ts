import api from '../axios';
import type {
  XSearchResponse,
  XTweetSearchResponse,
  XMessageGenerateRequest,
  XMessageGenerateResponse,
  XEngageRequest,
  XEngageResponse,
  XAuthStatusResponse,
} from '../types';

export const xReferralsApi = {
  getAuthUrl: async () => {
    const res = await api.get<{ status: string; authorization_url: string; state: string }>('/api/x/auth/url');
    return res.data;
  },

  callback: async (code: string, state: string, codeVerifier?: string) => {
    const res = await api.post<{ status: string; connected: boolean; message: string }>('/api/x/auth/callback', {
      code,
      state,
      code_verifier: codeVerifier,
    });
    return res.data;
  },

  getStatus: async () => {
    const res = await api.get<XAuthStatusResponse>('/api/x/auth/status');
    return res.data;
  },

  getTargets: async (limit: number = 30) => {
    const res = await api.get<{ status: string; total_targets: number; targets: any[] }>(`/api/x/targets?limit=${limit}`);
    return res.data;
  },

  search: async (company: string, role?: string, limit: number = 10) => {
    const res = await api.post<XSearchResponse>('/api/x/search', { company, role, limit });
    return res.data;
  },

  searchTweets: async (company: string, role?: string, limit: number = 10) => {
    const res = await api.post<XTweetSearchResponse>('/api/x/search-tweets', { company, role, limit });
    return res.data;
  },

  generateMessage: async (payload: XMessageGenerateRequest) => {
    const res = await api.post<XMessageGenerateResponse>('/api/x/generate-message', payload);
    return res.data;
  },

  engage: async (payload: XEngageRequest) => {
    const res = await api.post<XEngageResponse>('/api/x/engage', payload);
    return res.data;
  },

  sync: async (profiles: any[]) => {
    const res = await api.post<{ status: string; synced_count: number; new_contacts_count: number }>('/api/x/sync', { profiles });
    return res.data;
  },
};
