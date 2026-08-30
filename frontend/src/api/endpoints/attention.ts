import api from '../axios';

export interface QueryTokenItem {
  id: string;
  text: string;
  category: string;
  weight: number;
}

export interface KeyTokenItem {
  id: string;
  text: string;
  category: string;
  source: string;
}

export interface ValuePayloadItem {
  id: string;
  proof_point: string;
  context: string;
  impact_metric?: string | null;
}

export interface AttentionHeadItem {
  head_name: string;
  head_score: number;
  top_matches: Array<{
    query_id: string;
    query_text: string;
    key_id: string;
    key_text: string;
    attention_weight: number;
  }>;
}

export interface AttentionMatrixItem {
  query_tokens: QueryTokenItem[];
  key_tokens: KeyTokenItem[];
  weights: number[][];
}

export interface TailoredBulletItem {
  original_text: string;
  tailored_text: string;
  attention_score: number;
  matched_queries: string[];
  quant_metric?: string | null;
}

export interface CrossAttentionOutreachHookItem {
  target_pain_point: string;
  candidate_proof_point: string;
  attention_weight: number;
  hook_sentence: string;
  call_to_action: string;
}

export interface AttentionMatchResponse {
  status: string;
  overall_score: number;
  fit_label: string;
  heads: Record<string, AttentionHeadItem>;
  matrix: AttentionMatrixItem;
  top_attended_values: ValuePayloadItem[];
  tailored_bullets: TailoredBulletItem[];
  outreach_hooks: CrossAttentionOutreachHookItem[];
  summary_insight: string;
  timestamp: string;
}

export interface AttentionTailorResponse {
  status: string;
  total_bullets: number;
  tailored_bullets: TailoredBulletItem[];
  timestamp: string;
}

export interface AttentionOutreachResponse {
  status: string;
  contact_name: string;
  contact_title: string;
  company: string;
  role_type: string;
  subject: string;
  hook_message: string;
  attended_proof_point: string;
  impact_metric?: string | null;
  call_to_action: string;
  timestamp: string;
}

export const attentionApi = {
  match: async (jobDescription: string, customBullets?: string[]) => {
    const res = await api.post<AttentionMatchResponse>('/api/attention/match', {
      job_description: jobDescription,
      custom_bullets: customBullets,
    });
    return res.data;
  },

  tailor: async (jobDescription: string, customBullets?: string[]) => {
    const res = await api.post<AttentionTailorResponse>('/api/attention/tailor', {
      job_description: jobDescription,
      custom_bullets: customBullets,
    });
    return res.data;
  },

  outreach: async (contactName: string, contactTitle: string, company: string, jobDescription?: string) => {
    const res = await api.post<AttentionOutreachResponse>('/api/attention/outreach', {
      contact_name: contactName,
      contact_title: contactTitle,
      company,
      job_description: jobDescription,
    });
    return res.data;
  },
};
