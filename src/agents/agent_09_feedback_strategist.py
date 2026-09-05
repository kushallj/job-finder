"""
agent_09_feedback_strategist.py — Feedback & Strategy Learning Agent.

STRATEGY
--------
src/feedback/feedback_loop.py already learns hook-type weights and best
send-hours from OutreachRecord history — this agent doesn't duplicate that.
It closes a gap that's specific to a *target-company-list* strategy: does
outreach to Tier-1 ("High" hiring probability) companies actually convert
better than Tier-2/3? Does chasing fresh funding signals actually beat
outreach to companies with stale signals? Those are testable questions this
repo's target_companies.yml/signal-scout design makes, and answering them
is what should adjust agent_07_priority_scheduler.py's tier weighting over
time — otherwise "Tier 1 = High probability" stays a static, one-time
research judgment forever instead of an assumption this system tests.

Method:
  1. Pull OutreachRecord rows (existing src.models table) joined to Job.company.
  2. Map each company to its target_companies.yml tier via AgentContext.
  3. Compute reply_rate per tier = replied / sent.
  4. Normalize into a multiplier around 1.0 (mean tier performance = 1.0)
     with a dampening factor so a handful of early data points can't
     wildly swing priorities — min data points enforced (MIN_SAMPLE_SIZE).
  5. Write multipliers into agent_state.db `strategy_weights` table under
     keys like "tier:1", "tier:2" — consumed directly by
     agent_07_priority_scheduler.py.

Degrades gracefully: if src.database / OutreachRecord aren't queryable
(fresh repo, no sends yet), leaves weights at the neutral default (1.0)
rather than erroring the whole pipeline.

DAG node contract:
    Input:  AgentContext
    Output: AgentResult.data = {"tier_reply_rates": {...}, "new_weights": {...}}
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict

from .base import AgentContext, AgentResult, BaseAgent, get_state_conn

MIN_SAMPLE_SIZE = 5     # don't reweight off fewer than this many sends per tier
DAMPENING = 0.5          # 0 = ignore new data, 1 = fully trust new data each run
WEIGHT_FLOOR = 0.6
WEIGHT_CEIL = 1.5

try:
    from src.database import SessionLocal
    from src.models import Job, OutreachRecord
    _DB_AVAILABLE = True
except Exception:  # noqa: BLE001
    _DB_AVAILABLE = False


class FeedbackStrategistAgent(BaseAgent):
    name = "feedback_strategist"

    def run(self) -> AgentResult:
        return self._timed(self._run)

    def _run(self) -> AgentResult:
        if not _DB_AVAILABLE:
            return AgentResult(
                agent=self.name, ok=True,
                summary="src.database/OutreachRecord not importable — keeping neutral (1.0) tier weights.",
                data={"tier_reply_rates": {}, "new_weights": {}},
                warnings=["Run once outreach has actually been sent through the main DB-backed pipeline."],
            )

        try:
            tier_stats = self._compute_tier_reply_rates()
        except Exception as exc:  # noqa: BLE001
            return AgentResult(
                agent=self.name, ok=True,
                summary=f"Could not query outreach history ({exc}) — keeping neutral tier weights.",
                data={"tier_reply_rates": {}, "new_weights": {}},
                warnings=[str(exc)],
            )

        new_weights = self._blend_weights(tier_stats)
        self._persist_weights(new_weights)

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Updated {len(new_weights)} tier weight(s) from {sum(s['sent'] for s in tier_stats.values())} sends.",
            data={"tier_reply_rates": tier_stats, "new_weights": new_weights},
        )

    def _compute_tier_reply_rates(self) -> Dict[str, Dict[str, float]]:
        session = SessionLocal()
        try:
            rows = (
                session.query(OutreachRecord.status, Job.company)
                .join(Job, OutreachRecord.job_id == Job.id)
                .all()
            )
            from src.models import OutreachFunnelEvent
            funnel_events = session.query(OutreachFunnelEvent).all()
        except Exception:
            funnel_events = []
        finally:
            session.close()

        sent_by_tier: Dict[int, int] = defaultdict(int)
        replied_by_tier: Dict[int, int] = defaultdict(int)

        for status, company in rows:
            company_cfg = self.context.company(company or "") or {}
            tier = company_cfg.get("tier", 99)
            sent_by_tier[tier] += 1
            if status in ("replied",):
                replied_by_tier[tier] += 1

        for evt in funnel_events:
            company_cfg = self.context.company(evt.company or "") or {}
            tier = company_cfg.get("tier", 99)
            if evt.event_type in ("email_sent",):
                sent_by_tier[tier] += 1
            elif evt.event_type in ("reply_received", "interview_scheduled", "offer_received"):
                replied_by_tier[tier] += 1
                sent_by_tier[tier] = max(sent_by_tier[tier], replied_by_tier[tier])


        stats = {}
        for tier, sent in sent_by_tier.items():
            replied = replied_by_tier.get(tier, 0)
            stats[str(tier)] = {
                "sent": sent, "replied": replied,
                "reply_rate": round(replied / sent, 3) if sent else 0.0,
            }
        return stats

    def _blend_weights(self, tier_stats: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        eligible = {t: s for t, s in tier_stats.items() if s["sent"] >= MIN_SAMPLE_SIZE}
        if not eligible:
            return {}

        mean_rate = sum(s["reply_rate"] for s in eligible.values()) / len(eligible)
        if mean_rate == 0:
            return {}

        current = self._load_current_weights()
        new_weights = {}
        for tier, s in eligible.items():
            key = f"tier:{tier}"
            relative = s["reply_rate"] / mean_rate  # 1.0 = average performer
            prior = current.get(key, 1.0)
            blended = prior * (1 - DAMPENING) + relative * DAMPENING
            new_weights[key] = round(min(WEIGHT_CEIL, max(WEIGHT_FLOOR, blended)), 3)
        return new_weights

    @staticmethod
    def _load_current_weights() -> Dict[str, float]:
        conn = get_state_conn()
        rows = conn.execute("SELECT key, weight FROM strategy_weights").fetchall()
        conn.close()
        return {k: v for k, v in rows}

    @staticmethod
    def _persist_weights(weights: Dict[str, float]) -> None:
        if not weights:
            return
        conn = get_state_conn()
        now = time.time()
        for key, weight in weights.items():
            conn.execute(
                "INSERT INTO strategy_weights (key, weight, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET weight=excluded.weight, updated_at=excluded.updated_at",
                (key, weight, now),
            )
        conn.commit()
        conn.close()


if __name__ == "__main__":
    ctx = AgentContext.load()
    result = FeedbackStrategistAgent(ctx).run()
    print(result.to_json())
