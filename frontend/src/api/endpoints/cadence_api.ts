import api from '../axios';

export interface CadenceAnalysisResult {
  status: string;
  word_count: number;
  duration_seconds: number;
  wpm: number;
  cadence_status: string;
  cadence_color: string;
  pacing_advice: string;
  total_fillers_detected: number;
  filler_breakdown: Record<string, number>;
  clarity_score: number;
  is_ramble_warning: boolean;
  ramble_check_in_cue: string | null;
}

export interface StarAdherence {
  score: number;
  situation_detected: boolean;
  task_detected: boolean;
  action_detected: boolean;
  result_metrics_detected: boolean;
}

export interface VoiceScorecardResult {
  status: string;
  session_id: string;
  overall_executive_score: number;
  executive_rating: string;
  wpm_summary: {
    average_wpm: number;
    status: string;
  };
  clarity_summary: {
    clarity_score: number;
    total_fillers: number;
    filler_breakdown: Record<string, number>;
  };
  star_framework_adherence: StarAdherence;
}

export const cadenceCoachApi = {
  analyzeCadence: async (payload: {
    transcript: string;
    duration_seconds: number;
    is_continuous_monologue?: boolean;
  }): Promise<CadenceAnalysisResult> => {
    const res = await api.post<CadenceAnalysisResult>('/api/sidekick/cadence/analyze', payload);
    return res.data;
  },

  generateScorecard: async (payload: {
    session_id: string;
    total_duration_seconds: number;
    transcripts: string[];
  }): Promise<VoiceScorecardResult> => {
    const res = await api.post<VoiceScorecardResult>('/api/sidekick/cadence/scorecard', payload);
    return res.data;
  },
};
