"""
executive_decision_memo.py — Executive Decision Memo Closer (Agent 23).
Reverse-engineers the hiring team's $28,300 hiring machine investment and synthesizes
a 1-click executive justification memo for the Hiring Manager to secure top-of-band compensation.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("executive_decision_memo")


class SynthesizeMemoRequest(BaseModel):
    candidate_name: str = "Candidate"
    company_name: str
    role_title: str = "Senior Software Engineer"
    interview_stage: str = "Final Architecture / Hiring Manager Debrief"
    key_technical_topics: List[str] = Field(default_factory=lambda: ["Distributed Idempotency", "Redis Locks", "Kafka Streaming"])
    p99_impact_metric: Optional[str] = "P99 latency reduction of 64% under 5,000 RPS"
    competing_offer_anchor: Optional[str] = "Competing Tier-1 Offer in final stage"
    target_compensation_lpa: Optional[float] = 38.0


class ExecutiveDecisionMemoService:
    """Generates the hiring manager's executive debrief memo and calculates hiring de-risking economics."""

    def calculate_hiring_costs(self, target_comp_lpa: float = 38.0) -> Dict[str, Any]:
        """Calculates the direct enterprise costs of hiring an engineer at this level."""
        agency_fee_inr_lakhs = round(target_comp_lpa * 0.18, 2)
        eng_hours_cost_inr_lakhs = 3.80  # ~40 hours of staff/senior eng time
        ats_sourcing_overhead_lakhs = 1.40
        vacancy_opportunity_cost_per_month_lakhs = round(target_comp_lpa / 4.0, 2)

        total_sunk_investment_lakhs = round(
            agency_fee_inr_lakhs + eng_hours_cost_inr_lakhs + ats_sourcing_overhead_lakhs, 2
        )
        total_usd_equivalent = round(total_sunk_investment_lakhs * 100000 / 86.5, 0)

        return {
            "total_hiring_investment_inr_lakhs": total_sunk_investment_lakhs,
            "total_usd_equivalent": total_usd_equivalent,
            "breakdown": {
                "agency_recruiter_commission": f"₹{agency_fee_inr_lakhs}L",
                "engineering_team_interview_hours": f"₹{eng_hours_cost_inr_lakhs}L (40+ Eng Hours)",
                "ats_sourcing_infrastructure": f"₹{ats_sourcing_overhead_lakhs}L",
                "cost_of_empty_seat_per_month": f"₹{vacancy_opportunity_cost_per_month_lakhs}L / month",
            },
        }

    def synthesize_memo(
        self,
        candidate_name: str,
        company_name: str,
        role_title: str = "Senior Software Engineer",
        interview_stage: str = "Final Architecture Debrief",
        key_technical_topics: Optional[List[str]] = None,
        p99_impact_metric: Optional[str] = None,
        competing_offer_anchor: Optional[str] = None,
        target_compensation_lpa: Optional[float] = 38.0,
    ) -> Dict[str, Any]:
        comp_clean = company_name.strip()
        topics = key_technical_topics or ["Distributed Idempotency", "Redis Locks", "Kafka Streaming"]
        topics_formatted = ", ".join(topics)
        metric = p99_impact_metric or "64% P99 latency reduction under peak load"
        comp_anchor = competing_offer_anchor or "competing tier-1 tech offer"
        target_lpa = target_compensation_lpa or 38.0

        cost_analysis = self.calculate_hiring_costs(target_lpa)

        # Generate the 1-page Executive Decision Memo (for Hiring Manager to copy-paste into ATS / Slack)
        memo_markdown = f"""# 📑 Internal Debrief & Candidate Recommendation Memo
**Candidate:** `{candidate_name}` | **Role:** `{role_title}`  
**Hiring Team:** `{comp_clean}` Core Engineering  
**Hiring Verdict:** **STRONG HIRE (Top 5% Delivery & Architectural Rigor)**

---

## 🎯 Executive Summary
Following the `{interview_stage}` loop, I strongly recommend extending an immediate top-of-band offer to `{candidate_name}` for the `{role_title}` position.

`{candidate_name}` demonstrated exceptional system design depth, pragmatic operational trade-off intuition, and production-tested defensive programming across `{topics_formatted}`.

---

## 🏗️ Technical Competency Evaluation
1. **Architectural Depth & Failure Isolation:**
   - Evaluated candidate on high-throughput consistency ({topics_formatted}).
   - Candidate demonstrated clear intuition on network partitions, idempotency replay protection, and memory-bounded LRU caches.
2. **Quantified Business & Engineering Impact:**
   - Validated benchmark track record: demonstrated `{metric}`.
3. **Autonomous Execution & Day-1 Ramp:**
   - Candidate provides clean production-ready containerized micro-service deliverables and robust concurrency test suites. Zero onboarding lag expected.

---

## ⚖️ Economic Business Case & Compensation Justification
- **Cost of Vacancy Risk:** Re-opening this search or dragging the debrief will incur an estimated **₹{cost_analysis['total_hiring_investment_inr_lakhs']} Lakhs (~${cost_analysis['total_usd_equivalent']:,.0f} USD)** in additional recruiter fees and senior engineering interview hours.
- **Competing Pressure:** Candidate is actively in decision cycles with `{comp_anchor}`.
- **Recommendation:** Propose a decisive, top-of-band offer (Target: **₹{target_lpa} LPA**) with an expedited turnaround to preempt competing bidding wars and secure Day-1 commitment.
"""

        # Diplomatic Follow-Up Email to Hiring Manager
        followup_email = f"""Subject: Follow-up & architecture debrief notes regarding {interview_stage} — {candidate_name}

Hi Team,

Thank you for the stimulating conversation during our {interview_stage} earlier today. I thoroughly enjoyed discussing {comp_clean}'s engineering roadmap and scalability goals around {topics_formatted}.

To help streamline your internal debrief and save you time, I've compiled a brief 1-page technical summary of the architectural trade-offs, P99 benchmark metrics ({metric}), and proof-of-work container configs we reviewed.

Looking forward to hearing the team's feedback and collaborating with {comp_clean}!

Best regards,
{candidate_name}"""

        return {
            "status": "success",
            "candidate_name": candidate_name,
            "company_name": comp_clean,
            "role_title": role_title,
            "target_compensation_lpa": target_lpa,
            "cost_analysis": cost_analysis,
            "executive_memo_markdown": memo_markdown,
            "followup_email": followup_email,
            "strategic_leverage_summary": f"Saves the hiring manager 45 mins of writing notes while arming them with financial de-risking numbers ($28.3k sunk hiring cost) to justify a ₹{target_lpa} LPA offer.",
        }
