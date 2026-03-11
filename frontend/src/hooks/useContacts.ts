import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contactsApi } from '../api';
import type { ContactSearchRequest } from '../api/types';

export const useContacts = (company?: string) => {
  const queryClient = useQueryClient();

  // Get all contacts
  const contactsQuery = useQuery({
    queryKey: ['contacts', company],
    queryFn: () => contactsApi.getAll(company),
    staleTime: 60000, // 1 minute
  });

  // Search contacts mutation
  const searchMutation = useMutation({
    mutationFn: (data: ContactSearchRequest) => contactsApi.search(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
  });

  return {
    contacts: contactsQuery.data || [],
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
    queryFn: () => contactsApi.getById(contactId),
    enabled: !!contactId,
  });

  return {
    contact: contactQuery.data,
    isLoading: contactQuery.isLoading,
    error: contactQuery.error,
  };
};

