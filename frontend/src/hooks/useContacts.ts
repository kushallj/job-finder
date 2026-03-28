import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contactsApi } from '../api';
import type { ContactSearchRequest } from '../api/types';

export const useContacts = (filters: { page: number; limit: number; company?: string }) => {
  const queryClient = useQueryClient();

  // Get all contacts
  const contactsQuery = useQuery({
    queryKey: ['contacts', filters.page, filters.limit, filters.company],
    queryFn: async () => {
      try {
        const data = await contactsApi.getAll(filters.company, filters.page, filters.limit);
        console.log('[Contacts Hook] Contacts fetched:', {
          count: data.contacts?.length || 0,
          total: data.pagination?.total || 0,
          page: filters.page,
        });
        return data;
      } catch (error) {
        console.error('[Contacts Hook] Failed to fetch contacts:', error);
        throw error;
      }
    },
    staleTime: 60000, // 1 minute
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // Search contacts mutation
  const searchMutation = useMutation({
    mutationFn: async (data: ContactSearchRequest) => {
      try {
        const result = await contactsApi.search(data);
        console.log('[Contacts Hook] Search completed:', {
          company: data.company_name,
          found: result.contacts?.length || 0,
        });
        return result;
      } catch (error) {
        console.error('[Contacts Hook] Search failed:', error);
        throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  return {
    contacts: contactsQuery.data?.contacts || [],
    pagination: contactsQuery.data?.pagination || { page: 1, limit: 50, total: 0, pages: 0 },
    isLoading: contactsQuery.isLoading,
    error: contactsQuery.error,
    
    // Mutations
    search: searchMutation.mutate,
    searchAsync: searchMutation.mutateAsync,
    isSearching: searchMutation.isPending,
    searchError: searchMutation.error,
    searchResult: searchMutation.data,
    
    // Refetch
    refetch: contactsQuery.refetch,
  };
};

export const useContact = (contactId: number) => {
  const contactQuery = useQuery({
    queryKey: ['contact', contactId],
    queryFn: async () => {
      try {
        const data = await contactsApi.getById(contactId);
        console.log('[Contact Hook] Contact fetched:', contactId);
        return data;
      } catch (error) {
        console.error('[Contact Hook] Failed to fetch contact:', contactId, error);
        throw error;
      }
    },
    enabled: !!contactId,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  return {
    contact: contactQuery.data,
    isLoading: contactQuery.isLoading,
    error: contactQuery.error,
  };
};

