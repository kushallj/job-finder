'use strict';

(function () {
  const BACKEND_URL = 'http://localhost:8000';

  function extractJobDetails() {
    const href = window.location.href;
    let title = '', company = '', location = '', description = '', source = 'linkedin';

    if (href.includes('linkedin.com')) {
      source = 'linkedin';
      title = document.querySelector('.job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title, h1')?.textContent?.trim() || '';
      company = document.querySelector('.job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name, a.ember-view[href*="/company/"]')?.textContent?.trim() || '';
      location = document.querySelector('.job-details-jobs-unified-top-card__bullet, .jobs-unified-top-card__bullet')?.textContent?.trim() || 'Remote';
      description = document.querySelector('#job-details, .jobs-description__content')?.textContent?.trim() || '';
    } else if (href.includes('indeed.com')) {
      source = 'indeed';
      title = document.querySelector('h1.jobsearch-JobInfoHeader-title, [data-testid="simpler-jobTitle"]')?.textContent?.trim() || '';
      company = document.querySelector('[data-testid="inlineHeader-companyName"] a, [data-company-name="true"]')?.textContent?.trim() || '';
      location = document.querySelector('[data-testid="inlineHeader-companyLocation"]')?.textContent?.trim() || 'Remote';
      description = document.querySelector('#jobDescriptionText')?.textContent?.trim() || '';
    }

    return { title, company, location, description, url: href.split('?')[0], source };
  }

  function injectFloatingWidget() {
    if (document.getElementById('jobfinder-capture-card')) return;

    const details = extractJobDetails();
    if (!details.title && !details.company) return;

    const container = document.createElement('div');
    container.id = 'jobfinder-capture-card';
    container.innerHTML = `
      <div class="jf-header">
        <div class="jf-title">⚡ JobFinder Capture</div>
        <button id="jf-close-btn" class="jf-close">✕</button>
      </div>
      <div class="jf-body">
        <div class="jf-role"><strong>${details.title || 'Job Posting'}</strong></div>
        <div class="jf-company">${details.company || 'Unknown Company'}</div>
        <div id="jf-score-badge" class="jf-score-badge" style="display:none;"></div>
        <button id="jf-save-btn" class="jf-save-btn">💾 Save & Score Job</button>
        <div id="jf-status" class="jf-status"></div>
      </div>
    `;

    document.body.appendChild(container);

    document.getElementById('jf-close-btn').addEventListener('click', () => {
      container.remove();
    });

    document.getElementById('jf-save-btn').addEventListener('click', async () => {
      const btn = document.getElementById('jf-save-btn');
      const status = document.getElementById('jf-status');
      const badge = document.getElementById('jf-score-badge');

      btn.disabled = true;
      btn.textContent = 'Saving & Scoring...';

      try {
        const payload = {
          title: details.title || 'Untitled Role',
          company: details.company || 'Unknown Company',
          location: details.location,
          description: details.description,
          url: details.url,
          source: details.source,
          score: true,
        };

        const res = await fetch(`${BACKEND_URL}/api/jobs/capture`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const data = await res.json();
        if (res.ok) {
          status.textContent = data.already_existed ? 'Job updated in database ✓' : 'Job captured into CRM ✓';
          if (data.match_score !== null && data.match_score !== undefined) {
            badge.style.display = 'block';
            badge.textContent = `🎯 Match Score: ${Math.round(data.match_score)}%`;
          }
          btn.textContent = 'Saved ✓';
        } else {
          status.textContent = `Error: ${data.message || 'Capture failed'}`;
          btn.disabled = false;
          btn.textContent = 'Retry Save';
        }
      } catch (err) {
        status.textContent = `Backend offline (${err.message})`;
        btn.disabled = false;
        btn.textContent = 'Retry Save';
      }
    });
  }

  // Initial check and observation for single-page navigations
  setTimeout(injectFloatingWidget, 1500);
  let lastUrl = location.href;
  new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
      lastUrl = url;
      setTimeout(injectFloatingWidget, 1500);
    }
  }).observe(document, { subtree: true, childList: true });
})();
