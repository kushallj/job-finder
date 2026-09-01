import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import {
  useCompanies,
  useDailyPipeline,
  useLeads,
  useLeadsList,
  useNetworker,
  usePitch,
  useInterviewQuestions,
  useScoreAnswer,
  useNegotiationBenchmark,
  useNegotiationCounter,
} from '../useAgents';
import { agentsApi } from '../../api';

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

describe('useAgents Hook Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('useCompanies fetches target company list', async () => {
    const mockCompanies = { companies: [{ name: 'Stripe', tier: 1, domain: 'stripe.com' }] };
    vi.spyOn(agentsApi, 'getCompanies').mockResolvedValue(mockCompanies);

    const { result } = renderHook(() => useCompanies(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockCompanies);
  });

  it('useDailyPipeline triggers daily run mutation', async () => {
    const mockRunRes = { status: 'completed', processed: 25 };
    vi.spyOn(agentsApi, 'runDaily').mockResolvedValue(mockRunRes);

    const { result } = renderHook(() => useDailyPipeline(), { wrapper: createWrapper() });

    let data;
    await act(async () => {
      data = await result.current.mutateAsync([1, 2]);
    });

    expect(data).toEqual(mockRunRes);
  });

  it('useLeads provides queryBank, runLeads, and updateLeadStatus', async () => {
    vi.spyOn(agentsApi, 'getQueryBank').mockResolvedValue({ queries: [{ category: 'YC AI', query: 'site:jobs.lever.co' }] });
    vi.spyOn(agentsApi, 'runLeads').mockResolvedValue({ leads: [] });
    vi.spyOn(agentsApi, 'updateLeadStatus').mockResolvedValue({ status: 'saved' });

    const { result } = renderHook(() => useLeads(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.queryBank.isSuccess).toBe(true);
    });

    expect(result.current.queryBank.data?.queries.length).toBe(1);

    await act(async () => {
      await result.current.updateLeadStatus.mutateAsync({ leadId: 5, status: 'saved' });
    });
  });

  it('useNegotiationBenchmark queries benchmark for target company', async () => {
    const mockBenchmark = { company: 'Google', level: 'L6', p50_total_comp_lpa: 120 };
    vi.spyOn(agentsApi, 'getNegotiationBenchmark').mockResolvedValue(mockBenchmark);

    const { result } = renderHook(() => useNegotiationBenchmark('Google', true), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockBenchmark);
  });

  it('useScoreAnswer scores user interview STAR response', async () => {
    const mockScore = { score: 92, feedback: 'Strong STAR execution', metrics: { action: 95 } };
    vi.spyOn(agentsApi, 'scoreInterviewAnswer').mockResolvedValue(mockScore);

    const { result } = renderHook(() => useScoreAnswer(), { wrapper: createWrapper() });

    let scoreRes;
    await act(async () => {
      scoreRes = await result.current.mutateAsync({
        question: 'Tell me about a time you optimized latency',
        answer: 'I profiled the async queue and reduced p99 by 60%',
      });
    });

    expect(scoreRes).toEqual(mockScore);
  });
});
