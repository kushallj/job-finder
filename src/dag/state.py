"""
state.py — NEXUS pipeline state (the single shared object threading through all nodes).

Design principle: the State is the single source of truth for the entire pipeline run.
Every node reads from it and writes back to it. No hidden side effects.

Immutability: we don't enforce it (Python dataclasses aren't immutable by default),
but by convention each node only APPENDS to lists / INSERTS into dicts — never deletes.
This makes the state log-like: you can inspect any intermediate stage after the run.

Serialisation: the dataclass is JSON-serialisable (primitive types only in fields).
This lets you checkpoint state to disk and resume interrupted runs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class NodeStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"


@dataclass
class NEXUSState:
    """
    Shared state object for the NEXUS DAG pipeline.

    Lifecycle:
        1. Caller populates *config* fields (search_queries, resume_path, dry_run).
        2. Graph engine copies and passes through each node.
        3. After completion, *outputs* fields hold all pipeline results.
        4. *telemetry* fields record timing + errors for observability.
    """

    # ── Config (set by caller before run) ─────────────────────────────────────
    search_queries:       List[str]            = field(default_factory=lambda: [
        "Software Engineer", "Backend Developer", "Python Developer"
    ])
    resume_path:          str                  = "data/resume.txt"
    dry_run:              bool                 = False          # True = no emails sent
    max_jobs_per_query:   int                  = 5             # cap scraping per query
    max_jobs_to_tailor:   int                  = 5             # cap resume variants
    max_companies:        int                  = 10            # cap contact intel
    company_size_hint:    int                  = 150           # default for DM matrix

    # ── Stage 1 outputs: Job Scraping ──────────────────────────────────────────
    scraped_jobs:         List[Any]            = field(default_factory=list)   # src.models.Job
    jobs_new_count:       int                  = 0

    # ── Stage 2 outputs: JD Analysis ──────────────────────────────────────────
    jd_analyses:          Dict[int, Any]       = field(default_factory=dict)   # job_id → JDAnalysis

    # ── Stage 3a outputs: Resume Tailoring ────────────────────────────────────
    resume_variants:      Dict[int, Any]       = field(default_factory=dict)   # job_id → ResumeVariant
    avg_ats_score:        float                = 0.0

    # ── Stage 3b outputs: Contact Intelligence ────────────────────────────────
    contact_results:      Dict[str, Any]       = field(default_factory=dict)   # company → IntelligenceResult
    top_contacts:         List[Any]            = field(default_factory=list)   # RankedContact (all companies)

    # ── Stage 4 outputs: Personalization ──────────────────────────────────────
    personalized_outreaches: List[Any]         = field(default_factory=list)   # PersonalizedOutreach
    avg_personalization_score: float           = 0.0

    # ── Stage 5 outputs: Outreach ─────────────────────────────────────────────
    outreach_results:     List[Any]            = field(default_factory=list)
    emails_sent:          int                  = 0
    emails_skipped:       int                  = 0

    # ── Stage 6 outputs: Feedback ─────────────────────────────────────────────
    feedback_snapshot:    Optional[Any]        = None           # LearningSnapshot
    recommendations:      List[Any]            = field(default_factory=list)

    # ── Routing ────────────────────────────────────────────────────────────────
    # Conditional edges read this to decide the next node.
    # A node sets it before returning; the router consumes it.
    route_decision:       str                  = ""

    # ── Telemetry ──────────────────────────────────────────────────────────────
    node_status:          Dict[str, NodeStatus] = field(default_factory=dict)
    node_timings_ms:      Dict[str, float]      = field(default_factory=dict)
    errors:               List[str]             = field(default_factory=list)
    warnings:             List[str]             = field(default_factory=list)
    started_at:           str                   = field(
                              default_factory=lambda: datetime.now(timezone.utc).isoformat()
                          )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def mark_node_start(self, node_name: str) -> float:
        """Record node start; returns monotonic timestamp for timing."""
        self.node_status[node_name] = NodeStatus.RUNNING
        return time.monotonic()

    def mark_node_done(self, node_name: str, t0: float) -> None:
        self.node_status[node_name] = NodeStatus.COMPLETED
        self.node_timings_ms[node_name] = round((time.monotonic() - t0) * 1000)

    def mark_node_failed(self, node_name: str, error: str, t0: float) -> None:
        self.node_status[node_name] = NodeStatus.FAILED
        self.node_timings_ms[node_name] = round((time.monotonic() - t0) * 1000)
        self.errors.append(f"[{node_name}] {error}")

    def mark_node_skipped(self, node_name: str) -> None:
        self.node_status[node_name] = NodeStatus.SKIPPED

    def summary(self) -> str:
        total_ms = sum(self.node_timings_ms.values())
        lines = [
            "NEXUS Pipeline Summary",
            f"  Jobs scraped:       {len(self.scraped_jobs)} ({self.jobs_new_count} new)",
            f"  JDs analyzed:       {len(self.jd_analyses)}",
            f"  Resumes tailored:   {len(self.resume_variants)} (avg ATS {self.avg_ats_score:.0f}/100)",
            f"  Companies analyzed: {len(self.contact_results)}",
            f"  Top contacts:       {len(self.top_contacts)}",
            f"  Personalized:       {len(self.personalized_outreaches)} (avg score {self.avg_personalization_score:.0f}/100)",
            f"  Emails sent:        {self.emails_sent} (skipped {self.emails_skipped})",
            f"  Total runtime:      {total_ms/1000:.1f}s",
        ]
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
            for e in self.errors[:3]:
                lines.append(f"    - {e}")
        timing_str = "  Node timings: " + " | ".join(
            f"{k}={v:.0f}ms" for k, v in self.node_timings_ms.items()
        )
        lines.append(timing_str)
        return "\n".join(lines)
