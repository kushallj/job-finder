"""
frontier_ai_radar.py — Frontier AI & RLHF High-Income Arbitrage Radar (Agent 19).
Maps global AI evaluation platforms ($40–$120/hr USD), grades code-eval benchmarks,
and calculates USD/INR side-income earning potential for engineers.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("frontier_ai_radar")

FRONTIER_AI_PLATFORMS: List[Dict[str, Any]] = [
    {
        "id": "alignerr",
        "name": "Alignerr (by Labelbox)",
        "hourly_rate_usd": 65.0,
        "hourly_rate_range": "$50 – $85/hr USD",
        "primary_focus": "Python / Systems Code Evaluation & Reasoning Models",
        "payout_frequency": "Weekly (Direct Bank / PayPal)",
        "onboarding_difficulty": "High (Technical Assessment)",
        "direct_apply_url": "https://alignerr.com",
        "tags": ["Python", "Algorithms", "LLM Reasoning", "Weekly Payout"],
    },
    {
        "id": "outlier_ai",
        "name": "Outlier.ai (by Scale AI)",
        "hourly_rate_usd": 55.0,
        "hourly_rate_range": "$40 – $75/hr USD",
        "primary_focus": "RLHF Code Quality, Security Edge-Cases & Prompt Engineering",
        "payout_frequency": "Weekly (Airwallex / PayPal)",
        "onboarding_difficulty": "Medium-High",
        "direct_apply_url": "https://outlier.ai",
        "tags": ["Full-Stack", "Docker", "Security", "High Volume"],
    },
    {
        "id": "mercor",
        "name": "Mercor",
        "hourly_rate_usd": 85.0,
        "hourly_rate_range": "$60 – $120/hr USD",
        "primary_focus": "Frontier AI Lab Contracts & Agent Architecture Work",
        "payout_frequency": "Bi-Weekly (Stripe Express)",
        "onboarding_difficulty": "Very High (AI Video + Code Interview)",
        "direct_apply_url": "https://mercor.com",
        "tags": ["Silicon Valley Labs", "Distributed Systems", "High Comp"],
    },
    {
        "id": "micro1",
        "name": "Micro1 (AI Talent Cloud)",
        "hourly_rate_usd": 50.0,
        "hourly_rate_range": "$40 – $70/hr USD",
        "primary_focus": "Autonomous Coding Agent Pre-Training & Verification",
        "payout_frequency": "Monthly (Direct Wire / Deel)",
        "onboarding_difficulty": "Medium",
        "direct_apply_url": "https://micro1.ai",
        "tags": ["AI Vetted", "Deel Payout", "Long-Term Projects"],
    },
    {
        "id": "data_annotation",
        "name": "DataAnnotation.tech",
        "hourly_rate_usd": 45.0,
        "hourly_rate_range": "$40 – $60/hr USD",
        "primary_focus": "Software Engineering & Math Model Evaluation",
        "payout_frequency": "Unlimited Daily Cash-Out (PayPal)",
        "onboarding_difficulty": "Medium",
        "direct_apply_url": "https://dataannotation.tech",
        "tags": ["Flexible Hours", "Daily Payout", "Math & Code"],
    },
    {
        "id": "turing",
        "name": "Turing LLM Post-Training",
        "hourly_rate_usd": 60.0,
        "hourly_rate_range": "$45 – $90/hr USD",
        "primary_focus": "Enterprise Code-Gen Fine-Tuning & Multi-Language Evals",
        "payout_frequency": "Bi-Weekly (Deel / Direct Bank)",
        "onboarding_difficulty": "Medium-High",
        "direct_apply_url": "https://turing.com",
        "tags": ["Enterprise AI", "Global Contracts"],
    },
]

CODE_EVAL_SAMPLE_CHALLENGE = {
    "challenge_id": "eval_py_01",
    "prompt": "Evaluate this LLM-generated LRU Cache implementation for subtle race conditions, Big-O violations, and edge-case errors.",
    "buggy_code": '''class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {} # Key to Value
        self.order = [] # Order of keys

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.order.remove(key) # O(N) linear scan!
        self.order.append(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest = self.order.pop(0) # O(N) list pop(0)!
            del self.cache[oldest]
        self.cache[key] = value
        self.order.append(key)
''',
    "rubric_key_points": [
        "Identified O(N) list removal in get() violating O(1) requirement",
        "Identified O(N) pop(0) in put() violating O(1) requirement",
        "Recommended Doubly-Linked List + Hash Map or collections.OrderedDict",
        "Checked capacity <= 0 edge-case validation",
        "Checked thread-safety / concurrent access considerations",
    ],
}


class BenchmarkRequest(BaseModel):
    critique_text: str = Field(..., description="Candidate's critique of the buggy LLM code sample")
    weekly_hours_available: int = Field(default=15, ge=1, le=40, description="Hours available per week")
    usd_to_inr_rate: float = Field(default=86.5, description="Current USD to INR conversion rate")


class FrontierAiRadarService:
    """Evaluates frontier AI earning potential and scores candidate code-evaluation abilities."""

    def get_platforms(self) -> List[Dict[str, Any]]:
        return FRONTIER_AI_PLATFORMS

    def get_sample_challenge(self) -> Dict[str, Any]:
        return CODE_EVAL_SAMPLE_CHALLENGE

    def evaluate_benchmark(
        self,
        critique_text: str,
        weekly_hours: int = 15,
        usd_inr_rate: float = 86.5,
    ) -> Dict[str, Any]:
        text_lower = critique_text.lower()

        # Score candidate's critique on RLHF rubric
        found_o_n_removal = any(k in text_lower for k in ["o(n)", "linear scan", "remove(", "list.remove", "slow removal"])
        found_pop_zero = any(k in text_lower for k in ["pop(0)", "pop zero", "linear pop", "shift array"])
        found_ordered_dict = any(k in text_lower for k in ["ordereddict", "doubly linked", "linked list", "node pointer", "hash map"])
        found_capacity_edge = any(k in text_lower for k in ["capacity <= 0", "negative capacity", "zero capacity", "edge case"])
        found_concurrency = any(k in text_lower for k in ["thread", "concurrency", "race condition", "lock", "mutex", "atomic"])

        rubric_hits = [
            {"criterion": "O(N) list.remove() complexity violation caught", "passed": found_o_n_removal, "weight": 25},
            {"criterion": "O(N) pop(0) array shift penalty caught", "passed": found_pop_zero, "weight": 25},
            {"criterion": "Doubly-Linked List / OrderedDict architecture proposed", "passed": found_ordered_dict, "weight": 25},
            {"criterion": "Negative / zero capacity boundary validation checked", "passed": found_capacity_edge, "weight": 15},
            {"criterion": "Thread-safety / race condition vulnerability noted", "passed": found_concurrency, "weight": 10},
        ]

        total_score = sum(r["weight"] for r in rubric_hits if r["passed"])

        # Tier & Qualification Status
        if total_score >= 85:
            tier_status = "Tier 1: Senior RLHF Evaluator (Mercor / Alignerr Ready)"
            projected_hourly_rate = 75.0
            badge_color = "#00FFA3"
        elif total_score >= 60:
            tier_status = "Tier 2: Intermediate Code Evaluator (Outlier / Turing Ready)"
            projected_hourly_rate = 55.0
            badge_color = "#00F0FF"
        else:
            tier_status = "Tier 3: Developing (Needs Deeper Big-O & Rigor Focus)"
            projected_hourly_rate = 40.0
            badge_color = "#FFE600"

        # Calculate Income Projections
        monthly_hours = weekly_hours * 4.2
        monthly_earnings_usd = round(monthly_hours * projected_hourly_rate, 2)
        monthly_earnings_inr = round(monthly_earnings_usd * usd_inr_rate, 2)
        annual_earnings_inr_lakhs = round((monthly_earnings_inr * 12) / 100000.0, 2)

        return {
            "status": "success",
            "benchmark_score": total_score,
            "tier_status": tier_status,
            "badge_color": badge_color,
            "projected_hourly_rate_usd": projected_hourly_rate,
            "weekly_hours": weekly_hours,
            "monthly_hours": round(monthly_hours, 1),
            "projections": {
                "monthly_usd": monthly_earnings_usd,
                "monthly_inr": monthly_earnings_inr,
                "annual_inr_lakhs": annual_earnings_inr_lakhs,
            },
            "rubric_breakdown": rubric_hits,
            "top_recommended_platforms": [
                p for p in FRONTIER_AI_PLATFORMS if p["hourly_rate_usd"] >= (projected_hourly_rate - 15)
            ][:3],
        }
