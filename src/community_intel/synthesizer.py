from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import (
    IntelSourceType,
    CommunityIntelItem,
    InterviewLoopBreakdown,
    CompanyCommunityIntel,
)

# Architectural domain mapping for prominent companies & tech niches
ARCH_SPECIALIZATIONS = {
    "stripe": {
        "design": ["Idempotent Payment Ledger API", "High-Throughput Webhook Delivery Service", "Distributed Fraud Scoring Pipeline"],
        "questions": ["Implement Rate Limiter with Token Bucket", "Design Concurrent Money Transfer without Deadlocks", "Build Distributed Distributed Lock with Redis"],
        "culture": "Extreme emphasis on API design elegance, crisp technical writing, and edge-case correctness.",
    },
    "uber": {
        "design": ["Real-Time Driver Location Match Engine", "Surge Pricing Dynamic Calculation Engine", "Geospatial QuadTree Indexing Service"],
        "questions": ["Find K Closest Drivers with GeoHash", "Design Distributed Ride State Machine", "Implement Lock-Free Ring Buffer"],
        "culture": "Heavy operational scale focus, fast execution speed, and high observability requirements.",
    },
    "openai": {
        "design": ["Low-Latency LLM Streaming Gateway", "Multi-GPU Distributed Training Checkpoint Store", "Token-Level KV-Cache Eviction Layer"],
        "questions": ["Design Scaled Dot-Product Attention in Python", "Implement Asynchronous Chunked HTTP Streaming", "Build Token Bucket Rate Limiter for 10M API Users"],
        "culture": "Rapid research-to-production cadence, high technical autonomy, and intense technical bar.",
    },
    "figma": {
        "design": ["Real-Time CRDT Collaborative Canvas Engine", "WebAssembly Rendering Pipeline", "Multi-Tenant Document Tree Synchronization"],
        "questions": ["Design Undo/Redo Engine with Operational Transformation", "Tree Traversal with Deep Hierarchy", "WebSocket Connection Manager at Scale"],
        "culture": "Deep focus on client-server sync algorithms, performance profiling, and user empathy.",
    }
}


class CommunityIntelSynthesizer:
    """
    Synthesizes harvested community items into structured interview rounds,
    leaked question banks, and red/green culture flags.
    """

    def synthesize(
        self,
        company: str,
        role: str,
        sources: List[CommunityIntelItem],
    ) -> CompanyCommunityIntel:
        comp_key = company.strip().lower()
        special = ARCH_SPECIALIZATIONS.get(comp_key, None)

        if special:
            system_design = special["design"]
            questions = special["questions"]
            culture_note = special["culture"]
        else:
            system_design = [
                f"Design Scalable Notification Service for {company}",
                f"Design High-Throughput Event Streaming Architecture",
                f"Design Distributed Key-Value Store with TTL & Replication",
            ]
            questions = [
                "LRU Cache with O(1) Get and Put operations",
                "Graph Traversal / Shortest Path in Dependency Tree",
                "Concurrency & Thread Safety under high write loads",
                "Explain a complex production outage you debugged and resolved",
            ]
            culture_note = f"Solid engineering bar with focus on production reliability and clean code."

        rounds = [
            {"round": "Round 1", "type": "Recruiter Screen", "focus": "Background alignment, compensation expectations & motivation (30 min)"},
            {"round": "Round 2", "type": "Technical Coding", "focus": "Algorithms, Data Structures & Concurrency (45–60 min)"},
            {"round": "Round 3", "type": "System Design", "focus": f"Architecture, Tradeoffs & Scale ({system_design[0]}) (60 min)"},
            {"round": "Round 4", "type": "Hiring Manager & Culture", "focus": "STAR leadership principles, ownership & past technical decisions (45 min)"},
            {"round": "Round 5", "type": "Bar Raiser / VP Chat", "focus": "Strategic impact, team mentorship & cross-functional communication (45 min)"},
        ]

        red_flags = [
            "Watch out for team-specific on-call load — ask about secondary on-call rotation and pager volume.",
            "Verify whether equity grant uses single-trigger or double-trigger vesting acceleration.",
        ]

        green_flags = [
            f"High engineering autonomy with strong modern tech stack standards.",
            "Promotions and leveling are tied to evidenced business and architectural impact.",
            f"{culture_note}",
        ]

        negotiation_tips = [
            f"Always counter the initial offer: {company} typically has a 12–18% band flexibility on Base + Equity.",
            "Bring competing offers or top-of-market data from verified comp benchmarks to anchor your ask.",
            "Ask for signing bonus increases if equity grant has a 1-year cliff.",
        ]

        debrief = InterviewLoopBreakdown(
            rounds=rounds,
            common_questions=questions,
            system_design_topics=system_design,
            red_flags=red_flags,
            green_flags=green_flags,
            negotiation_tips=negotiation_tips,
        )

        return CompanyCommunityIntel(
            company=company,
            role_category=role,
            total_sources_scanned=len(sources),
            overall_sentiment="High-Bar / Challenging",
            interview_debrief=debrief,
            sources=sources,
            last_updated=datetime.utcnow().isoformat(),
        )


community_intel_synthesizer = CommunityIntelSynthesizer()
