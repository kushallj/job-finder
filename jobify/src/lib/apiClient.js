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

// Services call the backend only in the signed-in workspace (/app) with VITE_API_BASE_URL set.
// /demo must never call the API. AppProvider sets this on every render, so it is
// current before any page effect runs.
let liveMode = false;
export const setLiveMode = (on) => { liveMode = Boolean(on); };
export const isLive = () => liveMode && Boolean(env.apiBaseUrl);

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

/**
 * POST and read a text/event-stream response, calling onEvent(event, data) per SSE event.
 * Errors before the stream starts (401/402/404/422/503) throw ApiError like api().
 * No total timeout (replies can be long); abort with `signal` (fetch throws AbortError).
 */
export async function apiStream(path, { method = "POST", body, signal, onEvent } = {}) {
  if (!env.apiBaseUrl) throw new ApiError(0, "api_not_configured", "VITE_API_BASE_URL is not set");
  const token = await getToken();
  const res = await fetch(env.apiBaseUrl + path, {
    method,
    signal,
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, data?.error?.code || "http_error", data?.error?.message || res.statusText);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  const emit = (block) => {
    let event = "message";
    const data = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (data.length) onEvent?.(event, JSON.parse(data.join("\n")));
  };
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      emit(buf.slice(0, i));
      buf = buf.slice(i + 2);
    }
  }
  if (buf.trim()) emit(buf);
}
