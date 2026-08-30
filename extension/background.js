importScripts("common.js");

// Central message router. Both the popup and content scripts send
// { type, payload } messages here rather than calling fetch() directly —
// this keeps API-base-URL logic and CORS/CSP handling in one place.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender).then(sendResponse);
  return true; // keep the message channel open for the async response
});

async function handleMessage(message, sender) {
  switch (message.type) {
    case "PING_BACKEND":
      return apiFetch("/api/health");

    case "GET_STATS":
      return apiFetch("/api/stats");

    case "GET_JOBS":
      return apiFetch(
        `/api/jobs?page=${message.page || 1}&limit=${message.limit || 20}`
      );

    case "GET_PENDING_OUTREACH":
      return apiFetch(
        `/api/jobs/pending-outreach?min_score=${message.minScore ?? 50}&limit=${
          message.limit || 20
        }`
      );

    case "RUN_QUERY":
      return apiFetch("/run-query", {
        method: "POST",
        body: {
          query: message.query,
          min_score: message.minScore ?? 50,
        },
        timeoutMs: 120000,
      });

    case "FIND_CONTACTS":
      return apiFetch("/api/contacts/search", {
        method: "POST",
        body: { company_name: message.company },
        timeoutMs: 60000,
      });

    case "SEND_OUTREACH":
      // Deliberately requires an explicit job_id + confirmation from the
      // popup UI — this extension never sends outreach automatically.
      return apiFetch("/api/outreach/send", {
        method: "POST",
        body: message.payload,
        timeoutMs: 60000,
      });

    case "CAPTURE_JOB":
      return apiFetch("/api/jobs/capture", {
        method: "POST",
        body: message.payload,
        timeoutMs: 60000,
      });

    case "GET_API_BASE_URL":
      return { ok: true, data: { apiBaseUrl: await getApiBaseUrl() } };

    case "SET_API_BASE_URL":
      await setApiBaseUrl(message.url);
      return { ok: true };

    default:
      return { ok: false, error: `Unknown message type: ${message.type}` };
  }
}
