import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsApi } from '../api';
import type { QueryRequest } from '../api/types';

export const useJobs = () => {
  const queryClient = useQueryClient();

  // Get pending outreach jobs
  const pendingOutreachQuery = useQuery({
    queryKey: ['jobs', 'pending-outreach'],
    queryFn: () => jobsApi.getPendingOutreach(50, 50),
    staleTime: 30000, // 30 seconds
  });

  // Run query mutation
  const runQueryMutation = useMutation({
    mutationFn: (data: QueryRequest) => jobsApi.runQuery(data),
    onSuccess: () => {
      // Invalidate and refetch jobs
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  return {
    // Queries
    pendingOutreach: pendingOutreachQuery.data,
    isPendingOutreachLoading: pendingOutreachQuery.isLoading,
    pendingOutreachError: pendingOutreachQuery.error,
    
    // Mutations
    runQuery: runQueryMutation.mutate,
    runQueryAsync: runQueryMutation.mutateAsync,
    isRunningQuery: runQueryMutation.isPending,
    queryError: runQueryMutation.error,
    queryResult: runQueryMutation.data,
    
    // Refetch
    refetchPendingOutreach: pendingOutreachQuery.refetch,
  };
};

export const useJob = (jobId: number) => {
  const jobQuery = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.getJob(jobId),
    enabled: !!jobId,
  });

  return {
    job: jobQuery.data,
    isLoading: jobQuery.isLoading,
    error: jobQuery.error,
    refetch: jobQuery.refetch,
  };
};

