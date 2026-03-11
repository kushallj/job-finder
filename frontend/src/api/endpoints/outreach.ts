import api from '../axios';
import type {
  OutreachRequest,
  OutreachResponse,
  FollowUpRequest,
  FollowUpResponse,
} from '../types';

export const outreachApi = {
  /**
   * Send outreach email to a contact for a specific job
   */
  send: async (data: OutreachRequest): Promise<OutreachResponse> => {
    const response = await api.post<OutreachResponse>('/api/outreach/send', data);
    return response.data;
  },

  /**
   * Send a follow-up email for an existing outreach
   */
  sendFollowUp: async (data: FollowUpRequest): Promise<FollowUpResponse> => {
    const response = await api.post<FollowUpResponse>('/api/outreach/followup', data);
    return response.data;
  },

  /**
   * Update outreach status
   */
  updateStatus: async (outreachId: number, status: string): Promise<void> => {
    const response = await api.put(`/api/outreach/${outreachId}/status`, { status });
    return response.data;
  },
};

