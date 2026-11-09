import { CONVERSATIONS } from "../mocks/conversations.js";
import { readStore, writeStore, wait, uid } from "../lib/storage.js";
import { api, apiStream, ApiError, isLive } from "../lib/apiClient.js";

/**
 * ChatService contract.
 *   getConversations() / createConversation(mode) / renameConversation(id, title)
 *   deleteConversation(id) / sendMessage(id, text, mode, { signal, onDelta }) -> assistant message
 *   isLive() -> true when replies come from the API
 * Live (/app + API): /conversations CRUD; POST /conversations/:id/messages streams SSE
 *   (event user | delta {text} | done {message, creditsCharged} | error {code, message, refunded}).
 *   onDelta(text) receives reply chunks as they arrive. The server charges credits; a provider
 *   failure before any text is refunded. The reply comes from the server's CHAT_PROVIDER
 *   ("echo" stub until an LLM is chosen). Nothing is ever sent on the user's behalf.
 * /demo or no API: scripted local replies; no AI provider is called.
 */
const load = () => readStore("chats", CONVERSATIONS);
const save = (v) => writeStore("chats", v);

const REPLIES = [
  (t) => `This is a simulated reply. A real assistant would research founders for "${t}". In demo mode I can only point you to the Founders directory, where hiring companies are filterable.`,
  (t) => `Demo response: for "${t}", start by shortlisting three companies in the Founders tab, then draft a short email that references one specific project of yours. Nothing is sent without your approval.`,
];

const mock = {
  async getConversations() {
    await wait(120);
    return load().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  },
  async createConversation(mode = "agent") {
    const c = { id: uid("conv"), title: "New chat", mode, updatedAt: new Date().toISOString(), messages: [] };
    save([c, ...load()]);
    return c;
  },
  async renameConversation(id, title) {
    save(load().map((c) => (c.id === id ? { ...c, title } : c)));
  },
  async deleteConversation(id) {
    save(load().filter((c) => c.id !== id));
  },
  /** Appends the user message, then resolves with the simulated assistant message. Abortable. */
  async sendMessage(id, text, mode, { signal } = {}) {
    const now = () => new Date().toISOString();
    const user = { id: uid("m"), role: "user", content: text, at: now() };
    save(load().map((c) => (c.id === id ? { ...c, mode, title: c.messages.length ? c.title : text.slice(0, 48), messages: [...c.messages, user], updatedAt: now() } : c)));
    await new Promise((resolve, reject) => {
      const timer = setTimeout(resolve, 1400);
      signal?.addEventListener("abort", () => {
        clearTimeout(timer);
        reject(new DOMException("Stopped", "AbortError"));
      });
    });
    const reply = { id: uid("m"), role: "assistant", content: REPLIES[text.length % REPLIES.length](text), at: now(), demo: true, mode };
    save(load().map((c) => (c.id === id ? { ...c, messages: [...c.messages, reply], updatedAt: now() } : c)));
    return reply;
  },
};

const live = {
  getConversations: async () => (await api("/conversations", { query: { pageSize: 100 } })).items,
  createConversation: (mode = "agent") => api("/conversations", { method: "POST", body: { mode } }),
  renameConversation: (id, title) => api(`/conversations/${encodeURIComponent(id)}`, { method: "PATCH", body: { title } }),
  deleteConversation: (id) => api(`/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }),
  async sendMessage(id, text, mode, { signal, onDelta } = {}) {
    let message = null;
    let failure = null;
    await apiStream(`/conversations/${encodeURIComponent(id)}/messages`, {
      body: { content: text, mode },
      signal,
      onEvent: (event, data) => {
        if (event === "delta") onDelta?.(data.text);
        else if (event === "done") message = data.message;
        else if (event === "error") failure = data;
      },
    });
    if (failure) {
      const err = new ApiError(502, failure.code, failure.message);
      err.refunded = Boolean(failure.refunded);
      throw err;
    }
    return message;
  },
};

const impl = () => (isLive() ? live : mock);

export const chatService = {
  isLive: () => isLive(),
  getConversations: () => impl().getConversations(),
  createConversation: (mode) => impl().createConversation(mode),
  renameConversation: (id, title) => impl().renameConversation(id, title),
  deleteConversation: (id) => impl().deleteConversation(id),
  sendMessage: (id, text, mode, opts) => impl().sendMessage(id, text, mode, opts),
};
