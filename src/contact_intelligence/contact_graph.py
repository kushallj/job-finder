"""
contact_graph.py — Contact graph construction and adjacency inference.

Why a graph?
  A flat ranked list tells you "who to email first."
  A graph tells you "who knows who" and "what path leads to the decision maker."

  Example:
    You found 6 contacts at Stripe:
      John (CTO), Sarah (VP Eng), Mike (EM), Alice (EM), Tom (Recruiter), Lisa (SWE)

    Graph edges (inferred from tier proximity + department):
      John ─── Sarah  (tier gap = 1, same dept → strong edge)
      Sarah ─── Mike  (tier gap = 1 → strong)
      Sarah ─── Alice (tier gap = 1 → strong)
      Tom  ─── Sarah  (recruiter ↔ hiring manager → functional edge)
      Lisa ─── Mike   (IC ↔ EM in same dept → peer edge)

    This lets us:
      - Find the shortest path to the decision maker (Mike/Alice)
      - Identify who's most "connected" (Sarah = VP is the bridge)
      - Surface Lisa as a potential peer referral to Mike

Graph representation:
  Custom adjacency-list graph (no networkx dependency).
  Nodes: GraphNode (contact + hierarchy score)
  Edges: GraphEdge (weighted by tier proximity + department match)

Edge weight formula:
  base = 1 / (tier_gap + 1)        # closer tiers → stronger connection
  dept_bonus = 0.3 if same_dept     # same department → stronger connection
  functional = 0.4 if recruiter↔manager  # functional hiring relationship
  weight = min(1.0, base + dept_bonus + functional)

Adjacency inference rules:
  1. All contacts at the same company are potentially connected
  2. Contacts within 1 tier step get a strong edge (weight ≥ 0.5)
  3. Contacts within 2 tier steps get a medium edge (weight ≥ 0.3)
  4. Contacts 3+ tiers apart get a weak edge (weight ≥ 0.1) — skips reporting levels
  5. Recruiter ↔ Manager always gets a functional edge (hiring process link)
  6. IC ↔ direct Manager always gets a peer edge
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .role_hierarchy import RoleHierarchy, HierarchyScore, RoleTier


# ---------------------------------------------------------------------------
# Graph data structures
# ---------------------------------------------------------------------------

@dataclass
class GraphNode:
    """A contact node in the company contact graph."""
    contact_id:   str             # email or "name|company" (unique key)
    name:         str
    title:        str
    email:        str             = ""
    company:      str             = ""
    department:   str             = ""
    score:        HierarchyScore  = None   # populated during build
    email_confidence: float       = 0.0   # from email_engine

    @property
    def tier(self) -> RoleTier:
        return self.score.tier if self.score else RoleTier.UNKNOWN


@dataclass
class GraphEdge:
    """A directed edge from source → target."""
    source:   str       # contact_id
    target:   str       # contact_id
    weight:   float     # 0-1 (higher = stronger inferred relationship)
    edge_type: str      # "reporting" | "peer" | "functional" | "cross_dept"


@dataclass
class ContactGraph:
    """
    Adjacency-list company contact graph.

    Attributes:
        nodes:     contact_id → GraphNode
        adj:       contact_id → List[(neighbor_id, weight)]
        edges:     all edges (for analysis)
    """
    company:  str
    nodes:    Dict[str, GraphNode]           = field(default_factory=dict)
    adj:      Dict[str, List[Tuple[str, float]]] = field(default_factory=lambda: defaultdict(list))
    edges:    List[GraphEdge]                = field(default_factory=list)

    # ── Node accessors ─────────────────────────────────────────────────────────

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.contact_id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        self.adj[edge.source].append((edge.target, edge.weight))
        self.adj[edge.target].append((edge.source, edge.weight))  # undirected
        self.edges.append(edge)

    def neighbors(self, contact_id: str) -> List[Tuple[str, float]]:
        return self.adj.get(contact_id, [])

    def node(self, contact_id: str) -> Optional[GraphNode]:
        return self.nodes.get(contact_id)

    # ── Path finding ───────────────────────────────────────────────────────────

    def shortest_path(
        self, source_id: str, target_id: str
    ) -> List[str]:
        """
        BFS shortest path from source to target contact.
        Returns list of contact_ids (empty if no path).
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            return []
        if source_id == target_id:
            return [source_id]

        visited: Set[str] = {source_id}
        queue:   deque    = deque([[source_id]])

        while queue:
            path = queue.popleft()
            node = path[-1]
            for neighbor, _ in self.neighbors(node):
                if neighbor == target_id:
                    return path + [target_id]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return []

    def path_to_decision_maker(self, from_id: str) -> Optional[List[str]]:
        """Find shortest path from any contact to the top decision maker."""
        # Find the highest-tier node (lowest tier number)
        best_id   = None
        best_tier = RoleTier.UNKNOWN
        for cid, node in self.nodes.items():
            if cid == from_id:
                continue
            if node.tier < best_tier:
                best_tier = node.tier
                best_id   = cid

        if best_id is None:
            return None
        return self.shortest_path(from_id, best_id)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def degree(self, contact_id: str) -> int:
        return len(self.adj.get(contact_id, []))

    def weighted_degree(self, contact_id: str) -> float:
        return sum(w for _, w in self.adj.get(contact_id, []))

    def summary(self) -> str:
        return (
            f"ContactGraph({self.company}): "
            f"{len(self.nodes)} nodes, {len(self.edges)} edges"
        )


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

