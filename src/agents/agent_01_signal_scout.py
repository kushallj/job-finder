"""
agent_01_signal_scout.py — Signal Scout Agent.

STRATEGY
--------
The single biggest lever in this whole system is timing: outreach sent
within ~2-4 weeks of a funding round, IPO filing, or leadership hire gets
read differently than a cold email sent to a company that hasn't been in
the news in a year. This agent's only job is to keep config/target_companies.yml
signals fresh and flag which companies just got "hot."

DAG node contract:
    Input:  AgentContext (config/target_companies.yml already loaded)
    Output: AgentResult.data = {
        "hot_companies": [...],       # signals < HOT_WINDOW_DAYS old
        "stale_companies": [...],     # no signal refresh in STALE_WINDOW_DAYS
        "all_signals": [...],
    }

Sourcing (in priority order):
  1. Manually-curated signals already in config/target_companies.yml
     (the labor-market research baked in at repo setup time).
  2. Optional live refresh via web search / RSS if WebSearch tooling is
     wired up by the caller (Claude Code, n8n, etc.) — this agent exposes
     `ingest_signal()` for that purpose; it does not itself scrape, to
     avoid duplicating src/personalization/company_researcher.py.

Persistence: writes every signal into data/agent_state.db (company_signals
table) so agent_07_priority_scheduler.py can compute freshness decay.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List

from .base import AgentContext, AgentResult, BaseAgent, get_state_conn

HOT_WINDOW_DAYS = 45     # signal age below which a company is "hot"
STALE_WINDOW_DAYS = 180  # signal age above which a company needs re-verification


@dataclass
class Signal:
    company: str
    signal_type: str   # funding | ipo_filing | expansion | leadership | product | acquisition | financials
    detail: str
    source: str
    date: str           # ISO-ish string, e.g. "2026-06-30" or "2026"


class SignalScoutAgent(BaseAgent):
    name = "signal_scout"

    def run(self, refresh_from_web: bool = False) -> AgentResult:
        return self._timed(self._run, refresh_from_web)

    def _run(self, refresh_from_web: bool) -> AgentResult:
        conn = get_state_conn()
        cur = conn.cursor()

        # 1. Load baked-in signals from target_companies.yml into local state
        #    (idempotent — skips exact duplicates).
        ingested = 0
        for company in self.context.companies:
            name = company.get("name", "unknown")
            for sig in company.get("signals", []):
                exists = cur.execute(
                    "SELECT 1 FROM company_signals WHERE company=? AND signal_type=? AND detail=?",
                    (name, sig.get("type"), sig.get("detail")),
                ).fetchone()
                if exists:
                    continue
                cur.execute(
                    "INSERT INTO company_signals (company, signal_type, detail, source, signal_date, discovered_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (name, sig.get("type"), sig.get("detail"), sig.get("source"),
                     str(sig.get("date")), time.time()),
                )
                ingested += 1
        conn.commit()

        if refresh_from_web:
            self.log.info(
                "refresh_from_web=True but this agent does not scrape directly — "
                "call ingest_signal() from a WebSearch-capable caller (Claude Code /nexus deep, "
                "n8n workflow, etc.) and re-run this agent to recompute freshness."
            )

        # 2. Classify hot vs stale
        hot, stale, all_signals = [], [], []
        now = datetime.utcnow()
        seen_companies = {}
        for row in cur.execute(
            "SELECT company, signal_type, detail, source, signal_date, discovered_at FROM company_signals"
        ):
            company, sig_type, detail, source, sig_date, discovered_at = row
            all_signals.append({
                "company": company, "type": sig_type, "detail": detail,
                "source": source, "date": sig_date,
            })
            age_days = self._estimate_age_days(sig_date, now)
            prev = seen_companies.get(company)
            if prev is None or age_days < prev:
                seen_companies[company] = age_days

        for company, age_days in seen_companies.items():
            if age_days is None:
                continue
            if age_days <= HOT_WINDOW_DAYS:
                hot.append({"company": company, "freshest_signal_age_days": age_days})
            elif age_days >= STALE_WINDOW_DAYS:
                stale.append({"company": company, "freshest_signal_age_days": age_days})

        hot.sort(key=lambda x: x["freshest_signal_age_days"])
        conn.close()

        return AgentResult(
            agent=self.name,
            ok=True,
            summary=f"{ingested} new signals ingested; {len(hot)} companies hot, {len(stale)} stale.",
            data={"hot_companies": hot, "stale_companies": stale, "all_signals": all_signals},
        )

    def ingest_signal(self, sig: Signal) -> None:
        """Manual/external hook — call this after a WebSearch/deep-research pass
        (e.g. from `/nexus deep <company>`) to add a freshly-discovered signal."""
        conn = get_state_conn()
        conn.execute(
            "INSERT INTO company_signals (company, signal_type, detail, source, signal_date, discovered_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (sig.company, sig.signal_type, sig.detail, sig.source, sig.date, time.time()),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def _estimate_age_days(sig_date: str, now: datetime):
        """Best-effort parse of dates like '2026-06-30', '2026-06', or '2026'."""
        for fmt in ("%Y-%m-%d", "%Y-%m"):
            try:
                dt = datetime.strptime(sig_date, fmt)
                return (now - dt).days
            except ValueError:
                continue
        if sig_date.isdigit() and len(sig_date) == 4:
            # Year-only signal — treat as mid-year for a rough estimate.
            dt = datetime(int(sig_date), 6, 30)
            return max((now - dt).days, 0)
        return None


if __name__ == "__main__":
    logging_ctx = AgentContext.load()
    result = SignalScoutAgent(logging_ctx).run()
    print(result.to_json())
