import api from '../axios';
import type { StatsResponse, HealthStatus, RootResponse } from '../types';

export const statsApi = {
  /**
   * Get outreach statistics
   */
  getStats: async (): Promise<StatsResponse> => {
    const response = await api.get<StatsResponse>('/api/stats');
    return response.data;
  },

  /**
   * Get detailed health status of all subsystems
   */
  getHealth: async (): Promise<HealthStatus> => {
    const response = await api.get<HealthStatus>('/api/health');
    return response.data;
  },

  /**
   * Basic root health check
   */
  getRoot: async (): Promise<RootResponse> => {
    const response = await api.get<RootResponse>('/');
    return response.data;
  },
};

