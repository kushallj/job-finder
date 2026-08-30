import api from '../axios';

export interface SpamWordMatch {
  word: string;
  category: string;
  severity: 'warning' | 'critical';
  suggested_alternatives: string[];
  position: number;
}

export interface DeliverabilityDraftResponse {
  status: string;
  spam_score: number;
  deliverability_tier: string;
  is_safe: boolean;
  flesch_kincaid_grade: number;
  reading_time_seconds: number;
  word_count: number;
  char_count: number;
  link_count: number;
  uppercase_ratio: number;
  spam_matches: SpamWordMatch[];
  subject_score: number;
  subject_advice: string;
  deliverability_recommendations: string[];
  timestamp: string;
}

export interface DeliverabilityDraftRequest {
  subject: string;
  body: string;
}

export const deliverabilityApi = {
  analyzeDraft: (data: DeliverabilityDraftRequest) =>
    api.post<DeliverabilityDraftResponse>('/api/deliverability/analyze-draft', data),
};
