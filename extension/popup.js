// Popup logic for Job Finder Companion.
// Every backend call is routed through background.js via chrome.runtime.sendMessage
// so CORS/timeout/error handling stays in one place (see common.js).

function send(message) {
  return new Promise((resolve) => chrome.runtime.sendMessage(message, resolve));
}

function el(sel) {
  return document.querySelector(sel);
}

function showBanner(text) {
  const b = el("#connectionBanner");
  b.textContent = text;
  b.classList.remove("hidden");
}
function hideBanner() {
  el("#connectionBanner").classList.add("hidden");
}

// ── Tabs ─────────────────────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    el(`#tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "autofill") checkActiveTabEdits();
    if (btn.dataset.tab === "workday") loadWorkdayStatus();
    if (btn.dataset.tab === "nextraise") loadNextRaiseStatus();
    if (btn.dataset.tab === "jobs") loadJobs();
    if (btn.dataset.tab === "outreach") loadPending();
  });
});

async function checkActiveTabEdits() {
  const section = el("#popupLearningSection");
  const listEl = el("#popupLearningList");
  if (!section || !listEl) return;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) return;

  try {
    const [res] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        if (window.FormEngine && typeof window.FormEngine.getEditedFields === "function") {
          const edits = window.FormEngine.getEditedFields(document);
          return edits.map(e => ({
            question: e.question,
            category: e.category,
            currentValue: e.currentValue,
            originalValue: e.originalValue,
          }));
        }
        return [];
      }
    });

    const edits = (res && res.result) || [];
    if (!edits.length) {
      section.classList.add("hidden");
      listEl.innerHTML = "";
      return;
    }

    section.classList.remove("hidden");
    listEl.innerHTML = edits.map((item) => `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0; border-bottom:1px solid #334155;">
        <span style="color:#94a3b8; max-width:110px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeAttr(item.question || item.category)}">${escapeHtml(item.question || item.category)}</span>
        <span style="color:#38bdf8; font-weight:700; max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(item.currentValue)}</span>
      </div>
    `).join("");

    const saveBtn = el("#popupSaveAllBtn");
    if (saveBtn) {
      saveBtn.onclick = async () => {
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving…";
        const saveRes = await send({
          type: "SAVE_ANSWERS_BATCH",
          answers: edits.map(e => ({
            question: e.question,
            answer: e.currentValue,
            category: e.category,
            source: "user_edited"
          }))
        });
        if (saveRes && saveRes.ok) {
          saveBtn.textContent = "✓ Saved";
          await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => {
              const elements = Array.from(document.querySelectorAll('[data-jf-autofilled="true"]'));
              elements.forEach(el => {
                el.dataset.jfOriginalValue = el.value || '';
              });
            }
          });
          setTimeout(checkActiveTabEdits, 1200);
        } else {
          saveBtn.disabled = false;
          saveBtn.textContent = "Retry";
        }
      };
    }
  } catch (_) {}
}


el("#autofillCurrentTabBtn")?.addEventListener("click", async () => {
  const statusEl = el("#autofillStatus");
  const captchaEl = el("#popupCaptchaBanner");
  const auditDrawer = el("#popupAuditDrawer");

  statusEl.className = "status";
  statusEl.textContent = "Scanning and autofilling React/Next.js inputs on active tab…";
  if (captchaEl) captchaEl.classList.add("hidden");
  if (auditDrawer) {
    auditDrawer.classList.add("hidden");
    auditDrawer.innerHTML = "";
  }
  el("#autofillCurrentTabBtn").disabled = true;

  const res = await send({ type: "AUTOFILL_ACTIVE_TAB" });
  el("#autofillCurrentTabBtn").disabled = false;

  if (!res.ok) {
    statusEl.className = "status err";
    statusEl.textContent = res.error || "Autofill execution failed.";
    return;
  }

  const d = res.data;
  if (d && d.filled_count !== undefined) {
    statusEl.className = "status ok";
    statusEl.textContent = `Autofilled ${d.filled_count} fields cleanly with React event dispatch!`;

    // CAPTCHA Alert
    if (d.captcha && d.captcha.detected && captchaEl) {
      captchaEl.classList.remove("hidden");
      captchaEl.innerHTML = `⚠️ <strong>${escapeHtml(d.captcha.type)} Detected</strong>: Please solve verification on page. All other fields filled!`;
    }

    // Audit Breakdown Drawer
    if (d.details && d.details.length > 0 && auditDrawer) {
      auditDrawer.classList.remove("hidden");
      auditDrawer.innerHTML = `<div style="font-weight:700; color:#38bdf8; margin-bottom:6px;">Ghost Fill Summary (${d.filled_count} fields):</div>` +
        d.details.slice(0, 10).map((item) => `
          <div style="display:flex; justify-content:space-between; padding:3px 0; border-bottom:1px solid #334155;">
            <span style="color:#94a3b8;">${escapeHtml(item.category || item.label || 'Custom Question')}</span>
            <span style="color:#38bdf8; font-weight:600; max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeAttr(String(item.value))}">${escapeHtml(String(item.value))}</span>
          </div>
        `).join('');
    }
  } else {
    statusEl.className = "status";
    statusEl.textContent = (d && d.error) || "Autofill completed.";
  }
});

