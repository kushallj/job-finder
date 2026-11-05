import { JOBS } from "../mocks/jobs.js";
import { readStore, writeStore, wait } from "../lib/storage.js";

/**
 * JobService contract. Local implementation; swap for an API-backed one later.
 *   list(query)      -> { items, total, page, pageSize }
 *   get(id)          -> Job | null
 *   getUserState()   -> { saved: string[], applied: string[] }
 *   toggleSaved(id)  -> string[]
 *   markApplied(id)  -> string[]
 */
const parseSalary = (s) => {
  const m = s.match(/([₹$£])([\d.]+)([LK])/);
  if (!m) return 0;
  const v = Number(m[2]) * (m[3] === "L" ? 100000 : 1000);
  return m[1] === "₹" ? v / 83 : m[1] === "£" ? v * 1.25 : v;
};
const minYears = (s) => Number((s.match(/\d+/) || [0])[0]);

export const jobService = {
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
  getUserState() {
    return readStore("jobs:state", { saved: [], applied: [] });
  },
  toggleSaved(id) {
    const s = this.getUserState();
    s.saved = s.saved.includes(id) ? s.saved.filter((x) => x !== id) : [...s.saved, id];
    writeStore("jobs:state", s);
    return s;
  },
  markApplied(id) {
    const s = this.getUserState();
    if (!s.applied.includes(id)) s.applied = [...s.applied, id];
    writeStore("jobs:state", s);
    return s;
  },
};
