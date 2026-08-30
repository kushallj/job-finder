'use strict';

const port = chrome.runtime.connect({ name: 'JOBFINDER_POPUP' });

const statusPill = document.getElementById('backend-status-pill');
const targetsSummary = document.getElementById('targets-summary');
const noteInput = document.getElementById('note-template');
const charCounter = document.getElementById('char-counter');
const logBox = document.getElementById('log-box');

function appendLog(msg) {
  const line = document.createElement('div');
  line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  logBox.appendChild(line);
  logBox.scrollTop = logBox.scrollHeight;
}

port.onMessage.addListener(msg => {
  if (msg.type === 'LOG') {
    appendLog(msg.message);
  } else if (msg.type === 'BACKEND_STATUS') {
    if (msg.ok) {
      statusPill.className = 'status-pill status-online';
      statusPill.textContent = '● Backend Connected';
    } else {
      statusPill.className = 'status-pill status-offline';
      statusPill.textContent = '○ Backend Offline';
    }
  } else if (msg.type === 'TARGETS_SYNCED') {
    targetsSummary.textContent = `Targeting: ${msg.companies.slice(0, 4).join(', ')} (${msg.companies.length} total)`;
  }
});

port.postMessage({ type: 'CHECK_BACKEND' });

chrome.storage.local.get(['config'], stored => {
  const cfg = stored.config || {};
  const companies = cfg.companies || ['Meta', 'Google', 'Stripe'];
  targetsSummary.textContent = `Targeting: ${companies.slice(0, 4).join(', ')} (${companies.length} total)`;
  noteInput.value = cfg.connectionNote || "Hi {name}, I noticed your work at {company}. I'm applying for {role} and would love to connect for a referral. Thanks!";
  updateCharCount();
});

function updateCharCount() {
  const len = noteInput.value.length;
  charCounter.textContent = `${len} / 200 chars`;
  if (len > 200) {
    charCounter.className = 'char-count over-limit';
  } else {
    charCounter.className = 'char-count';
  }
}

noteInput.addEventListener('input', () => {
  updateCharCount();
  chrome.storage.local.get(['config'], stored => {
    const cfg = stored.config || {};
    cfg.connectionNote = noteInput.value;
    chrome.storage.local.set({ config: cfg });
  });
});

document.getElementById('sync-targets-btn').addEventListener('click', () => {
  port.postMessage({ type: 'SYNC_TARGETS' });
});

document.getElementById('btn-run-all').addEventListener('click', () => {
  port.postMessage({ type: 'START_RUN', stage: 'all' });
});

document.getElementById('btn-discover').addEventListener('click', () => {
  port.postMessage({ type: 'START_RUN', stage: 'discover' });
});

document.getElementById('btn-connect').addEventListener('click', () => {
  port.postMessage({ type: 'START_RUN', stage: 'connect' });
});

document.getElementById('btn-followup').addEventListener('click', () => {
  port.postMessage({ type: 'START_RUN', stage: 'followup' });
});
