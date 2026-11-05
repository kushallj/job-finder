import React, { useEffect, useRef, useState } from "react";
import { AppWindow, Eye, Copy, ExternalLink, EyeOff, Sparkles, FileText, Github, User, Code2, Briefcase, GraduationCap, Trophy, FlaskConical, Globe, Plus, Trash2, ArrowUp, ArrowDown, Pencil, X, Loader2 } from "lucide-react";
import { portfolioService } from "../../services/portfolioService.js";
import { uid } from "../../lib/storage.js";
import { useApp } from "../AppProvider.jsx";
import { Badge, Button, ConfirmDialog, Dialog, Field, Input, PageHeader, Textarea } from "../ui.jsx";
import { cn } from "../../lib/utils.js";

const TABS = [
  { id: "identity", label: "Identity", icon: User },
  { id: "projects", label: "Projects", icon: Code2 },
  { id: "experience", label: "Experience", icon: Briefcase },
  { id: "education", label: "Education", icon: GraduationCap },
  { id: "hacks", label: "Hacks", icon: Trophy },
  { id: "research", label: "Research", icon: FlaskConical },
  { id: "socials", label: "Socials", icon: Globe },
  { id: "custom", label: "Custom", icon: Sparkles },
];
const LIST_LABELS = {
  projects: ["Project name", "Link", "Add project"],
  experience: ["Role", "Company and period", "Add experience"],
  education: ["Degree", "School and period", "Add education"],
  hacks: ["Hackathon / hack", "Result or link", "Add hack"],
  research: ["Paper / topic", "Venue or link", "Add research"],
};
const isUrl = (v) => !v || /^https?:\/\/.+\..+/.test(v);
const baseHost = "jobify.example";

function ListEditor({ kind, items, onChange }) {
  const [edit, setEdit] = useState(null);
  const [err, setErr] = useState("");
  const [l1, l2, addLabel] = LIST_LABELS[kind];
  const move = (i, d) => { const n = [...items]; const j = i + d; if (j < 0 || j >= n.length) return; [n[i], n[j]] = [n[j], n[i]]; onChange(n); };
  const save = () => {
    if (!edit.title.trim()) return setErr("Required");
    onChange(edit.id ? items.map((x) => (x.id === edit.id ? edit : x)) : [...items, { ...edit, id: uid(kind) }]);
    setEdit(null); setErr("");
  };
  return (
    <div>
      <div className="flex justify-between items-center mb-3"><h3 className="text-[14px] font-semibold capitalize">{kind}</h3><Button size="sm" onClick={() => { setErr(""); setEdit({ title: "", subtitle: "", description: "" }); }}><Plus className="w-3.5 h-3.5" />{addLabel}</Button></div>
      {items.length === 0 && <p className="text-[13px] text-[#707070] py-6 text-center border border-dashed border-[#E7E7E7] rounded-lg">Nothing here yet.</p>}
      <ul className="flex flex-col gap-2">
        {items.map((it, i) => (
          <li key={it.id} className="flex items-start gap-2 rounded-lg border border-[#E7E7E7] p-3">
            <div className="flex-1 min-w-0"><div className="text-[13.5px] font-medium">{it.title}</div>{it.subtitle && <div className="text-[12px] text-[#707070] break-all">{it.subtitle}</div>}{it.description && <p className="text-[12.5px] text-[#444] mt-1">{it.description}</p>}</div>
            <div className="flex gap-0.5 shrink-0">
              <button type="button" aria-label="Move up" disabled={i === 0} onClick={() => move(i, -1)} className="w-7 h-7 rounded hover:bg-[#F4F4F4] disabled:opacity-30 flex items-center justify-center"><ArrowUp className="w-3.5 h-3.5" /></button>
              <button type="button" aria-label="Move down" disabled={i === items.length - 1} onClick={() => move(i, 1)} className="w-7 h-7 rounded hover:bg-[#F4F4F4] disabled:opacity-30 flex items-center justify-center"><ArrowDown className="w-3.5 h-3.5" /></button>
              <button type="button" aria-label={`Edit ${it.title}`} onClick={() => { setErr(""); setEdit(it); }} className="w-7 h-7 rounded hover:bg-[#F4F4F4] flex items-center justify-center"><Pencil className="w-3.5 h-3.5" /></button>
              <button type="button" aria-label={`Delete ${it.title}`} onClick={() => onChange(items.filter((x) => x.id !== it.id))} className="w-7 h-7 rounded hover:bg-[#F4F4F4] flex items-center justify-center"><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          </li>
        ))}
      </ul>
      <Dialog open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit item" : addLabel} width={440} footer={<><Button variant="outline" onClick={() => setEdit(null)}>Cancel</Button><Button onClick={save}>Save</Button></>}>
        {edit && <div className="flex flex-col gap-4">
          <Field label={l1} htmlFor="li-t" error={err}><Input id="li-t" value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} /></Field>
          <Field label={l2} htmlFor="li-s"><Input id="li-s" value={edit.subtitle} onChange={(e) => setEdit({ ...edit, subtitle: e.target.value })} /></Field>
          <Field label="Description" htmlFor="li-d"><Textarea id="li-d" value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} /></Field>
        </div>}
      </Dialog>
    </div>
  );
}

