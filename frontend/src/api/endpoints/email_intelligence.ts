import api from '../axios';

export interface DiscoveredContactItem {
  name: string;
  first_name?: string;
  last_name?: string;
  title: string;
  company: string;
  domain?: string;
  email: string;
  confidence_score: number;
  persona_score: number;
  source: string;
  mail_provider?: string;
  verified: boolean;
  is_deliverable: boolean;
  linkedin_url?: string;
  github_username?: string;
}

export interface EmailDiscoveryResponse {
  status: string;
  company: string;
  domain: string;
  has_mx: boolean;
  mail_provider: string;
  total_found: number;
  contacts: DiscoveredContactItem[];
  recommended_contact?: DiscoveredContactItem | null;
  timestamp: string;
}

export interface EmailVerifyResponse {
  status: string;
  email: string;
  is_valid_syntax: boolean;
  is_disposable: boolean;
  is_free_mail: boolean;
  has_mx_records: boolean;
  mx_records: string[];
  mail_provider: string;
  confidence_score: number;
  verification_status: string;
  reason?: string | null;
  timestamp: string;
}

export interface SearchDorkItem {
  dork_type: string;
  query: string;
  target_role?: string | null;
  description: string;
  url?: string | null;
}

export interface EmailDorksResponse {
  status: string;
  company: string;
  domain: string;
  total_dorks: number;
  dorks: SearchDorkItem[];
  timestamp: string;
}

export interface EmailPermutationItem {
  pattern_name: string;
  email: string;
  domain: string;
  confidence_score: number;
  has_mx: boolean;
}

export interface EmailPermutationsResponse {
  status: string;
  full_name: string;
  domain: string;
  has_mx: boolean;
  total_permutations: number;
  permutations: EmailPermutationItem[];
  timestamp: string;
}

export const emailIntelligenceApi = {
  discover: async (
    company: string,
    jobTitle?: string,
    websiteHint?: string,
    targetName?: string,
    limit: number = 6
  ) => {
    const res = await api.post<EmailDiscoveryResponse>('/api/email-intelligence/discover', {
      company,
      job_title: jobTitle,
      website_hint: websiteHint,
      target_name: targetName,
      limit,
    });
    return res.data;
  },

  verify: async (email: string) => {
    const res = await api.post<EmailVerifyResponse>('/api/email-intelligence/verify', { email });
    return res.data;
  },

  getDorks: async (company: string, domain?: string, personName?: string, roleTitle?: string) => {
    const res = await api.post<EmailDorksResponse>('/api/email-intelligence/dorks', {
      company,
      domain,
      person_name: personName,
      role_title: roleTitle,
    });
    return res.data;
  },

  getPermutations: async (fullName: string, domain: string) => {
    const res = await api.post<EmailPermutationsResponse>('/api/email-intelligence/permutations', {
      full_name: fullName,
      domain,
    });
    return res.data;
  },
};
