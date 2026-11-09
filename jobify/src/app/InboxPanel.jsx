import React, { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Inbox, Send, ShieldAlert } from "lucide-react";
import { inboxService } from "../services/inboxService.js";
import { useApp } from "./AppProvider.jsx";
import { Badge, Button, Dialog, EmptyState, Skeleton, Textarea } from "./ui.jsx";
import { cn } from "../lib/utils.js";

const fmt = (iso) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "");
const STAGE_LABEL = { interview: "Interview", offer: "Offer", rejected: "Rejected" };

/**
 * Side panel for the job-hunt inbox: message list -> message -> reply.
 * Replies are only ever sent by the explicit Send button (never automatically).
 */
export default function InboxPanel({ open, onClose, sending, onChanged }) {
  const { toast } = useApp();
  const [items, setItems] = useState(null);
  const [current, setCurrent] = useState(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setItems((await inboxService.list()).items); }
    catch { setItems([]); toast("Couldn't load your inbox. Try again.", "error"); }
  }, [toast]);
  useEffect(() => { if (open) { setCurrent(null); setItems(null); load(); } }, [open, load]);

  const openMessage = async (m) => {
    try {
      const full = await inboxService.get(m.id);
      setCurrent(full); setDraft("");
      if (!m.read) { setItems((xs) => xs.map((x) => (x.id === m.id ? { ...x, read: true } : x))); onChanged?.(); }
    } catch { toast("Couldn't open that message.", "error"); }
  };

  const send = async () => {
    setBusy(true);
    try {
      await inboxService.reply(current.id, draft.trim());
      toast(`Reply sent to ${current.from.email}.`);
      setDraft(""); setCurrent(null); load(); onChanged?.();
    } catch (e) {
      toast(e?.code === "SEND_LIMIT_REACHED" ? "Daily reply limit reached. Try again tomorrow." : "Couldn't send the reply. Try again.", "error");
    } finally { setBusy(false); }
  };

  const canReply = current && current.direction === "in" && sending;

  return (
    <Dialog open={open} onClose={onClose} side width={560} title={current ? current.subject : "Job inbox"}
      footer={canReply ? (
        <div className="w-full flex flex-col gap-2">
          <Textarea aria-label="Reply" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={`Reply to ${current.from.name || current.from.email}…`} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCurrent(null)}>Back</Button>
            <Button onClick={send} disabled={busy || !draft.trim()}><Send className="w-3.5 h-3.5" />{busy ? "Sending…" : "Send reply"}</Button>
          </div>
        </div>
      ) : current ? <Button variant="ghost" onClick={() => setCurrent(null)}><ArrowLeft className="w-3.5 h-3.5" />Back</Button> : null}>
      {current ? (
        <article className="flex flex-col gap-3 text-[13.5px]">
          <div className="text-[12.5px] text-[#707070]">
            <div><span className="font-medium text-[#161616]">{current.from.name || current.from.email}</span>{current.from.name && ` <${current.from.email}>`}</div>
            <div>To {current.to} · {fmt(current.receivedAt)}</div>
          </div>
          {current.senderVerified === false && (
            <div className="flex items-start gap-2 rounded-lg bg-[#FFF4E5] text-[#8A5300] px-3 py-2 text-[12.5px]">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />The sender couldn't be verified, so this email didn't move any card. Be careful with links.
            </div>
          )}
          {current.movedTo && <Badge tone="success">Moved card to {STAGE_LABEL[current.movedTo] || current.movedTo}</Badge>}
          <pre className="whitespace-pre-wrap font-sans leading-relaxed">{current.body}</pre>
          {current.direction === "in" && !sending && <p className="text-[12px] text-[#707070]">Replying from Jobify isn't available yet. Reply from your own email for now.</p>}
        </article>
      ) : items === null ? (
        <div className="flex flex-col gap-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-16" />)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={Inbox} title="No emails yet" text="Use your job email on applications. Recruiter replies will appear here and update your board." />
      ) : (
        <ul className="flex flex-col divide-y divide-[#EEE]">
          {items.map((m) => (
            <li key={m.id}>
              <button type="button" onClick={() => openMessage(m)} className="w-full text-left py-3 px-1 hover:bg-[#F7F7F7] rounded-lg">
                <div className="flex items-center gap-2">
                  {m.direction === "in" && !m.read && <span className="w-2 h-2 rounded-full bg-[#2685E8]" aria-label="Unread" />}
                  <span className={cn("text-[13px] truncate", m.direction === "in" && !m.read && "font-semibold")}>
                    {m.direction === "out" ? `To ${m.to}` : m.from.name || m.from.email}
                  </span>
                  <span className="ml-auto text-[11.5px] text-[#888] shrink-0">{fmt(m.receivedAt)}</span>
                </div>
                <div className={cn("text-[13px] truncate", m.direction === "in" && !m.read ? "text-[#161616]" : "text-[#555]")}>{m.subject}</div>
                <div className="text-[12px] text-[#888] truncate">{m.snippet}</div>
                <div className="flex gap-1.5 mt-1">
                  {m.movedTo && <Badge tone="success">→ {STAGE_LABEL[m.movedTo] || m.movedTo}</Badge>}
                  {m.senderVerified === false && <Badge tone="warning">Unverified sender</Badge>}
                  {m.direction === "out" && <Badge tone="neutral">Sent</Badge>}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Dialog>
  );
}
