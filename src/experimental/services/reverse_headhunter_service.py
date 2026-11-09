"""
reverse_headhunter_service.py — Reverse Headhunter Bounty Network (Agent 20).
Monetizes warm candidate introductions and internal referrals ($1k–$5k USD / ₹1L–₹5L bounties),
with automated pitch packs, candidate dossiers, and escrow commission tracking.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("reverse_headhunter_service")

REVERSE_HEADHUNTER_LISTINGS: List[Dict[str, Any]] = [
    {
        "bounty_id": "bounty_stripe_01",
        "company_name": "Stripe",
        "role_title": "Staff Distributed Systems Engineer",
        "location": "Remote / Singapore / US",
        "bounty_amount_usd": 5000,
        "bounty_amount_inr_lakhs": 4.32,
        "hiring_priority": "URGENT — Team Scaling",
        "escrow_status": "VERIFIED_ESCROW",
        "tech_stack": ["Go", "Distributed Consensus", "Raft", "AWS"],
        "minimum_experience_years": 6,
        "hiring_manager_team": "Core Ledger & Money Movement Architecture",
    },
    {
        "bounty_id": "bounty_openai_02",
        "company_name": "OpenAI",
        "role_title": "Inference Systems Infrastructure Engineer",
        "location": "San Francisco / Remote",
        "bounty_amount_usd": 7500,
        "bounty_amount_inr_lakhs": 6.48,
        "hiring_priority": "TOP_TIER — Frontier Labs",
        "escrow_status": "VERIFIED_ESCROW",
        "tech_stack": ["CUDA", "Python", "C++", "Triton", "Kubernetes"],
        "minimum_experience_years": 5,
        "hiring_manager_team": "Triton Kernel & Real-Time Serving Ops",
    },
    {
        "bounty_id": "bounty_razorpay_03",
        "company_name": "Razorpay",
        "role_title": "Principal Architect — Payments Core",
        "location": "Bangalore (Hybrid / Remote Option)",
        "bounty_amount_usd": 3000,
        "bounty_amount_inr_lakhs": 2.60,
        "hiring_priority": "ACTIVE",
        "escrow_status": "VERIFIED_ESCROW",
        "tech_stack": ["Golang", "Kafka", "PostgreSQL", "Redis High Availability"],
        "minimum_experience_years": 7,
        "hiring_manager_team": "High-Throughput Settlement Platform",
    },
    {
        "bounty_id": "bounty_mercari_04",
        "company_name": "Mercari Japan",
        "role_title": "Senior Backend Engineer (English Environment)",
        "location": "Tokyo, Japan (Full Visa Relocation)",
        "bounty_amount_usd": 4000,
        "bounty_amount_inr_lakhs": 3.46,
        "hiring_priority": "GLOBAL_SPONSOR",
        "escrow_status": "VERIFIED_ESCROW",
        "tech_stack": ["Go", "GCP", "Spanner", "Microservices"],
        "minimum_experience_years": 4,
        "hiring_manager_team": "Global Marketplace Platform",
    },
    {
        "bounty_id": "bounty_cred_05",
        "company_name": "CRED",
        "role_title": "Lead Platform Engineer",
        "location": "Bangalore",
        "bounty_amount_usd": 2500,
        "bounty_amount_inr_lakhs": 2.16,
        "hiring_priority": "ACTIVE",
        "escrow_status": "VERIFIED_ESCROW",
        "tech_stack": ["Java / Kotlin", "Kafka", "DynamoDB", "gRPC"],
        "minimum_experience_years": 5,
        "hiring_manager_team": "Growth & Financial Cloud Mesh",
    },
]


class PitchPackRequest(BaseModel):
    candidate_name: str = "Ujjwal"
    target_company: str = "Stripe"
    role_title: str = "Staff Distributed Systems Engineer"
    referrer_name: str = "Alex / Senior Peer Referrer"
    key_strengths: List[str] = Field(default_factory=lambda: ["Raft consensus implementation", "P99 latency reduction by 64%", "Defensive idempotency"])
    years_experience: int = Field(default=6, ge=1, le=25)
    github_portfolio: Optional[str] = "https://github.com/ujjwal-sovereign"


class ReverseHeadhunterService:
    """Manages high-value referral bounties, pitch pack synthesis, and escrow commission rules."""

    def get_listings(
        self,
        company_filter: Optional[str] = None,
        min_bounty_usd: float = 0.0,
    ) -> List[Dict[str, Any]]:
        listings = REVERSE_HEADHUNTER_LISTINGS
        if company_filter:
            c_lower = company_filter.lower().strip()
            listings = [l for l in listings if c_lower in l["company_name"].lower()]
        if min_bounty_usd > 0:
            listings = [l for l in listings if l["bounty_amount_usd"] >= min_bounty_usd]
        return listings

    def generate_pitch_pack(
        self,
        candidate_name: str,
        target_company: str,
        role_title: str = "Staff Engineer",
        referrer_name: str = "Peer Referrer",
        key_strengths: Optional[List[str]] = None,
        years_experience: int = 6,
        github_portfolio: Optional[str] = None,
        usd_to_inr_rate: float = 86.5,
    ) -> Dict[str, Any]:
        strengths = key_strengths or ["Raft consensus implementation", "P99 latency reduction by 64%", "Defensive idempotency"]
        strengths_bullets = "\\n".join([f"- {s}" for s in strengths])
        comp_clean = target_company.strip()

        # Find matching listing or fallback
        listing = next((l for l in REVERSE_HEADHUNTER_LISTINGS if comp_clean.lower() in l["company_name"].lower()), None)
        bounty_usd = listing["bounty_amount_usd"] if listing else 3500
        bounty_inr_lakhs = round((bounty_usd * usd_to_inr_rate) / 100000.0, 2)

        # 1. Internal Hiring Manager Referral Note
        hiring_manager_email = f"""Subject: Warm Referral: {candidate_name} — {role_title} (High-Conviction Production Track Record)

