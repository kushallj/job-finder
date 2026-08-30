import api from '../axios';

export interface ResumeDocumentResponse {
  status: string;
  document_type: string;
  company: string;
  role_title: string;
  ats_match_score: number;
  html_content: string;
  plain_text: string;
  suggested_keywords: string[];
  timestamp: string;
}

export interface ResumeGenerateRequest {
  candidate_name?: string;
  candidate_email?: string;
  candidate_phone?: string;
  candidate_location?: string;
  candidate_linkedin?: string;
  candidate_github?: string;
  role_title: string;
  company: string;
  job_description?: string;
  custom_bullets?: string[];
}

export interface CoverLetterGenerateRequest {
  candidate_name?: string;
  candidate_email?: string;
  company: string;
  role_title: string;
  hiring_manager_name?: string;
  job_description?: string;
}

export const resumeGeneratorApi = {
  generateAtsResume: (data: ResumeGenerateRequest) =>
    api.post<ResumeDocumentResponse>('/api/resume/generate-ats', data),
  generateCoverLetter: (data: CoverLetterGenerateRequest) =>
    api.post<ResumeDocumentResponse>('/api/resume/generate-cover-letter', data),
};