el("#settingsBtn").addEventListener("click", () => chrome.runtime.openOptionsPage());

// ── Overview ─────────────────────────────────────────────────────────────
async function loadStats() {
  const res = await send({ type: "GET_STATS" });
  if (!res.ok) {
    showBanner(res.error);
    return;
  }
  hideBanner();
  const s = res.data.stats || res.data; // tolerate either {status, stats:{...}} or flat shape
  const values = [
    s.total_jobs,
    s.total_contacts,
    s.total_applications,
    s.emails_sent,
  ];
  document.querySelectorAll("#statsGrid .stat-value").forEach((elm, i) => {
    elm.textContent = values[i] ?? "–";
  });
  el("#successRate").textContent =
    typeof s.success_rate === "number" ? `${s.success_rate.toFixed(1)}%` : "–";
}
el("#refreshStats").addEventListener("click", loadStats);

// ── Workday Auto-Apply ────────────────────────────────────────────────────
async function loadWorkdayStatus() {
  const res = await send({ type: "WORKDAY_GET_STATUS" });
  if (!res.ok) {
    showBanner(res.error || "Failed to load Workday status.");
    return;
  }
  hideBanner();
  const data = res.data;
  const config = data.config || {};
  const profile = data.profile || {};
  if (el("#wdEmail") && profile.email) {
    el("#wdEmail").textContent = profile.email;
  }
  if (el("#wdDailyProgress")) {
    el("#wdDailyProgress").textContent = `${config.daily_used ?? 0} / ${config.daily_limit ?? 100}`;
  }
  if (el("#wdAccountsCount")) {
    el("#wdAccountsCount").textContent = `${data.accounts_count ?? 0}`;
  }
}

el("#refreshWdBtn")?.addEventListener("click", loadWorkdayStatus);

el("#launchWdBatchBtn")?.addEventListener("click", async () => {
  const targetCount = parseInt(el("#wdBatchCount").value, 10) || 25;
  const minFitScore = parseFloat(el("#wdMinScore").value) || 60.0;
  const statusEl = el("#wdStatus");
  statusEl.className = "status";
  statusEl.textContent = `Dispatching batch of ${targetCount} jobs via Workday Autopilot...`;
  el("#launchWdBatchBtn").disabled = true;

  const res = await send({
    type: "WORKDAY_BATCH_APPLY",
    targetCount,
    minFitScore,
  });
  el("#launchWdBatchBtn").disabled = false;

  if (!res.ok) {
    statusEl.className = "status err";
    statusEl.textContent = res.error || "Workday batch application failed.";
    return;
  }

  const d = res.data;
  if (d.status === "completed") {
    statusEl.className = "status ok";
    statusEl.textContent = `Dispatched ${d.successful_submissions} Workday applications! Quota: ${d.daily_progress}`;
  } else {
    statusEl.className = "status";
    statusEl.textContent = d.message || "Batch completed.";
  }
  loadWorkdayStatus();
});

