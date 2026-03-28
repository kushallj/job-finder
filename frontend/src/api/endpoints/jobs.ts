import api from '../axios';
import type {
  QueryRequest,
  QueryResponse,
  PendingOutreachResponse,
  Job,
} from '../types';

export const jobsApi = {
  /**
   * Run a full job search pipeline:
   * Fetch jobs from APIs → Store in DB → AI processing with resume matching
   */
  runQuery: async (data: QueryRequest): Promise<QueryResponse> => {
    const response = await api.post<QueryResponse>('/run-query', data);
    return response.data;
  },

  /**
   * Get all jobs with pagination, sorted by recently fetched
   */
  getAllJobs: async (page: number = 1, limit: number = 50): Promise<PendingOutreachResponse> => {
    const response = await api.get<PendingOutreachResponse>('/api/jobs', {
      params: { page, limit },
    });
    return response.data;
  },

  /**
   * Get jobs that are pending outreach (matched with resume but not yet reached out)
   */
  getPendingOutreach: async (minScore: number = 50, limit: number = 50): Promise<PendingOutreachResponse> => {
    const response = await api.get<PendingOutreachResponse>('/api/jobs/pending-outreach', {
      params: { min_score: minScore, limit },
    });
    return response.data;
  },

  /**
   * Get a specific job by ID
   */
  getJob: async (jobId: number): Promise<Job> => {
    const response = await api.get<Job>(`/api/jobs/${jobId}`);
    return response.data;
  },

  /**
   * Search jobs (if endpoint exists)
   */
  searchJobs: async (query: string): Promise<{ jobs: Job[] }> => {
    const response = await api.post<{ jobs: Job[] }>('/api/jobs/search', { query });
    return response.data;
  },
};

