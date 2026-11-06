import { COMPANIES, FOUNDER_COUNTRIES, FOUNDER_INDUSTRIES, UNLOCK_COST } from "../mocks/founders.js";
import { readStore, writeStore, wait } from "../lib/storage.js";
import { api, isLive } from "../lib/apiClient.js";

/**
 * FounderService contract.
 *   list(query)        -> { items, total, page, pageSize }
 *   facets()           -> { countries, industries, unlockCost }
 *   getState()         -> Promise<{ saved: string[], unlocked: string[] }>
 *   toggleSaved(id)    -> Promise<state>
 *   unlock(id, credits)-> Promise<{ ok, state, cost?, company?, error? }>
 * Live (/app + API): GET /founders, GET /founders/facets, GET /me/founders/state,
 *   PUT /me/founders/:id/saved, POST /founders/:id/unlock. The server charges credits and
 *   only returns founder emails for companies the user has unlocked.
 * /demo or no API: fictional fixtures; no real contact data.
 */
const mock = {
  async list({ q = "", country = "", industry = "", hiringOnly = false, page = 1, pageSize = 10 } = {}) {
    await wait(200);
    const needle = q.trim().toLowerCase();
    const items = COMPANIES.filter((c) => {
      if (country && c.country !== country) return false;
      if (industry && c.industry !== industry) return false;
      if (hiringOnly && !c.hiring) return false;
      if (!needle) return true;
      return `${c.name} ${c.industry} ${c.location} ${c.description} ${c.founders.map((f) => f.name).join(" ")}`.toLowerCase().includes(needle);
    });
    return { items: items.slice((page - 1) * pageSize, page * pageSize), total: items.length, page, pageSize };
  },
  async facets() {
    return { countries: FOUNDER_COUNTRIES, industries: FOUNDER_INDUSTRIES, unlockCost: UNLOCK_COST };
  },
  async getState() {
    return readStore("founders:state", { saved: [], unlocked: [] });
  },
  async toggleSaved(id) {
    const s = await this.getState();
    s.saved = s.saved.includes(id) ? s.saved.filter((x) => x !== id) : [...s.saved, id];
    writeStore("founders:state", s);
    return s;
  },
  async unlock(id, availableCredits) {
    const s = await this.getState();
    if (s.unlocked.includes(id)) return { ok: true, state: s, cost: 0 };
    if (availableCredits < UNLOCK_COST) return { ok: false, state: s, error: "Not enough credits" };
    s.unlocked = [...s.unlocked, id];
    writeStore("founders:state", s);
    return { ok: true, state: s, cost: UNLOCK_COST };
  },
};

const live = {
  list: (query = {}) => api("/founders", { query }),
  facets: () => api("/founders/facets"),
  getState: () => api("/me/founders/state"),
  toggleSaved: (id) => api(`/me/founders/${encodeURIComponent(id)}/saved`, { method: "PUT" }),
  async unlock(id) {
    try {
      return await api(`/founders/${encodeURIComponent(id)}/unlock`, { method: "POST" });
    } catch (e) {
      if (e?.status === 402) return { ok: false, state: await live.getState(), error: "Not enough credits" };
      throw e;
    }
  },
};

const impl = () => (isLive() ? live : mock);

export const founderService = {
  list: (query) => impl().list(query),
  facets: () => impl().facets(),
  getState: () => impl().getState(),
  toggleSaved: (id) => impl().toggleSaved(id),
  unlock: (id, credits) => impl().unlock(id, credits),
};