// ── NextRaise Auto-Apply ──────────────────────────────────────────────────
async function loadNextRaiseStatus() {
  const res = await send({ type: "NEXTRAISE_GET_STATUS" });
  if (!res.ok) {
    showBanner(res.error || "Failed to load NextRaise status.");
    return;
  }
  hideBanner();
  const data = res.data;
  const q = data.quota || {};
  const acct = data.account || {};
  if (el("#nrEmail") && acct.account_email) {
    el("#nrEmail").textContent = acct.account_email;
  }
  if (el("#nrDailyProgress")) {
    el("#nrDailyProgress").textContent = `${q.daily_used ?? 0} / ${q.daily_limit ?? 300}`;
  }
  if (el("#nrRemaining")) {
    el("#nrRemaining").textContent = `${q.daily_remaining ?? 300}`;
  }
}

el("#refreshNrBtn")?.addEventListener("click", loadNextRaiseStatus);

el("#launchNrBatchBtn")?.addEventListener("click", async () => {
  const targetCount = parseInt(el("#nrBatchCount").value, 10) || 250;
  const minFitScore = parseFloat(el("#nrMinScore").value) || 50.0;
  const statusEl = el("#nrStatus");
  statusEl.className = "status";
  statusEl.textContent = `Dispatching batch of ${targetCount} jobs via NextRaise...`;
  el("#launchNrBatchBtn").disabled = true;

  const res = await send({
    type: "NEXTRAISE_BATCH_APPLY",
    targetCount,
    minFitScore,
  });
  el("#launchNrBatchBtn").disabled = false;

  if (!res.ok) {
    statusEl.className = "status err";
    statusEl.textContent = res.error || "Batch application failed.";
    return;
  }

  const d = res.data;
  if (d.status === "completed") {
    statusEl.className = "status ok";
    statusEl.textContent = `Dispatched ${d.successful_submissions} applications! Quota: ${d.daily_progress}`;
  } else {
    statusEl.className = "status";
    statusEl.textContent = d.message || "Batch completed.";
  }
  loadNextRaiseStatus();
});

// ── Jobs list ────────────────────────────────────────────────────────────
let jobsPage = 1;

async function loadJobs() {
  const listEl = el("#jobsList");
  listEl.innerHTML = "Loading…";
  const res = await send({ type: "GET_JOBS", page: jobsPage, limit: 15 });
  if (!res.ok) {
    listEl.innerHTML = `<div class="empty">${res.error}</div>`;
    return;
  }
  hideBanner();
  const { jobs, pagination } = res.data;
  el("#jobsPageLabel").textContent = `Page ${pagination.page} / ${Math.max(pagination.pages, 1)}`;
  if (!jobs.length) {
    listEl.innerHTML = `<div class="empty">No jobs saved yet.</div>`;
    return;
  }
  listEl.innerHTML = jobs
    .map(
      (j) => `
      <div class="card">
        <div class="title">${escapeHtml(j.title)}</div>
        <div class="meta">${escapeHtml(j.company || "")}${j.location ? " · " + escapeHtml(j.location) : ""}</div>
        <div class="meta">${escapeHtml(j.source)} · ${j.fetched_at ? new Date(j.fetched_at).toLocaleDateString() : ""}</div>
        ${j.url ? `<a href="${escapeAttr(j.url)}" target="_blank">Open posting ↗</a>` : ""}
      </div>`
    )
    .join("");
}
el("#jobsPrev").addEventListener("click", () => {
  if (jobsPage > 1) {
    jobsPage--;
    loadJobs();
  }
});
el("#jobsNext").addEventListener("click", () => {
  jobsPage++;
  loadJobs();
});

