import api from '../axios';

export interface CommunityIntelItem {
  source: 'reddit' | 'hackernews' | 'medium' | 'substack' | 'youtube';
  title: string;
  url: string;
  author?: string;
  published_at?: string;
  summary: string;
  relevance_score: number;
  tags: string[];
}

export interface InterviewLoopBreakdown {
  rounds: Array<{ round: string; type: string; focus: string }>;
  common_questions: string[];
  system_design_topics: string[];
  red_flags: string[];
  green_flags: string[];
  negotiation_tips: string[];
}

export interface CompanyCommunityIntel {
  status: string;
  company: string;
  role_category: string;
  total_sources_scanned: number;
  overall_sentiment: string;
  interview_debrief: InterviewLoopBreakdown;
  sources: CommunityIntelItem[];
  last_updated: string;
}

export const communityIntelApi = {
  getCompanyIntel: (company: string, role?: string, forceRefresh: boolean = false) =>
    api.get<CompanyCommunityIntel>(`/api/community-intel/company/${encodeURIComponent(company)}`, {
      params: { role, force_refresh: forceRefresh },
    }),
  getJobIntel: (jobId: number) =>
    api.get<CompanyCommunityIntel>(`/api/jobs/${jobId}/community-intel`),
  harvestCompanyIntel: (company: string, roleCategory?: string, forceRefresh: boolean = true) =>
    api.post<CompanyCommunityIntel>('/api/community-intel/harvest', {
      company,
      role_category: roleCategory,
      force_refresh: forceRefresh,
    }),
};
