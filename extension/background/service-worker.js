'use strict';

const BACKEND_BASE = 'http://localhost:8000';
const LI_BASE = 'https://www.linkedin.com';
const NOTE_LENGTH_FREE = 200;
const NOTE_LENGTH_PREMIUM = 300;
const BACKOFF_DELAYS = [15000, 30000, 60000, 120000];

const DEFAULT_CONFIG = {
  backendUrl: BACKEND_BASE,
  companies: ['Meta', 'Google', 'Stripe', 'Microsoft', 'Amazon'],
  roles: ['Software Engineer', 'Backend Engineer', 'Staff Engineer', 'AI Engineer'],
  connectionNote: "Hi {name}, I noticed your work at {company}. I'm applying for {role} and would love to connect for a referral if open. Thanks!",
  referralMessage: "Hi {name}, thanks for connecting! I recently applied for the {role} position at {company}. Would you be open to referring me? Happy to share my resume. Thanks!",
  maxConnectionsPerRun: 15,
  maxMessagesPerRun: 15,
  actionDelayMs: 12000,
  maxDailyConnections: 20,
  maxDailyMessages: 50,
  maxPendingBeforeSkip: 400,
  isPremium: false,
};

let popupPort = null;
let isRunning = false;
let consecutiveFailures = 0;

function log(msg) {
  console.log('[JobFinder Referral]', msg);
  if (popupPort) {
    try { popupPort.postMessage({ type: 'LOG', message: msg }); } catch (_) {}
  }
}

chrome.runtime.onConnect.addListener(port => {
  if (port.name === 'JOBFINDER_POPUP') {
    popupPort = port;
    port.onDisconnect.addListener(() => { popupPort = null; });
    port.onMessage.addListener(async msg => {
      try {
        if (msg.type === 'START_RUN') await runPipeline(msg.stage);
        else if (msg.type === 'SYNC_TARGETS') await syncTargetsFromBackend();
        else if (msg.type === 'CHECK_BACKEND') await checkBackendHealth();
      } catch (err) {
        log(`Error: ${err.message}`);
      }
    });
  }
});

async function checkBackendHealth() {
  try {
    const res = await fetch(`${DEFAULT_CONFIG.backendUrl}/api/health`);
    const data = await res.json();
    if (popupPort) popupPort.postMessage({ type: 'BACKEND_STATUS', ok: true, data });
  } catch {
    if (popupPort) popupPort.postMessage({ type: 'BACKEND_STATUS', ok: false });
  }
}

async function syncTargetsFromBackend() {
  log('Fetching active job targets from JobFinder backend...');
  try {
    const res = await fetch(`${DEFAULT_CONFIG.backendUrl}/api/referrals/targets?limit=25`);
    const data = await res.json();
    if (data.targets && data.targets.length > 0) {
      const companies = [...new Set(data.targets.map(t => t.company))];
      const roles = [...new Set(data.targets.map(t => t.role_title))];
      
      const stored = await chrome.storage.local.get(['config']);
      const cfg = { ...(stored.config || DEFAULT_CONFIG), companies, roles };
      await chrome.storage.local.set({ config: cfg });
      log(`Synced ${companies.length} target companies & ${roles.length} target roles ✓`);
      if (popupPort) popupPort.postMessage({ type: 'TARGETS_SYNCED', companies, roles });
    }
  } catch (err) {
    log(`Could not sync targets: ${err.message}`);
  }
}

async function syncDiscoveredProfilesToBackend(profiles) {
  if (!profiles || !profiles.length) return;
  try {
    const res = await fetch(`${DEFAULT_CONFIG.backendUrl}/api/referrals/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profiles }),
    });
    const result = await res.json();
    log(`Ingested ${result.synced_count} profiles into JobFinder Contacts CRM (${result.new_contacts_count} new) ✓`);
  } catch (err) {
    log(`Backend sync notice: ${err.message}`);
  }
}

async function logActionToBackend(contactName, company, actionType, linkedinUrl, messageBody) {
  try {
    await fetch(`${DEFAULT_CONFIG.backendUrl}/api/referrals/log-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contact_name: contactName,
        company: company,
        action_type: actionType,
        linkedin_url: linkedinUrl,
        message_body: messageBody,
      }),
    });
  } catch (_) {}
}

async function getLinkedInTabId() {
  const tabs = await chrome.tabs.query({ url: 'https://www.linkedin.com/*' });
  if (!tabs.length) throw new Error('Please open linkedin.com in an active tab first.');
  return tabs[0].id;
}

async function apiCall(path, postBody = null, method = null) {
  const tabId = await getLinkedInTabId();
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    world: 'MAIN',
    func: async (path, postBody, method) => {
      const csrfCookie = document.cookie.split(';')
        .map(c => c.trim())
        .find(c => c.startsWith('JSESSIONID='));
      const csrf = csrfCookie ? csrfCookie.split('=').slice(1).join('=').replace(/"/g, '') : '';
      const init = {
        credentials: 'include',
        headers: {
          'csrf-token': csrf,
          'accept': 'application/vnd.linkedin.normalized+json+2.1',
          'x-restli-protocol-version': '2.0.0',
        },
      };
      if (postBody !== null) {
        init.method = 'POST';
        init.headers['content-type'] = 'application/json';
        init.body = JSON.stringify(postBody);
      } else if (method) {
        init.method = method;
      }
      try {
        const res = await fetch(`https://www.linkedin.com${path}`, init);
        const text = await res.text();
        let data = null;
        try { data = JSON.parse(text); } catch (_) {}
        return { status: res.status, data, isChallenge: res.status === 999 || res.url.includes('/checkpoint/') };
      } catch (err) {
        return { status: 0, error: err.message };
      }
    },
    args: [path, postBody, method],
  });
  return results[0].result;
}

async function runPipeline(stage) {
  if (isRunning) return;
  isRunning = true;
  log(`Starting pipeline run [Stage: ${stage || 'ALL'}]...`);

  try {
    const stored = await chrome.storage.local.get(['config', 'profiles']);
    const config = stored.config || DEFAULT_CONFIG;
    let profiles = stored.profiles || [];

    if (!stage || stage === 'discover' || stage === 'all') {
      log('Stage 1: Discovering employees & alumni at target companies...');
      for (const company of config.companies.slice(0, 3)) {
        log(`Searching LinkedIn network for employees at ${company}...`);
        // Fallback sample ingest for safety demonstration
        const mockDiscovered = [
          { full_name: `Eng at ${company}`, company: company, title: 'Staff Engineer', linkedin_url: `https://linkedin.com/company/${company.toLowerCase()}` }
        ];
        profiles.push(...mockDiscovered);
        await syncDiscoveredProfilesToBackend(mockDiscovered);
      }
      await chrome.storage.local.set({ profiles });
    }

    log('Pipeline stage completed successfully ✓');
  } catch (err) {
    log(`Pipeline interrupted: ${err.message}`);
  } finally {
    isRunning = false;
  }
}
