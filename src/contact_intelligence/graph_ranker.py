"""
graph_ranker.py — Personalized PageRank contact ranker.

Algorithm:
  Standard PageRank computes "how often does a random walk land on this node?"
  Personalized PageRank adds a seed distribution so the walk restarts
  preferentially at nodes that match our goal (hiring decision makers).

  Personalized PageRank formula:
    PR(v) = α × seed(v) + (1 - α) × Σ_u [ PR(u) × w(u,v) / deg(u) ]

  Where:
    α      = 0.15  (restart probability — standard PageRank uses 0.15)
    seed   = normalized distribution over "goal" nodes
    w(u,v) = edge weight between u and v
    deg(u) = weighted degree of u

  Goal nodes (seed distribution):
    We seed on MANAGER and DIRECTOR tier nodes with higher weight,
    because these are the most likely hiring decision makers.

  Convergence: 30 iterations (typical PageRank converges in 20-50 for
  graphs this small: 5-20 nodes per company).

Output (RankedContact):
  decision_maker_score   — hierarchy score × 100
  graph_centrality       — PageRank score (0-1, normalized to 0-100)
  reachability_score     — email confidence × tier accessibility
  outreach_priority      — weighted combination (main sort key)
  recommended_approach   — derived from tier + company size
  decision_path          — shortest path to top decision maker
  outreach_notes         — actionable approach advice
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .role_hierarchy import RoleTier
from .contact_graph import ContactGraph, GraphNode


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class RankedContact:
    """A contact with full intelligence scoring for outreach prioritization."""
    node:                  GraphNode
    decision_maker_score:  float      # 0-100 — hierarchy × company size
    graph_centrality:      float      # 0-100 — personalized PageRank
    reachability_score:    float      # 0-100 — email quality × accessibility
    outreach_priority:     float      # 0-100 — main sort key (weighted combo)
    recommended_approach:  str        # "direct_pitch" | "hr_route" | "warm_intro" | "peer_intro"
    decision_path:         List[str]  = field(default_factory=list)  # names of path to DM
    decision_path_role:    str        = ""    # "direct_decision_maker" | "budget_owner" | etc.
    outreach_notes:        str        = ""    # actionable advice

    @property
    def name(self) -> str:
        return self.node.name

    @property
    def email(self) -> str:
        return self.node.email

    @property
    def title(self) -> str:
        return self.node.title

    def __repr__(self) -> str:
        return (
            f"RankedContact({self.name!r} | {self.title!r} | "
            f"priority={self.outreach_priority:.0f} | "
            f"approach={self.recommended_approach})"
        )


# ---------------------------------------------------------------------------
# GraphRanker
# ---------------------------------------------------------------------------

class GraphRanker:
    """
    Ranks all contacts in a company graph using Personalized PageRank.

    Usage:
        ranker  = GraphRanker()
        ranked  = ranker.rank(graph, job_title="Software Engineer")
        for rc in ranked:
            print(rc)
    """

    # PageRank hyperparameters
    ALPHA      = 0.15    # restart probability
    ITERATIONS = 35      # convergence iterations
    EPSILON    = 1e-6    # convergence tolerance

    # Output score weights
    W_DM          = 0.45   # decision maker probability
    W_CENTRALITY  = 0.25   # graph centrality (PageRank)
    W_REACHABLE   = 0.30   # email reachability

    def rank(
        self,
        graph:        ContactGraph,
        job_title:    str = "",
        is_tech_role: bool = True,
    ) -> List[RankedContact]:
        """
        Rank all contacts in the graph by outreach priority.
        Returns list sorted by outreach_priority descending.
        """
        if not graph.nodes:
            return []

        # ── Step 1: Personalized PageRank ──────────────────────────────────────
        pr_scores = self._personalized_pagerank(graph)

        # Normalize PageRank to 0-100
        max_pr = max(pr_scores.values()) if pr_scores else 1.0
        norm_pr = {cid: (v / max_pr) * 100 for cid, v in pr_scores.items()}

        # ── Step 2: Score each contact ─────────────────────────────────────────
        ranked: List[RankedContact] = []
        for cid, node in graph.nodes.items():
            dm_score      = node.score.combined_dm_score if node.score else 20.0
            centrality    = norm_pr.get(cid, 0.0)
            reachability  = self._reachability_score(node)

            priority = (
                dm_score     * self.W_DM +
                centrality   * self.W_CENTRALITY +
                reachability * self.W_REACHABLE
            )

            approach    = self._recommended_approach(node, graph)
            dm_path     = self._path_to_dm(cid, graph)
            path_names  = [graph.nodes[i].name for i in dm_path if i in graph.nodes]

            ranked.append(RankedContact(
                node                 = node,
                decision_maker_score = dm_score,
                graph_centrality     = centrality,
                reachability_score   = reachability,
                outreach_priority    = round(priority, 1),
                recommended_approach = approach,
                decision_path        = path_names,
                decision_path_role   = node.score.decision_path_role if node.score else "",
                outreach_notes       = node.score.outreach_notes if node.score else "",
            ))

        ranked.sort(key=lambda r: r.outreach_priority, reverse=True)
        return ranked

    # ── Personalized PageRank ──────────────────────────────────────────────────

    def _personalized_pagerank(self, graph: ContactGraph) -> Dict[str, float]:
        """
        Power-iteration personalized PageRank.

        Seed distribution: proportional to (MANAGER=1.0, DIRECTOR=0.8,
        VP=0.6, RECRUITER=0.5, other=0.2).
        """
        nodes   = list(graph.nodes.keys())
        n       = len(nodes)
        if n == 0:
            return {}
        if n == 1:
            return {nodes[0]: 1.0}

        idx = {cid: i for i, cid in enumerate(nodes)}

        # Seed vector (personalization)
        seed_weights = {
            RoleTier.MANAGER:   1.00,
            RoleTier.DIRECTOR:  0.80,
            RoleTier.VP:        0.60,
            RoleTier.RECRUITER: 0.50,
            RoleTier.C_SUITE:   0.40,
            RoleTier.FOUNDER:   0.40,
            RoleTier.IC:        0.15,
            RoleTier.UNKNOWN:   0.20,
        }
        raw_seed = [seed_weights.get(graph.nodes[cid].tier, 0.20) for cid in nodes]
        seed_sum = sum(raw_seed) or 1.0
        seed     = [s / seed_sum for s in raw_seed]

        # Build weighted adjacency (row-normalized transition matrix)
        # trans[i] = list of (j, w_ij / deg_i)
        trans: List[List[Tuple[int, float]]] = [[] for _ in range(n)]
        for cid in nodes:
            i       = idx[cid]
            nbrs    = graph.neighbors(cid)
            tot_w   = sum(w for _, w in nbrs)
            if tot_w > 0:
                for nb_id, w in nbrs:
                    j = idx.get(nb_id)
                    if j is not None:
                        trans[i].append((j, w / tot_w))

        # Power iteration
        pr   = [1.0 / n] * n
        for _ in range(self.ITERATIONS):
            new_pr = [self.ALPHA * seed[i] for i in range(n)]
            for i in range(n):
                for j, prob in trans[i]:
                    new_pr[j] += (1 - self.ALPHA) * pr[i] * prob
            # Check convergence
            delta = sum(abs(new_pr[i] - pr[i]) for i in range(n))
            pr = new_pr
            if delta < self.EPSILON:
                break

        return {nodes[i]: pr[i] for i in range(n)}

    # ── Reachability score ─────────────────────────────────────────────────────

    @staticmethod
    def _reachability_score(node: GraphNode) -> float:
        """
        0-100 score for how easy this contact is to actually reach.
        Combines email confidence + role accessibility.
        """
        # Email confidence (0-100 → 0-60 contribution)
        email_c = min(100.0, node.email_confidence)
        email_contrib = email_c * 0.60

        # Has a real email (not just a generic alias)?
        if node.email:
            email_contrib += 15

        # Role accessibility (ICs often more responsive to cold email than C-suite)
        tier_access = {
            RoleTier.MANAGER:   25,
            RoleTier.RECRUITER: 22,
            RoleTier.DIRECTOR:  18,
            RoleTier.IC:        20,
            RoleTier.VP:        12,
            RoleTier.C_SUITE:   8,
            RoleTier.FOUNDER:   10,
            RoleTier.UNKNOWN:   10,
        }
        role_contrib = tier_access.get(node.tier, 10)

        return min(100.0, email_contrib + role_contrib)

    # ── Recommended approach ───────────────────────────────────────────────────

    @staticmethod
    def _recommended_approach(node: GraphNode, graph: ContactGraph) -> str:
        """Recommend the outreach strategy for this contact."""
        tier = node.tier

        if tier == RoleTier.MANAGER:
            return "direct_pitch"
        if tier == RoleTier.RECRUITER:
            return "hr_route"
        if tier == RoleTier.IC:
            # Check if they're connected to a manager
            for nb_id, _ in graph.neighbors(node.contact_id):
                nb = graph.node(nb_id)
                if nb and nb.tier == RoleTier.MANAGER:
                    return "peer_intro"
            return "direct_pitch"
        if tier in (RoleTier.FOUNDER, RoleTier.C_SUITE):
            return "direct_pitch"   # small company: go straight to top
        if tier in (RoleTier.VP, RoleTier.DIRECTOR):
            return "warm_intro"

        return "direct_pitch"

    # ── Path to decision maker ─────────────────────────────────────────────────

    @staticmethod
    def _path_to_dm(from_id: str, graph: ContactGraph) -> List[str]:
        """Find the path from this contact to the top decision maker."""
        # DM = highest-priority contact we know of (MANAGER or FOUNDER for small cos)
        best_id   = None
        best_tier = RoleTier.UNKNOWN
        for cid, node in graph.nodes.items():
            if cid != from_id and node.tier < best_tier:
                best_tier = node.tier
                best_id   = cid

        if best_id is None or best_id == from_id:
            return [from_id]

        return graph.shortest_path(from_id, best_id)
