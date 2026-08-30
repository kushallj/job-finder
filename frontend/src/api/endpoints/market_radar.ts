import api from '../axios';

export interface RemoteArbitrageRole {
  title: string;
  company: string;
  country: string;
  currency: string;
  base_comp_range: string;
  inr_equivalent_range: string;
  ppp_multiplier: number;
  tz_overlap_hours: string;
  tax_advantage: string;
  source_url: string;
  skills_required: string[];
}

export interface GCCHubInsight {
  hub_city: string;
  active_openings: number;
  top_employers: string[];
  median_senior_ctc: string;
  growth_yoy: string;
}

export interface MarketRadarResponse {
  status: string;
  usd_to_inr_rate: number;
  eur_to_inr_rate: number;
  remote_global_roles: RemoteArbitrageRole[];
  top_gcc_hubs: GCCHubInsight[];
  timestamp: string;
}

export const marketRadarApi = {
  getOpportunities: () => api.get<MarketRadarResponse>('/api/market-radar/opportunities'),
};
