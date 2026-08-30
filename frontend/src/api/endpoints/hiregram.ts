import api from '../axios';

export type InterviewerPersona = 'recruiter_sara' | 'architect_alex' | 'bar_raiser_marcus' | 'startup_cto_elena';

export interface TurnDialogue {
  turn_index: number;
  question: string;
  interviewer_persona: string;
  candidate_answer: string;
  duration_seconds: number;
  wpm: number;
  filler_words_detected: string[];
  star_breakdown: Record<string, number>;
  turn_score: number;
  strengths: string[];
  areas_for_improvement: string[];
  gold_standard_ideal_answer: string;
  completed: boolean;
}

export interface InterviewDiagnosticScorecard {
  session_id: string;
  company: string;
  role_title: string;
  persona: InterviewerPersona;
  overall_score: number;
  readiness_verdict: string;
  technical_depth_score: number;
  star_structure_score: number;
  delivery_cadence_score: number;
  leadership_impact_score: number;
  turns: TurnDialogue[];
  key_strengths: string[];
  high_priority_improvements: string[];
  practice_drills_recommended: string[];
  created_at: string;
}

export interface HiregramStartSessionResponse {
  status: string;
  session_id: string;
  company: string;
  role_title: string;
  persona: string;
  total_questions: number;
  current_turn: TurnDialogue;
}

export interface HiregramSubmitTurnResponse {
  status: string;
  session_id: string;
  evaluated_turn: TurnDialogue;
  next_turn: TurnDialogue | null;
  is_finished: boolean;
  current_question_number: number;
  total_questions: number;
}

export interface HiregramFinalizeResponse {
  status: string;
  scorecard: InterviewDiagnosticScorecard;
}

export const hiregramApi = {
  startSession: (data: {
    company: string;
    role_title: string;
    persona?: InterviewerPersona;
    job_description?: string;
    candidate_resume_summary?: string;
    total_questions_target?: number;
  }) => api.post<HiregramStartSessionResponse>('/api/hiregram/start-session', data),

  submitTurn: (data: {
    session_id: string;
    answer_text: string;
    duration_seconds?: number;
  }) => api.post<HiregramSubmitTurnResponse>('/api/hiregram/submit-turn', data),

  finalizeSession: (sessionId: string) =>
    api.post<HiregramFinalizeResponse>(`/api/hiregram/finalize-session?session_id=${encodeURIComponent(sessionId)}`),

  getSessionScorecard: (sessionId: string) =>
    api.get<HiregramFinalizeResponse>(`/api/hiregram/sessions/${encodeURIComponent(sessionId)}`),
};
