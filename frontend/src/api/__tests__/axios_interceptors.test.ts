import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../axios';

describe('Axios Client & Interceptors', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('configures default base settings correctly', () => {
    expect(api.defaults.timeout).toBe(30000);
    expect(api.defaults.headers['Content-Type']).toBe('application/json');
  });

  it('attaches X-Trace-ID header on outgoing requests', async () => {
    // Intercept request configuration through interceptor handler
    const requestInterceptor = (api.interceptors.request as unknown as {
      handlers: Array<{ fulfilled: (config: unknown) => unknown }>;
    }).handlers[0];

    expect(requestInterceptor).toBeDefined();

    const config = {
      headers: {} as Record<string, string>,
      method: 'get',
      url: '/api/stats',
    };

    const modifiedConfig = (await requestInterceptor.fulfilled(config)) as {
      headers: Record<string, string>;
    };

    expect(modifiedConfig.headers['X-Trace-ID']).toBeDefined();
    expect(modifiedConfig.headers['X-Trace-ID'].length).toBe(8);
  });

  it('logs response on fulfilled response interceptor', () => {
    const responseInterceptor = (api.interceptors.response as unknown as {
      handlers: Array<{ fulfilled: (response: unknown) => unknown }>;
    }).handlers[0];

    const response = {
      status: 200,
      config: { method: 'get', url: '/api/jobs' },
      data: { status: 'success' },
    };

    const result = responseInterceptor.fulfilled(response);
    expect(result).toBe(response);
  });

  it('rejects error and logs error on rejected response interceptor', async () => {
    const responseInterceptor = (api.interceptors.response as unknown as {
      handlers: Array<{ rejected: (error: unknown) => Promise<unknown> }>;
    }).handlers[0];

    const error = {
      message: 'Network Timeout',
      config: { method: 'post', url: '/api/outreach', headers: { 'X-Trace-ID': 'abcd1234' } },
      response: { status: 504 },
    };

    await expect(responseInterceptor.rejected(error)).rejects.toEqual(error);
  });
});
