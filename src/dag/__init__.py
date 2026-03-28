"""
src/dag — LangGraph-inspired DAG Orchestration Engine (Task 1)

Implements a StateGraph execution model:
  - Nodes   : async functions  (State → State)
  - Edges   : dependency declarations (src → dst)
  - Routing : conditional edges (State → next_node_name)
  - Execution: Kahn's topological sort + asyncio.gather() for parallel branches

Why rebuild instead of using LangGraph?
  LangGraph is excellent but pulls in the full LangChain stack (~200 MB).
  This 200-line engine replicates the exact same execution model with
  zero new dependencies — and it's easier to debug.

NEXUS DAG topology:
                    scrape_node
                        │
                   analyze_jd_node
                        │
          ┌─────────────┴─────────────┐
   tailor_resume_node      contact_intel_node   ← parallel
          └─────────────┬─────────────┘
                  personalize_node
                        │
                   outreach_node
                        │
                   feedback_node  (conditional — skipped on dry_run)
                        │
                       END
"""

from .state import NEXUSState, NodeStatus
from .graph import StateGraph, CompiledGraph, END
from .nexus_graph import build_nexus_graph

__all__ = [
    "NEXUSState",
    "NodeStatus",
    "StateGraph",
    "CompiledGraph",
    "END",
    "build_nexus_graph",
]
