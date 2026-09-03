import api from '../axios';

export interface BackendServicesStatus {
  gemini_configured: boolean;
  serpapi_configured: boolean;
  hunter_configured: boolean;
  apollo_configured: boolean;
  smtp_configured: boolean;
  telegram_configured: boolean;
  discord_configured: boolean;
  slack_configured: boolean;
  tsenta_configured: boolean;
}

export interface BackendConfigStatusResponse {
  status: string;
  version: string;
  backend_time: string;
  services: BackendServicesStatus;
  database: {
    type: 'postgresql' | 'sqlite';
    url_configured: boolean;
  };
}

export interface KeyValidationRequest {
  gemini_api_key?: string;
  serpapi_key?: string;
  hunter_api_key?: string;
  gmail_address?: string;
  gmail_password?: string;
}

export interface ValidationItemResult {
  valid: boolean;
  message: string;
}

export interface KeyValidationResponse {
  status: string;
  results: {
    gemini?: ValidationItemResult;
    serpapi?: ValidationItemResult;
    hunter?: ValidationItemResult;
    smtp?: ValidationItemResult;
  };
}

export const configApi = {
  getStatus: async (): Promise<BackendConfigStatusResponse> => {
    const res = await api.get<BackendConfigStatusResponse>('/api/config/status');
    return res.data;
  },

  validateKeys: async (keys: KeyValidationRequest): Promise<KeyValidationResponse> => {
    const res = await api.post<KeyValidationResponse>('/api/config/validate-keys', keys);
    return res.data;
  },

  pingBackend: async (url?: string): Promise<{ ok: boolean; latencyMs: number }> => {
    const start = performance.now();
    try {
      const target = url ? `${url.replace(/\/+$/, '')}/api/health` : '/api/health';
      const res = await fetch(target, { method: 'GET', signal: AbortSignal.timeout(6000) });
      const latencyMs = Math.round(performance.now() - start);
      return { ok: res.ok, latencyMs };
    } catch {
      return { ok: false, latencyMs: 0 };
    }
  },
};
