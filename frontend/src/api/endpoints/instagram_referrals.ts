import api from '../axios';

export interface InstagramProfile {
  username: string;
  name: string;
  title?: string;
  company: string;
  bio: string;
  is_founder: boolean;
  profile_url: string;
  threads_handle?: string;
  verified: boolean;
  followers_count?: number;
}

export interface InstagramSearchResponse {
  status: string;
  company: string;
  total_found: number;
  profiles: InstagramProfile[];
}

export interface InstagramMessageResponse {
  status: string;
  target_username: string;
  action_type: string;
  message: string;
  intent_url: string;
  character_count: number;
  timestamp: string;
}

export const instagramReferralsApi = {
  search: (data: { company: string; role_keyword?: string; founder_only?: boolean }) =>
    api.post<InstagramSearchResponse>('/api/instagram/search', data),
  generateMessage: (data: {
    action_type: 'dm' | 'story_reply' | 'comment';
    target_username: string;
    company: string;
    name: string;
    role_title: string;
    portfolio_link?: string;
  }) => api.post<InstagramMessageResponse>('/api/instagram/generate-message', data),
};
