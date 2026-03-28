"""
nexus_graph.py — Wires the NEXUS DAG nodes into a compiled StateGraph.

DAG topology:

  START
    │
  scrape_node           ← fetch jobs from all platforms
    │
  analyze_jd_node       ← extract JD skills/requirements (batch LLM)
    │
    ├──── tailor_resume_node   ← generate tailored PDFs   (parallel)
    │
    └──── contact_intel_node   ← graph-rank contacts       (parallel)
    │
  personalize_node      ← generate personalized email per contact
    │
  outreach_node         ← send (or dry-run) emails
    │
    ├──[run_feedback]── feedback_node  ← update hook weights + digest
    │
    └──[skip_feedback]─ END

Conditional routing:
  After outreach_node:
    if state.route_decision == "run_feedback" AND not state.dry_run → feedback_node
    else → END

Why this topology?
  - analyze_jd must finish before resume tailoring (needs JDAnalysis for ATS scoring)
  - tailor_resume and contact_intel are independent → parallel (save ~40% wall time)
  - personalize needs both resume variants (for role-fit hooks) and ranked contacts
  - feedback only runs after real sends (no feedback on dry runs)
"""

from __future__ import annotations

from .graph import StateGraph, CompiledGraph, END
from .state import NEXUSState
from .nodes import (
    scrape_node,
    analyze_jd_node,
    tailor_resume_node,
    contact_intel_node,
    personalize_node,
    outreach_node,
    feedback_node,
)


def _feedback_router(state: NEXUSState) -> str:
    """
    Route after outreach_node:
      - "run_feedback" if emails were sent and not a dry run
      - "skip_feedback" (→ END) otherwise
    """
    if state.dry_run:
        return "skip_feedback"
    if state.route_decision == "run_feedback" and state.emails_sent > 0:
        return "run_feedback"
    return "skip_feedback"


def build_nexus_graph() -> CompiledGraph:
    """
    Construct and compile the NEXUS StateGraph.

    Returns a CompiledGraph ready to call:
        result = await build_nexus_graph().run(initial_state)
    """
    graph = StateGraph(NEXUSState)

    # ── Register nodes ──────────────────────────────────────────────────────
    graph.add_node("scrape",        scrape_node)
    graph.add_node("analyze_jd",    analyze_jd_node)
    graph.add_node("tailor_resume", tailor_resume_node)
    graph.add_node("contact_intel", contact_intel_node)
    graph.add_node("personalize",   personalize_node)
    graph.add_node("outreach",      outreach_node)
    graph.add_node("feedback",      feedback_node)

    # ── Edges ────────────────────────────────────────────────────────────────
    # Sequential: scrape → analyze_jd
    graph.add_edge("scrape",        "analyze_jd")

    # Fan-out: analyze_jd → [tailor_resume, contact_intel] (parallel)
    graph.add_edge("analyze_jd",    "tailor_resume")
    graph.add_edge("analyze_jd",    "contact_intel")

    # Fan-in: both parallel branches → personalize
    graph.add_edge("tailor_resume", "personalize")
    graph.add_edge("contact_intel", "personalize")

    # Sequential: personalize → outreach
    graph.add_edge("personalize",   "outreach")

    # Conditional: outreach → feedback OR END
    graph.add_conditional_edge(
        src       = "outreach",
        condition = _feedback_router,
        mapping   = {
            "run_feedback":  "feedback",
            "skip_feedback": END,
        },
    )

    # ── Entry + finish ───────────────────────────────────────────────────────
    graph.set_entry_point("scrape")
    graph.set_finish_point("feedback")

    return graph.compile()


# Default queries and config for a full pipeline run
DEFAULT_CONFIG = {
    "search_queries": [
        "Python Software Engineer",
        "Backend Developer FastAPI",
        "Full Stack Developer React",
        "Software Development Engineer",
        "GenAI Engineer",
    ],
    "resume_path":        "data/resume.txt",
    "dry_run":            False,
    "max_jobs_per_query": 5,
    "max_jobs_to_tailor": 5,
    "max_companies":      10,
    "company_size_hint":  150,
}
