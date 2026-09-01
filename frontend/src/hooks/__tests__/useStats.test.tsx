import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useStats } from '../useStats';
import { statsApi } from '../../api';

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

describe('useStats Hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches system stats and recent outreach list', async () => {
    const mockStats = {
      stats: {
        total_jobs: 150,
        total_contacts: 80,
        total_applications: 35,
        total_outreach_attempts: 60,
        emails_sent: 50,
        follow_ups_sent: 10,
        success_rate: 28.5,
      },
      recent_outreach: [
        { id: 1, contact_name: 'John Doe', company: 'Google', status: 'sent' },
      ],
      source: 'database',
      timestamp: '2026-08-31T10:00:00Z',
    };

    const mockHealth = {
      status: 'healthy',
      database: 'connected',
      ollama: 'connected',
      email: 'ready',
    };

    vi.spyOn(statsApi, 'getStats').mockResolvedValue(mockStats);
    vi.spyOn(statsApi, 'getHealth').mockResolvedValue(mockHealth);

    const { result } = renderHook(() => useStats(), { wrapper: createWrapper() });

    expect(result.current.isLoadingStats).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoadingStats).toBe(false);
    });

    expect(result.current.stats.total_jobs).toBe(150);
    expect(result.current.recentOutreach.length).toBe(1);
    expect(result.current.health).toEqual(mockHealth);
  });

  it('provides safe fallback zeros when stats data is undefined', async () => {
    vi.spyOn(statsApi, 'getStats').mockResolvedValue({} as never);
    vi.spyOn(statsApi, 'getHealth').mockResolvedValue({ status: 'ok' });

    const { result } = renderHook(() => useStats(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoadingStats).toBe(false);
    });

    expect(result.current.stats).toEqual({
      total_jobs: 0,
      total_contacts: 0,
      total_applications: 0,
      total_outreach_attempts: 0,
      emails_sent: 0,
      follow_ups_sent: 0,
      success_rate: 0,
    });
  });
});
