"""
agent_07_priority_scheduler.py — Priority Scheduler Agent.

STRATEGY
--------
Two facts from the research this repo is built on:
  1. Fit score alone doesn't capture timing — a 90%-fit role at a company
     that raised money 11 months ago is a worse bet *this week* than an
     80%-fit role at a company that filed its DRHP 3 days ago.
  2. You can't email all 20 target companies at once without it reading as
     spam-cannon outreach. Something has to rank the queue.

This agent combines:
  - fit_score        (from agent_03_fit_scorer.py, 0-100)
  - signal_freshness  (from agent_01_signal_scout.py; exponential decay,
                        half-life = HALF_LIFE_DAYS)
  - tier_weight       (tier 1 target companies get a floor boost)
  - learned_weight    (from agent_09_feedback_strategist.py; starts at 1.0,
                        adjusted based on which signal_types/company tiers
                        have actually converted to replies)

...into a single priority_score, and writes the day's send queue into
data/agent_state.db (priority_queue table) capped at MAX_DAILY_SENDS so
outreach stays deliberate, not spray-and-pray.

DAG node contract:
    Input:  AgentContext, scored_roles: List[dict] (from agent_03),
            signals: List[dict] (from agent_01)
    Output: AgentResult.data = {"queue": [...] top MAX_DAILY_SENDS, "all_ranked": [...]}
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List

from .base import AgentContext, AgentResult, BaseAgent, get_state_conn

HALF_LIFE_DAYS = 30.0     # signal loses half its "freshness boost" every 30 days
MAX_DAILY_SENDS = 8       # deliberate cadence, not spam-cannon
TIER_FLOOR_BOOST = {1: 15.0, 2: 5.0, 3: 0.0}


class PriorityScheduleAgent(BaseAgent):
    name = "priority_scheduler"

    def run(self, scored_roles: List[Dict[str, Any]], signals: List[Dict[str, Any]]) -> AgentResult:
        return self._timed(self._run, scored_roles, signals)

    def _run(self, scored_roles: List[Dict[str, Any]], signals: List[Dict[str, Any]]) -> AgentResult:
        freshest_age_by_company = self._freshest_age_by_company(signals)
        learned_weights = self._load_learned_weights()

        ranked = []
        for role in scored_roles:
            company = role.get("company", "unknown")
            company_cfg = self.context.company(company) or {}
            tier = company_cfg.get("tier", 99)

            age_days = freshest_age_by_company.get(company)
            freshness_boost = self._decay(age_days) * 20.0  # up to +20 pts for very fresh signal
            tier_boost = TIER_FLOOR_BOOST.get(tier, 0.0)
            learned_mult = learned_weights.get(f"tier:{tier}", 1.0)

            base_score = role.get("score", 0.0)
            priority = (base_score + freshness_boost + tier_boost) * learned_mult

            ranked.append({
                "company": company,
                "title": role.get("title", ""),
                "url": role.get("url", ""),
                "fit_score": base_score,
                "freshness_boost": round(freshness_boost, 1),
                "tier_boost": tier_boost,
                "learned_multiplier": round(learned_mult, 2),
                "priority_score": round(priority, 1),
                "recommendation": role.get("recommendation", "Skip"),
            })

        ranked.sort(key=lambda r: r["priority_score"], reverse=True)
        # Only queue roles that already cleared the fit-scorer's floor threshold.
        queueable = [r for r in ranked if r["recommendation"] != "Skip"]
        queue = queueable[:MAX_DAILY_SENDS]

        self._persist_queue(queue)

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Ranked {len(ranked)} roles; queued top {len(queue)} for outreach today "
                    f"(cap={MAX_DAILY_SENDS}).",
            data={"queue": queue, "all_ranked": ranked},
        )

    @staticmethod
    def _decay(age_days) -> float:
        """Exponential decay, 1.0 at age=0, 0.5 at HALF_LIFE_DAYS, ~0 for old/unknown signals."""
        if age_days is None:
            return 0.0
        return math.pow(0.5, age_days / HALF_LIFE_DAYS)

    @staticmethod
    def _freshest_age_by_company(signals: List[Dict[str, Any]]) -> Dict[str, float]:
        # Signals arrive pre-computed with an "age_days" or via hot_companies
        # shape from agent_01; support both.
        out: Dict[str, float] = {}
        for s in signals:
            company = s.get("company")
            age = s.get("freshest_signal_age_days", s.get("age_days"))
            if company is None or age is None:
                continue
            if company not in out or age < out[company]:
                out[company] = age
        return out

    @staticmethod
    def _load_learned_weights() -> Dict[str, float]:
        conn = get_state_conn()
        rows = conn.execute("SELECT key, weight FROM strategy_weights").fetchall()
        conn.close()
        return {k: v for k, v in rows} if rows else {}

    @staticmethod
    def _persist_queue(queue: List[Dict[str, Any]]) -> None:
        conn = get_state_conn()
        now = time.time()
        for item in queue:
            conn.execute(
                "INSERT INTO priority_queue (company, role_title, priority_score, reason, queued_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (item["company"], item["title"], item["priority_score"],
                 f"fit={item['fit_score']} fresh_boost={item['freshness_boost']} tier_boost={item['tier_boost']}",
                 now),
            )
        conn.commit()
        conn.close()


if __name__ == "__main__":
    ctx = AgentContext.load()
    demo_roles = [
        {"company": "SolarSquare", "title": "Backend Engineer", "score": 78.0, "recommendation": "Apply"},
        {"company": "Zenatix", "title": "Backend Engineer", "score": 90.0, "recommendation": "Apply"},
    ]
    demo_signals = [
        {"company": "SolarSquare", "freshest_signal_age_days": 10},
        {"company": "Zenatix", "freshest_signal_age_days": 900},
    ]
    result = PriorityScheduleAgent(ctx).run(demo_roles, demo_signals)
    print(result.to_json())
