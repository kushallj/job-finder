import api from '../axios';

export interface FillerWordStats {
  total_fillers: number;
  filler_percentage: number;
  fillers_by_word: Record<string, number>;
}

export interface CadenceStats {
  wpm: number;
  duration_seconds: number;
  cadence_rating: string;
}

export interface StarEvaluation {
  situation_score: number;
  task_score: number;
  action_score: number;
  result_score: number;
  overall_star_score: number;
}

export interface VoiceFeedbackResponse {
  status: string;
  speech_delivery_score: number;
  filler_stats: FillerWordStats;
  cadence_stats: CadenceStats;
  star_eval: StarEvaluation;
  delivery_tips: string[];
  timestamp: string;
}

export interface VoiceFeedbackRequest {
  transcript: string;
  duration_seconds: number;
  target_focus?: string;
}

export const voiceInterviewerApi = {
  analyzeVoiceResponse: (data: VoiceFeedbackRequest) =>
    api.post<VoiceFeedbackResponse>('/api/interview/voice-feedback', data),
};
