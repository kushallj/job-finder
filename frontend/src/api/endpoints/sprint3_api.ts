import api from '../axios';

export interface PoWTemplate {
  id: string;
  title: string;
  category: string;
  companies: string[];
  description: string;
}

export interface PoWDeliverables {
  status: string;
  company_name: string;
  project_title: string;
  architecture_overview: string;
  mermaid_diagram: string;
  app_code_filename: string;
  app_code: string;
  test_code_filename: string;
  test_code: string;
  dockerfile: string;
  github_actions_ci: string;
  pr_description_markdown: string;
  benchmark_metrics: {
    p99_latency_reduction_percent: number;
    concurrency_rps_tested: number;
    state_inconsistencies: number;
    memory_bounded_big_o: string;
  };
}

export interface EscalationTier {
  tier_level: number;
  tier_name: string;
  recommended_trigger_window: string;
  subject: string;
  body: string;
  strategic_intent: string;
}

export interface CompanySlaBenchmark {
  company_name: string;
  avg_feedback_turnaround_hours: number;
  ghosting_rate_percent: number;
  is_verified_fast_track: boolean;
  tier_rating: string;
  recruiter_responsiveness: string;
}

export interface AntiGhostingEscalationResponse {
  status: string;
  company_name: string;
  interview_stage: string;
  days_elapsed: number;
  company_sla_benchmark: CompanySlaBenchmark;
  risk_metrics: {
    ghosting_risk_percent: number;
    sla_status: string;
    sla_color: string;
    hours_elapsed: number;
    standard_benchmark_hours: number;
  };
  escalation_tiers: EscalationTier[];
}

export const sprint3Api = {
  getTemplates: async (): Promise<{ status: string; templates: PoWTemplate[] }> => {
    const res = await api.get<{ status: string; templates: PoWTemplate[] }>('/api/pow/templates');
    return res.data;
  },

  fabricatePoW: async (payload: {
    company_name: string;
    role_title?: string;
    archetype_id?: string;
    custom_problem_statement?: string;
    target_tech_stack?: string;
  }): Promise<PoWDeliverables> => {
    const res = await api.post<PoWDeliverables>('/api/pow/fabricate', payload);
    return res.data;
  },

  getSlaIndex: async (): Promise<{ status: string; companies: CompanySlaBenchmark[] }> => {
    const res = await api.get<{ status: string; companies: CompanySlaBenchmark[] }>('/api/anti-ghosting/sla-index');
    return res.data;
  },

  synthesizeEscalation: async (payload: {
    company_name: string;
    interview_stage: string;
    days_elapsed: number;
    recruiter_name?: string;
    candidate_leverage?: string;
    competing_company?: string;
  }): Promise<AntiGhostingEscalationResponse> => {
    const res = await api.post<AntiGhostingEscalationResponse>('/api/anti-ghosting/escalate', payload);
    return res.data;
  },
};
