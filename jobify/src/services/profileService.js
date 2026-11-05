import { readStore, writeStore } from "../lib/storage.js";
import { api, isLive } from "../lib/apiClient.js";

/**
 * Matching profile: what Match % on Jobs is computed from. Backend: GET/PUT /me/profile.
 *   get()          -> Profile
 *   save(profile)  -> Profile   (server trims, de-duplicates and validates)
 * Profile = { skills: string[], targetRoles: string[], yearsOfExperience: number | null,
 *             locations: string[], complete: boolean }
 */
const EMPTY = { skills: [], targetRoles: [], yearsOfExperience: null, locations: [] };
const withComplete = (p) => ({ ...p, complete: p.skills.length > 0 });

const mock = {
  async get() { return withComplete(readStore("profile", EMPTY)); },
  async save(p) {
    const clean = { ...EMPTY, ...p };
    writeStore("profile", clean);
    return withComplete(clean);
  },
};

const live = {
  get: () => api("/me/profile"),
  save: ({ skills, targetRoles, yearsOfExperience, locations }) =>
    api("/me/profile", { method: "PUT", body: { skills, targetRoles, yearsOfExperience, locations } }),
};

export const profileService = {
  get: () => (isLive() ? live : mock).get(),
  save: (p) => (isLive() ? live : mock).save(p),
};
