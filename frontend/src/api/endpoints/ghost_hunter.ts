import api from '../axios';

export interface GhostSignal {
  name: string;
  description: string;
  score_impact: number;
  severity: 'positive' | 'warning' | 'critical';
}

export interface GhostAnalysisResponse {
  status: string;
  ghost_score: number;
  urgency_label: string;
  is_ghost_risk: boolean;
  confidence_score: number;
  estimated_age_days?: number | null;
  signals: GhostSignal[];
  action_recommendation: string;
  timestamp: string;
}

export interface GhostAnalysisRequest {
  title: string;
  company: string;
  description: string;
  posted_date?: string;
  has_decision_maker?: boolean;
}

export const ghostHunterApi = {
  analyze: (data: GhostAnalysisRequest) =>
    api.post<GhostAnalysisResponse>('/api/ghost-hunter/analyze', data),
  getJobGhostScore: (jobId: number | string) =>
    api.get<GhostAnalysisResponse>(`/api/jobs/${jobId}/ghost-score`),
};

