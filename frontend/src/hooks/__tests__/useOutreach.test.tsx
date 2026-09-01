import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useOutreach } from '../useOutreach';
import { outreachApi } from '../../api';

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

describe('useOutreach Hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sends outreach email via mutation', async () => {
    const sendResponse = { status: 'sent', outreach_id: 101 };
    vi.spyOn(outreachApi, 'send').mockResolvedValue(sendResponse);

    const { result } = renderHook(() => useOutreach(), { wrapper: createWrapper() });

    let mutationData;
    await act(async () => {
      mutationData = await result.current.sendOutreachAsync({
        contact_id: 5,
        job_id: 12,
        template_type: 'initial_outreach',
      });
    });

    expect(mutationData).toEqual(sendResponse);
  });

  it('sends follow-up email via mutation', async () => {
    const followUpRes = { status: 'sent', outreach_id: 102 };
    vi.spyOn(outreachApi, 'sendFollowUp').mockResolvedValue(followUpRes);

    const { result } = renderHook(() => useOutreach(), { wrapper: createWrapper() });

    let mutationData;
    await act(async () => {
      mutationData = await result.current.sendFollowUpAsync({
        outreach_id: 101,
        step: 2,
      });
    });

    expect(mutationData).toEqual(followUpRes);
  });

  it('updates outreach status via mutation', async () => {
    const updateSpy = vi.spyOn(outreachApi, 'updateStatus').mockResolvedValue({ status: 'updated' });

    const { result } = renderHook(() => useOutreach(), { wrapper: createWrapper() });

    act(() => {
      result.current.updateStatus({ outreachId: 55, status: 'replied' });
    });

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(55, 'replied');
    });
  });
});
