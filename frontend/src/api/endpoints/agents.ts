import api from '../axios';
import type {
  CompaniesResponse,
  DailyPipelineResult,
  LeadsResult,
  BooleanQuery,
  BooleanLead,
  NetworkerResult,
  PitchResult,
  InterviewQuestion,
  InterviewScore,
  NegotiateBenchmark,
  NegotiateCounter,
  OutreachDraftResult,
  AgentResult,
} from '../types';

export const agentsApi = {
  getCompanies: async (): Promise<CompaniesResponse> => {
    const response = await api.get<CompaniesResponse>('/api/agents/companies');
    return response.data;
  },

  runDaily: async (tiers?: number[]): Promise<DailyPipelineResult> => {
    const response = await api.post<DailyPipelineResult>('/api/agents/daily', { tiers });
    return response.data;
  },

  runLeads: async (categories?: string[]): Promise<LeadsResult> => {
    const response = await api.post<LeadsResult>('/api/agents/leads', { categories });
    return response.data;
  },

  getQueryBank: async (): Promise<{ queries: BooleanQuery[] }> => {
    const response = await api.get('/api/agents/leads/bank');
    return response.data;
  },

  listLeads: async (params?: { status?: string; category?: string }): Promise<{ leads: BooleanLead[] }> => {
    const response = await api.get('/api/agents/leads/list', { params });
    return response.data;
  },

  updateLeadStatus: async (leadId: number, status: BooleanLead['status']): Promise<void> => {
    await api.put(`/api/agents/leads/${leadId}/status`, { status });
  },

  runInterviewPrep: async (
    company: string, role_title = ''
  ): Promise<AgentResult<{ dossier_markdown: string; likely_focus_areas: string[] }>> => {
    const response = await api.post('/api/agents/interview-prep', { company, role_title });
    return response.data;
  },

  runNetworker: async (company: string, job_description = ''): Promise<NetworkerResult> => {
    const response = await api.post<NetworkerResult>('/api/agents/networker', { company, job_description });
    return response.data;
  },

  runPitch: async (company: string, job_description = ''): Promise<AgentResult<PitchResult>> => {
    const response = await api.post('/api/agents/pitch', { company, job_description });
    return response.data;
  },

  getInterviewQuestions: async (
    company: string, role_title = '', job_description = '', num_questions = 5
  ): Promise<AgentResult<{ questions: InterviewQuestion[] }>> => {
    const response = await api.post('/api/agents/interview/questions', {
      company, role_title, job_description, num_questions,
    });
    return response.data;
  },

  scoreInterviewAnswer: async (
    question: string, answer: string, focus_area = ''
  ): Promise<AgentResult<InterviewScore>> => {
    const response = await api.post('/api/agents/interview/score', { question, answer, focus_area });
    return response.data;
  },

  getNegotiationBenchmark: async (company: string): Promise<AgentResult<NegotiateBenchmark>> => {
    const response = await api.get('/api/agents/negotiate/benchmark', { params: { company } });
    return response.data;
  },

  getNegotiationCounter: async (
    company: string, offer_amount_lpa: number
  ): Promise<AgentResult<NegotiateCounter>> => {
    const response = await api.post('/api/agents/negotiate/counter', { company, offer_amount_lpa });
    return response.data;
  },

  runOutreachDraft: async (
    company: string, role_title = '', job_description = ''
  ): Promise<OutreachDraftResult> => {
    const response = await api.post<OutreachDraftResult>('/api/agents/outreach-draft', {
      company, role_title, job_description,
    });
    return response.data;
  },

  runWeeklyLearning: async (): Promise<AgentResult> => {
    const response = await api.post('/api/agents/weekly-learning');
    return response.data;
  },
};