function Preview({ p }) {
  const i = p.identity;
  return (
    <div className="bg-white text-[#161616] p-6 md:p-8">
      <div className="w-16 h-16 rounded-full bg-[#F0F0F0] flex items-center justify-center mb-3"><User className="w-7 h-7 text-[#A0A0A0]" aria-hidden="true" /></div>
      <h2 className="text-[22px] font-semibold font-display">{i.fullName || "Your name"}</h2>
      <p className="text-[#626262]">{i.jobTitle}</p>
      {i.tagline && <p className="italic text-[13px] mt-2 text-[#444]">{i.tagline}</p>}
      <div className="flex flex-wrap gap-1.5 mt-3">{i.skills.map((s) => <Badge key={s}>{s}</Badge>)}</div>
      {i.bio && <p className="mt-4 text-[13.5px] leading-relaxed text-[#444]">{i.bio}</p>}
      {["projects", "experience", "education"].map((k) => p[k].length > 0 && (
        <section key={k} className="mt-6"><h3 className="text-[12px] uppercase tracking-wide text-[#707070] mb-2">{k}</h3>
          <ul className="space-y-2">{p[k].map((x) => <li key={x.id}><div className="text-[13.5px] font-medium">{x.title}</div><div className="text-[12px] text-[#707070]">{x.subtitle}</div>{x.description && <div className="text-[12.5px] text-[#444]">{x.description}</div>}</li>)}</ul></section>
      ))}
      {p.custom.map((c) => <section key={c.id} className="mt-6"><h3 className="text-[12px] uppercase tracking-wide text-[#707070] mb-2">{c.title}</h3><p className="text-[13px] text-[#444] whitespace-pre-wrap">{c.body}</p></section>)}
      <p className="mt-6 text-[12px] text-[#707070]">{p.contact.email}</p>
    </div>
  );
}

