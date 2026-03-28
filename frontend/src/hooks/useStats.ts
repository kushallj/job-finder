import { useQuery } from '@tanstack/react-query';
import { statsApi } from '../api';

export const useStats = () => {
  const statsQuery = useQuery({
    queryKey: ['stats'],
    queryFn: async () => {
      try {
        const data = await statsApi.getStats();
        console.log('[Stats Hook] Stats fetched successfully:', data);
        return data;
      } catch (error) {
        console.error('[Stats Hook] Failed to fetch stats:', error);
        throw error;
      }
    },
    staleTime: 5000, // 5 seconds - faster updates
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 2, // Retry failed requests twice
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      try {
        const data = await statsApi.getHealth();
        console.log('[Health Hook] Health check completed:', data);
        return data;
      } catch (error) {
        console.error('[Health Hook] Failed to fetch health:', error);
        throw error;
      }
    },
    staleTime: 10000, // 10 seconds
    refetchInterval: 60000, // Refetch every 60 seconds
    retry: 1,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  return {
    stats: statsQuery.data?.stats || {
      total_jobs: 0,
      total_contacts: 0,
      total_applications: 0,
      total_outreach_attempts: 0,
      emails_sent: 0,
      follow_ups_sent: 0,
      success_rate: 0,
    },
    recentOutreach: statsQuery.data?.recent_outreach || [],
    isLoadingStats: statsQuery.isLoading,
    statsError: statsQuery.error,
    refetchStats: statsQuery.refetch,
    statsSource: statsQuery.data?.source || 'unknown',
    statsTimestamp: statsQuery.data?.timestamp,
    
    health: healthQuery.data,
    isLoadingHealth: healthQuery.isLoading,
    healthError: healthQuery.error,
    refetchHealth: healthQuery.refetch,
  };
};