// ── Outreach ─────────────────────────────────────────────────────────────
async function loadPending() {
  const listEl = el("#pendingList");
  listEl.innerHTML = "Loading…";
  const minScore = parseInt(el("#minScore").value, 10) || 0;
  const res = await send({ type: "GET_PENDING_OUTREACH", minScore, limit: 15 });
  if (!res.ok) {
    listEl.innerHTML = `<div class="empty">${res.error}</div>`;
    return;
  }
  hideBanner();
  const { jobs } = res.data;
  if (!jobs.length) {
    listEl.innerHTML = `<div class="empty">No scored jobs pending outreach.</div>`;
    return;
  }
  listEl.innerHTML = jobs
    .map(
      (j) => `
      <div class="card" data-job-id="${j.id}" data-company="${escapeAttr(j.company)}">
        <div class="title">${escapeHtml(j.title)}</div>
        <div class="meta">${escapeHtml(j.company || "")}${j.location ? " · " + escapeHtml(j.location) : ""}</div>
        <div class="row-actions">
          <button class="secondary find-contacts">Find contacts</button>
        </div>
        <div class="contacts"></div>
      </div>`
    )
    .join("");

  listEl.querySelectorAll(".find-contacts").forEach((btn) => {
    btn.onclick = async (e) => {
      const card = e.target.closest(".card");
      const company = card.dataset.company;
      const jobId = card.dataset.jobId;
      const contactsEl = card.querySelector(".contacts");
      contactsEl.textContent = "Searching…";
      const res = await send({ type: "FIND_CONTACTS", company });
      if (!res.ok) {
        contactsEl.innerHTML = `<div class="empty">${res.error}</div>`;
        return;
      }
      const contacts = res.data.contacts || [];
      if (!contacts.length) {
        contactsEl.innerHTML = `<div class="empty">No contacts found for ${escapeHtml(company)}.</div>`;
        return;
      }
      contactsEl.innerHTML = contacts
        .map(
          (c, i) => `
          <div class="card" style="margin-top:6px;">
            <div class="title">${escapeHtml(c.name)}</div>
            <div class="meta">${escapeHtml(c.title || "")} · ${escapeHtml(c.email)}</div>
            <div class="row-actions">
              <button class="danger send-btn" data-email="${escapeAttr(c.email)}" data-job-id="${jobId}" data-name="${escapeAttr(c.name)}">Send outreach</button>
            </div>
          </div>`
        )
        .join("");
      contactsEl.querySelectorAll(".send-btn").forEach((sb) => {
        sb.addEventListener("click", () => confirmSend(sb.dataset.jobId, sb.dataset.email, sb.dataset.name));
      });
    };
  });
}
el("#minScore").addEventListener("change", loadPending);

let pendingSend = null;
function confirmSend(jobId, email, name) {
  pendingSend = { job_id: parseInt(jobId, 10), contact_email: email };
  el("#outreachConfirmText").textContent = `Send a personalized outreach email to ${name} (${email})? Your backend will generate and send this via your configured mail account.`;
  el("#outreachConfirm").classList.remove("hidden");
}
el("#outreachCancel").addEventListener("click", () => {
  pendingSend = null;
  el("#outreachConfirm").classList.add("hidden");
});
el("#outreachConfirmBtn").addEventListener("click", async () => {
  if (!pendingSend) return;
  el("#outreachConfirmBtn").disabled = true;
  const res = await send({ type: "SEND_OUTREACH", payload: pendingSend });
  el("#outreachConfirmBtn").disabled = false;
  el("#outreachConfirm").classList.add("hidden");
  pendingSend = null;
  if (res.ok) {
    loadPending();
  } else {
    alert("Send failed: " + res.error);
  }
});

// ── Search / run pipeline ───────────────────────────────────────────────
el("#runQueryBtn").addEventListener("click", async () => {
  const query = el("#searchQuery").value.trim();
  const minScore = parseInt(el("#searchMinScore").value, 10) || 0;
  const statusEl = el("#searchStatus");
  if (!query) {
    statusEl.className = "status err";
    statusEl.textContent = "Enter a search query first.";
    return;
  }
  statusEl.className = "status";
  statusEl.textContent = "Running pipeline — this can take a minute…";
  el("#runQueryBtn").disabled = true;
  const res = await send({ type: "RUN_QUERY", query, minScore });
  el("#runQueryBtn").disabled = false;
  if (!res.ok) {
    statusEl.className = "status err";
    statusEl.textContent = res.error;
    return;
  }
  const stats = res.data.statistics;
  statusEl.className = "status ok";
  statusEl.textContent = `Done — fetched ${stats.jobs_fetched}, processed ${stats.jobs_completed} in ${stats.processing_time_seconds}s.`;
});

function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function escapeAttr(str) {
  return escapeHtml(str);
}

// ── Init ─────────────────────────────────────────────────────────────────
(async function init() {
  const ping = await send({ type: "PING_BACKEND" });
  if (!ping.ok) {
    showBanner(`Can't reach backend — check the URL in ⚙️ Settings and make sure the server is running.`);
  }
  loadStats();
})();
