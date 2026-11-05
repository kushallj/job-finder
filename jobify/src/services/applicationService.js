import { APPLICATIONS } from "../mocks/applications.js";
import { readStore, writeStore, wait, uid } from "../lib/storage.js";

/**
 * ApplicationService contract (local only).
 *   list() / create(app) / update(id, patch) / remove(id) / sync()
 *   getConnection() / connect() / disconnect()   <- Gmail status is SIMULATED
 *
 * Connection states: not_connected | pending | connected | syncing | failed | disconnected
 */
const load = () => readStore("applications", APPLICATIONS);
const save = (v) => writeStore("applications", v);

export const applicationService = {
  async list() {
    await wait(250);
    return load();
  },
  async create(data) {
    await wait(150);
    const app = { id: uid("app"), stage: "applied", messages: 1, notes: "", events: [], offer: null, subject: "Added manually", sender: "", date: new Date().toISOString(), source: "manual", ...data };
    save([app, ...load()]);
    return app;
  },
  async update(id, patch) {
    await wait(100);
    const next = load().map((a) => (a.id === id ? { ...a, ...patch } : a));
    save(next);
    return next.find((a) => a.id === id);
  },
  async remove(id) {
    await wait(100);
    save(load().filter((a) => a.id !== id));
  },
  getConnection() {
    return readStore("gmail", { status: "not_connected", email: null, lastSync: null, nextScan: null, simulated: true });
  },
  async connect(email) {
    writeStore("gmail", { status: "pending", email, lastSync: null, nextScan: null, simulated: true });
    await wait(900);
    const c = { status: "connected", email, lastSync: new Date().toISOString(), nextScan: new Date(Date.now() + 864e5).toISOString(), simulated: true };
    writeStore("gmail", c);
    return c;
  },
  async sync({ fail = false } = {}) {
    const c = this.getConnection();
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
  disconnect() {
    const c = { status: "disconnected", email: null, lastSync: null, nextScan: null, simulated: true };
    writeStore("gmail", c);
    return c;
  },
};
