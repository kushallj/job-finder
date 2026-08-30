import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { lifecycleApi } from '../api/endpoints/lifecycle';

export const useActionQueue = (limit = 12) => {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['action-queue', limit],
    queryFn: () => lifecycleApi.queue(limit),
    staleTime: 10000,
  });

  const doNext = useMutation({
    mutationFn: (jobId: number) => lifecycleApi.doNext(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['action-queue'] });
      queryClient.invalidateQueries({ queryKey: ['opportunity-brief'] });
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  return { ...query, doNext: doNext.mutateAsync, isWorking: doNext.isPending };
};
