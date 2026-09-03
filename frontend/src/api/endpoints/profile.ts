import api from '../axios';

export interface CandidateProfileData {
  id?: number;
  full_name: string;
  email: string;
  phone?: string;
  location?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  years_of_experience: number;
  current_title?: string;
  bio_summary?: string;
  skills: string[];
  target_roles: string[];
  target_locations: string[];
  updated_at?: string;
}

export interface TargetCompanyData {
  id?: number;
  name: string;
  domain: string;
  tier: string;
  industry?: string;
  headquarters?: string;
  funding_stage?: string;
  signal_score: number;
  signal_notes?: string;
  is_active?: boolean;
}

export interface FunnelMetricsData {
  funnel_counts: {
    lead_discovered: number;
    packet_generated: number;
    review_approved: number;
    email_sent: number;
    reply_received: number;
    interview_scheduled: number;
    offer_received: number;
  };
  total_sent: number;
  replies: number;
  interviews: number;
  offers: number;
  reply_rate_pct: number;
  interview_rate_pct: number;
  recent_events: Array<{
    id: number;
    event_type: string;
    company: string;
    role_title?: string;
    contact_name?: string;
    channel: string;
    created_at: string;
  }>;
}

export const profileApi = {
  getCurrentProfile: async (): Promise<CandidateProfileData> => {
    const res = await api.get<{ status: string; profile: CandidateProfileData }>('/api/profile/current');
    return res.data.profile;
  },

  updateProfile: async (data: Partial<CandidateProfileData>): Promise<CandidateProfileData> => {
    const res = await api.post<{ status: string; profile: CandidateProfileData }>('/api/profile/current', data);
    return res.data.profile;
  },

  uploadResume: async (file: File): Promise<CandidateProfileData> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<{ status: string; profile: CandidateProfileData }>(
      '/api/profile/upload-resume',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return res.data.profile;
  },

  uploadResumeText: async (rawText: string): Promise<CandidateProfileData> => {
    const res = await api.post<{ status: string; profile: CandidateProfileData }>(
      '/api/profile/upload-resume',
      null,
      { params: { raw_text: rawText } }
    );
    return res.data.profile;
  },

  getTargetCompanies: async (): Promise<TargetCompanyData[]> => {
    const res = await api.get<{ status: string; total: number; companies: TargetCompanyData[] }>('/api/profile/target-companies');
    return res.data.companies;
  },

  addTargetCompany: async (company: Partial<TargetCompanyData>): Promise<TargetCompanyData> => {
    const res = await api.post<{ status: string; company: TargetCompanyData }>('/api/profile/target-companies', company);
    return res.data.company;
  },

  getFunnelMetrics: async (): Promise<FunnelMetricsData> => {
    const res = await api.get<FunnelMetricsData>('/api/funnel/metrics');
    return res.data;
  },

  logFunnelEvent: async (event: {
    event_type: string;
    company: string;
    role_title?: string;
    contact_name?: string;
    contact_email?: string;
    channel?: string;
    match_score?: number;
    notes?: string;
  }): Promise<{ status: string; event_id: number }> => {
    const res = await api.post('/api/funnel/event', event);
    return res.data;
  },
};
