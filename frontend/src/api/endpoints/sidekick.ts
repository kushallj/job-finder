import api from '../axios';

export interface SidekickStatus {
  status: string;
  invisibility_supported: boolean;
  total_trie_indexed_keys: number;
  rag_indexed_documents: number;
  local_llm_configured: boolean;
}

export interface SidekickQueryResponse {
  source: 'trie_exact_match' | 'hybrid_rag_retrieval' | 'generative_llm_stream';
  tier: number;
  title: string;
  category: string;
  bullets: string[];
  latency_microseconds?: number;
  latency_milliseconds?: number;
  latency_display: string;
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  category: string;
  bullets: string[];
}

export const sidekickApi = {
  getStatus: async (): Promise<SidekickStatus> => {
    const res = await api.get<SidekickStatus>('/api/sidekick/status');
    return res.data;
  },

  query: async (query: string, candidateContext?: string): Promise<SidekickQueryResponse> => {
    const res = await api.post<SidekickQueryResponse>('/api/sidekick/query', {
      query,
      candidate_context: candidateContext,
    });
    return res.data;
  },

  getBank: async (): Promise<{ total_documents: number; documents: KnowledgeDocument[] }> => {
    const res = await api.get<{ total_documents: number; documents: KnowledgeDocument[] }>('/api/sidekick/bank');
    return res.data;
  },

  setWindowInvisible: async (windowTitle?: string): Promise<{ status: string; mechanism: string; is_invisible: boolean }> => {
    const res = await api.post<{ status: string; mechanism: string; is_invisible: boolean }>('/api/sidekick/window/set-invisible', {
      window_title: windowTitle,
    });
    return res.data;
  },

  addCustomQuestion: async (payload: {
    id: string;
    title: string;
    keywords: string[];
    category: string;
    bullets: string[];
  }): Promise<{ status: string; total_indexed_keys: number }> => {
    const res = await api.post('/api/sidekick/bank/add', payload);
    return res.data;
  },
};
