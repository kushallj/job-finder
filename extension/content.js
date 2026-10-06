// Job Finder Companion — content script
//
// Runs on LinkedIn/Indeed job pages. Extracts the job currently being
// viewed and shows a small floating widget with a "Save to Job Finder"
// button. All backend calls go through background.js via messaging —
// this script never talks to the API directly.

(function () {
  const SITE_EXTRACTORS = {
    "linkedin.com": extractLinkedIn,
    "indeed.com": extractIndeed,
  };

  function currentSite() {
    return Object.keys(SITE_EXTRACTORS).find((s) => location.hostname.includes(s));
  }

  function text(el) {
    return el ? el.textContent.trim().replace(/\s+/g, " ") : "";
  }

  function firstMatch(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && text(el)) return el;
    }
    return null;
  }

  // Selectors are best-effort and intentionally redundant since job sites
  // change their DOM often. Anything not found is left blank and the user
  // can fill it in manually in the widget before saving.
  function extractLinkedIn() {
    const title = firstMatch([
      "h1.job-details-jobs-unified-top-card__job-title",
      "h1.top-card-layout__title",
      ".jobs-unified-top-card__job-title h1",
      "h1",
    ]);
    const company = firstMatch([
      ".job-details-jobs-unified-top-card__company-name a",
      ".job-details-jobs-unified-top-card__company-name",
      ".topcard__org-name-link",
      "a.jobs-unified-top-card__company-name",
    ]);
    const location = firstMatch([
      ".job-details-jobs-unified-top-card__primary-description-container span",
      ".topcard__flavor--bullet",
      ".jobs-unified-top-card__bullet",
    ]);
    const description = firstMatch([
      "#job-details",
      ".jobs-description__content",
      ".jobs-box__html-content",
      ".description__text",
    ]);
    return {
      title: text(title),
      company: text(company),
      location: text(location),
      description: text(description).slice(0, 20000),
    };
  }

  function extractIndeed() {
    const title = firstMatch([
      "h1.jobsearch-JobInfoHeader-title",
      "h1[data-testid='jobsearch-JobInfoHeader-title']",
      "h1",
    ]);
    const company = firstMatch([
      "[data-testid='inlineHeader-companyName']",
      ".jobsearch-InlineCompanyRating div a",
      ".jobsearch-CompanyInfoContainer a",
    ]);
    const location = firstMatch([
      "[data-testid='inlineHeader-companyLocation']",
      ".jobsearch-JobInfoHeader-subtitle > div",
    ]);
    const description = firstMatch(["#jobDescriptionText"]);
    return {
      title: text(title),
      company: text(company),
      location: text(location),
      description: text(description).slice(0, 20000),
    };
  }

  function extractJob() {
    const site = currentSite();
    const raw = site ? SITE_EXTRACTORS[site]() : {};
    return {
      title: raw.title || document.title.split(/[-|]/)[0].trim(),
      company: raw.company || "",
      location: raw.location || "",
      description: raw.description || "",
      url: location.href.split("?")[0],
      source: site || location.hostname,
    };
  }

  function looksLikeJobPage() {
    const site = currentSite();
    if (!site) return false;
    if (site === "linkedin.com") return /\/jobs\/(view|collections)/.test(location.pathname) || /currentJobId=/.test(location.search);
    if (site === "indeed.com") return /viewjob/.test(location.pathname) || /vjk=/.test(location.search);
    return false;
  }

  let widgetHost = null;
  let lastUrl = "";

  function removeWidget() {
    if (widgetHost) {
      widgetHost.remove();
      widgetHost = null;
    }
  }

  function buildWidget(job) {
    removeWidget();

    widgetHost = document.createElement("div");
    widgetHost.id = "jf-companion-host";
    document.body.appendChild(widgetHost);
    const shadow = widgetHost.attachShadow({ mode: "open" });

    const style = document.createElement("style");
    style.textContent = `
      :host { all: initial; }
      .card {
        position: fixed; bottom: 20px; right: 20px; z-index: 2147483647;
        width: 320px; font-family: -apple-system, Segoe UI, Roboto, sans-serif;
        background: #0f172a; border-radius: 14px; box-shadow: 0 12px 40px rgba(0,0,0,.45);
        border: 1px solid #334155; overflow: hidden; color: #f8fafc;
      }
      .header {
        background: linear-gradient(135deg, #1e293b, #0f172a); color: #fff; padding: 12px 14px;
        display: flex; align-items: center; justify-content: space-between;
        font-size: 13px; font-weight: 700; border-bottom: 1px solid #334155;
      }
      .badge {
        background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 10px;
        padding: 2px 7px; border-radius: 9999px; border: 1px solid rgba(16, 185, 129, 0.3); font-weight: 700;
      }
      .close { cursor: pointer; opacity: .7; font-size: 16px; line-height: 1; }
      .close:hover { opacity: 1; }
      .body { padding: 14px; }
      label { font-size: 11px; color: #94a3b8; display: block; margin-top: 8px; font-weight: 600; }
      input {
        width: 100%; box-sizing: border-box; padding: 7px 9px; margin-top: 3px;
        background: #1e293b; border: 1px solid #475569; border-radius: 6px; font-size: 13px; color: #f1f5f9;
      }
      input:focus { outline: none; border-color: #38bdf8; }
      .row { display: flex; gap: 8px; margin-top: 10px; }
      button {
        flex: 1; padding: 8px 10px; border: none; border-radius: 6px;
        font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s;
      }
      .save { background: #2563eb; color: #fff; }
      .save:hover { background: #1d4ed8; }
      .nextraise { background: linear-gradient(135deg, #7c3aed, #a855f7); color: #fff; }
      .nextraise:hover { background: linear-gradient(135deg, #6d28d9, #9333ea); }
      .autofill-btn { background: linear-gradient(135deg, #10b981, #059669); color: #fff; }
      .autofill-btn:hover { background: linear-gradient(135deg, #059669, #047857); }
      .status { font-size: 12px; margin-top: 8px; min-height: 16px; line-height: 1.4; }
      .status.ok { color: #34d399; }
      .status.err { color: #f87171; }
      .status.warn { color: #fbbf24; }
      .checkline { display: flex; align-items: center; gap: 6px; margin-top: 10px; font-size: 11px; color: #94a3b8; }
      .captcha-banner {
        display: none; background: #7c2d12; border: 1px solid #f97316; border-radius: 6px;
        padding: 8px 10px; margin-top: 10px; font-size: 11px; color: #ffedd5; line-height: 1.3;
      }
      .captcha-banner.active { display: block; animation: pulse 2s infinite; }
      .audit-drawer {
        display: none; background: #1e293b; border-radius: 8px; padding: 8px 10px; margin-top: 10px;
        max-height: 110px; overflow-y: auto; font-size: 11px; border: 1px solid #334155;
      }
      .audit-drawer.active { display: block; }
      .audit-item { display: flex; justify-content: space-between; padding: 2px 0; border-bottom: 1px solid #334155; }
      .audit-item span:first-child { color: #94a3b8; }
      .audit-item span:last-child { color: #38bdf8; font-weight: 600; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .learning-drawer {
        display: none; background: #0f172a; border: 1px solid #8b5cf6; border-radius: 8px;
        padding: 8px 10px; margin-top: 10px; font-size: 11px; max-height: 140px; overflow-y: auto;
      }
      .learning-drawer.active { display: block; }
      .learn-item { margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid #1e293b; }
      .learn-item:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
      .learn-btn {
        background: linear-gradient(135deg, #7c3aed, #a855f7); color: #fff;
        border: none; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: 700;
        cursor: pointer; margin-top: 4px; width: 100%; transition: all 0.2s;
      }
      .learn-btn:hover { background: linear-gradient(135deg, #6d28d9, #9333ea); }
      .learn-btn.saved { background: #059669; cursor: default; }
      @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.8; } }
    `;
    shadow.appendChild(style);

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="header">
        <div style="display:flex; align-items:center; gap:6px;">
          <span>🤖 Job Co-Pilot</span>
          <span class="badge">PRO</span>
        </div>
        <span class="close" title="Dismiss">✕</span>
      </div>
      <div class="body">
        <label>Job Title</label>
        <input class="f-title" />
        <label>Company</label>
        <input class="f-company" />
        <label>Location</label>
        <input class="f-location" />
        <div class="checkline">
          <input type="checkbox" class="f-score" id="jf-score-cb" />
          <label for="jf-score-cb" style="margin:0;">Score against candidate profile</label>
        </div>
        <div class="row">
          <button class="save">Save Job</button>
          <button class="nextraise" title="1-click apply via NextRaise">🚀 NextRaise</button>
        </div>
        <div class="row" style="margin-top:6px;">
          <button class="autofill-btn" title="Fill form with React event dispatch &amp; Answer Bank">⚡ Co-Pilot Autofill</button>
        </div>
        <div class="captcha-banner" id="captchaBanner">
          ⚠️ <strong>Verification Detected</strong>: Please solve the CAPTCHA challenge on the page. All other fields were filled automatically!
        </div>
        <div class="status" id="coPilotStatus"></div>
        <div class="audit-drawer" id="auditDrawer"></div>
        <div class="learning-drawer" id="learningDrawer"></div>
      </div>
    `;
    shadow.appendChild(card);

    const $ = (sel) => shadow.querySelector(sel);
    $(".f-title").value = job.title;
    $(".f-company").value = job.company;
    $(".f-location").value = job.location;
    $(".close").addEventListener("click", removeWidget);

    $(".autofill-btn").addEventListener("click", async () => {
      const statusEl = $("#coPilotStatus");
      const captchaEl = $("#captchaBanner");
      const auditDrawer = $("#auditDrawer");

      statusEl.className = "status";
      statusEl.textContent = "Co-Pilot analyzing DOM & querying Answer Bank…";
      captchaEl.classList.remove("active");
      auditDrawer.classList.remove("active");
      auditDrawer.innerHTML = "";
      $(".autofill-btn").disabled = true;

      chrome.runtime.sendMessage({ type: "WORKDAY_GET_PROFILE" }, async (profRes) => {
        $(".autofill-btn").disabled = false;
        const profile = profRes && profRes.ok ? profRes.data : {};
        if (window.FormEngine && typeof window.FormEngine.autofillForm === "function") {
          const resolver = async (questionText, category) => {
            return new Promise((resolve) => {
              chrome.runtime.sendMessage(
                {
                  type: "RESOLVE_QUESTION",
                  question: questionText,
                  job_title: job.title || "Software Engineer",
                  company: job.company || "Company",
                  job_description: job.description || "",
                  category: category,
                },
                (response) => {
                  if (response && response.ok && response.data) {
                    resolve(response.data.answer);
                  } else {
                    resolve(null);
                  }
                }
              );
            });
          };

          const res = await window.FormEngine.autofillForm(document, profile, resolver);
          
          // Check for CAPTCHA
          if (res.captcha && res.captcha.detected) {
            captchaEl.classList.add("active");
            captchaEl.innerHTML = `⚠️ <strong>${res.captcha.type} Detected</strong>: Please solve verification on the page. All other fields filled!`;
          }

          // Build audit preview drawer
          if (res.details && res.details.length > 0) {
            auditDrawer.classList.add("active");
            auditDrawer.innerHTML = `<div style="font-weight:700; color:#38bdf8; margin-bottom:4px;">Ghost Fill Summary (${res.filled_count} fields):</div>` +
              res.details.slice(0, 8).map(d => `
                <div class="audit-item">
                  <span>${d.category || 'Custom Question'}</span>
                  <span title="${escapeAttr(String(d.value))}">${escapeHtml(String(d.value).slice(0, 22))}</span>
                </div>
              `).join('');
          }

          statusEl.className = "status ok";
          statusEl.textContent = `Ghost Fill Complete: ${res.filled_count} fields populated cleanly ✓`;
          refreshLearningLoop();
        } else {
          statusEl.className = "status err";
          statusEl.textContent = "FormEngine script initializing…";
        }
      });
    });

    function refreshLearningLoop() {
      const learningDrawer = $("#learningDrawer");
      if (!learningDrawer) return;
      if (!window.FormEngine || typeof window.FormEngine.getEditedFields !== "function") return;
      const edits = window.FormEngine.getEditedFields(document);
      if (!edits || edits.length === 0) {
        learningDrawer.classList.remove("active");
        learningDrawer.innerHTML = "";
        return;
      }

      learningDrawer.classList.add("active");
      const bulkButtonHtml = edits.length >= 2 ? `
        <button class="learn-btn bulk-save-btn" style="background:linear-gradient(135deg, #10b981, #059669); margin-bottom:8px;">
          💾 Save All Corrections (${edits.length})
        </button>
      ` : '';

      learningDrawer.innerHTML = `<div style="font-weight:700; color:#c084fc; margin-bottom:6px;">💡 Learned Corrections (${edits.length}):</div>` +
        bulkButtonHtml +
        edits.map((item, idx) => `
          <div class="learn-item">
            <div style="color:#94a3b8; font-size:10px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeAttr(item.question || item.category)}">${escapeHtml(item.question || item.category)}</div>
            <div style="color:#38bdf8; font-weight:700; margin-top:2px;">➔ ${escapeHtml(item.currentValue)}</div>
            <button class="learn-btn" data-idx="${idx}">💾 Save to Answer Bank</button>
          </div>
        `).join("");

      const bulkBtn = learningDrawer.querySelector(".bulk-save-btn");
      if (bulkBtn) {
        bulkBtn.addEventListener("click", () => {
          bulkBtn.disabled = true;
          bulkBtn.textContent = "Saving all corrections…";
          chrome.runtime.sendMessage(
            {
              type: "SAVE_ANSWERS_BATCH",
              answers: edits.map(e => ({
                question: e.question,
                answer: e.currentValue,
                category: e.category,
                source: "user_edited",
              })),
            },
            (batchRes) => {
              if (batchRes && batchRes.ok) {
                bulkBtn.textContent = "✓ All Corrections Saved!";
                edits.forEach(e => {
                  try { e.element.dataset.jfOriginalValue = e.currentValue; } catch (_) {}
                });
                setTimeout(refreshLearningLoop, 1500);
              } else {
                bulkBtn.disabled = false;
                bulkBtn.textContent = "Retry Bulk Save";
              }
            }
          );
        });
      }

      learningDrawer.querySelectorAll(".learn-btn:not(.bulk-save-btn)").forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = parseInt(btn.dataset.idx, 10);
          const editItem = edits[idx];
          if (!editItem) return;

          btn.disabled = true;
          btn.textContent = "Saving to Answer Bank…";

          chrome.runtime.sendMessage(
            {
              type: "SAVE_ANSWER",
              question: editItem.question,
              answer: editItem.currentValue,
              category: editItem.category,
              source: "user_edited",
            },
            (response) => {
              if (response && response.ok) {
                btn.textContent = "✓ Saved & Remembered!";
                btn.className = "learn-btn saved";
                try {
                  editItem.element.dataset.jfOriginalValue = editItem.currentValue;
                } catch (_) {}
                setTimeout(refreshLearningLoop, 1500);
              } else {
                btn.disabled = false;
                btn.textContent = "Retry Save";
              }
            }
          );
        });
      });
    }

    let activePillEl = null;
    function showFloatingFieldPill(inputEl) {
      if (!inputEl || !inputEl.dataset || inputEl.dataset.jfAutofilled !== "true") return;
      const currentVal = inputEl.type === "checkbox" ? String(inputEl.checked) : String(inputEl.value || "").trim();
      const origVal = (inputEl.dataset.jfOriginalValue || "").trim();
      if (!currentVal || currentVal === origVal) {
        if (activePillEl) {
          activePillEl.remove();
          activePillEl = null;
        }
        return;
      }

      if (activePillEl) activePillEl.remove();

      const rect = inputEl.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) return;

      const pill = document.createElement("div");
      pill.id = "jf-floating-learning-pill";
      pill.style.cssText = `
        position: absolute;
        top: ${window.scrollY + rect.bottom + 4}px;
        left: ${window.scrollX + rect.left}px;
        z-index: 2147483646;
        background: #0f172a;
        color: #f8fafc;
        border: 1px solid #8b5cf6;
        border-radius: 6px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        font-family: -apple-system, Segoe UI, Roboto, sans-serif;
        font-size: 11px;
        padding: 5px 9px;
        display: flex;
        align-items: center;
        gap: 6px;
      `;

      const qText = inputEl.dataset.jfQuestion || (window.FormEngine ? window.FormEngine.findAssociatedLabel(inputEl) : "Field");
      const cat = inputEl.dataset.jfCategory || "";

      pill.innerHTML = `
        <span style="color:#c084fc; font-weight:600;">💡 Save to Bank?</span>
        <button style="background:#7c3aed; color:#fff; border:none; border-radius:4px; padding:3px 8px; font-size:10px; font-weight:700; cursor:pointer;">Save</button>
        <span style="cursor:pointer; opacity:0.6; font-size:12px; margin-left:2px;" title="Dismiss">✕</span>
      `;

      document.body.appendChild(pill);
      activePillEl = pill;

      const saveBtn = pill.querySelector("button");
      const closeBtn = pill.querySelector("span:last-child");

      saveBtn.addEventListener("click", () => {
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving…";
        chrome.runtime.sendMessage(
          {
            type: "SAVE_ANSWER",
            question: qText,
            answer: currentVal,
            category: cat,
            source: "user_edited",
          },
          (res) => {
            if (res && res.ok) {
              pill.innerHTML = `<span style="color:#34d399; font-weight:700;">✓ Learned into Answer Bank!</span>`;
              inputEl.dataset.jfOriginalValue = currentVal;
              setTimeout(() => {
                if (activePillEl === pill) {
                  pill.remove();
                  activePillEl = null;
                }
                refreshLearningLoop();
              }, 1200);
            } else {
              saveBtn.disabled = false;
              saveBtn.textContent = "Retry";
            }
          }
        );
      });

      closeBtn.addEventListener("click", () => {
        pill.remove();
        if (activePillEl === pill) activePillEl = null;
      });
    }

    const onUserFormEdit = (e) => {
      if (e.target && e.target.dataset && e.target.dataset.jfAutofilled === "true") {
        refreshLearningLoop();
        showFloatingFieldPill(e.target);
      }
    };
    document.addEventListener("input", onUserFormEdit, true);
    document.addEventListener("change", onUserFormEdit, true);
    document.addEventListener("focusin", (e) => {
      if (e.target && e.target.dataset && e.target.dataset.jfAutofilled === "true") {
        showFloatingFieldPill(e.target);
      }
    }, true);

    $(".save").addEventListener("click", () => {
      const statusEl = $("#coPilotStatus");
      statusEl.className = "status";
      statusEl.textContent = "Saving…";
      $(".save").disabled = true;

      const payload = {
        title: $(".f-title").value.trim(),
        company: $(".f-company").value.trim(),
        location: $(".f-location").value.trim(),
        description: job.description,
        url: job.url,
        source: job.source,
        score: $(".f-score").checked,
      };

      chrome.runtime.sendMessage({ type: "CAPTURE_JOB", payload }, (res) => {
        $(".save").disabled = false;
        if (!res || !res.ok) {
          statusEl.className = "status err";
          statusEl.textContent = (res && res.error) || "Save failed.";
          return;
        }
        const d = res.data;
        let msg = d.already_existed ? "Already saved." : "Saved ✓";
        if (typeof d.match_score === "number") {
          msg += ` — match score: ${Math.round(d.match_score)}/100`;
        } else if (d.score_error) {
          msg += ` (scoring failed: ${d.score_error})`;
        }
        statusEl.className = "status ok";
        statusEl.textContent = msg;
      });
    });

    $(".nextraise").addEventListener("click", () => {
      const statusEl = $(".status");
      statusEl.className = "status";
      statusEl.textContent = "Applying via NextRaise (canaby007@gmail.com)…";
      $(".nextraise").disabled = true;

      const payload = {
        title: $(".f-title").value.trim(),
        company: $(".f-company").value.trim(),
        location: $(".f-location").value.trim(),
        description: job.description,
        url: job.url,
        source: job.source,
        score: true,
      };

      // 1. Capture job
      chrome.runtime.sendMessage({ type: "CAPTURE_JOB", payload }, (captureRes) => {
        if (!captureRes || !captureRes.ok || !captureRes.data || !captureRes.data.job_id) {
          $(".nextraise").disabled = false;
          statusEl.className = "status err";
          statusEl.textContent = (captureRes && captureRes.error) || "Job capture failed.";
          return;
        }

        const jobId = captureRes.data.job_id;
        // 2. Dispatch NextRaise auto-apply
        chrome.runtime.sendMessage({ type: "NEXTRAISE_APPLY_JOB", jobId }, (nrRes) => {
          $(".nextraise").disabled = false;
          if (!nrRes || !nrRes.ok) {
            statusEl.className = "status err";
            statusEl.textContent = (nrRes && nrRes.error) || "NextRaise dispatch failed.";
            return;
          }
          const nrData = nrRes.data;
          statusEl.className = "status ok";
          statusEl.textContent = `Applied ✓ Receipt: ${nrData.receipt_id || "NR-SUCCESS"}`;
        });
      });
    });
  }

  function tryShowWidget() {
    if (!looksLikeJobPage()) {
      removeWidget();
      return;
    }
    const job = extractJob();
    if (!job.title) {
      removeWidget();
      return;
    }
    buildWidget(job);
  }

  // LinkedIn/Indeed are SPAs — the URL changes without a full page load
  // when the user clicks between job listings, so poll for URL changes
  // instead of relying on a single page-load event.
  function watchForNavigation() {
    setInterval(() => {
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        setTimeout(tryShowWidget, 800); // let the SPA render the new job
      }
    }, 1000);
  }

  tryShowWidget();
  watchForNavigation();
})();
