import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsApi } from '../api';
import type { QueryRequest } from '../api/types';

export const useJobs = (page: number = 1, limit: number = 50) => {
  const queryClient = useQueryClient();

  // Get all jobs with pagination and fast auto-refresh
  const allJobsQuery = useQuery({
    queryKey: ['jobs', 'all', page, limit],
    queryFn: () => jobsApi.getAllJobs(page, limit),
    staleTime: 5000, // 5 seconds
    refetchInterval: 10000, // Auto-refetch every 10 seconds to catch newly crawled jobs
  });

  // Get pending outreach jobs
  const pendingOutreachQuery = useQuery({
    queryKey: ['jobs', 'pending-outreach'],
    queryFn: () => jobsApi.getPendingOutreach(50, 50),
    staleTime: 5000,
    refetchInterval: 15000,
  });


  // Run query mutation
  const runQueryMutation = useMutation({
    mutationFn: (data: QueryRequest) => jobsApi.runQuery(data),
    onSuccess: () => {
      // Invalidate queries so they refetch on next render
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
  });

  return {
    // All jobs query
    allJobs: allJobsQuery.data?.jobs || [],
    allJobsTotal: allJobsQuery.data?.pagination?.total || 0,
    allJobsPages: allJobsQuery.data?.pagination?.pages || 0,
    isAllJobsLoading: allJobsQuery.isLoading,
    allJobsError: allJobsQuery.error,
    refetchAllJobs: allJobsQuery.refetch,
    
    // Pending outreach query
    pendingOutreach: pendingOutreachQuery.data,
    isPendingOutreachLoading: pendingOutreachQuery.isLoading,
    pendingOutreachError: pendingOutreachQuery.error,
    refetchPendingOutreach: pendingOutreachQuery.refetch,
    
    // Mutations
    runQuery: runQueryMutation.mutate,
    runQueryAsync: runQueryMutation.mutateAsync,
    isRunningQuery: runQueryMutation.isPending,
    queryError: runQueryMutation.error,
    queryResult: runQueryMutation.data,
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

