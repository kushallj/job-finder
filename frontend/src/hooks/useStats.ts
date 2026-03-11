import { useQuery } from '@tanstack/react-query';
import { statsApi } from '../api';

export const useStats = () => {
  const statsQuery = useQuery({
    queryKey: ['stats'],
    queryFn: () => statsApi.getStats(),
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
  });

  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: () => statsApi.getHealth(),
    staleTime: 10000, // 10 seconds
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  return {
    stats: statsQuery.data?.stats,
    recentOutreach: statsQuery.data?.recent_outreach,
    isLoadingStats: statsQuery.isLoading,
    statsError: statsQuery.error,
    refetchStats: statsQuery.refetch,
    
    health: healthQuery.data,
    isLoadingHealth: healthQuery.isLoading,
    healthError: healthQuery.error,
  };
};

