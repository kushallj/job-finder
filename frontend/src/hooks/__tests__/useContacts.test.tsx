import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useContacts, useContact } from '../useContacts';
import { contactsApi } from '../../api';

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

describe('useContacts Hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches contacts with company filter and pagination', async () => {
    const mockResponse = {
      contacts: [
        { id: 1, name: 'Alice Manager', company: 'Google', title: 'Engineering Director' },
      ],
      pagination: { total: 10, pages: 1, page: 1, limit: 50 },
    };

    vi.spyOn(contactsApi, 'getAll').mockResolvedValue(mockResponse);

    const { result } = renderHook(
      () => useContacts({ page: 1, limit: 50, company: 'Google' }),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.contacts).toEqual(mockResponse.contacts);
    expect(result.current.pagination.total).toBe(10);
  });

  it('triggers search mutation and returns results', async () => {
    vi.spyOn(contactsApi, 'getAll').mockResolvedValue({
      contacts: [],
      pagination: { total: 0, pages: 0, page: 1, limit: 50 },
    });
    const searchRes = { contacts: [{ id: 99, name: 'Bob Recruiter', company: 'Amazon' }] };
    vi.spyOn(contactsApi, 'search').mockResolvedValue(searchRes);

    const { result } = renderHook(
      () => useContacts({ page: 1, limit: 50 }),
      { wrapper: createWrapper() }
    );

    let mutationData;
    await act(async () => {
      mutationData = await result.current.searchAsync({ company_name: 'Amazon' });
    });

    expect(mutationData).toEqual(searchRes);
  });

  it('useContact hook fetches a single contact by id', async () => {
    const singleContact = { id: 7, name: 'Sarah Tech Lead', company: 'Apple' };
    vi.spyOn(contactsApi, 'getById').mockResolvedValue(singleContact);

    const { result } = renderHook(() => useContact(7), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.contact).toEqual(singleContact);
  });
});
