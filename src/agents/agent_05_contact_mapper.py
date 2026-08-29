"""
agent_05_contact_mapper.py — Contact & Warm-Path Mapper Agent.

STRATEGY
--------
Cold outreach to a generic "careers@" inbox converts far worse than reaching
the actual hiring manager or a peer engineer who can refer you internally.
This agent doesn't reinvent contact discovery — it's a thin, target-company-aware
wrapper around the already-sophisticated src/contact_intelligence.IntelligenceEngine
(graph-based PageRank contact ranking), seeded with:
  - the company's domain from config/target_companies.yml
  - the specific role title from agent_02_ats_hunter.py / agent_03_fit_scorer.py

It exists as its own agent (rather than calling IntelligenceEngine directly
from the orchestrator) so that:
  1. Company-tier gating lives in one place (don't burn contact-discovery
     API budget on tier-3 "Low" hiring-probability companies).
  2. Results are cached per (company, role_title) in agent_state.db so
     re-running the pipeline daily doesn't re-hit external contact APIs.

DAG node contract:
    Input:  AgentContext, company: str, role_title: str, domain: str = ""
    Output: AgentResult.data = {
        "top_contact": {...} | None, "outreach_order": [...], "company_size_est": int
    }
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

from .base import AgentContext, AgentResult, BaseAgent, get_state_conn

try:
    from src.contact_intelligence.intelligence_engine import IntelligenceEngine
    _CI_AVAILABLE = True
except Exception:  # noqa: BLE001
    _CI_AVAILABLE = False

MIN_TIER_FOR_LIVE_LOOKUP = 2  # skip tier-3 "watch-list" companies by default
CACHE_TTL_SECONDS = 7 * 24 * 3600


class ContactMapperAgent(BaseAgent):
    name = "contact_mapper"

    def run(self, company: str, role_title: str, domain: str = "",
            force_refresh: bool = False) -> AgentResult:
        return self._timed(self._run, company, role_title, domain, force_refresh)

    def _run(self, company: str, role_title: str, domain: str, force_refresh: bool) -> AgentResult:
        company_cfg = self.context.company(company) or {}
        tier = company_cfg.get("tier", 99)
        domain = domain or company_cfg.get("domain", "")

        if tier > MIN_TIER_FOR_LIVE_LOOKUP:
            return AgentResult(
                agent=self.name, ok=True,
                summary=f"Skipped live contact lookup for {company} (tier {tier} — below budget threshold).",
                data={"top_contact": None, "outreach_order": [], "company_size_est": 0},
                warnings=[f"Set MIN_TIER_FOR_LIVE_LOOKUP >= {tier} to include this company."],
            )

        cached = None if force_refresh else self._read_cache(company, role_title)
        if cached:
            return AgentResult(
                agent=self.name, ok=True,
                summary=f"Contact ranking for {company} loaded from cache.",
                data=cached,
            )

        if not _CI_AVAILABLE:
            return AgentResult(
                agent=self.name, ok=False,
                summary="src.contact_intelligence.IntelligenceEngine not importable — "
                        "check its dependencies are installed.",
            )

        try:
            result = asyncio.run(self._analyze(company, domain, role_title))
        except RuntimeError:
            # already inside an event loop (e.g. called from an async caller)
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self._analyze(company, domain, role_title))

        payload = self._to_payload(result)
        self._write_cache(company, role_title, payload)

        top = payload.get("top_contact")
        top_name = top.get("name", "unnamed contact") if top else "no contact found"
        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Ranked contacts for {company}: top pick {top_name}.",
            data=payload,
        )

    @staticmethod
    async def _analyze(company: str, domain: str, role_title: str):
        engine = IntelligenceEngine()
        return await engine.analyze(company_name=company, domain=domain, job_title=role_title)

    @staticmethod
    def _to_payload(result) -> Dict[str, Any]:
        ranked = getattr(result, "ranked_contacts", []) or []

        def _c(rc):
            if is_dataclass(rc):
                return asdict(rc)
            return dict(rc) if isinstance(rc, dict) else {"name": str(rc)}

        outreach_order = [_c(rc) for rc in ranked]
        return {
            "top_contact": outreach_order[0] if outreach_order else None,
            "outreach_order": outreach_order,
            "company_size_est": getattr(result, "company_size_est", 0),
        }

    @staticmethod
    def _read_cache(company: str, role_title: str) -> Optional[Dict[str, Any]]:
        conn = get_state_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contact_cache (
                company TEXT, role_title TEXT, payload TEXT, cached_at REAL,
                PRIMARY KEY (company, role_title)
            )
        """)
        row = conn.execute(
            "SELECT payload, cached_at FROM contact_cache WHERE company=? AND role_title=?",
            (company, role_title),
        ).fetchone()
        conn.close()
        if not row:
            return None
        payload_json, cached_at = row
        if time.time() - cached_at > CACHE_TTL_SECONDS:
            return None
        return json.loads(payload_json)

    @staticmethod
    def _write_cache(company: str, role_title: str, payload: Dict[str, Any]) -> None:
        conn = get_state_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contact_cache (
                company TEXT, role_title TEXT, payload TEXT, cached_at REAL,
                PRIMARY KEY (company, role_title)
            )
        """)
        conn.execute(
            "INSERT OR REPLACE INTO contact_cache (company, role_title, payload, cached_at) VALUES (?, ?, ?, ?)",
            (company, role_title, json.dumps(payload, default=str), time.time()),
        )
        conn.commit()
        conn.close()


if __name__ == "__main__":
    ctx = AgentContext.load()
    result = ContactMapperAgent(ctx).run(company="Yubi", role_title="Backend Software Engineer")
    print(result.to_json())
