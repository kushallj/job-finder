import api from '../axios';
import type {
  StartupDiscoveryRequest,
  StartupDiscoveryResponse,
} from '../types';

export const startupsApi = {
  /**
   * Discover recently funded startups
   */
  discover: async (data: StartupDiscoveryRequest): Promise<StartupDiscoveryResponse> => {
    const response = await api.post<StartupDiscoveryResponse>('/api/startups/discover', data);
    return response.data;
  },
};
