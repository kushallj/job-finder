import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useActionQueue } from '../useActionQueue';
import { lifecycleApi } from '../../api/endpoints/lifecycle';

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

describe('useActionQueue Hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches prioritized action queue items', async () => {
    const queueData = {
      items: [
        {
          job_id: 12,
          job_title: 'Staff AI Engineer',
          company: 'Anthropic',
          current_state: 'saved',
          next_action: 'tailor_resume',
          priority_score: 95,
        },
      ],
      total: 1,
    };

    vi.spyOn(lifecycleApi, 'queue').mockResolvedValue(queueData);

    const { result } = renderHook(() => useActionQueue(5), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(queueData);
  });

  it('triggers doNext mutation and executes lifecycle transition', async () => {
    vi.spyOn(lifecycleApi, 'queue').mockResolvedValue({ items: [], total: 0 });
    const actionRes = { status: 'success', next_state: 'applied' };
    vi.spyOn(lifecycleApi, 'doNext').mockResolvedValue(actionRes);

    const { result } = renderHook(() => useActionQueue(), { wrapper: createWrapper() });

    let mutationResult;
    await act(async () => {
      mutationResult = await result.current.doNext(12);
    });

    expect(mutationResult).toEqual(actionRes);
  });
});
