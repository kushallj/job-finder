"""
src/contact_intelligence — Contact Intelligence & Graph Mining (Task 4)

Adds decision-maker intelligence and graph-based ranking on top of the
existing ContactFinder discovery layer.

Pipeline:
  raw contacts (from ContactFinder + EmailDiscoveryEngine)
      ↓
  RoleHierarchy.score(contact)     → seniority tier + decision_maker_prob
      ↓
  ContactGraph.build(contacts)     → adjacency inference + graph structure
      ↓
  GraphRanker.rank(graph, job)     → personalized PageRank scores
      ↓
  IntelligenceEngine.analyze()     → RankedContact list with full metadata

Key outputs per contact:
  decision_maker_score   — 0-100 how likely they make the hiring call
  reachability_score     — 0-100 email quality + role accessibility
  graph_centrality       — influence within their company network
  outreach_priority      — combined score (sort key)
  recommended_approach   — direct_pitch | hr_route | warm_intro | referral
  decision_path          — their role in the hiring chain (e.g. "budget owner")
"""

from .role_hierarchy import RoleTier, RoleHierarchy, HierarchyScore
from .contact_graph import ContactGraph, ContactGraphBuilder, GraphNode, GraphEdge
from .graph_ranker import GraphRanker, RankedContact
from .intelligence_engine import IntelligenceEngine, get_engine

__all__ = [
    "RoleTier",
    "RoleHierarchy",
    "HierarchyScore",
    "ContactGraph",
    "ContactGraphBuilder",
    "GraphNode",
    "GraphEdge",
    "GraphRanker",
    "RankedContact",
    "IntelligenceEngine",
    "get_engine",
]
