import api from '../axios';

export interface FleetAgentRunResult {
  agent_name: string;
  display_title: string;
  avatar: string;
  status: string;
  summary: string;
  actions_taken: number;
  deliverables: Array<Record<string, any>>;
  duration_seconds: number;
  timestamp: string;
}

export interface FleetCycleResult {
  fleet_id: string;
  cycle_id: string;
  is_active: boolean;
  has_api_key: boolean;
  total_actions_executed: number;
  agent_runs: FleetAgentRunResult[];
  execution_time_seconds: number;
  completed_at: string;
}

export interface AgentFleetConfig {
  google_gemini_api_key?: string;
  autonomous_mode: boolean;
  execution_interval_hours: number;
  enabled_agents: string[];
  target_roles: string[];
  target_locations: string[];
}

export const agentFleetApi = {
  getConfig: () => api.get<AgentFleetConfig>('/api/fleet/config'),
  updateConfig: (config: AgentFleetConfig) => api.post<AgentFleetConfig>('/api/fleet/config', config),
  runCycle: (config?: Partial<AgentFleetConfig>) =>
    api.post<{ status: string; cycle: FleetCycleResult }>('/api/fleet/run-cycle', config),
};
