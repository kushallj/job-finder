import { COMPANIES, UNLOCK_COST } from "../mocks/founders.js";
import { readStore, writeStore, wait } from "../lib/storage.js";

/**
 * FounderService contract (local only). No scraping, no real contact data.
 *   list(query) -> { items, total, page, pageSize }
 *   getState()  -> { saved: string[], unlocked: string[] }
 *   toggleSaved(id) / unlock(id, credits) -> { ok, state, error? }
 */
export const founderService = {
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
  getState() {
    return readStore("founders:state", { saved: [], unlocked: [] });
  },
  toggleSaved(id) {
    const s = this.getState();
    s.saved = s.saved.includes(id) ? s.saved.filter((x) => x !== id) : [...s.saved, id];
    writeStore("founders:state", s);
    return s;
  },
  unlock(id, availableCredits) {
    const s = this.getState();
    if (s.unlocked.includes(id)) return { ok: true, state: s, cost: 0 };
    if (availableCredits < UNLOCK_COST) return { ok: false, state: s, error: "Not enough credits" };
    s.unlocked = [...s.unlocked, id];
    writeStore("founders:state", s);
    return { ok: true, state: s, cost: UNLOCK_COST };
  },
};
