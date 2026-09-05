import api from '../axios';

// ── Feature 7: Reverse Headhunter Types ──────────────────────────────────────
export interface HeadhunterBountyListing {
  bounty_id: string;
  company_name: string;
  role_title: string;
  location: string;
  bounty_amount_usd: number;
  bounty_amount_inr_lakhs: number;
  hiring_priority: string;
  escrow_status: string;
  tech_stack: string[];
  minimum_experience_years: number;
  hiring_manager_team: string;
}

export interface PitchPackResponse {
  status: string;
  candidate_name: string;
  target_company: string;
  role_title: string;
  referrer_name: string;
  bounty_financials: {
    total_bounty_usd: number;
    total_bounty_inr_lakhs: number;
    milestone_1_payout_usd: number;
    milestone_1_condition: string;
    milestone_2_payout_usd: number;
    milestone_2_condition: string;
    escrow_guarantee: string;
  };
  hiring_manager_referral_email: string;
  peer_outreach_script: string;
  strategic_advantage: string;
}

// ── Feature 8: Geo-Arbitrage Types ───────────────────────────────────────────
export interface GeoMarket {
  market_id: string;
  region: string;
  city: string;
  currency: string;
  currency_symbol: string;
  average_gross_salary_range: string;
  english_adoption_score: number;
  visa_type: string;
  pr_timeline_months: number;
  key_employers: string[];
  tax_bracket_effective_percent: number;
  col_index_vs_bangalore: number;
  fx_to_inr: number;
  visa_sponsorship_status: string;
  relocation_perks: string;
}

export interface PppCalculationResponse {
  status: string;
  market: GeoMarket;
  financials: {
    gross_salary_local: number;
    currency: string;
    effective_tax_percent: number;
    net_salary_local_annual: number;
    net_salary_local_monthly: number;
    gross_inr_lakhs: number;
    net_inr_lakhs: number;
    net_usd_annual: number;
    estimated_monthly_expenses_inr: number;
    net_monthly_savings_inr: number;
    annual_savings_inr_lakhs: number;
    india_baseline_annual_savings_lakhs: number;
    savings_expansion_multiplier: number;
  };
  visa_dossier: {
    visa_name: string;
    permanent_residence_timeline: string;
    relocation_perks: string;
    employer_sponsorship: string;
  };
  takeaway_summary: string;
}

// ── Feature 9: Web3 Bounty Types ────────────────────────────────────────────
export interface Web3BountyListing {
  bounty_id: string;
  ecosystem: string;
  title: string;
  reward_usd: number;
  token: string;
  difficulty: string;
  skills_required: string[];
  deadline_days_left: number;
  organization: string;
  escrow_verified: boolean;
  submission_url: string;
}

export interface Web3ProposalResponse {
  status: string;
  bounty_id: string;
  bounty_title: string;
  organization: string;
  reward_usd: number;
  reward_inr_lakhs: number;
  proposal_markdown: string;
  skills_covered: string[];
  action_summary: string;
}

// ── API Caller ───────────────────────────────────────────────────────────────
export const sprint5Api = {
  // Feature 7
  getHeadhunterListings: async (params?: { company?: string; min_bounty?: number }): Promise<{ status: string; listings: HeadhunterBountyListing[] }> => {
    const res = await api.get<{ status: string; listings: HeadhunterBountyListing[] }>('/api/bounties/headhunter/listings', { params });
    return res.data;
  },

  generatePitchPack: async (payload: {
    candidate_name?: string;
    target_company: string;
    role_title?: string;
    referrer_name?: string;
    key_strengths?: string[];
    years_experience?: number;
    github_portfolio?: string;
  }): Promise<PitchPackResponse> => {
    const res = await api.post<PitchPackResponse>('/api/bounties/headhunter/pitch-pack', payload);
    return res.data;
  },

  // Feature 8
  getGeoMarkets: async (region?: string): Promise<{ status: string; markets: GeoMarket[] }> => {
    const res = await api.get<{ status: string; markets: GeoMarket[] }>('/api/geo-arbitrage/markets', { params: { region } });
    return res.data;
  },

  calculatePpp: async (payload: {
    gross_annual_salary: number;
    market_id: string;
    current_inr_ctc_lpa?: number;
  }): Promise<PppCalculationResponse> => {
    const res = await api.post<PppCalculationResponse>('/api/geo-arbitrage/ppp-calc', payload);
    return res.data;
  },

  // Feature 9
  getWeb3Bounties: async (params?: { ecosystem?: string; min_reward?: number }): Promise<{ status: string; bounties: Web3BountyListing[] }> => {
    const res = await api.get<{ status: string; bounties: Web3BountyListing[] }>('/api/web3-bounties/listings', { params });
    return res.data;
  },

  synthesizeWeb3Proposal: async (payload: {
    bounty_id: string;
    candidate_name?: string;
    proposed_architecture?: string;
    timeline_days?: number;
    github_profile?: string;
  }): Promise<Web3ProposalResponse> => {
    const res = await api.post<Web3ProposalResponse>('/api/web3-bounties/proposal', payload);
    return res.data;
  },
};
