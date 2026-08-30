import api from '../axios';

export interface BooleanDorkResult {
  title: string;
  query: string;
  explanation: string;
  search_url: string;
  category: string;
}

export interface CopilotChatResponse {
  status: string;
  session_id: string;
  reply: string;
  dorks: BooleanDorkResult[];
  suggested_followups: string[];
  timestamp: string;
}

export interface CopilotDorksResponse {
  status: string;
  total_dorks: number;
  dorks: BooleanDorkResult[];
  timestamp: string;
}

export interface CopilotStartersResponse {
  status: string;
  starters: Array<{ title: string; prompt: string }>;
}

export const copilotApi = {
  chat: (data: { message: string; session_id?: string; target_company?: string; role_title?: string }) =>
    api.post<CopilotChatResponse>('/api/copilot/chat', data),
  getStarters: () =>
    api.get<CopilotStartersResponse>('/api/copilot/starters'),
  generateDorks: (data: { role_title: string; company?: string; intent?: string }) =>
    api.post<CopilotDorksResponse>('/api/copilot/generate-dorks', data),
};
