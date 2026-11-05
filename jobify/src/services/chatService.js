import { CONVERSATIONS } from "../mocks/conversations.js";
import { readStore, writeStore, wait, uid } from "../lib/storage.js";

/**
 * ChatService contract (LocalChatService). No AI provider is called.
 *   getConversations() / createConversation(mode) / renameConversation(id, title)
 *   deleteConversation(id) / sendMessage(id, text, mode, { signal }) -> assistant message
 */
const load = () => readStore("chats", CONVERSATIONS);
const save = (v) => writeStore("chats", v);

const REPLIES = [
  (t) => `This is a simulated reply. A real assistant would research founders for "${t}". In demo mode I can only point you to the Founders directory, where hiring companies are filterable.`,
  (t) => `Demo response: for "${t}", start by shortlisting three companies in the Founders tab, then draft a short email that references one specific project of yours. Nothing is sent without your approval.`,
];

export const chatService = {
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
