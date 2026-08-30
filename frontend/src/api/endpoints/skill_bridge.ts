import api from '../axios';

export interface SkillGapAnalysis {
  candidate_skills: string[];
  required_skills: string[];
  gap_skills: string[];
  match_percentage: number;
}

export interface MicroProjectSpec {
  title: string;
  tagline: string;
  duration_estimate: string;
  skills_proven: string[];
  architecture_overview: string;
  starter_code_files: Record<string, string>;
  demonstration_prompt: string;
}

export interface SkillBridgeProjectResponse {
  status: string;
  company: string;
  role_title: string;
  gap_analysis: SkillGapAnalysis;
  project_spec: MicroProjectSpec;
  timestamp: string;
}

export const skillBridgeApi = {
  generateProject: (data: {
    company: string;
    role_title: string;
    job_description?: string;
    candidate_skills?: string[];
  }) => api.post<SkillBridgeProjectResponse>('/api/skill-bridge/generate-project', data),
};
