import api from '../axios';
import type { OpportunityBrief } from '../types';

export interface SubmissionPacket {
  job_id: number;
  application_id: number | null;
  resume_version: string | null;
  cover_letter: string | null;
  proof_url: string | null;
  proof_notes: string | null;
  proof_logged_at: string | null;
}

export const opportunitiesApi = {
  brief: async (jobId: number): Promise<OpportunityBrief> => {
    const response = await api.get<OpportunityBrief>(`/api/opportunities/${jobId}/brief`);
    return response.data;
  },
  packet: async (jobId: number): Promise<SubmissionPacket> => {
    const response = await api.get<SubmissionPacket>(`/api/opportunities/${jobId}/packet`);
    return response.data;
  },
  doNext: async (jobId: number) => {
    const response = await api.post(`/api/opportunities/${jobId}/do-next`);
    return response.data;
  },
  logProof: async (applicationId: number, proof: { confirmation_number?: string; proof_note?: string; proof_url?: string }) => {
    const response = await api.post(`/api/applications/${applicationId}/proof`, {
      proof_url: proof.proof_url,
      proof_notes: [proof.confirmation_number ? `Confirmation: ${proof.confirmation_number}` : '', proof.proof_note].filter(Boolean).join(' | '),
    });
    return response.data;
  },
};