Hi Hiring Team,

I am writing to directly refer {candidate_name} for the {role_title} position at {comp_clean}.

Having reviewed their distributed systems deliverables and architectural rigor ({years_experience}+ years in high-throughput environments), they are an exceptional technical fit with zero ramp-up lag:

Core Technical Highlights:
{strengths_bullets}
Portfolio / Proof of Work: {github_portfolio or 'Available upon request'}

{candidate_name} is actively evaluating tier-1 opportunities, and I believe their day-1 impact on our core infrastructure would be immense. Could we fast-track their profile for an initial technical sync?

Best regards,
{referrer_name}"""

        # 2. LinkedIn / Telegram Peer Outreach Script
        peer_outreach_script = f"""Hi {candidate_name},

I came across your impressive distributed systems work and wanted to connect. My engineering peers at {comp_clean} are aggressively scaling their {role_title} team, and your background in {strengths[0]} is an exact match for what they are building.

I can make a direct, high-priority introduction to the hiring manager to bypass the recruiter queue. Would you be open to exploring this? Let me know and I'll submit your warm intro pack today!

Best,
{referrer_name}"""

        # 3. Escrow Terms
        escrow_breakdown = {
            "total_bounty_usd": bounty_usd,
            "total_bounty_inr_lakhs": bounty_inr_lakhs,
            "milestone_1_payout_usd": round(bounty_usd * 0.5, 2),
            "milestone_1_condition": "Candidate Day 1 Start Date Verified",
            "milestone_2_payout_usd": round(bounty_usd * 0.5, 2),
            "milestone_2_condition": "90-Day Retention Milestone Verified",
            "escrow_guarantee": "Funds locked in smart contract / verified escrow prior to candidate intro.",
        }

        return {
            "status": "success",
            "candidate_name": candidate_name,
            "target_company": comp_clean,
            "role_title": role_title,
            "referrer_name": referrer_name,
            "bounty_financials": escrow_breakdown,
            "hiring_manager_referral_email": hiring_manager_email,
            "peer_outreach_script": peer_outreach_script,
            "strategic_advantage": f"Bypasses ATS spam filters via a direct engineering endorsement, netting ${bounty_usd:,} USD (₹{bounty_inr_lakhs}L) in referral bounty.",
        }
