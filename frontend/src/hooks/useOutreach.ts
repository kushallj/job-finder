import { useMutation, useQueryClient } from '@tanstack/react-query';
import { outreachApi } from '../api';
import type { OutreachRequest, FollowUpRequest } from '../api/types';

export const useOutreach = () => {
  const queryClient = useQueryClient();

  // Send outreach mutation
  const sendOutreachMutation = useMutation({
    mutationFn: (data: OutreachRequest) => outreachApi.send(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outreach'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  // Send follow-up mutation
  const sendFollowUpMutation = useMutation({
    mutationFn: (data: FollowUpRequest) => outreachApi.sendFollowUp(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outreach'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  // Update status mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ outreachId, status }: { outreachId: number; status: string }) =>
      outreachApi.updateStatus(outreachId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outreach'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  return {
    // Mutations
    sendOutreach: sendOutreachMutation.mutate,
    sendOutreachAsync: sendOutreachMutation.mutateAsync,
    isSendingOutreach: sendOutreachMutation.isPending,
    outreachError: sendOutreachMutation.error,
    outreachResult: sendOutreachMutation.data,
    
    sendFollowUp: sendFollowUpMutation.mutate,
    sendFollowUpAsync: sendFollowUpMutation.mutateAsync,
    isSendingFollowUp: sendFollowUpMutation.isPending,
    followUpError: sendFollowUpMutation.error,
    followUpResult: sendFollowUpMutation.data,
    
    updateStatus: updateStatusMutation.mutate,
    isUpdatingStatus: updateStatusMutation.isPending,
  };
};

