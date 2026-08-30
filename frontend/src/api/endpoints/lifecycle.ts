import api from '../axios';
import type { ActionQueueResponse, LifecycleStatus } from '../types';

export const lifecycleApi = {
  queue: async (limit = 12): Promise<ActionQueueResponse> =>
    (await api.get<ActionQueueResponse>('/api/action-queue', { params: { limit } })).data,
  doNext: async (jobId: number) =>
    (await api.post(`/api/opportunities/${jobId}/do-next`)).data,
  transition: async (applicationId: number, status: LifecycleStatus) =>
    (await api.post(`/api/applications/${applicationId}/transition`, { status })).data,
};
