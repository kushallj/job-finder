import { env } from "../config/env.js";

/**
 * Thin fetch wrapper for the Jobify backend. Services call this instead of fetch().
 *
 * - Attaches the Clerk session JWT:  Authorization: Bearer <token>
 * - Errors are normalised to ApiError { status, code, message } (backend shape: { error: { code, message } })
 * - Supports AbortSignal and a default timeout
 *
 * The token getter is registered once by AppProvider via setTokenGetter(getToken).
 */
export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

let getToken = async () => null;
export const setTokenGetter = (fn) => { getToken = fn; };

const DEFAULT_TIMEOUT_MS = 15000;

export async function api(path, { method = "GET", query, body, signal, timeout = DEFAULT_TIMEOUT_MS, headers = {} } = {}) {
  if (!env.apiBaseUrl) throw new ApiError(0, "api_not_configured", "VITE_API_BASE_URL is not set");

  const url = new URL(env.apiBaseUrl + path);
  Object.entries(query || {}).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    (Array.isArray(v) ? v : [v]).forEach((x) => url.searchParams.append(k, String(x)));
  });

  const timer = new AbortController();
  const timeoutId = setTimeout(() => timer.abort(), timeout);
  signal?.addEventListener("abort", () => timer.abort(), { once: true });

  try {
    const token = await getToken();
    const res = await fetch(url, {
      method,
      signal: timer.signal,
      headers: {
        Accept: "application/json",
        ...(body !== undefined && { "Content-Type": "application/json" }),
        ...(token && { Authorization: `Bearer ${token}` }),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      throw new ApiError(res.status, data?.error?.code || "http_error", data?.error?.message || res.statusText);
    }
    return data;
  } finally {
    clearTimeout(timeoutId);
  }
}
