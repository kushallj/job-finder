import React, { useEffect, useMemo, useState } from "react";
import { Search, SlidersHorizontal, Briefcase, Bookmark, BookmarkCheck, MapPin, X } from "lucide-react";
import { jobService } from "../../services/jobService.js";
import { applicationService } from "../../services/applicationService.js";
import { JOB_FILTER_OPTIONS as OPT } from "../../mocks/jobs.js";
import { useApp } from "../AppProvider.jsx";
import { Avatar, Badge, Button, Dialog, EmptyState, Field, PageHeader, Pagination, Select, Skeleton } from "../ui.jsx";
import { cn } from "../../lib/utils.js";

const PAGE_SIZE = 20;
const EMPTY = { workModes: [], types: [], countries: [], skills: [], minSalaryUsd: 0, maxYears: null, matchOnly: false };
const modeTone = { Remote: "success", Hybrid: "neutral", Onsite: "neutral" };

function MatchBar({ value }) {
  const color = value >= 85 ? "#13A875" : value >= 75 ? "#EBAA20" : "#A0A0A0";
  return (
    <div className="flex items-center gap-2">
      <div className="w-[140px] h-1.5 rounded-full bg-[#EEE] overflow-hidden" role="presentation"><div style={{ width: `${value}%`, background: color }} className="h-full rounded-full" /></div>
      <span className="text-[12.5px] font-medium tabular-nums w-9">{value}%</span>
    </div>
  );
}

const Chip = ({ active, onClick, children }) => (
  <button type="button" aria-pressed={active} onClick={onClick}
    className={cn("h-8 px-3 rounded-full border text-[12.5px]", active ? "bg-[#141414] text-white border-[#141414]" : "bg-white border-[#E7E7E7] hover:bg-[#F4F4F4]")}>{children}</button>
);

const toggle = (arr, v) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

