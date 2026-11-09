import { PORTFOLIO } from "../mocks/portfolio.js";
import { readStore, writeStore, wait } from "../lib/storage.js";
import { api, isLive } from "../lib/apiClient.js";

/**
 * PortfolioService contract (all methods return Promises).
 *   get() / saveDraft(p) / publish(p, username) / unpublish(p) / regenerate(p)
 *   checkUsername(name) -> { available, reason? }
 *   isLive() -> true when backed by the API (UI drops the "demo/simulated" copy)
 * Live (/app + API): GET/PUT /portfolio, POST/DELETE /portfolio/publish,
 *   GET /portfolio/username-available?name=, POST /portfolio/regenerate.
 *   The server owns status, username and sources; publishing snapshots the draft, and
 *   GET /portfolio/:username (public) serves only that snapshot.
 *   Regenerate fills empty fields from the saved matching profile; it never overwrites edits.
 * /demo or no API: local fixtures; nothing is hosted.
 */
const TAKEN = ["admin", "jobify", "demo", "test"];

const mock = {
  async get() {
    return readStore("portfolio", PORTFOLIO);
  },
  async saveDraft(p) {
    await wait(300);
    writeStore("portfolio", p);
    return p;
  },
  async checkUsername(name) {
    await wait(200);
    if (!/^[a-z0-9-]{3,24}$/.test(name)) return { available: false, reason: "Use 3 to 24 lowercase letters, numbers or hyphens" };
    if (TAKEN.includes(name)) return { available: false, reason: "That username is taken" };
    return { available: true };
  },
  async publish(p, username) {
    await wait(700);
    const next = { ...p, status: "published", username };
    writeStore("portfolio", next);
    return next;
  },
  async unpublish(p) {
    await wait(300);
    const next = { ...p, status: "draft" };
    writeStore("portfolio", next);
    return next;
  },
  async regenerate(p, { fail = false } = {}) {
    await wait(1600);
    if (fail) throw new Error("Simulated regeneration failure");
    const next = { ...p, sources: { ...p.sources, snapshot: new Date().toISOString() } };
    writeStore("portfolio", next);
    return next;
  },
};

const live = {
  get: () => api("/portfolio"),
  saveDraft: (p) => api("/portfolio", { method: "PUT", body: p }),
  checkUsername: (name) => api("/portfolio/username-available", { query: { name } }),
  // Save first so the snapshot includes edits still waiting on the autosave debounce.
  async publish(p, username) {
    await live.saveDraft(p);
    return api("/portfolio/publish", { method: "POST", body: { username } });
  },
  // Save first: the response replaces page state, so pending edits would otherwise be lost.
  async unpublish(p) {
    await live.saveDraft(p);
    return api("/portfolio/publish", { method: "DELETE" });
  },
  async regenerate(p) {
    await live.saveDraft(p);
    return api("/portfolio/regenerate", { method: "POST" });
  },
};

const impl = () => (isLive() ? live : mock);

export const portfolioService = {
  isLive: () => isLive(),
  get: () => impl().get(),
  saveDraft: (p) => impl().saveDraft(p),
  checkUsername: (name) => impl().checkUsername(name),
  publish: (p, username) => impl().publish(p, username),
  unpublish: (p) => impl().unpublish(p),
  regenerate: (p, opts) => impl().regenerate(p, opts),
};
