import api from '../axios';

export interface YearlyCompBreakdown {
  year: number;
  base_salary: number;
  cash_bonus: number;
  equity_vested: number;
  total_pre_tax: number;
  take_home_post_tax: number;
}

export interface CompSimulationResponse {
  status: string;
  company: string;
  role_title: string;
  four_year_total_pre_tax: number;
  four_year_total_post_tax: number;
  average_annual_comp: number;
  yearly_breakdowns: YearlyCompBreakdown[];
  negotiation_counter_target: number;
  negotiation_advice: string;
  timestamp: string;
}

export interface OfferPackageInput {
  company: string;
  role_title: string;
  base_salary: number;
  signon_bonus?: number;
  target_bonus_pct?: number;
  equity_grant_usd?: number;
  vesting_schedule?: string;
  startup_exit_multiple?: number;
  estimated_tax_rate?: number;
}

export const compSimulatorApi = {
  simulate: (data: OfferPackageInput) =>
    api.post<CompSimulationResponse>('/api/comp/simulate', data),
  compare: (offers: OfferPackageInput[]) =>
    api.post<CompSimulationResponse[]>('/api/comp/compare', { offers }),
};
