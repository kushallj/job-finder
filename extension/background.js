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

    case "NEXTRAISE_GET_STATUS":
      return apiFetch("/api/nextraise/status");

    case "NEXTRAISE_BATCH_APPLY":
      return apiFetch("/api/nextraise/batch-apply", {
        method: "POST",
        body: {
          target_count: message.targetCount ?? 250,
          min_fit_score: message.minFitScore ?? 50,
        },
        timeoutMs: 180000,
      });

    case "NEXTRAISE_APPLY_JOB":
      return apiFetch(`/api/nextraise/apply/${message.jobId}`, {
        method: "POST",
        timeoutMs: 60000,
      });

    case "WORKDAY_GET_STATUS":
      return apiFetch("/api/workday/status");

    case "WORKDAY_BATCH_APPLY":
      return apiFetch("/api/workday/batch-apply", {
        method: "POST",
        body: {
          target_count: message.targetCount ?? 25,
          min_fit_score: message.minFitScore ?? 60,
        },
        timeoutMs: 180000,
      });

    case "WORKDAY_APPLY_JOB":
      return apiFetch(`/api/workday/apply/${message.jobId}`, {
        method: "POST",
        timeoutMs: 60000,
      });

    case "WORKDAY_GET_PROFILE":
      return apiFetch("/api/workday/profile");

    case "RESOLVE_QUESTION":
      return apiFetch("/api/workday/resolve-question", {
        method: "POST",
        body: {
          question: message.question,
          job_title: message.job_title || "Software Engineer",
          company: message.company || "Company",
          job_description: message.job_description || "",
          category: message.category,
        },
        timeoutMs: 60000,
      });

    case "SAVE_ANSWER":
      return apiFetch("/api/workday/save-answer", {
        method: "POST",
        body: {
          question: message.question,
          answer: message.answer,
          category: message.category,
          source: message.source || "user_edited",
          approved: message.approved !== undefined ? message.approved : true,
        },
        timeoutMs: 30000,
      });

    case "SAVE_ANSWERS_BATCH":
      return apiFetch("/api/workday/save-answers-batch", {
        method: "POST",
        body: {
          answers: message.answers || [],
        },
        timeoutMs: 30000,
      });

    case "GET_ANSWERS":
      return apiFetch(`/api/workday/answers?limit=${message.limit || 50}`);


    case "AUTOFILL_ACTIVE_TAB": {
      const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!activeTab || !activeTab.id) {
        return { ok: false, error: "No active browser tab detected." };
      }
      const profileRes = await apiFetch("/api/workday/profile");
      const profile = profileRes.ok ? profileRes.data : {};
      
      try {
        const [result] = await chrome.scripting.executeScript({
          target: { tabId: activeTab.id },
          func: async (candidateData) => {
            if (window.FormEngine && typeof window.FormEngine.autofillForm === "function") {
              const resolver = async (questionText, category) => {
                return new Promise((resolve) => {
                  chrome.runtime.sendMessage(
                    {
                      type: "RESOLVE_QUESTION",
                      question: questionText,
                      job_title: document.title || "Software Engineer",
                      company: location.hostname,
                      category: category,
                    },
                    (res) => {
                      if (res && res.ok && res.data) {
                        resolve(res.data.answer);
                      } else {
                        resolve(null);
                      }
                    }
                  );
                });
              };
              return await window.FormEngine.autofillForm(document, candidateData, resolver);
            }
            return { error: "FormEngine not loaded on this tab yet." };
          },
          args: [profile],
        });
        return { ok: true, data: result.result };
      } catch (err) {
        return { ok: false, error: `Script execution error: ${err.message}` };
      }
    }

    case "GET_API_BASE_URL":
      return { ok: true, data: { apiBaseUrl: await getApiBaseUrl() } };

    case "SET_API_BASE_URL":
      await setApiBaseUrl(message.url);
      return { ok: true };

    default:
      return { ok: false, error: `Unknown message type: ${message.type}` };
  }
}