export default function PortfolioPage() {
  const { toast } = useApp();
  const [p, setP] = useState(() => portfolioService.get());
  const [saved, setSaved] = useState(true);
  const [tab, setTab] = useState("identity");
  const [preview, setPreview] = useState(null); // "draft" | "visitor"
  const [skill, setSkill] = useState("");
  const [uname, setUname] = useState(p.username || "");
  const [unameState, setUnameState] = useState(null);
  const [busy, setBusy] = useState(null);
  const [errors, setErrors] = useState({});
  const [confirmRegen, setConfirmRegen] = useState(false);
  const first = useRef(true);

  const update = (fn) => { setP((cur) => fn(cur)); setSaved(false); };
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    const t = setTimeout(async () => { await portfolioService.saveDraft(p); setSaved(true); }, 600);
    return () => clearTimeout(t);
  }, [p]);

  useEffect(() => {
    if (!uname) return setUnameState(null);
    setUnameState("checking");
    const t = setTimeout(async () => setUnameState(await portfolioService.checkUsername(uname)), 350);
    return () => clearTimeout(t);
  }, [uname]);

  const live = p.status === "published";
  const url = `https://${p.username || uname || "username"}.${baseHost}`;

  const validateContact = () => {
    const e = {};
    if (p.contact.email && !/^\S+@\S+\.\S+$/.test(p.contact.email)) e.email = "Enter a valid email";
    ["website", "calendar", "resume"].forEach((k) => { if (!isUrl(p.contact[k])) e[k] = "Enter a URL starting with https://"; });
    ["github", "linkedin", "x"].forEach((k) => { if (!isUrl(p.socials[k])) e[k] = "Enter a URL starting with https://"; });
    setErrors(e);
    return !Object.keys(e).length;
  };

  const publish = async () => {
    if (!p.identity.fullName.trim()) return toast("Add your full name before publishing.", "error");
    if (!validateContact()) return toast("Fix the highlighted fields first.", "error");
    if (unameState?.available !== true) return toast("Choose an available username.", "error");
    setBusy("publish");
    setP(await portfolioService.publish(p, uname));
    setBusy(null);
    toast("Published in demo mode. No public site is actually hosted.");
  };

  const regenerate = async () => {
    setConfirmRegen(false); setBusy("regen");
    try { setP(await portfolioService.regenerate(p)); toast("Preview regenerated (simulated)."); }
    catch { toast("Regeneration failed (simulated).", "error"); }
    setBusy(null);
  };

  const id = (k) => (e) => update((c) => ({ ...c, identity: { ...c.identity, [k]: e.target.value } }));
  const con = (k) => (e) => update((c) => ({ ...c, contact: { ...c.contact, [k]: e.target.value } }));
  const soc = (k) => (e) => update((c) => ({ ...c, socials: { ...c.socials, [k]: e.target.value } }));

  const card = "rounded-xl border border-[#E7E7E7] bg-white p-5";

  return (
    <div className="min-h-full">
      <PageHeader icon={AppWindow} title="Portfolio" sub={<Badge tone={saved ? "success" : "warning"}>{saved ? "Saved" : "Saving…"}</Badge>}>
        <Button variant="outline" onClick={() => setPreview("draft")}><Eye className="w-3.5 h-3.5" />Preview draft</Button>
        <Button variant="outline" disabled={!live} onClick={() => setPreview("visitor")}><Eye className="w-3.5 h-3.5" />Preview</Button>
      </PageHeader>

      <div className="max-w-[830px] mx-auto p-4 md:p-6 flex flex-col gap-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[["Status", live ? "Live" : "Draft", live ? "#13A875" : "#EBAA20"], ["Projects", p.projects.length, "#2685E8"], ["Experiences", p.experience.length, "#8B5CF6"], ["Custom", p.custom.length, "#F59E0B"]].map(([k, v, c]) => (
            <div key={k} className="rounded-xl border border-[#E7E7E7] bg-white p-4"><div className="flex items-center gap-1.5 text-[12px] text-[#707070]"><span className="w-1.5 h-1.5 rounded-full" style={{ background: c }} />{k}</div><div className="text-[20px] font-semibold mt-1.5">{v}</div></div>
          ))}
        </div>

        {live && (
          <div className="rounded-xl border border-[#BEE8D6] bg-[#EAF8F2] p-4 flex flex-wrap items-center gap-3">
            <div className="mr-auto"><div className="text-[13.5px] font-medium">Portfolio is live (demo)</div><div className="text-[12px] font-mono text-[#444] break-all">{url}</div></div>
            <Button variant="outline" size="sm" onClick={async () => { try { await navigator.clipboard.writeText(url); toast("Link copied."); } catch { toast("Copy failed.", "error"); } }}><Copy className="w-3.5 h-3.5" />Copy</Button>
            <Button variant="outline" size="sm" onClick={() => setPreview("visitor")}><ExternalLink className="w-3.5 h-3.5" />Open</Button>
            <Button variant="danger" size="sm" onClick={async () => { setP(await portfolioService.unpublish(p)); toast("Unpublished."); }}><EyeOff className="w-3.5 h-3.5" />Unpublish</Button>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-4">
          <section className={card} aria-label="Source freshness">
            <h2 className="text-[14px] font-semibold">Source freshness</h2><p className="text-[12px] text-[#707070] mb-3">What the current portfolio is grounded in.</p>
            <ul className="flex flex-col gap-2 text-[12.5px]">
              <li className="flex items-center gap-2 rounded-lg border border-[#E7E7E7] p-2.5"><FileText className="w-4 h-4 text-[#707070]" /><span className="flex-1">Resume <span className="block text-[11px] text-[#888]">Demo fixture · {p.sources.resume}</span></span><Button size="sm" variant="outline" onClick={() => setTab("identity")}>Review</Button></li>
              <li className="flex items-center gap-2 rounded-lg border border-[#E7E7E7] p-2.5"><Github className="w-4 h-4 text-[#707070]" /><span className="flex-1">GitHub <span className="block text-[11px] text-[#888]">{p.socials.github ? "Link saved, not analysed" : "Not connected"}</span></span><Button size="sm" variant="outline" onClick={() => setTab("socials")}>Review</Button></li>
              <li className="flex items-center gap-2 rounded-lg border border-[#E7E7E7] p-2.5"><Sparkles className="w-4 h-4 text-[#707070]" /><span className="flex-1">Portfolio snapshot <span className="block text-[11px] text-[#888]">{p.sources.snapshot ? new Date(p.sources.snapshot).toLocaleString() : "Not generated yet"}</span></span></li>
            </ul>
            <p className="text-[11px] text-[#888] mt-2">Resume parsing and GitHub analysis arrive with the backend.</p>
          </section>
          <section className={card} aria-label="Regenerate">
            <div className="flex items-center"><h2 className="text-[14px] font-semibold">Regenerate</h2>{live && <Badge tone="success" className="ml-auto">Published</Badge>}</div>
            <p className="text-[12px] text-[#707070] mb-3">AI reads your resume and GitHub to build content (simulated in this build).</p>
            <Button className="w-full" disabled={busy === "regen"} onClick={() => setConfirmRegen(true)}>{busy === "regen" ? <><Loader2 className="w-4 h-4 animate-spin" />Regenerating…</> : <><Sparkles className="w-4 h-4" />Regenerate</>}</Button>
          </section>
        </div>

        <div className="rounded-xl border border-[#E7E7E7] bg-white overflow-hidden"><Preview p={p} /></div>

        <div role="tablist" aria-label="Portfolio sections" className="flex gap-1 overflow-x-auto rounded-xl border border-[#E7E7E7] bg-white p-1">
          {TABS.map(({ id: tid, label, icon: Icon }) => (
            <button key={tid} type="button" role="tab" aria-selected={tab === tid} onClick={() => setTab(tid)}
              className={cn("inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12.5px] whitespace-nowrap", tab === tid ? "bg-[#F0F0F0] font-medium" : "text-[#707070] hover:bg-[#F7F7F7]")}><Icon className="w-3.5 h-3.5" />{label}</button>
          ))}
        </div>

        <div role="tabpanel" className={card}>
          {tab === "identity" && (
            <div className="flex flex-col gap-4">
              <h3 className="text-[14px] font-semibold">Personal info</h3>
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Full name" htmlFor="fn"><Input id="fn" value={p.identity.fullName} onChange={id("fullName")} /></Field>
                <Field label="First name" htmlFor="fi"><Input id="fi" value={p.identity.firstName} onChange={id("firstName")} /></Field>
                <Field label="Job title" htmlFor="jt"><Input id="jt" value={p.identity.jobTitle} onChange={id("jobTitle")} /></Field>
                <Field label="Tagline" htmlFor="tg"><Input id="tg" value={p.identity.tagline} onChange={id("tagline")} /></Field>
              </div>
              <Field label="Bio" htmlFor="bio"><Textarea id="bio" value={p.identity.bio} onChange={id("bio")} /></Field>
              <Field label="Intro labels (comma-separated)" htmlFor="il" hint="Rotating labels shown on your portfolio hero"><Input id="il" value={p.identity.introLabels} onChange={id("introLabels")} /></Field>
              <Field label="Skills" htmlFor="sk">
                <div className="flex flex-wrap gap-1.5 mb-2">{p.identity.skills.map((s) => <Badge key={s} className="gap-1">{s}<button type="button" aria-label={`Remove ${s}`} onClick={() => update((c) => ({ ...c, identity: { ...c.identity, skills: c.identity.skills.filter((x) => x !== s) } }))}><X className="w-3 h-3" /></button></Badge>)}</div>
                <form onSubmit={(e) => { e.preventDefault(); const v = skill.trim().toLowerCase(); if (v && !p.identity.skills.includes(v)) update((c) => ({ ...c, identity: { ...c.identity, skills: [...c.identity.skills, v] } })); setSkill(""); }} className="flex gap-2">
                  <Input id="sk" value={skill} onChange={(e) => setSkill(e.target.value)} placeholder="Add a skill" /><Button type="submit" variant="outline">Add</Button>
                </form>
              </Field>
              <h3 className="text-[14px] font-semibold pt-2">Contact</h3>
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Email" htmlFor="em" error={errors.email}><Input id="em" type="email" value={p.contact.email} onChange={con("email")} onBlur={validateContact} /></Field>
                <Field label="Website" htmlFor="wb" error={errors.website}><Input id="wb" value={p.contact.website} onChange={con("website")} onBlur={validateContact} /></Field>
                <Field label="Calendar URL" htmlFor="cl" error={errors.calendar}><Input id="cl" placeholder="https://cal.com/you" value={p.contact.calendar} onChange={con("calendar")} onBlur={validateContact} /></Field>
                <Field label="Resume URL" htmlFor="rs" error={errors.resume}><Input id="rs" value={p.contact.resume} onChange={con("resume")} onBlur={validateContact} /></Field>
              </div>
            </div>
          )}
          {["projects", "experience", "education", "hacks", "research"].includes(tab) && <ListEditor key={tab} kind={tab} items={p[tab]} onChange={(items) => update((c) => ({ ...c, [tab]: items }))} />}
          {tab === "socials" && (
            <div className="grid sm:grid-cols-2 gap-4">
              {[["github", "GitHub URL"], ["linkedin", "LinkedIn URL"], ["x", "X URL"]].map(([k, l]) => <Field key={k} label={l} htmlFor={`s-${k}`} error={errors[k]}><Input id={`s-${k}`} placeholder="https://" value={p.socials[k]} onChange={soc(k)} onBlur={validateContact} /></Field>)}
              <p className="sm:col-span-2 text-[11.5px] text-[#888]">Links are saved only. GitHub OAuth and repo analysis are not connected.</p>
            </div>
          )}
          {tab === "custom" && (
            <div>
              <div className="flex justify-between items-center mb-3"><h3 className="text-[14px] font-semibold">Custom sections</h3><Button size="sm" onClick={() => update((c) => ({ ...c, custom: [...c.custom, { id: uid("cs"), title: "New section", body: "" }] }))}><Plus className="w-3.5 h-3.5" />Add section</Button></div>
              {p.custom.length === 0 && <p className="text-[13px] text-[#707070] py-6 text-center border border-dashed border-[#E7E7E7] rounded-lg">No custom sections.</p>}
              <div className="flex flex-col gap-3">{p.custom.map((c) => (
                <div key={c.id} className="rounded-lg border border-[#E7E7E7] p-3 flex flex-col gap-2">
                  <div className="flex gap-2"><Input aria-label="Section title" value={c.title} onChange={(e) => update((x) => ({ ...x, custom: x.custom.map((y) => (y.id === c.id ? { ...y, title: e.target.value } : y)) }))} />
                    <Button variant="outline" aria-label={`Delete ${c.title}`} onClick={() => update((x) => ({ ...x, custom: x.custom.filter((y) => y.id !== c.id) }))}><Trash2 className="w-4 h-4" /></Button></div>
                  <Textarea aria-label="Section content" value={c.body} onChange={(e) => update((x) => ({ ...x, custom: x.custom.map((y) => (y.id === c.id ? { ...y, body: e.target.value } : y)) }))} />
                </div>))}</div>
            </div>
          )}
        </div>

        <section className={card} aria-label="Publish">
          <h2 className="text-[14px] font-semibold flex items-center gap-1.5"><Eye className="w-4 h-4" />Publish</h2>
          <p className="text-[12px] text-[#707070] mb-3">Publishing claims yourname.{baseHost} (demo only).</p>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-[12px] text-[#707070]">https://</span>
            <Input aria-label="Username" className="w-[180px]" value={uname} onChange={(e) => setUname(e.target.value.toLowerCase())} placeholder="username" />
            <span className="font-mono text-[12px] text-[#707070]">.{baseHost}</span>
          </div>
          <p role="status" className={cn("text-[12px] mt-1.5", unameState?.available ? "text-[#13A875]" : "text-[#DC4C5C]")}>
            {unameState === "checking" ? <span className="text-[#888]">Checking…</span> : unameState ? (unameState.available ? "Username is available" : unameState.reason) : ""}
          </p>
          <Button className="w-full mt-3 h-10" disabled={busy === "publish"} onClick={publish}>{busy === "publish" ? <><Loader2 className="w-4 h-4 animate-spin" />Publishing…</> : <><Eye className="w-4 h-4" />{live ? "Update & Publish" : "Publish"}</>}</Button>
        </section>
      </div>

      <Dialog open={!!preview} onClose={() => setPreview(null)} title={preview === "visitor" ? `Visitor view · ${url}` : "Draft preview"} width={720}>
        <div className="rounded-lg border border-[#E7E7E7] overflow-hidden"><Preview p={p} /></div>
      </Dialog>
      <ConfirmDialog open={confirmRegen} onClose={() => setConfirmRegen(false)} title="Regenerate portfolio?" confirmLabel="Regenerate" message="This refreshes the generated snapshot. Your manual edits stay in place." onConfirm={regenerate} />
    </div>
  );
}
