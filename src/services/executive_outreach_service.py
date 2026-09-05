"""
executive_outreach_service.py — Autonomous Executive Outbound Pitch Engine (Agent 25).
Bypasses junior recruiters to pitch Engineering Directors, VPs of Engineering, and CTOs directly
with high-conviction Trojan Horse architecture proposals and 3-stage drip campaigns.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("executive_outreach_service")

EXECUTIVE_PAIN_POINTS: List[Dict[str, Any]] = [
    {
        "pain_id": "p99_latency_bottleneck",
        "title": "P99 Tail Latency & Cache Stampede in Core Microservices",
        "category": "Performance & Scalability",
        "default_metric": "Reduced P99 tail latency from 850ms to 42ms under 15,000 RPS",
        "solution_hook": "Singleflight request coalescing + Redis connection pooling + async ring buffers",
    },
    {
        "pain_id": "cloud_cost_overrun",
        "title": "AWS Cloud Ingestion & Egress Cost Inefficiencies ($350k+/yr)",
        "category": "Cost & Infrastructure Optimization",
        "default_metric": "Cut monthly AWS compute & egress bill by 38% via zero-copy serialization",
        "solution_hook": "Protobuf/FlatBuffers binary encoding + Kafka batch compression + memory-bounded queues",
    },
    {
        "pain_id": "kafka_lag_backpressure",
        "title": "Kafka Consumer Lag & Thread Starvation During Traffic Spikes",
        "category": "Streaming & Reliability",
        "default_metric": "Eliminated consumer group rebalances and maintained 0-lag at 250k events/sec",
        "solution_hook": "Dynamic worker actor pools + backpressure-aware bounded queues with exponential backoff",
    },
]


class ExecutiveCampaignRequest(BaseModel):
    candidate_name: str = "Ujjwal"
    target_company: str = "Databricks"
    executive_name: str = "David (VP of Engineering)"
    executive_title: str = "VP of Core Infrastructure Engineering"
    pain_point_id: Optional[str] = "p99_latency_bottleneck"
    custom_proof_of_work_url: Optional[str] = "https://github.com/ujjwal-sovereign/distributed-idempotency-engine"


class ExecutiveOutreachService:
    """Generates 3-stage personalized executive outbound campaigns."""

    def get_pain_points(self) -> List[Dict[str, Any]]:
        return EXECUTIVE_PAIN_POINTS

    def generate_campaign(
        self,
        candidate_name: str,
        target_company: str,
        executive_name: str,
        executive_title: str = "VP of Engineering",
        pain_point_id: Optional[str] = None,
        custom_proof_of_work_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        comp_clean = target_company.strip()
        exec_first = executive_name.split()[0].replace("(", "").replace(")", "")
        pain = next((p for p in EXECUTIVE_PAIN_POINTS if p["pain_id"] == pain_point_id), EXECUTIVE_PAIN_POINTS[0])
        pow_url = custom_proof_of_work_url or "https://github.com/ujjwal-sovereign/distributed-idempotency-engine"

        # Stage 1: The Technical Opportunity & Free Architecture Fix
        stage_1_subject = f"Architecture note regarding {comp_clean}'s {pain['category']} — {candidate_name}"
        stage_1_body = f"""Hi {exec_first},

I've been following {comp_clean}'s engineering trajectory and notice your team is scaling distributed state across high-concurrency clusters.

In similar environments, teams often run into {pain['title'].lower()}. I recently engineered a production-tested fix leveraging {pain['solution_hook']}, which achieved {pain['default_metric']}.

I put together a clean, open-source micro-repo and benchmark container here:
{pow_url}

Zero expectations — just thought this architectural pattern might save your core infrastructure team a few weeks of debugging.

Best regards,
{candidate_name}"""

        # Stage 2: Technical Follow-Up with Deliverables (Day 4)
        stage_2_subject = f"Re: Architecture note regarding {comp_clean}'s {pain['category']} — benchmark data"
        stage_2_body = f"""Hi {exec_first},

Quick follow-up on my note earlier this week regarding {pain['solution_hook']}.

I ran a quick synthetic load test simulating 50,000 concurrent connections with network jitter. The concurrency harness maintained strict memory bounds (<128MB RAM) and zero deadlocks.

If {comp_clean} is actively hiring for Senior / Staff Distributed Systems roles to tackle these scaling frontiers, I'd love to chat. Otherwise, feel free to share the repo with your engineering leads!

Best,
{candidate_name}"""

        # Stage 3: Executive 15-Minute Sync or Clean Closeout (Day 8)
        stage_3_subject = f"Closing the loop — {candidate_name} // {comp_clean}"
        stage_3_body = f"""Hi {exec_first},

I know how busy scaling {comp_clean}'s engineering org can be, so I will close the loop here.

I am currently evaluating two final-stage Principal / Staff engineering conversations, but {comp_clean}'s technical roadmap remains my top choice. 

If you're open to a brief 15-minute sync this week to explore if my distributed systems background aligns with your H2 goals, let me know. Either way, cheering for {comp_clean}'s continued scale!

Best regards,
{candidate_name}"""

        stages = [
            {
                "stage_number": 1,
                "timing": "Day 1 (Initial Value-Add Delivery)",
                "subject": stage_1_subject,
                "body": stage_1_body,
                "strategic_goal": "Establish instant technical credibility without asking for a job.",
            },
            {
                "stage_number": 2,
                "timing": "Day 4 (Technical Benchmark Proof)",
                "subject": stage_2_subject,
                "body": stage_2_body,
                "strategic_goal": "Demonstrate proof-of-work rigor and link to runnable deliverables.",
            },
            {
                "stage_number": 3,
                "timing": "Day 8 (Executive Call-to-Action & Clean Closeout)",
                "subject": stage_3_subject,
                "body": stage_3_body,
                "strategic_goal": "Leverage polite scarcity and provide a frictionless 15-minute sync trigger.",
            },
        ]

        return {
            "status": "success",
            "candidate_name": candidate_name,
            "target_company": comp_clean,
            "executive_name": executive_name,
            "executive_title": executive_title,
            "pain_point": pain,
            "campaign_stages": stages,
            "executive_leverage_summary": f"Directly pitches {executive_name} ({executive_title}) at {comp_clean} with 3 calibrated touches, eliminating recruiter screening friction.",
        }
