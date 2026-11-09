"""
anti_ghosting_service.py — Anti-Ghosting SLA & Recruiter Escalation Engine (Agent 18).
Monitors post-interview timeline decay, calculates ghosting risk percentages,
generates 3-tier high-leverage escalation drafts, and benchmarks company feedback velocity.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("anti_ghosting_service")

# Community Company Hiring SLA Benchmarks
COMPANY_SLA_INDEX: Dict[str, Dict[str, Any]] = {
    "pine labs": {
        "company_name": "Pine Labs",
        "avg_feedback_turnaround_hours": 48.0,
        "ghosting_rate_percent": 8.2,
        "is_verified_fast_track": True,
        "tier_rating": "A+ (Fast-Track Verified)",
        "recruiter_responsiveness": "High (48h avg)",
    },
    "cashfree": {
        "company_name": "Cashfree Payments",
        "avg_feedback_turnaround_hours": 54.0,
        "ghosting_rate_percent": 9.5,
        "is_verified_fast_track": True,
        "tier_rating": "A (Fast-Track Verified)",
        "recruiter_responsiveness": "High (54h avg)",
    },
    "ather energy": {
        "company_name": "Ather Energy",
        "avg_feedback_turnaround_hours": 68.0,
        "ghosting_rate_percent": 11.0,
        "is_verified_fast_track": True,
        "tier_rating": "A (Standard Tech SLA)",
        "recruiter_responsiveness": "Medium-High",
    },
    "cred": {
        "company_name": "CRED",
        "avg_feedback_turnaround_hours": 42.0,
        "ghosting_rate_percent": 6.1,
        "is_verified_fast_track": True,
        "tier_rating": "A+ (Fast-Track Verified)",
        "recruiter_responsiveness": "Very High (42h avg)",
    },
    "swiggy": {
        "company_name": "Swiggy",
        "avg_feedback_turnaround_hours": 76.0,
        "ghosting_rate_percent": 14.8,
        "is_verified_fast_track": False,
        "tier_rating": "B+ (Moderate)",
        "recruiter_responsiveness": "Moderate (76h avg)",
    },
    "razorpay": {
        "company_name": "Razorpay",
        "avg_feedback_turnaround_hours": 46.0,
        "ghosting_rate_percent": 7.4,
        "is_verified_fast_track": True,
        "tier_rating": "A+ (Fast-Track Verified)",
        "recruiter_responsiveness": "Very High (46h avg)",
    },
    "default": {
        "company_name": "Tech Employer Benchmark",
        "avg_feedback_turnaround_hours": 72.0,
        "ghosting_rate_percent": 18.5,
        "is_verified_fast_track": False,
        "tier_rating": "B (Industry Baseline)",
        "recruiter_responsiveness": "Standard (72h SLA)",
    },
}


class EscalationRequest(BaseModel):
    company_name: str
    interview_stage: str = "System Design / Final Round"
    days_elapsed: int = Field(..., ge=0, description="Days passed since interview completion")
    recruiter_name: Optional[str] = "Recruiting Team"
    candidate_leverage: Optional[str] = "Has Competing Timelines"
    competing_company: Optional[str] = "Another Tier-1 Tech Firm"


class AntiGhostingService:
    """Calculates ghosting risk, SLA breach status, and synthesizes multi-tier escalation scripts."""

    def get_company_sla(self, company_name: str) -> Dict[str, Any]:
        key = company_name.strip().lower()
        for k, val in COMPANY_SLA_INDEX.items():
            if k in key or key in k:
                return val
        return {
            "company_name": company_name.strip(),
            "avg_feedback_turnaround_hours": 72.0,
            "ghosting_rate_percent": 18.5,
            "is_verified_fast_track": False,
            "tier_rating": "B (Industry Baseline)",
            "recruiter_responsiveness": "Standard (72h SLA)",
        }

    def get_all_company_benchmarks(self) -> List[Dict[str, Any]]:
        return [v for k, v in COMPANY_SLA_INDEX.items() if k != "default"]

    def calculate_ghosting_risk(self, days_elapsed: int, stage: str, company_sla: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates ghosting probability based on days elapsed and stage sensitivity."""
        base_rate = company_sla.get("ghosting_rate_percent", 18.5)
        
        # Exponential timeline penalty
        if days_elapsed <= 2:
            risk = max(5.0, base_rate * 0.4)
            status = "Within 48h Executive SLA"
            color = "#00FFA3"
        elif days_elapsed <= 4:
            risk = min(40.0, base_rate * 1.2)
            status = "SLA Nudge Window (Day 3-4)"
            color = "#00F0FF"
        elif days_elapsed <= 7:
            risk = min(72.0, base_rate * 2.8)
            status = "SLA Warning: Timeline Slipping"
            color = "#FFE600"
        else:
            risk = min(94.0, base_rate * 4.2 + (days_elapsed - 7) * 4)
            status = "SLA Breached: High Ghosting Risk"
            color = "#FF0055"

        return {
            "ghosting_risk_percent": round(risk, 1),
            "sla_status": status,
            "sla_color": color,
            "hours_elapsed": days_elapsed * 24,
            "standard_benchmark_hours": company_sla.get("avg_feedback_turnaround_hours", 72.0),
        }

    def synthesize_escalations(
        self,
        company_name: str,
        interview_stage: str,
        days_elapsed: int,
        recruiter_name: Optional[str] = "Recruiting Team",
        candidate_leverage: Optional[str] = "Has Competing Timelines",
        competing_company: Optional[str] = "Another Tier-1 Tech Firm",
    ) -> Dict[str, Any]:
        company_clean = company_name.strip()
        recruiter_clean = recruiter_name.strip() if recruiter_name else "Recruiting Team"
        competing_clean = competing_company.strip() if competing_company else "another engineering team"

        company_sla = self.get_company_sla(company_clean)
        risk_metrics = self.calculate_ghosting_risk(days_elapsed, interview_stage, company_sla)

        # Tier 1: Gentle Value-Add (Days 3-4)
        tier1_subject = f"Quick check-in & follow-up regarding {interview_stage} — {company_clean}"
        tier1_body = f"""Hi {recruiter_clean},

I wanted to quickly check in following our {interview_stage} conversation earlier this week. I thoroughly enjoyed diving into {company_clean}'s engineering roadmap and scalability goals.

I've put together some follow-up thoughts on our architectural discussion and would love to hear the team's feedback whenever you have a moment.

Looking forward to hearing about the next steps!

Best regards,"""

        # Tier 2: Competing Timeline Leverage Trigger (Days 5-7)
        tier2_subject = f"Update regarding interview timeline / next steps with {company_clean}"
        tier2_body = f"""Hi {recruiter_clean},

I hope you're having a productive week.

I wanted to share a quick timeline update: I am currently in the final decision stages with {competing_clean}, but because I have a very strong conviction around {company_clean}'s mission and technical architecture, {company_clean} remains my top preference.

In order to align my decision window responsibly without losing momentum, could you let me know if there are any updates regarding our {interview_stage} debrief?

Thank you for your time and guidance!

Best regards,"""

        # Tier 3: Executive Hiring-Manager Escalation & Clean Closeout (Day 8+)
        tier3_subject = f"Connecting on {interview_stage} loop & engineering roadmap at {company_clean}"
        tier3_body = f"""Hi {recruiter_clean},

I'm reaching out as I am wrapping up my interview cycles this week. I wanted to confirm if the team has concluded the debrief for the {interview_stage}.

If the team has decided to pursue other directions, no worries at all—I truly appreciated meeting the engineering group and wish {company_clean} continued scale. If we are still moving forward, please let me know by the end of this week so I can accommodate {company_clean} in my final scheduling decisions.

Thanks again for all your support throughout the process.

Warmly,"""

        return {
            "status": "success",
            "company_name": company_clean,
            "interview_stage": interview_stage,
            "days_elapsed": days_elapsed,
            "company_sla_benchmark": company_sla,
            "risk_metrics": risk_metrics,
            "escalation_tiers": [
                {
                    "tier_level": 1,
                    "tier_name": "Level 1: Gentle Value-Add (Days 3–4)",
                    "recommended_trigger_window": "Days 3–4",
                    "subject": tier1_subject,
                    "body": tier1_body,
                    "strategic_intent": "Maintains top-of-mind presence while providing value without sounding impatient.",
                },
                {
                    "tier_level": 2,
                    "tier_name": "Level 2: Competing Timeline Leverage (Days 5–7)",
                    "recommended_trigger_window": "Days 5–7",
                    "subject": tier2_subject,
                    "body": tier2_body,
                    "strategic_intent": "Activates FOMO and professional scarcity, forcing recruiter to expedite internal debrief.",
                },
                {
                    "tier_level": 3,
                    "tier_name": "Level 3: Executive Closeout & Scarcity Seal (Day 8+)",
                    "recommended_trigger_window": "Day 8+",
                    "subject": tier3_subject,
                    "body": tier3_body,
                    "strategic_intent": "Preserves candidate high-status authority and forces a binary yes/no decision before closure.",
                },
            ],
        }
