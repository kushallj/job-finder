import api from '../axios';

export interface VCFirm {
  id: number;
  name: string;
  slug: string;
  website?: string;
  portfolio_url?: string;
  country_focus: string;
  region: string;
  companies_count: number;
  founders_count: number;
  last_synced_at?: string;
}

export interface CompanyFounder {
  id: number;
  company_id: number;
  company_name?: string;
  company_domain?: string;
  full_name: string;
  title?: string;
  email?: string;
  email_confidence: number;
  linkedin_url?: string;
  twitter_handle?: string;
  bio?: string;
  source: string;
  last_verified_at?: string;
}

export interface PortfolioCompany {
  id: number;
  vc_firm_id: number;
  vc_firm_name?: string;
  name: string;
  slug: string;
  domain?: string;
  website?: string;
  description?: string;
  batch_or_year?: string;
  funding_stage?: string;
  industry_tags: string[];
  careers_url?: string;
  last_scraped_at?: string;
  founders: CompanyFounder[];
}

export interface VCSyncResponse {
  vc_slug: string;
  vc_name: string;
  companies_synced: number;
  companies_updated: number;
  founders_discovered: number;
  status: string;
  message: string;
}

export interface BatchVCSyncResponse {
  total_firms_processed: number;
  total_companies_synced: number;
  total_founders_discovered: number;
  results: VCSyncResponse[];
}

export const vcApi = {
  getFirms: async (region?: string): Promise<VCFirm[]> => {
    const response = await api.get<VCFirm[]>('/api/vc/firms', {
      params: region && region !== 'All' ? { region } : {},
    });
    return response.data;
  },

  getRegions: async (): Promise<{ total_firms: number; regions: Record<string, number> }> => {
    const response = await api.get('/api/vc/regions');
    return response.data;
  },

  seed100: async (): Promise<{ status: string; firms_seeded: number }> => {
    const response = await api.post('/api/vc/seed-100');
    return response.data;
  },

  syncFirm: async (slug: string, maxCompanies: number = 20, enrichContacts: boolean = true): Promise<VCSyncResponse> => {
    const response = await api.post<VCSyncResponse>(`/api/vc/firms/${slug}/sync`, {
      max_companies: maxCompanies,
      enrich_contacts: enrichContacts,
    });
    return response.data;
  },

  batchSync: async (region?: string, maxCompanies: number = 10): Promise<BatchVCSyncResponse> => {
    const response = await api.post<BatchVCSyncResponse>('/api/vc/batch/sync', {
      region: region && region !== 'All' ? region : undefined,
      max_companies_per_firm: maxCompanies,
      enrich_contacts: true,
    });
    return response.data;
  },

  getCompanies: async (vcSlug?: string, limit: number = 50): Promise<PortfolioCompany[]> => {
    const response = await api.get<PortfolioCompany[]>('/api/vc/companies', {
      params: { vc_slug: vcSlug, limit },
    });
    return response.data;
  },

  getExportUrl: (vcSlug?: string): string => {
    const base = '/api/vc/export?format=csv';
    return vcSlug ? `${base}&vc_slug=${encodeURIComponent(vcSlug)}` : base;
  },

  getContinuousStatus: async (): Promise<ContinuousRunnerStatus> => {
    const response = await api.get<ContinuousRunnerStatus>('/api/vc/continuous/status');
    return response.data;
  },

  startContinuous: async (batchSize: number = 50, maxBatches?: number, intervalSeconds: number = 2.0): Promise<{ status: string }> => {
    const response = await api.post('/api/vc/continuous/start', null, {
      params: { batch_size: batchSize, max_batches: maxBatches, interval_seconds: intervalSeconds },
    });
    return response.data;
  },

  stopContinuous: async (): Promise<{ status: string }> => {
    const response = await api.post('/api/vc/continuous/stop');
    return response.data;
  },

  runBatchNow: async (): Promise<{ batch_number: number; founders_added: number; companies_added: number }> => {
    const response = await api.post('/api/vc/continuous/run-batch-now');
    return response.data;
  },
};

export interface ContinuousRunnerStatus {
  is_running: boolean;
  current_batch: number;
  total_harvested_in_session: number;
  last_run_timestamp?: string;
  current_firm_name?: string;
  total_founders_in_db: number;
  founders_with_verified_email: number;
  total_companies_in_db: number;
  total_firms_in_db: number;
  recent_logs: string[];
}

