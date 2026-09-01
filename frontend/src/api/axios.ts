import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';



const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging and trace ID
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const traceId = crypto.randomUUID().slice(0, 8);
    config.headers['X-Trace-ID'] = traceId;
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
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

