import React, { useCallback, useEffect, useRef, useState } from "react";
import { Search, Send, Target, Briefcase, Lightbulb, Sparkles, Copy, RotateCcw, Square, Plus, Trash2, Pencil, History, MessageCircle, Check } from "lucide-react";
import { chatService } from "../../services/chatService.js";
import { useApp } from "../AppProvider.jsx";
import { Button, ConfirmDialog, Dialog, Input, PageHeader, Skeleton, DemoNotice } from "../ui.jsx";
import { cn } from "../../lib/utils.js";

const SUGGESTIONS = [
  { icon: Target, text: "Founders who fit my profile" },
  { icon: Briefcase, text: "Founders hiring for my skills" },
  { icon: Lightbulb, text: "Founders with remote or intern roles" },
  { icon: Sparkles, text: "My strongest outreach angle" },
];
const CREDIT_COST = 5;

export default function ChatPage() {
  const { toast, credits, spendCredits, plan } = useApp();
  const [convs, setConvs] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const [mode, setMode] = useState("agent");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [renaming, setRenaming] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const abortRef = useRef(null);
  const endRef = useRef(null);

  const refresh = useCallback(async () => setConvs(await chatService.getConversations()), []);
  useEffect(() => { refresh(); }, [refresh]);

  const active = convs?.find((c) => c.id === activeId) || null;
  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [active?.messages.length, busy]);

  const send = async (override) => {
    const msg = (override ?? text).trim();
    if (!msg || busy) return;
    if (credits < CREDIT_COST) return toast(plan ? "Not enough AI credits this month." : "Choose a plan to get AI credits.", "error");
    let id = activeId;
    if (!id) {
      id = (await chatService.createConversation(mode)).id;
      setActiveId(id);
    }
    setText("");
    setBusy(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    // optimistic render of the user message
    setConvs((cs) => cs && cs.map((c) => (c.id === id ? { ...c, messages: [...c.messages, { id: "pending", role: "user", content: msg }] } : c)));
    try {
      await chatService.sendMessage(id, msg, mode, { signal: ctrl.signal });
      spendCredits(CREDIT_COST);
    } catch (e) {
      if (e.name !== "AbortError") toast("Something went wrong (simulated).", "error");
      else toast("Generation stopped.");
    } finally {
      setBusy(false);
      refresh();
    }
  };

  const retry = () => {
    const lastUser = [...(active?.messages || [])].reverse().find((m) => m.role === "user");
    if (lastUser) send(lastUser.content);
  };

  const copy = async (content) => {
    try { await navigator.clipboard.writeText(content); toast("Copied to clipboard."); } catch { toast("Copy failed.", "error"); }
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const newChat = () => { setActiveId(null); setText(""); setHistoryOpen(false); };

  const messages = active?.messages || (busy ? [] : []);

  return (
    <div className="h-full flex flex-col bg-white">
      <PageHeader icon={MessageCircle} title={active?.title || "New Chat"}>
        <Button size="sm" variant="outline" onClick={newChat}><Plus className="w-3.5 h-3.5" />New chat</Button>
        <Button size="sm" variant="outline" onClick={() => setHistoryOpen(true)} aria-label="Conversation history"><History className="w-3.5 h-3.5" />History</Button>
      </PageHeader>

      <div className="flex-1 overflow-y-auto">
        {!active || messages.length === 0 ? (
          <div className="min-h-full flex flex-col items-center justify-center px-4 py-10 text-center">
            <h2 className="text-[19px] font-semibold">Who should we email?</h2>
            <p className="mt-3 max-w-[400px] text-[13px] leading-relaxed text-[#707070]">
              Agent finds founders who fit your profile, researches their company, and writes a short email you approve before it goes out from your Gmail with your resume.
            </p>
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-[520px]">
              {SUGGESTIONS.map(({ icon: Icon, text: s }) => (
                <button key={s} type="button" onClick={() => { setText(s); document.getElementById("chat-input")?.focus(); }}
                  className="flex items-center gap-2.5 text-left rounded-xl border border-[#E7E7E7] bg-white hover:bg-[#FAFAFA] px-3.5 py-3 text-[12.5px]">
                  <Icon className="w-4 h-4 text-[#707070] shrink-0" aria-hidden="true" />{s}
                </button>
              ))}
            </div>
            <DemoNotice><span className="block mt-4">Replies are simulated. No AI service is called and no email is sent.</span></DemoNotice>
          </div>
        ) : (
          <div className="max-w-[720px] mx-auto px-4 py-6 flex flex-col gap-5">
            {messages.map((m, i) => (
              <div key={m.id} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                <div className={cn("max-w-[85%] rounded-2xl px-4 py-2.5 text-[13.5px] leading-relaxed", m.role === "user" ? "bg-[#141414] text-white" : "bg-[#F4F4F4]")}>
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  {m.role === "assistant" && (
                    <div className="mt-2 flex items-center gap-1 text-[#707070]">
                      <span className="text-[11px] mr-2">Simulated reply</span>
                      <button type="button" onClick={() => copy(m.content)} aria-label="Copy reply" className="w-7 h-7 rounded-md hover:bg-white flex items-center justify-center"><Copy className="w-3.5 h-3.5" /></button>
                      {i === messages.length - 1 && !busy && <button type="button" onClick={retry} aria-label="Retry" className="w-7 h-7 rounded-md hover:bg-white flex items-center justify-center"><RotateCcw className="w-3.5 h-3.5" /></button>}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && <div className="flex"><Skeleton className="h-10 w-48 rounded-2xl" /></div>}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <div className="shrink-0 px-4 pb-4 pt-2 bg-white">
        <div className="max-w-[640px] mx-auto rounded-2xl border border-[#E7E7E7] bg-white shadow-sm focus-within:border-[#161616]">
          <label htmlFor="chat-input" className="sr-only">Message</label>
          <textarea id="chat-input" rows={1} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey}
            placeholder="Who should I email for you?" className="w-full resize-none bg-transparent px-4 pt-3.5 pb-1 text-[13.5px] focus-visible:!outline-none placeholder:text-[#A0A0A0] max-h-40" />
          <div className="flex items-center gap-2 px-2.5 pb-2.5">
            <div role="radiogroup" aria-label="Mode" className="inline-flex rounded-full bg-[#F4F4F4] p-0.5 text-[12px]">
              {[["ask", Search, "Ask"], ["agent", Send, "Agent"]].map(([id, Icon, label]) => (
                <button key={id} type="button" role="radio" aria-checked={mode === id} onClick={() => setMode(id)}
                  className={cn("inline-flex items-center gap-1.5 h-7 px-3 rounded-full", mode === id ? "bg-white shadow-xs font-medium" : "text-[#707070]")}>
                  <Icon className="w-3.5 h-3.5" />{label}
                </button>
              ))}
            </div>
            <span className="ml-auto text-[11px] text-[#A0A0A0] hidden sm:inline">{credits} credits</span>
            {busy ? (
              <button type="button" onClick={() => abortRef.current?.abort()} aria-label="Stop generating" className="w-8 h-8 rounded-full bg-[#141414] text-white flex items-center justify-center"><Square className="w-3 h-3 fill-current" /></button>
            ) : (
              <button type="button" onClick={() => send()} disabled={!text.trim()} aria-label="Send message" className="w-8 h-8 rounded-full bg-[#141414] text-white flex items-center justify-center disabled:bg-[#E7E7E7] disabled:text-[#A0A0A0]"><Send className="w-3.5 h-3.5" /></button>
            )}
          </div>
        </div>
      </div>

      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} title="Conversations" side width={360}>
        {!convs ? <Skeleton className="h-32" /> : convs.length === 0 ? <p className="text-[13px] text-[#707070]">No conversations yet.</p> : (
          <ul className="flex flex-col gap-1">
            {convs.map((c) => (
              <li key={c.id} className={cn("group flex items-center gap-1 rounded-lg", c.id === activeId && "bg-[#F0F0F0]")}>
                <button type="button" className="flex-1 min-w-0 text-left px-3 py-2 text-[13px] truncate hover:bg-[#F7F7F7] rounded-lg" onClick={() => { setActiveId(c.id); setMode(c.mode); setHistoryOpen(false); }}>{c.title}</button>
                <button type="button" aria-label={`Rename ${c.title}`} onClick={() => setRenaming({ id: c.id, title: c.title })} className="w-7 h-7 rounded hover:bg-white flex items-center justify-center text-[#707070]"><Pencil className="w-3.5 h-3.5" /></button>
                <button type="button" aria-label={`Delete ${c.title}`} onClick={() => setDeleting(c)} className="w-7 h-7 rounded hover:bg-white flex items-center justify-center text-[#707070]"><Trash2 className="w-3.5 h-3.5" /></button>
              </li>
            ))}
          </ul>
        )}
      </Dialog>

      <Dialog open={!!renaming} onClose={() => setRenaming(null)} title="Rename conversation" width={400}
        footer={<><Button variant="outline" onClick={() => setRenaming(null)}>Cancel</Button>
          <Button disabled={!renaming?.title.trim()} onClick={async () => { await chatService.renameConversation(renaming.id, renaming.title.trim()); setRenaming(null); refresh(); toast("Renamed."); }}><Check className="w-3.5 h-3.5" />Save</Button></>}>
        <Input aria-label="Title" value={renaming?.title || ""} maxLength={80} onChange={(e) => setRenaming({ ...renaming, title: e.target.value })} />
      </Dialog>

      <ConfirmDialog open={!!deleting} onClose={() => setDeleting(null)} title="Delete conversation?" message={`"${deleting?.title}" will be removed from this browser.`}
        onConfirm={async () => { await chatService.deleteConversation(deleting.id); if (activeId === deleting.id) setActiveId(null); setDeleting(null); refresh(); toast("Conversation deleted."); }} />
    </div>
  );
}
