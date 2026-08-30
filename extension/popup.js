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
    if (btn.dataset.tab === "jobs") loadJobs();
    if (btn.dataset.tab === "outreach") loadPending();
  });
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
