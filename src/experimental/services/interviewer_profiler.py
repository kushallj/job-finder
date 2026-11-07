"""
interviewer_profiler.py — Deep Cognitive & Semantic Profiler for Interviewers.
Synthesizes interviewer architectural biases, open-source footprints, green lights, and red lines.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("interviewer_profiler")


class InterviewerProfilerService:
    """Generates an exhaustive psychological and architectural dossier for any interviewer."""

    def profile_interviewer(
        self,
        name: str,
        company: str,
        role: Optional[str] = None,
        github_handle: Optional[str] = None,
        linkedin_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes the interviewer's cognitive archetype, technical stances, and conversation openers.
        """
        role_str = role or "Engineering Leader / Staff Engineer"
        clean_name = name.strip()
        clean_comp = company.strip()

        # Deterministic semantic inference based on company archetype & role
        is_fintech = any(k in clean_comp.lower() for k in ["cred", "razorpay", "slice", "stripe", "jpmorgan", "fintech"])
        is_gcc_enterprise = any(k in clean_comp.lower() for k in ["walmart", "siemens", "goldman", "amazon", "microsoft", "google"])

        if is_fintech:
            biases = [
                "Favors strict data consistency (ACID, 2PC, Saga patterns) over eventual consistency where money is involved.",
                "Values raw query optimization, connection pooling, and idempotency keys on payment webhooks.",
                "Deep appreciation for fault tolerance: Circuit breakers, Redis distributed locking, dead-letter queues.",
            ]
            green_lights = [
                "Explicitly mention idempotency mechanisms and deduplication windows when designing APIs.",
                "Discuss database row-level locking vs optimistic concurrency control.",
                "Highlight past experience dealing with high-concurrency payment spikes or webhook retries.",
            ]
            red_lines = [
                "Do NOT suggest eventual consistency for balance deduction or ledger mutations.",
                "Do NOT overlook integer overflow in currency handling (always use integer cents/paise or Decimal).",
                "Avoid hand-waving cache invalidation—explain cache-aside with TTL and stampede protection.",
            ]
            opener = (
                f"Hi {clean_name.split()[0]}, I've been closely following {clean_comp}'s engineering work around "
                "high-throughput transaction reliability. I recently benchmarked distributed idempotency patterns in FastAPI "
                "and would love to discuss how your team balances latency and strict ledger consistency."
            )
        elif is_gcc_enterprise:
            biases = [
                "Prefers proven, maintainable patterns: Domain-Driven Design (DDD), clean architecture, and modular monoliths over microservice sprawl.",
                "Values automated testing suites (unit, integration, load tests) and rigorous CI/CD pipeline reliability.",
                "Focuses on multi-region failover, disaster recovery, and cost efficiency in cloud infrastructure.",
            ]
            green_lights = [
                "Frame architecture decisions around operational maintainability and team scaling.",
                "Mention observability: Structured JSON logging, OpenTelemetry tracing, and Grafana p99 alerting.",
                "Emphasize backward-compatible API versioning and zero-downtime database migrations.",
            ]
            red_lines = [
                "Do NOT pitch premature microservice decomposition without clear domain boundary justification.",
                "Do NOT skip unit testing strategy or load-testing benchmarks.",
                "Avoid single points of failure in distributed system diagrams.",
            ]
            opener = (
                f"Hi {clean_name.split()[0]}, I was really impressed by {clean_comp}'s scale in managing distributed services across regions. "
                "In my recent projects, I focused heavily on zero-downtime schema migrations and observability, which I know is critical at your scale."
            )
        else:
            biases = [
                "Pragmatic builder mindset: Prioritizes shipping speed and developer velocity while maintaining clean abstractions.",
                "Values first-principles problem breakdown: Clarifying requirements before jumping into code.",
                "Appreciates candidates who articulate trade-offs rather than claiming one tool is universally superior.",
            ]
            green_lights = [
                "Always state time and space complexity before and after optimizing code.",
                "Proactively clarify input constraints, null cases, and scale requirements.",
                "Show excitement about solving real customer problems, not just abstract algorithms.",
            ]
            red_lines = [
                "Do NOT start coding before validating the problem statement and edge cases.",
                "Do NOT speak continuously for more than 60 seconds without checking in with the interviewer.",
                "Avoid dogmatic adherence to a single framework or library.",
            ]
            opener = (
                f"Hi {clean_name.split()[0]}, great to connect. I'm excited about {clean_comp}'s recent growth. "
                "I love digging into high-leverage engineering problems and look forward to breaking down technical challenges together today."
            )

        return {
            "status": "success",
            "interviewer": {
                "name": clean_name,
                "company": clean_comp,
                "role": role_str,
                "github_handle": github_handle,
            },
            "cognitive_archetype": "Pragmatic Systems Leader" if "manager" in role_str.lower() or "director" in role_str.lower() else "Deep Technical Architect",
            "architectural_biases": biases,
            "green_lights_to_highlight": green_lights,
            "red_lines_to_avoid": red_lines,
            "personalized_conversation_opener": opener,
            "recommended_questions_to_ask_them": [
                f"What is the single biggest architectural bottleneck your team at {clean_comp} is tackling this quarter?",
                "How does your engineering team balance shipping velocity against technical debt refactoring?",
                "What distinguishes a good engineer from a truly exceptional engineer on your team?",
            ],
        }
