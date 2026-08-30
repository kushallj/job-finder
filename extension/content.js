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
        width: 300px; font-family: -apple-system, Segoe UI, Roboto, sans-serif;
        background: #fff; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,.2);
        border: 1px solid #e2e2e2; overflow: hidden; color: #1a1a1a;
      }
      .header {
        background: #14213d; color: #fff; padding: 10px 12px;
        display: flex; align-items: center; justify-content: space-between;
        font-size: 13px; font-weight: 600;
      }
      .close { cursor: pointer; opacity: .8; font-size: 16px; line-height: 1; }
      .close:hover { opacity: 1; }
      .body { padding: 12px; }
      label { font-size: 11px; color: #666; display: block; margin-top: 8px; }
      input {
        width: 100%; box-sizing: border-box; padding: 6px 8px; margin-top: 2px;
        border: 1px solid #ddd; border-radius: 6px; font-size: 13px;
      }
      .row { display: flex; gap: 8px; margin-top: 12px; }
      button {
        flex: 1; padding: 8px 10px; border: none; border-radius: 6px;
        font-size: 13px; font-weight: 600; cursor: pointer;
      }
      .save { background: #2563eb; color: #fff; }
      .save:hover { background: #1d4ed8; }
      .score { background: #eef2ff; color: #2563eb; }
      .status { font-size: 12px; margin-top: 8px; min-height: 16px; }
      .status.ok { color: #15803d; }
      .status.err { color: #b91c1c; }
      .checkline { display: flex; align-items: center; gap: 6px; margin-top: 10px; font-size: 12px; color: #444; }
    `;
    shadow.appendChild(style);

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="header">
        <span>💾 Job Finder</span>
        <span class="close" title="Dismiss">✕</span>
      </div>
      <div class="body">
        <label>Title</label>
        <input class="f-title" />
        <label>Company</label>
        <input class="f-company" />
        <label>Location</label>
        <input class="f-location" />
        <div class="checkline">
          <input type="checkbox" class="f-score" id="jf-score-cb" />
          <label for="jf-score-cb" style="margin:0;">Score against my resume</label>
        </div>
        <div class="row">
          <button class="save">Save job</button>
        </div>
        <div class="status"></div>
      </div>
    `;
    shadow.appendChild(card);

    const $ = (sel) => shadow.querySelector(sel);
    $(".f-title").value = job.title;
    $(".f-company").value = job.company;
    $(".f-location").value = job.location;
    $(".close").addEventListener("click", removeWidget);

    $(".save").addEventListener("click", () => {
      const statusEl = $(".status");
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
