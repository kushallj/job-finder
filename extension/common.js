// Shared helpers for the Job Finder Companion extension.
// Loaded by background.js and popup.js (content.js stays dependency-free
// since it runs in the page's world and only talks to background.js).

const DEFAULT_API_BASE_URL = "http://localhost:8000";

async function getApiBaseUrl() {
  const { apiBaseUrl } = await chrome.storage.sync.get("apiBaseUrl");
  return (apiBaseUrl || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

async function setApiBaseUrl(url) {
  await chrome.storage.sync.set({ apiBaseUrl: url.replace(/\/+$/, "") });
}

// Centralized fetch wrapper. Runs in the background service worker so it
// isn't subject to a job site's Content-Security-Policy, and so every
// caller (popup, content script via messaging) gets consistent error
// shapes instead of raw fetch exceptions.
async function apiFetch(path, { method = "GET", body, timeoutMs = 30000 } = {}) {
  const base = await getApiBaseUrl();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(base + path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      // non-JSON response body — leave data null
    }

    if (!res.ok) {
      const message =
        (data && (data.detail || data.message || data.error)) ||
        `Request failed (${res.status})`;
      return { ok: false, status: res.status, error: message, data };
    }
    return { ok: true, status: res.status, data };
  } catch (err) {
    const message =
      err.name === "AbortError"
        ? "Request timed out — is the backend running?"
        : `Could not reach backend at ${base} (${err.message}). Check the URL in Options and make sure the server is running.`;
    return { ok: false, status: 0, error: message };
  } finally {
    clearTimeout(timer);
  }
}
