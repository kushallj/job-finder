import api from '../axios';

export interface InterviewerDossier {
  status: string;
  interviewer: {
    name: string;
    company: string;
    role: string;
    github_handle?: string;
  };
  cognitive_archetype: string;
  architectural_biases: string[];
  green_lights_to_highlight: string[];
  red_lines_to_avoid: string[];
  personalized_conversation_opener: string;
  recommended_questions_to_ask_them: string[];
}

export interface CompensationOfferInput {
  id: string;
  company_name: string;
  role_title?: string;
  currency: string;
  base_salary: number;
  annual_bonus?: number;
  joining_bonus?: number;
  equity_total_grant?: number;
  equity_type: string;
  company_stage: string;
  deadline_date?: string;
}

export interface AnalyzedOffer {
  id: string;
  company_name: string;
  role_title: string;
  currency: string;
  base_salary: number;
  annual_bonus: number;
  joining_bonus: number;
  equity_annual_nominal: number;
  equity_annual_risk_adjusted: number;
  equity_risk_multiplier: number;
  year1_nominal_tc: number;
  year1_risk_adjusted_npv: number;
  four_year_avg_npv: number;
  deadline_date?: string;
}

export interface ArbitrageSimulationResponse {
  status: string;
  total_offers_analyzed: number;
  ranked_offers: AnalyzedOffer[];
  optimal_target: string;
  leverage_insights: string[];
}

export interface CounterScriptResponse {
  status: string;
  target_company: string;
  target_bump_percent: string;
  rescission_risk_score: string;
  email_script: string;
  verbal_phone_script: string;
}

export interface DefuseDeadlineResponse {
  status: string;
  company_name: string;
  defuser_email_script: string;
  tactical_rule: string;
}

export const interviewerProfilerApi = {
  profile: async (payload: {
    name: string;
    company: string;
    role?: string;
    github_handle?: string;
    linkedin_summary?: string;
  }): Promise<InterviewerDossier> => {
    const res = await api.post<InterviewerDossier>('/api/interviewer/profile', payload);
    return res.data;
  },
};

export const offerArbitrageApi = {
  simulateArbitrage: async (offers: CompensationOfferInput[]): Promise<ArbitrageSimulationResponse> => {
    const res = await api.post<ArbitrageSimulationResponse>('/api/negotiation/arbitrage', { offers });
    return res.data;
  },

  generateCounterScript: async (payload: {
    target_company: string;
    competing_company?: string;
    current_base: number;
    target_base: number;
    currency?: string;
    contact_role?: string;
  }): Promise<CounterScriptResponse> => {
    const res = await api.post<CounterScriptResponse>('/api/negotiation/counter-script', payload);
    return res.data;
  },

  defuseDeadline: async (payload: {
    company_name: string;
    current_deadline: string;
    extension_days?: number;
  }): Promise<DefuseDeadlineResponse> => {
    const res = await api.post<DefuseDeadlineResponse>('/api/negotiation/defuse-deadline', payload);
    return res.data;
  },
};
