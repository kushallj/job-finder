import api from '../axios';
import type { MarketIntelligenceResponse, ProviderSyncResponse } from '../types';

export const providersApi = {
  sync: async (query: string, location?: string, maxAgeDays = 30, limit = 50): Promise<ProviderSyncResponse> => {
    const response = await api.post<ProviderSyncResponse>('/api/providers/sync', {
      query,
      location,
      max_age_days: maxAgeDays,
      limit,
    });
    return response.data;
  },
  market: async (): Promise<MarketIntelligenceResponse> => {
    const response = await api.get<MarketIntelligenceResponse>('/api/market-intelligence');
    return response.data;
  },
};
