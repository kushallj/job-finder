import api from '../axios';

// ── Feature 11: System Design Whiteboard Types ──────────────────────────────
export interface SystemDesignArchetype {
  archetype_id: string;
  title: string;
  domain: string;
  default_dau: number;
  default_read_write_ratio: string;
  avg_payload_bytes: number;
  p99_sla_target: string;
  recommended_db: string;
}

export interface WhiteboardResponse {
  status: string;
  archetype_id: string;
  title: string;
  domain: string;
  p99_sla_target: string;
  capacity_estimates: {
    daily_active_users: number;
    total_requests_per_day: number;
    avg_qps: number;
    peak_qps: number;
    daily_storage_gb: number;
    daily_storage_tb: number;
    annual_storage_tb: number;
    ram_cache_required_gb: number;
    network_egress_mbps: number;
    network_egress_gbps: number;
  };
  mermaid_diagram: string;
  failure_matrix: Array<{
    failure_mode: string;
    risk: string;
    defensive_mitigation: string;
  }>;
  whiteboard_talking_points: string[];
}

// ── Feature 12: Executive Outreach Types ────────────────────────────────────
export interface ExecutivePainPoint {
  pain_id: string;
  title: string;
  category: string;
  default_metric: string;
  solution_hook: string;
}

export interface ExecutiveCampaignResponse {
  status: string;
  candidate_name: string;
  target_company: string;
  executive_name: string;
  executive_title: string;
  pain_point: ExecutivePainPoint;
  campaign_stages: Array<{
    stage_number: number;
    timing: string;
    subject: string;
    body: string;
    strategic_goal: string;
  }>;
  executive_leverage_summary: string;
}

// ── Feature 13: Sandbox Simulation Types ────────────────────────────────────
export interface SandboxModel {
  model_id: string;
  title: string;
  description: string;
  default_concurrency: number;
  default_cache_capacity_mb: number;
}

export interface SimulationResponse {
  status: string;
  model_id: string;
  title: string;
  description: string;
  metrics: {
    concurrency_rps: number;
    cache_hit_rate_percent: number;
    p50_latency_ms: number;
    p99_latency_ms: number;
    throttled_requests: number;
    error_rate_percent: number;
    failure_injection_active: boolean;
  };
  telemetry_timeline: Array<{
    timestamp_ms: number;
    event: string;
    status: string;
    active_connections: number;
  }>;
  architecture_takeaway: string;
}

// ── API Caller ───────────────────────────────────────────────────────────────
export const sprint6Api = {
  // Feature 11
  getSystemDesignArchetypes: async (): Promise<{ status: string; archetypes: SystemDesignArchetype[] }> => {
    const res = await api.get<{ status: string; archetypes: SystemDesignArchetype[] }>('/api/system-design/archetypes');
    return res.data;
  },

  estimateAndDiagram: async (payload: {
    archetype_id: string;
    daily_active_users?: number;
    avg_actions_per_user_day?: number;
    payload_size_bytes?: number;
  }): Promise<WhiteboardResponse> => {
    const res = await api.post<WhiteboardResponse>('/api/system-design/estimate-and-diagram', payload);
    return res.data;
  },

  // Feature 12
  getExecutivePainPoints: async (): Promise<{ status: string; pain_points: ExecutivePainPoint[] }> => {
    const res = await api.get<{ status: string; pain_points: ExecutivePainPoint[] }>('/api/executive-outreach/pain-points');
    return res.data;
  },

  generateExecutiveCampaign: async (payload: {
    candidate_name?: string;
    target_company: string;
    executive_name: string;
    executive_title?: string;
    pain_point_id?: string;
    custom_proof_of_work_url?: string;
  }): Promise<ExecutiveCampaignResponse> => {
    const res = await api.post<ExecutiveCampaignResponse>('/api/executive-outreach/campaign', payload);
    return res.data;
  },

  // Feature 13
  getSandboxModels: async (): Promise<{ status: string; models: SandboxModel[] }> => {
    const res = await api.get<{ status: string; models: SandboxModel[] }>('/api/sandbox/models');
    return res.data;
  },

  runSimulation: async (payload: {
    model_id: string;
    concurrency_rps?: number;
    failure_injection_enabled?: boolean;
  }): Promise<SimulationResponse> => {
    const res = await api.post<SimulationResponse>('/api/sandbox/simulate', payload);
    return res.data;
  },
};
