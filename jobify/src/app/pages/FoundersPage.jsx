import React, { useEffect, useState } from "react";
import { Search, Briefcase, MapPin, ExternalLink, Unlock, Heart, Linkedin, Mail, Users } from "lucide-react";
import { founderService } from "../../services/founderService.js";
import { FOUNDER_COUNTRIES, FOUNDER_INDUSTRIES, UNLOCK_COST } from "../../mocks/founders.js";
import { useApp } from "../AppProvider.jsx";
import { Avatar, Badge, Button, EmptyState, PageHeader, Pagination, Select, Skeleton } from "../ui.jsx";
import { cn } from "../../lib/utils.js";

const PAGE_SIZE = 10;
const XIcon = () => <svg viewBox="0 0 24 24" className="w-3 h-3" fill="currentColor" aria-hidden="true"><path d="M18.9 2H22l-7.4 8.4L23 22h-6.8l-5.3-7-6.1 7H1.7l7.9-9L1.3 2h7l4.8 6.4L18.9 2Zm-1.2 18h1.9L6.6 3.9H4.6L17.7 20Z" /></svg>;

export default function FoundersPage() {
  const { toast, credits, spendCredits, plan } = useApp();
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [country, setCountry] = useState("");
  const [industry, setIndustry] = useState("");
  const [hiringOnly, setHiringOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [state, setState] = useState(() => founderService.getState());
  const [expanded, setExpanded] = useState({});

  useEffect(() => { const t = setTimeout(() => setDq(q), 200); return () => clearTimeout(t); }, [q]);
  useEffect(() => setPage(1), [dq, country, industry, hiringOnly]);
  useEffect(() => {
    let c = false;
    setData(null);
    founderService.list({ q: dq, country, industry, hiringOnly, page, pageSize: PAGE_SIZE }).then((d) => !c && setData(d));
    return () => { c = true; };
  }, [dq, country, industry, hiringOnly, page]);

  const unlock = (co) => {
    const r = founderService.unlock(co.id, credits);
    if (!r.ok) return toast(plan ? "Not enough credits to unlock." : "Choose a plan to get credits.", "error");
    if (r.cost) spendCredits(r.cost);
    setState({ ...r.state });
    toast(`Unlocked ${co.name} (demo). No real contact data is provided.`);
  };

  return (
    <div className="min-h-full">
      <PageHeader icon={Users} title="Startup Founders" sub={<span className="text-[12.5px] text-[#707070] hidden md:inline">The people behind the startups (demo data)</span>}>
        <span className="text-[12px] text-[#707070]">{credits} credits</span>
      </PageHeader>

      <div className="px-4 md:px-6 py-3 flex flex-wrap gap-2 border-b border-[#E7E7E7] bg-white">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#A0A0A0]" aria-hidden="true" />
          <input aria-label="Search founders and companies" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search founders, companies, industries…"
            className="w-full h-10 rounded-lg border border-[#E7E7E7] pl-9 pr-3 text-[13.5px] focus:outline-none focus:border-[#161616]" />
        </div>
        <Select aria-label="Country" value={country} onChange={(e) => setCountry(e.target.value)} className="w-[150px]"><option value="">All countries</option>{FOUNDER_COUNTRIES.map((c) => <option key={c}>{c}</option>)}</Select>
        <Select aria-label="Industry" value={industry} onChange={(e) => setIndustry(e.target.value)} className="w-[160px]"><option value="">All industries</option>{FOUNDER_INDUSTRIES.map((c) => <option key={c}>{c}</option>)}</Select>
        <Button variant={hiringOnly ? "primary" : "outline"} className="h-10" aria-pressed={hiringOnly} onClick={() => setHiringOnly(!hiringOnly)}><Briefcase className="w-3.5 h-3.5" />Hiring</Button>
      </div>

      <div className="max-w-[1000px] mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        {!data && Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-44" />)}
        {data?.items.map((co) => {
          const unlocked = state.unlocked.includes(co.id);
          const saved = state.saved.includes(co.id);
          const open = expanded[co.id];
          const shown = open ? co.founders : co.founders.slice(0, 2);
          return (
            <article key={co.id} className="rounded-xl border border-[#E7E7E7] bg-white overflow-hidden">
              <div className="p-4">
                <div className="flex items-start gap-3">
                  <Avatar label={co.name[0]} color={co.color} fg="#fff" square size={40} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5"><h2 className="text-[14px] font-semibold truncate">{co.name}</h2>
                      <a href={co.website} target="_blank" rel="noreferrer noopener" aria-label={`${co.name} website (demo placeholder)`} className="text-[#A0A0A0] hover:text-[#161616]"><ExternalLink className="w-3 h-3" /></a></div>
                    <p className="flex items-center gap-1 text-[12px] text-[#707070]"><MapPin className="w-3 h-3" />{co.location}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1.5">
                    {co.hiring && <Badge tone="success">Hiring</Badge>}
                    <div className="flex gap-1">
                      <button type="button" aria-pressed={saved} aria-label={saved ? `Unsave ${co.name}` : `Save ${co.name}`} onClick={() => { setState({ ...founderService.toggleSaved(co.id) }); }} className="w-8 h-7 rounded-md border border-[#E7E7E7] flex items-center justify-center hover:bg-[#F4F4F4]"><Heart className={cn("w-3.5 h-3.5", saved && "fill-[#DC4C5C] text-[#DC4C5C]")} /></button>
                      <Button size="sm" variant="outline" className="h-7 text-[12px]" onClick={() => unlock(co)} disabled={unlocked}>{unlocked ? <><Unlock className="w-3 h-3" />Unlocked</> : <><Unlock className="w-3 h-3" />Unlock · {UNLOCK_COST} credits</>}</Button>
                    </div>
                  </div>
                </div>
                <p className="mt-3 text-[13px] text-[#444]">{co.description}</p>
                <p className="mt-2 text-[11.5px] text-[#888]">{co.industry}</p>
              </div>
              <ul className="border-t border-[#F0F0F0]">
                {shown.map((f) => (
                  <li key={f.id} className="flex items-center gap-3 px-4 py-2.5 border-b border-[#F7F7F7] last:border-0">
                    <Avatar label={f.initials} size={32} />
                    <div className="min-w-0 flex-1"><div className="text-[13px] font-medium">{f.name}</div><div className="text-[11.5px] text-[#707070]">{f.role}</div>
                      {unlocked && <div className="text-[11.5px] text-[#707070] flex items-center gap-1"><Mail className="w-3 h-3" />No email in demo data</div>}</div>
                    <a href={f.linkedin} target="_blank" rel="noreferrer noopener" aria-label={`${f.name} on LinkedIn`} className="w-7 h-7 rounded-md bg-[#0A66C2]/10 text-[#0A66C2] flex items-center justify-center"><Linkedin className="w-3.5 h-3.5" /></a>
                    {f.x && <a href={f.x} target="_blank" rel="noreferrer noopener" aria-label={`${f.name} on X`} className="w-7 h-7 rounded-md bg-[#141414]/10 text-[#141414] flex items-center justify-center"><XIcon /></a>}
                  </li>
                ))}
              </ul>
              {co.founders.length > 2 && (
                <button type="button" onClick={() => setExpanded({ ...expanded, [co.id]: !open })} className="w-full py-2 text-[12px] text-[#707070] hover:bg-[#FAFAFA] border-t border-[#F0F0F0]">{open ? "Show fewer" : `Show all ${co.founders.length} founders`}</button>
              )}
            </article>
          );
        })}
      </div>
      {data && data.items.length === 0 && <EmptyState icon={Search} title="No companies found" text="Try a different search or clear the filters." action={<Button variant="outline" onClick={() => { setQ(""); setCountry(""); setIndustry(""); setHiringOnly(false); }}>Clear filters</Button>} />}
      {data && <div className="flex justify-center pb-8"><Pagination page={page} total={data.total} pageSize={PAGE_SIZE} onChange={setPage} /></div>}
    </div>
  );
}
