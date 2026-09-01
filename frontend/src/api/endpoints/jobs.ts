import api from '../axios';
import type {
  QueryRequest,
  QueryResponse,
  PendingOutreachResponse,
  Job,
  JobsResponse,
  OpportunityBrief,
  JobQueryParams,
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
   * Get all jobs with multi-facet ORM filtering & pagination
   */
  getAllJobs: async (params: JobQueryParams | number = 1, limit: number = 50): Promise<JobsResponse> => {
    const queryParams = typeof params === 'number' ? { page: params, limit } : params;
    const response = await api.get<JobsResponse>('/api/jobs', {
      params: queryParams,
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
   * Get opportunity brief for decision-ready overview
   */
  getOpportunityBrief: async (jobId: number): Promise<OpportunityBrief> => {
    const response = await api.get<OpportunityBrief>(`/api/opportunities/${jobId}/brief`);
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

