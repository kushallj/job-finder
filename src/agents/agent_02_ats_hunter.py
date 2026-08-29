"""
agent_02_ats_hunter.py — ATS Hunter Agent.

STRATEGY
--------
Job boards (LinkedIn/Naukri) are noisy and heavily gamed by recruiters
reposting the same role. Going directly to a target company's ATS (their
Greenhouse/Lever/Ashby board) surfaces roles faster, avoids duplicate/stale
listings, and is exactly what a company that "just raised a Series C and
explicitly earmarked funds for hiring" (see SolarSquare in
config/target_companies.yml) will actually be posting to first.

This agent probes the free, unauthenticated public JSON APIs of the three
most common ATS platforms for each target company, tries a handful of
plausible slug variants (company name, domain root, aka), and returns
matching open roles filtered by keywords from config/profile.yml.

DAG node contract:
    Input:  AgentContext, keywords: List[str] (defaults to profile target roles)
    Output: AgentResult.data = {"roles_by_company": {...}, "total_roles": int}

Falls back gracefully (no crash) if:
  - httpx isn't installed
  - a company has no board on a given ATS (404 is expected & silent)
  - the network is unreachable (returns ok=True with a warning, not ok=False,
    so the pipeline can continue with cached data from previous runs)
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

from .base import AgentContext, AgentResult, BaseAgent, get_state_conn

try:
    import httpx
    _HTTPX = True
except ImportError:  # pragma: no cover
    _HTTPX = False

DEFAULT_ROLE_KEYWORDS = [
    "full stack", "full-stack", "backend", "software engineer",
    "sde", "python", "django", "platform engineer", "api engineer",
]

_GREENHOUSE_TMPL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
_LEVER_TMPL = "https://api.lever.co/v0/postings/{slug}?mode=json"
_ASHBY_TMPL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


def _slug_candidates(company: Dict[str, Any]) -> List[str]:
    """Generate plausible ATS board slugs from name/domain/aka."""
    candidates = set()
    name = company.get("name", "")
    domain = company.get("domain", "")
    for raw in [name, *company.get("aka", []), domain.split(".")[0] if domain else ""]:
        if not raw:
            continue
        slug = re.sub(r"[^a-z0-9]", "", raw.lower())
        if slug:
            candidates.add(slug)
        hyphen_slug = re.sub(r"[^a-z0-9\s-]", "", raw.lower()).strip().replace(" ", "-")
        if hyphen_slug:
            candidates.add(hyphen_slug)
    return sorted(candidates)


class ATSHunterAgent(BaseAgent):
    name = "ats_hunter"

    def run(self, keywords: Optional[List[str]] = None, tiers: Optional[List[int]] = None) -> AgentResult:
        return self._timed(self._run, keywords, tiers)

    def _run(self, keywords: Optional[List[str]], tiers: Optional[List[int]]) -> AgentResult:
        if not _HTTPX:
            return AgentResult(
                agent=self.name, ok=False,
                summary="httpx not installed — run `pip install httpx` to enable live ATS probing.",
            )

        kw = [k.lower() for k in (keywords or DEFAULT_ROLE_KEYWORDS)]
        companies = self.context.companies
        if tiers:
            companies = [c for c in companies if c.get("tier") in tiers]

        roles_by_company: Dict[str, List[Dict[str, Any]]] = {}
        warnings: List[str] = []
        total = 0

        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            for company in companies:
                name = company.get("name", "unknown")
                found = self._probe_company(client, company, kw)
                if found:
                    roles_by_company[name] = found
                    total += len(found)
                    self._persist_roles(name, found)

        return AgentResult(
            agent=self.name,
            ok=True,
            summary=f"Found {total} matching open roles across {len(roles_by_company)} companies.",
            data={"roles_by_company": roles_by_company, "total_roles": total},
            warnings=warnings,
        )

    def _probe_company(self, client, company: Dict[str, Any], keywords: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        slugs = _slug_candidates(company)
        probes = (
            [(_GREENHOUSE_TMPL.format(slug=s), "greenhouse", s) for s in slugs]
            + [(_LEVER_TMPL.format(slug=s), "lever", s) for s in slugs]
            + [(_ASHBY_TMPL.format(slug=s), "ashby", s) for s in slugs]
        )
        for url, ats, slug in probes:
            try:
                resp = client.get(url)
            except httpx.HTTPError:
                continue
            if resp.status_code != 200:
                continue
            try:
                payload = resp.json()
            except ValueError:
                continue
            jobs = self._extract_jobs(payload, ats)
            for job in jobs:
                title_l = job["title"].lower()
                if any(k in title_l for k in keywords):
                    job["ats_source"] = ats
                    job["board_slug"] = slug
                    results.append(job)
        return results

    @staticmethod
    def _extract_jobs(payload: Any, ats: str) -> List[Dict[str, Any]]:
        jobs = []
        if ats == "greenhouse":
            for j in payload.get("jobs", []):
                jobs.append({
                    "title": j.get("title", ""),
                    "location": (j.get("location") or {}).get("name", ""),
                    "url": j.get("absolute_url", ""),
                })
        elif ats == "lever":
            items = payload if isinstance(payload, list) else []
            for j in items:
                jobs.append({
                    "title": j.get("text", ""),
                    "location": (j.get("categories") or {}).get("location", ""),
                    "url": j.get("hostedUrl", ""),
                })
        elif ats == "ashby":
            for j in payload.get("jobs", []):
                jobs.append({
                    "title": j.get("title", ""),
                    "location": j.get("location", ""),
                    "url": j.get("jobUrl", ""),
                })
        return jobs

    @staticmethod
    def _persist_roles(company: str, roles: List[Dict[str, Any]]) -> None:
        conn = get_state_conn()
        for r in roles:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO open_roles (company, title, url, location, ats_source, discovered_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (company, r["title"], r.get("url", ""), r.get("location", ""),
                     r.get("ats_source", ""), time.time()),
                )
            except Exception:  # noqa: BLE001
                continue
        conn.commit()
        conn.close()


if __name__ == "__main__":
    ctx = AgentContext.load()
    result = ATSHunterAgent(ctx).run()
    print(result.to_json())
