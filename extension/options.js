const DEFAULT_URL = "http://localhost:8000";

const input = document.getElementById("apiUrl");
const status = document.getElementById("status");

async function load() {
  const { apiBaseUrl } = await chrome.storage.sync.get("apiBaseUrl");
  input.value = apiBaseUrl || DEFAULT_URL;
}

document.getElementById("saveBtn").addEventListener("click", async () => {
  let url;
  try {
    url = new URL(input.value.trim());
  } catch {
    status.className = "status err";
    status.textContent = "That doesn't look like a valid URL.";
    return;
  }

  const origin = url.origin + "/*";
  const isLocal = ["localhost", "127.0.0.1"].includes(url.hostname);

  if (!isLocal) {
    const granted = await chrome.permissions.request({ origins: [origin] });
    if (!granted) {
      status.className = "status err";
      status.textContent = "Permission denied — the extension can't reach that host without it.";
      return;
    }
  }

  await chrome.storage.sync.set({ apiBaseUrl: url.origin });
  status.className = "status ok";
  status.textContent = "Saved.";
});

load();
