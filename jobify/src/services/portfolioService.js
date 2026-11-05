import { PORTFOLIO } from "../mocks/portfolio.js";
import { readStore, writeStore, wait } from "../lib/storage.js";

/**
 * PortfolioService contract (local only).
 *   get() / saveDraft(p) / publish(username) / unpublish() / regenerate()
 *   checkUsername(name) -> { available, reason? }
 * Resume parsing and GitHub analysis are NOT implemented: adapters go here later.
 */
const TAKEN = ["admin", "jobify", "demo", "test"];

export const portfolioService = {
  get() {
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
