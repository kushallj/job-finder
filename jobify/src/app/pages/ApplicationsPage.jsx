import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Search, RefreshCw, Unplug, Plus, Mail, Calendar, MessageSquare, LayoutPanelTop, Trash2, Plug, Copy, Inbox } from "lucide-react";
import { applicationService } from "../../services/applicationService.js";
import { inboxService } from "../../services/inboxService.js";
import InboxPanel from "../InboxPanel.jsx";
import { STAGES } from "../../mocks/applications.js";
import { uid } from "../../lib/storage.js";
import { isLive } from "../../lib/apiClient.js";
import { useApp } from "../AppProvider.jsx";
import { Avatar, Badge, Button, ConfirmDialog, Dialog, EmptyState, Field, Input, PageHeader, Select, Skeleton, Textarea } from "../ui.jsx";
import { cn } from "../../lib/utils.js";

const fmt = (iso) => new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
const COLORS = ["#2563EB", "#059669", "#DC2626", "#7C3AED", "#D97706", "#0891B2", "#DB2777", "#141414"];
const colorFor = (s) => COLORS[[...s].reduce((a, c) => a + c.charCodeAt(0), 0) % COLORS.length];

const STATUS_LABEL = { not_connected: "Not connected", pending: "Connecting…", connected: "Gmail connected (simulated)", syncing: "Syncing…", failed: "Sync failed", disconnected: "Disconnected" };
const NO_CONN = { status: "not_connected", email: null, lastSync: null, nextScan: null };
// Reasons the backend puts on /app/applications?gmail=error&reason=... after Google's redirect.
const CONNECT_ERRORS = {
  ACCESS_DENIED: "Gmail access was declined.",
  GMAIL_SCOPE_DENIED: "Jobify needs read access to Gmail to track replies. Please allow it and try again.",
  GMAIL_IN_USE: "That Gmail account is already connected to another Jobify account.",
  GMAIL_NO_REFRESH_TOKEN: "Google didn't grant offline access. Please try connecting again.",
  INVALID_STATE: "The connect link expired. Please try again.",
};
const STATUS_TONE = { not_connected: "neutral", pending: "warning", connected: "success", syncing: "warning", failed: "danger", disconnected: "neutral" };

function AppCard({ a, onOpen, onDragStart }) {
  return (
    <div draggable onDragStart={(e) => onDragStart(e, a.id)} className="rounded-xl border border-[#E7E7E7] bg-white p-3 shadow-xs cursor-grab active:cursor-grabbing">
      <button type="button" onClick={() => onOpen(a)} className="w-full text-left" aria-label={`Open ${a.position} at ${a.company}`}>
        <div className="flex items-start gap-2.5">
          <Avatar label={a.company[0]} color={colorFor(a.company)} fg="#fff" square size={34} />
          <div className="min-w-0"><div className="text-[13.5px] font-semibold leading-snug">{a.position}</div><div className="text-[12px] text-[#707070]">{a.company}</div></div>
        </div>
        <div className="mt-2.5 rounded-lg bg-[#F7F7F7] px-2.5 py-2 text-[12px]">
          <div className="flex items-start gap-1.5"><Mail className="w-3.5 h-3.5 mt-0.5 shrink-0 text-[#707070]" /><span className="leading-snug">{a.subject}</span></div>
          {a.sender && <div className="pl-5 text-[11px] text-[#888]">From {a.sender}</div>}
        </div>
        <div className="mt-2.5 pt-2 border-t border-[#F0F0F0] flex items-center text-[11px] text-[#707070]">
          <Calendar className="w-3 h-3 mr-1" />{fmt(a.date)}
          {a.messages > 1 && <span className="ml-auto inline-flex items-center gap-1"><MessageSquare className="w-3 h-3" />{a.messages}</span>}
        </div>
      </button>
    </div>
  );
}

const blank = { company: "", position: "", stage: "applied", notes: "" };

