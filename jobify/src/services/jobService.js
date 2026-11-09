import { JOBS } from "../mocks/jobs.js";
import { readStore, writeStore, wait } from "../lib/storage.js";
import { api, isLive } from "../lib/apiClient.js";

/**
 * JobService contract. Backend: GET /jobs, GET /jobs/:id, GET /me/jobs/state,
 * PUT /me/jobs/:id/saved, POST /me/jobs/:id/applied. Mock fixtures in /demo or without an API.
 *   list(query)      -> { items, total, page, pageSize }
 *   get(id)          -> Job | null
 *   getUserState()   -> Promise<{ saved: string[], applied: string[] }>
 *   toggleSaved(id)  -> Promise<{ saved, applied }>
 *   markApplied(id)  -> Promise<{ saved, applied }>  (records only; nothing is sent to the employer)
 */
const parseSalary = (s) => {
  const m = s.match(/([₹$£])([\d.]+)([LK])/);
  if (!m) return 0;
  const v = Number(m[2]) * (m[3] === "L" ? 100000 : 1000);
  return m[1] === "₹" ? v / 83 : m[1] === "£" ? v * 1.25 : v;
};
const minYears = (s) => Number((s.match(/\d+/) || [0])[0]);

const mock = {
  async list({ q = "", workModes = [], types = [], countries = [], skills = [], matchOnly = false, minSalaryUsd = 0, maxYears = null, sort = "match", page = 1, pageSize = 20 } = {}) {
    await wait(250);
    const needle = q.trim().toLowerCase();
    let items = JOBS.filter((j) => {
      if (needle && !`${j.title} ${j.company} ${j.location} ${j.skills.join(" ")}`.toLowerCase().includes(needle)) return false;
      if (workModes.length && !workModes.includes(j.workMode)) return false;
      if (types.length && !types.includes(j.type)) return false;
      if (countries.length && !countries.includes(j.country)) return false;
      if (skills.length && !skills.every((s) => j.skills.includes(s))) return false;
      if (matchOnly && j.match < 80) return false;
      if (minSalaryUsd && parseSalary(j.salary) < minSalaryUsd) return false;
      if (maxYears !== null && minYears(j.experience) > maxYears) return false;
      return true;
    });
    const sorters = {
      match: (a, b) => b.match - a.match,
      recent: (a, b) => a.postedDaysAgo - b.postedDaysAgo,
      salary: (a, b) => parseSalary(b.salary) - parseSalary(a.salary),
      title: (a, b) => a.title.localeCompare(b.title),
    };
    items = [...items].sort(sorters[sort] || sorters.match);
    const total = items.length;
    return { items: items.slice((page - 1) * pageSize, page * pageSize), total, page, pageSize };
  },
  async get(id) {
    await wait(120);
    return JOBS.find((j) => j.id === id) || null;
  },
  async getUserState() {
    return readStore("jobs:state", { saved: [], applied: [] });
  },
  async toggleSaved(id) {
    const s = await this.getUserState();
    s.saved = s.saved.includes(id) ? s.saved.filter((x) => x !== id) : [...s.saved, id];
    writeStore("jobs:state", s);
    return s;
  },
  async markApplied(id) {
    const s = await this.getUserState();
    if (!s.applied.includes(id)) s.applied = [...s.applied, id];
    writeStore("jobs:state", s);
    return s;
  },
};

const live = {
  list: (query = {}) => api("/jobs", { query }),
  get: (id) => api(`/jobs/${encodeURIComponent(id)}`).catch((e) => (e.status === 404 ? null : Promise.reject(e))),
  getUserState: () => api("/me/jobs/state"),
  toggleSaved: (id) => api(`/me/jobs/${encodeURIComponent(id)}/saved`, { method: "PUT" }),
  markApplied: (id) => api(`/me/jobs/${encodeURIComponent(id)}/applied`, { method: "POST" }),
};

const impl = () => (isLive() ? live : mock);

export const jobService = {
  list: (query) => impl().list(query),
  get: (id) => impl().get(id),
  getUserState: () => impl().getUserState(),
  toggleSaved: (id) => impl().toggleSaved(id),
  markApplied: (id) => impl().markApplied(id),
};