export default function JobsPage() {
  const { toast } = useApp();
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [filters, setFilters] = useState(EMPTY);
  const [draft, setDraft] = useState(EMPTY);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [sort, setSort] = useState("match");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [user, setUser] = useState(() => jobService.getUserState());
  const [detail, setDetail] = useState(null);

  useEffect(() => { const t = setTimeout(() => setDebounced(q), 200); return () => clearTimeout(t); }, [q]);
  useEffect(() => setPage(1), [debounced, filters, sort]);
  useEffect(() => {
    let cancelled = false;
    setData(null); setError(false);
    jobService.list({ q: debounced, ...filters, sort, page, pageSize: PAGE_SIZE })
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setError(true));
    return () => { cancelled = true; };
  }, [debounced, filters, sort, page]);

  const activeCount = useMemo(
    () => filters.workModes.length + filters.types.length + filters.countries.length + filters.skills.length + (filters.minSalaryUsd ? 1 : 0) + (filters.maxYears !== null ? 1 : 0) + (filters.matchOnly ? 1 : 0),
    [filters]
  );

  const saveToggle = (job) => {
    const s = jobService.toggleSaved(job.id);
    setUser({ ...s });
    toast(s.saved.includes(job.id) ? "Job saved." : "Removed from saved.");
  };

  const apply = async (job) => {
    jobService.markApplied(job.id);
    await applicationService.create({ company: job.company, position: job.title, subject: "Marked as applied in Jobify", sender: "", source: "job" });
    setUser(jobService.getUserState());
    toast("Marked as applied and added to Applications. No application was sent to the company.");
  };

  const rows = data?.items || [];

  return (
    <div className="min-h-full bg-white">
      <PageHeader icon={Briefcase} title="Jobs">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#A0A0A0]" aria-hidden="true" />
          <input aria-label="Search jobs" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…"
            className="h-9 w-[180px] sm:w-[220px] rounded-lg border border-[#E7E7E7] pl-8 pr-3 text-[13px] focus:outline-none focus:border-[#161616]" />
        </div>
        <label className="sr-only" htmlFor="sort">Sort by</label>
        <Select id="sort" value={sort} onChange={(e) => setSort(e.target.value)} className="h-9 w-[130px] text-[13px]">
          <option value="match">Best match</option><option value="recent">Most recent</option><option value="salary">Salary</option><option value="title">Title A–Z</option>
        </Select>
        <Button variant="outline" onClick={() => { setDraft(filters); setFiltersOpen(true); }}>
          <SlidersHorizontal className="w-3.5 h-3.5" />Filters{activeCount > 0 && <span className="ml-1 text-[11px] bg-[#141414] text-white rounded-full px-1.5">{activeCount}</span>}
        </Button>
      </PageHeader>

      {/* Desktop table */}
      <div className="hidden lg:block overflow-x-auto">
        <table className="w-full text-[13px] min-w-[1000px]">
          <thead>
            <tr className="text-left text-[12px] text-[#707070] border-b border-[#E7E7E7] bg-[#FAFAFA]">
              {["Role", "Location", "Experience", "Skills", "Match %", "Work mode", "Action"].map((h) => <th key={h} scope="col" className="font-medium px-4 py-3 first:pl-6 last:pr-6 last:text-right">{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {!data && !error && Array.from({ length: 8 }, (_, i) => <tr key={i}><td colSpan={7} className="px-6 py-3"><Skeleton className="h-8" /></td></tr>)}
            {rows.map((j) => (
              <tr key={j.id} className="border-b border-[#F0F0F0] hover:bg-[#FAFAFA] cursor-pointer" onClick={() => setDetail(j)}>
                <td className="px-4 pl-6 py-1.5">
                  <div className="flex items-center gap-3">
                    <Avatar label={j.company[0]} color={j.companyColor} fg="#fff" square size={32} />
                    <div className="min-w-0"><div className="font-medium truncate">{j.title}</div><div className="text-[12px] text-[#707070]">{j.company}</div></div>
                  </div>
                </td>
                <td className="px-4 text-[#444]">{j.location}</td>
                <td className="px-4"><div>{j.experience}</div><div className="text-[12px] text-[#707070]">{j.salary}</div></td>
                <td className="px-4"><div className="flex gap-1.5 flex-wrap">{j.skills.slice(0, 2).map((s) => <Badge key={s} className="border border-[#E7E7E7] bg-white">{s}</Badge>)}{j.skills.length > 2 && <Badge className="border border-[#E7E7E7] bg-white">+{j.skills.length - 2}</Badge>}</div></td>
                <td className="px-4"><MatchBar value={j.match} /></td>
                <td className="px-4"><Badge tone={modeTone[j.workMode]}>{j.workMode}</Badge></td>
                <td className="px-4 pr-6 text-right"><button type="button" className="font-medium hover:underline" onClick={(e) => { e.stopPropagation(); setDetail(j); }} aria-label={`View ${j.title} at ${j.company}`}>View</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile / tablet cards */}
      <ul className="lg:hidden p-4 flex flex-col gap-3">
        {!data && !error && Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-28" />)}
        {rows.map((j) => (
          <li key={j.id}>
            <button type="button" onClick={() => setDetail(j)} className="w-full text-left rounded-xl border border-[#E7E7E7] p-4 hover:bg-[#FAFAFA]">
              <div className="flex items-start gap-3">
                <Avatar label={j.company[0]} color={j.companyColor} fg="#fff" square size={36} />
                <div className="min-w-0 flex-1"><div className="font-medium text-[14px]">{j.title}</div><div className="text-[12.5px] text-[#707070]">{j.company}</div></div>
                <span className="text-[13px] font-semibold">{j.match}%</span>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-[#707070]">
                <span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" />{j.location}</span><span>{j.experience}</span><span>{j.salary}</span><Badge tone={modeTone[j.workMode]}>{j.workMode}</Badge>
              </div>
            </button>
          </li>
        ))}
      </ul>

      {error && <EmptyState title="Couldn't load jobs" text="Something went wrong." action={<Button variant="outline" onClick={() => setFilters({ ...filters })}>Retry</Button>} />}
      {data && rows.length === 0 && (
        <EmptyState icon={Search} title="No roles match your search" text="Try removing filters or searching for a different term."
          action={<Button variant="outline" onClick={() => { setQ(""); setFilters({ ...EMPTY, matchOnly: false }); }}>Clear search and filters</Button>} />
      )}

      <div className="flex items-center justify-between px-4 md:px-6 py-3 border-t border-[#E7E7E7] text-[12.5px] text-[#707070] sticky bottom-0 bg-white">
        <span>{data ? (data.total ? `Showing ${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, data.total)} of ${data.total} roles (demo data)` : "0 roles") : "Loading…"}</span>
        {data && <Pagination page={page} total={data.total} pageSize={PAGE_SIZE} onChange={setPage} />}
      </div>

      <Dialog open={filtersOpen} onClose={() => setFiltersOpen(false)} title="Filters" side width={400}
        footer={<>
          <Button variant="ghost" onClick={() => setDraft({ ...EMPTY, matchOnly: false })}>Reset</Button>
          <Button onClick={() => { setFilters(draft); setFiltersOpen(false); }}>Apply filters</Button>
        </>}>
        <div className="flex flex-col gap-5">
          <label className="flex items-center gap-2 text-[13px]"><input type="checkbox" checked={draft.matchOnly} onChange={(e) => setDraft({ ...draft, matchOnly: e.target.checked })} />Strong matches only (80%+)</label>
          <Field label="Work mode"><div className="flex flex-wrap gap-2">{OPT.workModes.map((m) => <Chip key={m} active={draft.workModes.includes(m)} onClick={() => setDraft({ ...draft, workModes: toggle(draft.workModes, m) })}>{m}</Chip>)}</div></Field>
          <Field label="Employment type"><div className="flex flex-wrap gap-2">{OPT.types.map((m) => <Chip key={m} active={draft.types.includes(m)} onClick={() => setDraft({ ...draft, types: toggle(draft.types, m) })}>{m}</Chip>)}</div></Field>
          <Field label="Country"><div className="flex flex-wrap gap-2">{OPT.countries.map((m) => <Chip key={m} active={draft.countries.includes(m)} onClick={() => setDraft({ ...draft, countries: toggle(draft.countries, m) })}>{m}</Chip>)}</div></Field>
          <Field label="Skills"><div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto">{OPT.skills.map((m) => <Chip key={m} active={draft.skills.includes(m)} onClick={() => setDraft({ ...draft, skills: toggle(draft.skills, m) })}>{m}</Chip>)}</div></Field>
          <Field label="Max years of experience" htmlFor="yrs">
            <Select id="yrs" value={draft.maxYears ?? ""} onChange={(e) => setDraft({ ...draft, maxYears: e.target.value === "" ? null : Number(e.target.value) })}>
              <option value="">Any</option><option value="0">Entry level / internship</option><option value="2">Up to 2 years</option><option value="5">Up to 5 years</option><option value="8">Up to 8 years</option>
            </Select>
          </Field>
          <Field label="Minimum salary (USD equivalent)" htmlFor="sal">
            <Select id="sal" value={draft.minSalaryUsd} onChange={(e) => setDraft({ ...draft, minSalaryUsd: Number(e.target.value) })}>
              <option value={0}>Any</option><option value={5000}>$5K+</option><option value={30000}>$30K+</option><option value={60000}>$60K+</option><option value={120000}>$120K+</option>
            </Select>
          </Field>
        </div>
      </Dialog>

      <Dialog open={!!detail} onClose={() => setDetail(null)} title={detail?.title || ""} side width={520}
        footer={detail && <>
          <Button variant="outline" onClick={() => saveToggle(detail)}>{user.saved.includes(detail.id) ? <><BookmarkCheck className="w-4 h-4" />Saved</> : <><Bookmark className="w-4 h-4" />Save</>}</Button>
          <Button disabled={user.applied.includes(detail.id)} onClick={() => apply(detail)}>{user.applied.includes(detail.id) ? "Marked as applied" : "Mark as applied"}</Button>
        </>}>
        {detail && (
          <div className="flex flex-col gap-4 text-[13.5px]">
            <div className="flex items-center gap-3"><Avatar label={detail.company[0]} color={detail.companyColor} fg="#fff" square size={40} /><div><div className="font-medium">{detail.company}</div><div className="text-[12.5px] text-[#707070]">{detail.location} · {detail.workMode}</div></div><Badge tone="success" className="ml-auto">{detail.match}% match</Badge></div>
            <dl className="grid grid-cols-2 gap-3 text-[13px]">
              {[["Experience", detail.experience], ["Salary", detail.salary], ["Type", detail.type], ["Posted", `${detail.postedDaysAgo}d ago`]].map(([k, v]) => <div key={k}><dt className="text-[11.5px] text-[#707070]">{k}</dt><dd>{v}</dd></div>)}
            </dl>
            <div className="flex flex-wrap gap-1.5">{detail.skills.map((s) => <Badge key={s} className="border border-[#E7E7E7] bg-white">{s}</Badge>)}</div>
            <p className="leading-relaxed text-[#444]">{detail.description}</p>
            <div><h3 className="text-[12.5px] font-semibold mb-1">Responsibilities</h3><ul className="list-disc pl-5 text-[#444] space-y-0.5">{detail.responsibilities.map((r) => <li key={r}>{r}</li>)}</ul></div>
            <p className="text-[11.5px] text-[#888] flex items-start gap-1"><X className="w-3 h-3 mt-0.5 hidden" />Demo listing. "Mark as applied" only records it in Jobify; nothing is submitted to {detail.company}.</p>
          </div>
        )}
      </Dialog>
    </div>
  );
}
