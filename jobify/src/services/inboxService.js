import { readStore, writeStore, wait, uid } from "../lib/storage.js";
import { api, isLive } from "../lib/apiClient.js";

/**
 * Job-hunt inbox: every user gets their own address (name.xxxx@<inbox domain>) to put on
 * applications. Recruiter mail to it lands here and moves Application cards automatically.
 *   getInbox()                -> { address, receiving, sending, unread }
 *   list({ applicationId })   -> { items, total, page, pageSize }   (newest first)
 *   get(id)                   -> Message with body (marks it read)
 *   reply(id, body)           -> sent Message. Reply-only: Jobify addresses can't cold-email.
 * Message = { id, direction: "in"|"out", from: {name, email}, to, subject, snippet, receivedAt,
 *             read, applicationId, intent, movedTo, senderVerified, body? }
 * Live: GET /inbox, GET /inbox/messages, GET /inbox/messages/:id, POST /inbox/messages/:id/reply.
 */
const DEMO_ADDRESS = "alex.demo.k3m9@mail.jobify.example";
const ago = (h) => new Date(Date.now() - h * 36e5).toISOString();
const DEMO_MESSAGES = [
  { id: "m1", direction: "in", from: { name: "Priya Shah", email: "priya@tessellate.example" }, to: DEMO_ADDRESS,
    subject: "Interview invitation: Senior Frontend Engineer", snippet: "We'd love to schedule a 45-minute technical round next week.",
    body: "Hi Alex,\n\nThanks for applying. We'd love to schedule a 45-minute technical round next week. Does Tuesday or Wednesday afternoon work?\n\nBest,\nPriya",
    receivedAt: ago(3), read: false, applicationId: "app_1", intent: "INTERVIEW_INVITATION", movedTo: "interview", senderVerified: true },
  { id: "m2", direction: "in", from: { name: "Kavach Talent", email: "talent@kavach.example" }, to: DEMO_ADDRESS,
    subject: "Your application to Kavach Security", snippet: "We received your application and will be in touch.",
    body: "Hi Alex,\n\nWe received your application for Full Stack Engineer and will be in touch within two weeks.\n\nKavach Talent Team",
    receivedAt: ago(30), read: true, applicationId: null, intent: "FOLLOW_UP_REQUIRED", movedTo: null, senderVerified: true },
];
const load = () => readStore("inbox", DEMO_MESSAGES);
const save = (v) => writeStore("inbox", v);
const strip = ({ body, ...m }) => m;

const mock = {
  async getInbox() {
    return { address: DEMO_ADDRESS, receiving: true, sending: true, unread: load().filter((m) => m.direction === "in" && !m.read).length };
  },
  async list({ applicationId } = {}) {
    await wait(150);
    const items = load().filter((m) => !applicationId || m.applicationId === applicationId).map(strip);
    return { items, total: items.length, page: 1, pageSize: items.length };
  },
  async get(id) {
    const all = load().map((m) => (m.id === id ? { ...m, read: true } : m));
    save(all);
    return all.find((m) => m.id === id) || null;
  },
  async reply(id, body) {
    await wait(300);
    const orig = load().find((m) => m.id === id);
    const out = { id: uid("m"), direction: "out", from: { name: "Alex Demo", email: DEMO_ADDRESS }, to: orig.from.email,
      subject: orig.subject.toLowerCase().startsWith("re:") ? orig.subject : `Re: ${orig.subject}`, snippet: body.slice(0, 200), body,
      receivedAt: new Date().toISOString(), read: true, applicationId: orig.applicationId, intent: "OUTBOUND", movedTo: null, senderVerified: true };
    save([out, ...load()]);
    return out;
  },
};

const live = {
  getInbox: () => api("/inbox"),
  list: ({ applicationId } = {}) => api("/inbox/messages", { query: { applicationId } }),
  get: (id) => api(`/inbox/messages/${encodeURIComponent(id)}`),
  reply: (id, body) => api(`/inbox/messages/${encodeURIComponent(id)}/reply`, { method: "POST", body: { body } }),
};

const impl = () => (isLive() ? live : mock);

export const inboxService = {
  getInbox: () => impl().getInbox(),
  list: (q) => impl().list(q),
  get: (id) => impl().get(id),
  reply: (id, body) => impl().reply(id, body),
};
