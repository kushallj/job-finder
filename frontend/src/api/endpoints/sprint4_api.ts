import api from '../axios';

export interface FrontierPlatform {
  id: string;
  name: string;
  hourly_rate_usd: number;
  hourly_rate_range: string;
  primary_focus: string;
  payout_frequency: string;
  onboarding_difficulty: string;
  direct_apply_url: string;
  tags: string[];
}

export interface RubricItem {
  criterion: string;
  passed: boolean;
  weight: number;
}

export interface FrontierBenchmarkResponse {
  status: string;
  benchmark_score: number;
  tier_status: string;
  badge_color: string;
  projected_hourly_rate_usd: number;
  weekly_hours: number;
  monthly_hours: number;
  projections: {
    monthly_usd: number;
    monthly_inr: number;
    annual_inr_lakhs: number;
  };
  rubric_breakdown: RubricItem[];
  top_recommended_platforms: FrontierPlatform[];
}

export interface CodeEvalChallenge {
  challenge_id: string;
  prompt: string;
  buggy_code: string;
  rubric_key_points: string[];
}

export interface ExecutiveMemoResponse {
  status: string;
  candidate_name: string;
  company_name: string;
  role_title: string;
  target_compensation_lpa: number;
  cost_analysis: {
    total_hiring_investment_inr_lakhs: number;
    total_usd_equivalent: number;
    breakdown: {
      agency_recruiter_commission: string;
      engineering_team_interview_hours: string;
      ats_sourcing_infrastructure: string;
      cost_of_empty_seat_per_month: string;
    };
  };
  executive_memo_markdown: string;
  followup_email: string;
  strategic_leverage_summary: string;
}

export const sprint4Api = {
  getPlatforms: async (): Promise<{ status: string; platforms: FrontierPlatform[] }> => {
    const res = await api.get<{ status: string; platforms: FrontierPlatform[] }>('/api/frontier-ai/platforms');
    return res.data;
  },

  getSampleChallenge: async (): Promise<{ status: string; challenge: CodeEvalChallenge }> => {
    const res = await api.get<{ status: string; challenge: CodeEvalChallenge }>('/api/frontier-ai/challenge');
    return res.data;
  },

  evaluateBenchmark: async (payload: {
    critique_text: string;
    weekly_hours_available?: number;
    usd_to_inr_rate?: number;
  }): Promise<FrontierBenchmarkResponse> => {
    const res = await api.post<FrontierBenchmarkResponse>('/api/frontier-ai/benchmark', payload);
    return res.data;
  },

  synthesizeExecutiveMemo: async (payload: {
    candidate_name?: string;
    company_name: string;
    role_title?: string;
    interview_stage?: string;
    key_technical_topics?: string[];
    p99_impact_metric?: string;
    competing_offer_anchor?: string;
    target_compensation_lpa?: number;
  }): Promise<ExecutiveMemoResponse> => {
    const res = await api.post<ExecutiveMemoResponse>('/api/executive-memo/synthesize', payload);
    return res.data;
  },
};
