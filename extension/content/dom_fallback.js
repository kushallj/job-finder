'use strict';

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === 'DOM_CONNECT') {
    domConnect(msg.note).then(ok => sendResponse({ ok }));
    return true;
  }
  if (msg.type === 'DOM_MESSAGE') {
    domMessage(msg.body).then(ok => sendResponse({ ok }));
    return true;
  }
});

async function domConnect(note) {
  try {
    const connectBtn = [...document.querySelectorAll('button')].find(
      b => b.textContent.trim().toLowerCase() === 'connect'
    );
    if (!connectBtn) return false;
    connectBtn.click();
    return true;
  } catch (e) {
    return false;
  }
}

async function domMessage(body) {
  try {
    const msgBtn = [...document.querySelectorAll('button')].find(
      b => b.textContent.trim().toLowerCase() === 'message'
    );
    if (!msgBtn) return false;
    msgBtn.click();
    return true;
  } catch (e) {
    return false;
  }
}
