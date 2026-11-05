import { APPLICATIONS } from "../mocks/applications.js";
import { readStore, writeStore, wait, uid } from "../lib/storage.js";
import { api, isLive } from "../lib/apiClient.js";

/**
 * ApplicationService contract.
 *   list() / create(app) / update(id, patch) / remove(id)
 *     Live (/app + API): GET/POST /applications, PATCH/DELETE /applications/:id.
 *     /demo or no API: localStorage fixtures.
 *   getConnection() / connect() / sync() / disconnect()   (all async)
 *     Live: GET /gmail, POST /gmail/connect -> redirect to Google (read-only consent),
 *     POST /gmail/sync -> { ...state, result: { scanned, stored, advanced } }, DELETE /gmail.
 *     /demo or no API: SIMULATED; no inbox is accessed.
 *
 * Connection states: not_connected | pending | connected | syncing | failed | disconnected
 */
const load = () => readStore("applications", APPLICATIONS);
const save = (v) => writeStore("applications", v);

const live = {
  list: () => api("/applications").then((r) => r.items),
  create: (data) => api("/applications", { method: "POST", body: data }),
  update: (id, patch) => api(`/applications/${encodeURIComponent(id)}`, { method: "PATCH", body: patch }),
  remove: (id) => api(`/applications/${encodeURIComponent(id)}`, { method: "DELETE" }),
  getConnection: () => api("/gmail"),
  connect: async () => {
    const { url } = await api("/gmail/connect", { method: "POST" });
    window.location.assign(url); // Google consent; returns to /app/applications?gmail=...
    return { status: "pending", email: null, lastSync: null, nextScan: null };
  },
  sync: () => api("/gmail/sync", { method: "POST", timeout: 60000 }),
  disconnect: () => api("/gmail", { method: "DELETE" }),
};

export const applicationService = {
  async list() {
    if (isLive()) return live.list();
    await wait(250);
    return load();
  },
  async create(data) {
    if (isLive()) return live.create(data);
    await wait(150);
    const app = { id: uid("app"), stage: "applied", messages: 1, notes: "", events: [], offer: null, subject: "Added manually", sender: "", date: new Date().toISOString(), source: "manual", ...data };
    save([app, ...load()]);
    return app;
  },
  async update(id, patch) {
    if (isLive()) return live.update(id, patch);
    await wait(100);
    const next = load().map((a) => (a.id === id ? { ...a, ...patch } : a));
    save(next);
    return next.find((a) => a.id === id);
  },
  async remove(id) {
    if (isLive()) return live.remove(id);
    await wait(100);
    save(load().filter((a) => a.id !== id));
  },
  async getConnection() {
    if (isLive()) return live.getConnection();
    return readStore("gmail", { status: "not_connected", email: null, lastSync: null, nextScan: null, simulated: true });
  },
  async connect(email) {
    if (isLive()) return live.connect();
    writeStore("gmail", { status: "pending", email, lastSync: null, nextScan: null, simulated: true });
    await wait(900);
    const c = { status: "connected", email, lastSync: new Date().toISOString(), nextScan: new Date(Date.now() + 864e5).toISOString(), simulated: true };
    writeStore("gmail", c);
    return c;
  },
  async sync({ fail = false } = {}) {
    if (isLive()) return live.sync();
    const c = await this.getConnection();
    writeStore("gmail", { ...c, status: "syncing" });
    await wait(1200);
    if (fail) {
      writeStore("gmail", { ...c, status: "failed" });
      throw new Error("Simulated sync failure");
    }
    const done = { ...c, status: "connected", lastSync: new Date().toISOString(), nextScan: new Date(Date.now() + 864e5).toISOString() };
    writeStore("gmail", done);
    return done;
  },
  async disconnect() {
    if (isLive()) return live.disconnect();
    const c = { status: "disconnected", email: null, lastSync: null, nextScan: null, simulated: true };
    writeStore("gmail", c);
    return c;
  },
};
