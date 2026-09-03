import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

export const STORAGE_KEY_API_URL = 'job_finder_api_url';

export const getActiveApiBaseUrl = (): string => {

  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem(STORAGE_KEY_API_URL);
    if (saved && saved.trim()) {
      return saved.trim().replace(/\/+$/, '');
    }
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return '';
};

export const setActiveApiBaseUrl = (url: string): void => {
  if (typeof window !== 'undefined') {
    if (!url || !url.trim()) {
      localStorage.removeItem(STORAGE_KEY_API_URL);
    } else {
      localStorage.setItem(STORAGE_KEY_API_URL, url.trim().replace(/\/+$/, ''));
    }
  }
};

const api = axios.create({
  baseURL: getActiveApiBaseUrl(),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for dynamic URL switching, logging, and trace ID
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Dynamically update baseURL on each request in case user changed it in Setup Guide
    const currentBase = getActiveApiBaseUrl();
    if (currentBase) {
      config.baseURL = currentBase;
    }
    const traceId = crypto.randomUUID().slice(0, 8);
    config.headers['X-Trace-ID'] = traceId;
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.baseURL || ''}${config.url}`, {
      traceId,
      params: config.params,
    });
    return config;
  },

  (error: AxiosError) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response interceptor for logging and error handling
api.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      status: response.status,
    });
    return response;
  },
  (error: AxiosError) => {
    const traceId = error.config?.headers['X-Trace-ID'] || 'unknown';
    console.error(`[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
      traceId,
      status: error.response?.status,
      message: error.message,
    });
    return Promise.reject(error);
  }
);

export default api;

