import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useJobs, useJob } from '../useJobs';
import { jobsApi } from '../../api';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useJobs Hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches all jobs and handles pagination data correctly', async () => {
    const mockJobsResponse = {
      jobs: [
        { id: 1, title: 'Staff AI Engineer', company: 'Google', source: 'greenhouse', score: 95 },
        { id: 2, title: 'Senior Backend Lead', company: 'Stripe', source: 'lever', score: 88 },
      ],
      pagination: { total: 45, pages: 3, page: 1, limit: 20 },
      total: 45,
      page: 1,
      limit: 20,
    };

    vi.spyOn(jobsApi, 'getAllJobs').mockResolvedValue(mockJobsResponse);
    vi.spyOn(jobsApi, 'getPendingOutreach').mockResolvedValue([]);

    const { result } = renderHook(() => useJobs(1, 20), { wrapper: createWrapper() });

    expect(result.current.isAllJobsLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isAllJobsLoading).toBe(false);
    });

    expect(result.current.allJobs).toEqual(mockJobsResponse.jobs);
    expect(result.current.allJobsTotal).toBe(45);
    expect(result.current.allJobsPages).toBe(3);
  });

  it('executes runQuery mutation and updates state', async () => {
    vi.spyOn(jobsApi, 'getAllJobs').mockResolvedValue({ jobs: [], pagination: { total: 0, pages: 0, page: 1, limit: 10 }, total: 0, page: 1, limit: 10 });
    vi.spyOn(jobsApi, 'getPendingOutreach').mockResolvedValue([]);
    const mockMutationRes = { jobs_found: 12, jobs_scored: 10 };
    vi.spyOn(jobsApi, 'runQuery').mockResolvedValue(mockMutationRes);

    const { result } = renderHook(() => useJobs(), { wrapper: createWrapper() });

    let mutationData;
    await act(async () => {
      mutationData = await result.current.runQueryAsync({ query: 'python backend' });
    });

    expect(mutationData).toEqual(mockMutationRes);
  });

  it('useJob hook fetches a single job by id', async () => {
    const singleJob = { id: 42, title: 'Principal Architect', company: 'Meta' };
    vi.spyOn(jobsApi, 'getJob').mockResolvedValue(singleJob);

    const { result } = renderHook(() => useJob(42), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.job).toEqual(singleJob);
  });
});
