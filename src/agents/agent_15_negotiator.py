"""
agent_15_negotiator.py — Negotiator Agent.

STRATEGY
--------
Direct answer to NxtJob's "Negotiator" agent — comp-band benchmarking plus
a rehearsed counter-offer script. Uses ONLY numbers already in this repo's
config (comp_benchmark_inr_lpa per company in config/target_companies.yml,
target range in config/profile.yml) — never invents a market number.

Two operations:
  1. benchmark(company) — compares the company's known comp band against
     your target range, flags whether it's below/within/above, and
     suggests an anchor number (never below your floor, never above the
     company's known max).
  2. counter_script(company, offer_amount_lpa) — given an actual offer
     number, computes where it sits in the band and generates a short,
     concrete counter-offer script anchored to your real proof points
     (never generic "I have other offers" bluffing language unless you
     supply that context yourself).

DAG node contract:
    Input:  AgentContext, company: str
    Output: AgentResult.data = {"band": {...}, "suggested_ask_lpa": float, "position": str}

    Input:  AgentContext, company: str, offer_amount_lpa: float
    Output: AgentResult.data = {"position_in_band": str, "counter_ask_lpa": float, "script": str}
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import AgentContext, AgentResult, BaseAgent


class NegotiatorAgent(BaseAgent):
    name = "negotiator"

    def benchmark(self, company: str) -> AgentResult:
        return self._timed(self._benchmark, company)

    def counter_script(self, company: str, offer_amount_lpa: float) -> AgentResult:
        return self._timed(self._counter_script, company, offer_amount_lpa)

    # -- benchmarking ---------------------------------------------------------

    def _benchmark(self, company: str) -> AgentResult:
        company_cfg = self.context.company(company) or {}
        band = company_cfg.get("comp_benchmark_inr_lpa") or {}
        comp_target = self.context.profile.get("compensation", {})

        if not band or band.get("median") is None:
            return AgentResult(
                agent=self.name, ok=True,
                summary=f"No comp benchmark on file for {company} in config/target_companies.yml — "
                        f"add one (source + as_of date) before negotiating with real numbers.",
                data={"band": {}, "suggested_ask_lpa": None, "position": "unknown"},
                warnings=["Never negotiate off an invented number — add a sourced benchmark first."],
            )

        target_min = comp_target.get("target_ctc_lakhs_min")
        target_max = comp_target.get("target_ctc_lakhs_max")
        median = band.get("median")
        band_max = band.get("max", median)

        if target_min and median < target_min:
            position = "below_target"
            suggested_ask = min(band_max, target_min)
        elif target_max and median > target_max:
            position = "above_target"
            suggested_ask = median
        else:
            position = "within_target"
            # Anchor near the top of the company's band, not just the median —
            # standard negotiation guidance, still bounded by their known max.
            suggested_ask = min(band_max, (median + band_max) / 2) if band_max else median

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"{company} comp band (source: {band.get('source', 'estimate')}, "
                    f"as of {band.get('as_of', 'unknown')}): median {median} LPA, "
                    f"position relative to your target: {position}.",
            data={
                "band": band,
                "suggested_ask_lpa": round(suggested_ask, 1) if suggested_ask else None,
                "position": position,
            },
        )

    # -- counter-offer script ---------------------------------------------------

    def _counter_script(self, company: str, offer_amount_lpa: float) -> AgentResult:
        bench_result = self._benchmark(company)
        band = bench_result.data.get("band", {})
        median = band.get("median")
        band_max = band.get("max")

        if median is None:
            position_in_band = "unknown (no benchmark on file)"
            counter_ask = round(offer_amount_lpa * 1.12, 1)  # generic 12% ask, clearly labeled as a guess
            confidence_note = ("No sourced comp benchmark for this company — the counter-ask below is a "
                                "generic +12% starting point, not a market-backed number. Add a benchmark "
                                "to config/target_companies.yml for a stronger position.")
        else:
            if offer_amount_lpa < median:
                position_in_band = "below the company's own median"
                counter_ask = round(min(band_max or median * 1.15, median * 1.05), 1)
            elif band_max and offer_amount_lpa >= band_max:
                position_in_band = "at or above the company's known max"
                counter_ask = round(offer_amount_lpa * 1.03, 1)  # small ask, little room left
            else:
                position_in_band = "within the company's known band, below its max"
                counter_ask = round(min(band_max, offer_amount_lpa * 1.10), 1)
            confidence_note = f"Benchmark source: {band.get('source', 'estimate')} (as of {band.get('as_of', 'unknown')})."

        proof_points = self.context.profile.get("narrative", {}).get("proof_points_by_theme", {})
        anchor_proof = next(iter(proof_points.values()), "")
        basis = ("market research for this role" if median is None
                 else f"comp data for similar roles here ({band.get('source', 'estimate')})")

        script = (
            f"Thank you for the offer of {offer_amount_lpa} LPA — I'm genuinely excited about the role. "
            f"Based on {basis}, I was expecting something closer to {counter_ask} LPA, particularly given "
            f"{anchor_proof.rstrip('.').lower()}. Is there flexibility to get closer to that number?"
        )

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Offer of {offer_amount_lpa} LPA is {position_in_band}. Suggested counter: {counter_ask} LPA.",
            data={
                "position_in_band": position_in_band,
                "counter_ask_lpa": counter_ask,
                "script": script,
                "confidence_note": confidence_note,
            },
            warnings=[] if median is not None else ["Counter-ask is a generic heuristic, not benchmark-backed."],
        )


if __name__ == "__main__":
    ctx = AgentContext.load()
    agent = NegotiatorAgent(ctx)
    print(agent.benchmark("Perfios").to_json())
    print(agent.counter_script("Perfios", 14.0).to_json())