class ContactGraphBuilder:
    """
    Builds a ContactGraph from a list of raw contacts.

    Usage:
        builder = ContactGraphBuilder()
        graph   = builder.build(contacts, company="Stripe", company_size=500)
    """

    _hierarchy = RoleHierarchy()

    def build(
        self,
        contacts:     list,   # List[Contact] from contact_finder
        company:      str,
        company_size: int = 100,
    ) -> ContactGraph:
        graph = ContactGraph(company=company)

        # ── Step 1: Create nodes ───────────────────────────────────────────────
        for c in contacts:
            node_id = (c.email or "").lower() or f"{c.name}|{company}"
            score   = self._hierarchy.score(
                title        = c.title or "",
                company_size = company_size,
                is_tech_role = True,
            )
            node = GraphNode(
                contact_id       = node_id,
                name             = c.name or "",
                title            = c.title or "",
                email            = c.email or "",
                company          = company,
                department       = score.department,
                score            = score,
                email_confidence = getattr(c, "confidence_score", 0.0),
            )
            graph.add_node(node)

        # ── Step 2: Infer edges ────────────────────────────────────────────────
        node_list = list(graph.nodes.values())
        for i, a in enumerate(node_list):
            for b in node_list[i + 1:]:
                edge = self._infer_edge(a, b)
                if edge:
                    graph.add_edge(edge)

        return graph

    def _infer_edge(self, a: GraphNode, b: GraphNode) -> Optional[GraphEdge]:
        """
        Infer whether an edge exists between two nodes.
        Returns None if no meaningful relationship can be inferred.
        """
        tier_a = a.tier
        tier_b = b.tier
        tier_gap = abs(int(tier_a) - int(tier_b))

        # Skip IC ↔ IC in different departments (no meaningful connection)
        if tier_a == RoleTier.IC and tier_b == RoleTier.IC:
            if a.department != b.department:
                return None

        # Base weight from tier proximity
        if tier_gap == 0:
            base = 0.60    # same tier = peers
        elif tier_gap == 1:
            base = 0.55    # direct reporting relationship likely
        elif tier_gap == 2:
            base = 0.35    # skip-level
        elif tier_gap == 3:
            base = 0.20    # stretch
        else:
            base = 0.08    # very distant — weak signal

        # Department bonus
        dept_bonus = 0.25 if (a.department and a.department == b.department) else 0.0

        # Functional edge: Recruiter ↔ Manager (always connected in hiring)
        functional = 0.0
        edge_type  = "cross_dept"
        if tier_a == RoleTier.RECRUITER and tier_b == RoleTier.MANAGER:
            functional = 0.35
            edge_type  = "functional"
        elif tier_a == RoleTier.MANAGER and tier_b == RoleTier.RECRUITER:
            functional = 0.35
            edge_type  = "functional"
        elif tier_gap == 1:
            edge_type = "reporting"
        elif tier_gap == 0:
            edge_type = "peer"

        weight = min(1.0, base + dept_bonus + functional)

        # Only add edge if weight is meaningful
        if weight < 0.10:
            return None

        return GraphEdge(
            source    = a.contact_id,
            target    = b.contact_id,
            weight    = round(weight, 3),
            edge_type = edge_type,
        )