export default function ApplicationsPage() {
  const { toast } = useApp();
  const [apps, setApps] = useState(null);
  const [q, setQ] = useState("");
  const [mobileStage, setMobileStage] = useState("applied");
  const [dragOver, setDragOver] = useState(null);
  const [detailId, setDetailId] = useState(null);
  const [form, setForm] = useState(null); // create / edit
  const [errors, setErrors] = useState({});
  const [deleting, setDeleting] = useState(null);
  const live = isLive();
  const [conn, setConn] = useState(NO_CONN);
  const refreshConn = useCallback(() => applicationService.getConnection().then(setConn).catch(() => {}), []);
  // Job-hunt inbox: the user's Jobify address; recruiter replies to it move cards automatically.
  const [inbox, setInbox] = useState(null);
  const [inboxOpen, setInboxOpen] = useState(false);
  const refreshInbox = useCallback(() => inboxService.getInbox().then(setInbox).catch(() => {}), []);
  useEffect(() => { refreshInbox(); }, [refreshInbox]);
  const copyAddress = async () => {
    try { await navigator.clipboard.writeText(inbox.address); toast("Job email copied. Use it on your applications."); }
    catch { toast(inbox.address); }
  };
  useEffect(() => {
    refreshConn();
    // Returning from Google's consent screen.
    const params = new URLSearchParams(window.location.search);
    const result = params.get("gmail");
    if (!result) return;
    if (result === "connected") toast("Gmail connected (read-only). Run Sync to pull recruiter replies.");
    else toast(CONNECT_ERRORS[params.get("reason")] || "Couldn't connect Gmail. Please try again.", "error");
    window.history.replaceState(null, "", window.location.pathname);
  }, [refreshConn, toast]);
  const [eventDraft, setEventDraft] = useState({ title: "", at: "" });

  const load = useCallback(async () => {
    try { setApps(await applicationService.list()); }
    catch { setApps((prev) => prev || []); toast("Couldn't load applications. Try again.", "error"); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    const n = q.trim().toLowerCase();
    return (apps || []).filter((a) => !n || `${a.company} ${a.position} ${a.subject} ${a.sender}`.toLowerCase().includes(n));
  }, [apps, q]);
  const byStage = (id) => filtered.filter((a) => a.stage === id);
  const detail = apps?.find((a) => a.id === detailId) || null;

  const move = async (id, stage) => {
    const a = apps.find((x) => x.id === id);
    if (!a || a.stage === stage) return;
    setApps(apps.map((x) => (x.id === id ? { ...x, stage } : x)));
    try {
      await applicationService.update(id, { stage });
      toast(`Moved ${a.company} to ${STAGES.find((s) => s.id === stage).label}.`);
    } catch {
      setApps((cur) => cur.map((x) => (x.id === id ? { ...x, stage: a.stage } : x)));
      toast(`Couldn't move ${a.company}. Try again.`, "error");
    }
  };
  const patch = async (id, p) => {
    try { await applicationService.update(id, p); }
    catch { toast("Couldn't save that change. Try again.", "error"); }
    load();
  };

  const submit = async () => {
    const e = {};
    if (!form.company.trim()) e.company = "Company is required";
    if (!form.position.trim()) e.position = "Position is required";
    setErrors(e);
    if (Object.keys(e).length) return;
    try {
      if (form.id) { await applicationService.update(form.id, form); toast("Application updated."); }
      else { await applicationService.create(form); toast("Application added."); }
      setForm(null); load();
    } catch {
      toast("Couldn't save the application. Check the fields and try again.", "error");
    }
  };

  const connect = async () => {
    setConn({ ...conn, status: "pending" });
    try {
      setConn(await applicationService.connect("demo-inbox@jobify.example"));
      if (!live) toast("Simulated Gmail connection. No real inbox is accessed.");
    } catch (e) {
      setConn(conn);
      toast(e?.code === "GMAIL_NOT_CONFIGURED" ? "Gmail connection isn't available yet." : "Couldn't start the Gmail connection.", "error");
    }
  };
  const sync = async (fail) => {
    setConn({ ...conn, status: "syncing" });
    try {
      const res = await applicationService.sync({ fail });
      setConn(res);
      if (live) {
        const r = res.result || {};
        toast(r.stored ? `Synced: ${r.stored} recruiter email${r.stored === 1 ? "" : "s"} matched, ${r.advanced} card${r.advanced === 1 ? "" : "s"} moved.` : "Synced. No new recruiter emails.");
        load();
      } else toast("Sync completed (simulated).");
    } catch (e) {
      refreshConn();
      toast(e?.code === "GMAIL_REAUTH_REQUIRED" ? "Gmail access expired. Connect again." : live ? "Sync failed. Try again later." : "Sync failed (simulated).", "error");
    }
  };
  const disconnect = async () => {
    try { setConn(await applicationService.disconnect()); toast(live ? "Gmail disconnected. Access revoked and synced email bodies removed." : "Disconnected."); }
    catch { toast("Couldn't disconnect Gmail. Try again.", "error"); }
  };

  const connected = conn.status === "connected" || conn.status === "syncing";

  return (
    <div className="min-h-full">
      <PageHeader icon={LayoutPanelTop} title="Applications"
        sub={<>
          {(!live || conn.available) && <Badge tone={STATUS_TONE[conn.status]}>{live && conn.status === "connected" ? "Gmail connected" : STATUS_LABEL[conn.status]}</Badge>}
          {connected && <span className="text-[12px] text-[#707070] hidden xl:inline">{conn.email} · Last sync {conn.lastSync ? fmt(conn.lastSync) : "never"} · Next scan {conn.nextScan ? fmt(conn.nextScan) : "n/a"}</span>}
        </>}>
        <div className="relative">
          <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#A0A0A0]" aria-hidden="true" />
          <input aria-label="Search applications" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…" className="h-9 w-[160px] sm:w-[200px] rounded-lg border border-[#E7E7E7] pl-8 pr-3 text-[13px] focus:outline-none focus:border-[#161616]" />
        </div>
        {inbox?.address && (
          <>
            <Button variant="outline" onClick={copyAddress} title="Use this address on applications"><Copy className="w-3.5 h-3.5" /><span className="hidden lg:inline max-w-[220px] truncate">{inbox.address}</span><span className="lg:hidden">Job email</span></Button>
            <Button variant="outline" onClick={() => setInboxOpen(true)}><Inbox className="w-3.5 h-3.5" />Inbox{inbox.unread > 0 && <span className="ml-1 text-[11px] bg-[#2685E8] text-white rounded-full px-1.5">{inbox.unread}</span>}</Button>
          </>
        )}
        <Button variant="outline" onClick={() => { setErrors({}); setForm({ ...blank }); }}><Plus className="w-3.5 h-3.5" />Add</Button>
        {(!live || conn.available) && (connected ? (
          <>
            <Button disabled={conn.status === "syncing"} onClick={() => sync(false)}><RefreshCw className={cn("w-3.5 h-3.5", conn.status === "syncing" && "animate-spin")} />Sync</Button>
            <Button variant="outline" onClick={disconnect}><Unplug className="w-3.5 h-3.5" />Disconnect</Button>
          </>
        ) : (
          <Button disabled={conn.status === "pending"} onClick={connect}><Plug className="w-3.5 h-3.5" />{live ? "Connect Gmail" : "Connect Gmail (demo)"}</Button>
        ))}
        {conn.status === "failed" && <Button variant="outline" onClick={() => sync(false)}>Retry sync</Button>}
      </PageHeader>

      {/* Mobile stage tabs */}
      <div role="tablist" aria-label="Stages" className="md:hidden flex gap-1 overflow-x-auto px-4 pt-3">
        {STAGES.map((s) => (
          <button key={s.id} type="button" role="tab" aria-selected={mobileStage === s.id} onClick={() => setMobileStage(s.id)}
            className={cn("h-8 px-3 rounded-full text-[12.5px] whitespace-nowrap", mobileStage === s.id ? "bg-[#141414] text-white" : "bg-[#F0F0F0]")}>{s.label} {byStage(s.id).length}</button>
        ))}
      </div>

      <div className="p-4 md:p-6 flex gap-4 md:overflow-x-auto items-start">
        {!apps && Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-64 flex-1 min-w-[260px]" />)}
        {apps && STAGES.map((s) => {
          const list = byStage(s.id);
          return (
            <section key={s.id} aria-label={s.label}
              onDragOver={(e) => { e.preventDefault(); setDragOver(s.id); }} onDragLeave={() => setDragOver(null)}
              onDrop={(e) => { e.preventDefault(); setDragOver(null); move(e.dataTransfer.getData("text/plain"), s.id); }}
              className={cn("rounded-2xl border bg-[#F7F7F7] p-3 min-w-[280px] md:w-[300px] md:shrink-0 w-full", s.id !== mobileStage && "hidden md:block", dragOver === s.id ? "border-[#141414]" : "border-[#E7E7E7]")}>
              <header className="flex items-center gap-2 mb-3 px-1"><span className="w-2 h-2 rounded-full" style={{ background: s.dot }} /><h2 className="text-[13px] font-medium">{s.label}</h2><span className="ml-auto text-[11.5px] bg-white border border-[#E7E7E7] rounded-full px-2">{list.length}</span></header>
              <div className="flex flex-col gap-2.5">
                {list.map((a) => <AppCard key={a.id} a={a} onOpen={(x) => setDetailId(x.id)} onDragStart={(e, id) => e.dataTransfer.setData("text/plain", id)} />)}
                {list.length === 0 && <EmptyState title={`No ${s.label.toLowerCase()} applications`} text={s.id === "ghosted" ? "Applications with no reply for 30 days land here." : "Drag a card here or add an application."} />}
              </div>
            </section>
          );
        })}
      </div>

      {/* Create / edit */}
      <Dialog open={!!form} onClose={() => setForm(null)} title={form?.id ? "Edit application" : "Add application"} width={440}
        footer={<><Button variant="outline" onClick={() => setForm(null)}>Cancel</Button><Button onClick={submit}>{form?.id ? "Save" : "Add"}</Button></>}>
        {form && (
          <div className="flex flex-col gap-4">
            <Field label="Company" htmlFor="co" error={errors.company}><Input id="co" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} /></Field>
            <Field label="Position" htmlFor="po" error={errors.position}><Input id="po" value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })} /></Field>
            <Field label="Stage" htmlFor="st"><Select id="st" value={form.stage} onChange={(e) => setForm({ ...form, stage: e.target.value })}>{STAGES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</Select></Field>
            <Field label="Notes" htmlFor="no"><Textarea id="no" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
          </div>
        )}
      </Dialog>

      {/* Detail */}
      <Dialog open={!!detail} onClose={() => setDetailId(null)} title={detail ? `${detail.position} · ${detail.company}` : ""} side width={480}
        footer={detail && <><Button variant="outline" onClick={() => { setErrors({}); setForm({ ...detail }); }}>Edit</Button><Button variant="danger" onClick={() => setDeleting(detail)}><Trash2 className="w-3.5 h-3.5" />Delete</Button></>}>
        {detail && (
          <div className="flex flex-col gap-5 text-[13px]">
            <Field label="Status" htmlFor="dst"><Select id="dst" value={detail.stage} onChange={(e) => move(detail.id, e.target.value)}>{STAGES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</Select></Field>
            <section><h3 className="text-[12.5px] font-semibold mb-2">Communication timeline</h3>
              <ol className="border-l border-[#E7E7E7] pl-4 space-y-3">
                <li><div className="font-medium">{detail.subject}</div><div className="text-[11.5px] text-[#707070]">{fmt(detail.date)}{detail.sender && ` · ${detail.sender}`} · {detail.messages} message{detail.messages > 1 ? "s" : ""}</div></li>
                {detail.events.map((e) => <li key={e.id}><div className="font-medium">Interview: {e.title}</div><div className="text-[11.5px] text-[#707070]">{fmt(e.at)}</div></li>)}
                {detail.source !== "demo" && <li className="text-[11.5px] text-[#707070]">Added manually in Jobify</li>}
              </ol>
            </section>
            <section><h3 className="text-[12.5px] font-semibold mb-2">Notes</h3>
              <Textarea aria-label="Notes" defaultValue={detail.notes} onBlur={(e) => e.target.value !== detail.notes && patch(detail.id, { notes: e.target.value })} placeholder="Add notes…" />
            </section>
            <section><h3 className="text-[12.5px] font-semibold mb-2">Add interview event</h3>
              <div className="flex flex-wrap gap-2">
                <Input aria-label="Event title" placeholder="e.g. Onsite round" className="flex-1 min-w-[140px]" value={eventDraft.title} onChange={(e) => setEventDraft({ ...eventDraft, title: e.target.value })} />
                <Input aria-label="Event time" type="datetime-local" className="w-auto" value={eventDraft.at} onChange={(e) => setEventDraft({ ...eventDraft, at: e.target.value })} />
                <Button disabled={!eventDraft.title || !eventDraft.at} onClick={() => { patch(detail.id, { events: [...detail.events, { id: uid("ev"), ...eventDraft }] }); setEventDraft({ title: "", at: "" }); toast("Interview event added."); }}>Add</Button>
              </div>
            </section>
            {detail.stage === "offer" && (
              <section><h3 className="text-[12.5px] font-semibold mb-2">Offer details</h3>
                <div className="flex gap-2">
                  <Input aria-label="Offer amount" placeholder="Compensation" defaultValue={detail.offer?.salary || ""} onBlur={(e) => patch(detail.id, { offer: { ...(detail.offer || {}), salary: e.target.value } })} />
                  <Input aria-label="Offer deadline" type="date" className="w-auto" defaultValue={detail.offer?.deadline || ""} onBlur={(e) => patch(detail.id, { offer: { ...(detail.offer || {}), deadline: e.target.value } })} />
                </div>
              </section>
            )}
          </div>
        )}
      </Dialog>

      <InboxPanel open={inboxOpen} onClose={() => setInboxOpen(false)} sending={!!inbox?.sending} onChanged={() => { refreshInbox(); load(); }} />
      <ConfirmDialog open={!!deleting} onClose={() => setDeleting(null)} title="Delete application?" message={`${deleting?.position} at ${deleting?.company} will be removed.`}
        onConfirm={async () => {
          try { await applicationService.remove(deleting.id); toast("Application deleted."); setDetailId(null); }
          catch { toast("Couldn't delete the application. Try again.", "error"); }
          setDeleting(null); load();
        }} />
    </div>
  );
}
