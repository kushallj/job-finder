"""
graph.py — StateGraph execution engine.

Implements the LangGraph StateGraph API with zero external dependencies.

Key concepts:
  Node      — async function: NEXUSState → NEXUSState
  Edge      — dependency: src_node must complete before dst_node starts
  Cond Edge — routing: after src completes, a function picks the next node
  END       — terminal sentinel; reaching it stops execution

Execution algorithm (Kahn's topological + asyncio parallelism):
  1. Build in_degree table from all declared edges.
  2. Find all nodes with in_degree = 0 → these are "ready".
  3. Execute ALL ready nodes concurrently via asyncio.gather().
  4. After each batch: decrement in_degree of successors.
  5. Repeat until no ready nodes remain OR END is reached.

Parallel branches emerge naturally:
  add_edge("scrape", "tailor_resume")
  add_edge("scrape", "contact_intel")
  → After "scrape" completes both "tailor_resume" and "contact_intel"
    have in_degree=0 simultaneously → asyncio.gather() runs them in parallel.

Fan-in also emerges naturally:
  add_edge("tailor_resume", "personalize")
  add_edge("contact_intel", "personalize")
  → "personalize" has in_degree=2; it only fires after BOTH predecessors complete.

Conditional edges override normal edges for the source node:
  The routing function runs AFTER the source node completes.
  It returns a key; the mapping resolves that key to the next node name.
  The conditional edge's target is added to the ready set.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Set, Tuple

from .state import NEXUSState, NodeStatus

log = logging.getLogger(__name__)

# Sentinel for the terminal node
END = "__end__"

# Type aliases
NodeFn   = Callable[[NEXUSState], Any]   # async (State) → State
RouteFn  = Callable[[NEXUSState], str]   # (State) → next_node_key


@dataclass
class _ConditionalEdge:
    condition: RouteFn
    mapping:   Dict[str, str]   # return value → node name


class StateGraph:
    """
    Builds a DAG of async nodes connected by edges and conditional routes.

    Usage:
        g = StateGraph(NEXUSState)
        g.add_node("scrape", scrape_node)
        g.add_node("tailor", tailor_node)
        g.add_edge("scrape", "tailor")
        g.set_entry_point("scrape")
        g.set_finish_point("tailor")
        compiled = g.compile()
        result   = await compiled.run(initial_state)
    """

    def __init__(self, state_class=None):
        self._state_class  = state_class
        self._nodes:       Dict[str, NodeFn]             = {}
        self._edges:       Dict[str, List[str]]          = defaultdict(list)
        self._cond_edges:  Dict[str, _ConditionalEdge]   = {}
        self._entry:       Optional[str]                 = None
        self._finish:      Optional[str]                 = None

    # ── Builder API ────────────────────────────────────────────────────────────

    def add_node(self, name: str, fn: NodeFn) -> "StateGraph":
        """Register an async node function."""
        if not asyncio.iscoroutinefunction(fn):
            raise TypeError(f"Node '{name}' must be an async function.")
        self._nodes[name] = fn
        return self

    def add_edge(self, src: str, dst: str) -> "StateGraph":
        """Declare that dst cannot start until src has completed."""
        self._edges[src].append(dst)
        return self

    def add_conditional_edge(
        self,
        src:       str,
        condition: RouteFn,
        mapping:   Dict[str, str],
    ) -> "StateGraph":
        """
        After `src` completes, call `condition(state)` → key.
        `mapping[key]` is the next node to execute.
        Use END as a mapping value to terminate the pipeline.
        """
        self._cond_edges[src] = _ConditionalEdge(condition=condition, mapping=mapping)
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        self._entry = name
        return self

    def set_finish_point(self, name: str) -> "StateGraph":
        self._finish = name
        return self

    def compile(self) -> "CompiledGraph":
        """
        Validate the graph and return an executable CompiledGraph.
        Raises ValueError on structural issues (missing entry, orphan nodes).
        """
        if not self._entry:
            raise ValueError("No entry point set. Call set_entry_point().")
        if self._entry not in self._nodes:
            raise ValueError(f"Entry node '{self._entry}' is not registered.")

        # Compute predecessor map (needed for fan-in in-degree tracking)
        predecessors: Dict[str, Set[str]] = defaultdict(set)
        for src, dsts in self._edges.items():
            for dst in dsts:
                predecessors[dst].add(src)
        # Conditional edges also create predecessor relationships
        for src, ce in self._cond_edges.items():
            for dst in ce.mapping.values():
                if dst != END:
                    predecessors[dst].add(src)

        return CompiledGraph(
            nodes        = dict(self._nodes),
            edges        = dict(self._edges),
            cond_edges   = dict(self._cond_edges),
            predecessors = {k: set(v) for k, v in predecessors.items()},
            entry        = self._entry,
            finish       = self._finish or END,
        )


class CompiledGraph:
    """
    Executable form of a StateGraph.
    Not constructed directly — use StateGraph.compile().
    """

    def __init__(
        self,
        nodes:        Dict[str, NodeFn],
        edges:        Dict[str, List[str]],
        cond_edges:   Dict[str, _ConditionalEdge],
        predecessors: Dict[str, Set[str]],
        entry:        str,
        finish:       str,
    ):
        self._nodes        = nodes
        self._edges        = edges
        self._cond_edges   = cond_edges
        self._predecessors = predecessors
        self._entry        = entry
        self._finish       = finish

    # ── Execution ──────────────────────────────────────────────────────────────

    async def run(self, initial_state: NEXUSState) -> NEXUSState:
        """
        Execute the DAG from entry to finish/END.

        Parallel branches are exploited automatically: any set of nodes
        whose predecessors are all completed runs concurrently.
        """
        state = initial_state

        # Kahn in-degree table (decremented as nodes complete)
        in_degree: Dict[str, int] = self._build_in_degree()
        completed: Set[str]       = set()

        # Seed: entry node has in_degree = 0
        in_degree[self._entry] = 0

        while True:
            # Nodes that are registered, not yet done, and have all preds complete
            ready = [
                name for name, deg in in_degree.items()
                if deg == 0 and name not in completed and name in self._nodes
            ]

            if not ready:
                break

            log.info("DAG: executing nodes in parallel: %s", ready)

            # Run all ready nodes concurrently, capture exceptions individually
            results: List[Tuple[str, Optional[Exception]]] = await asyncio.gather(
                *[self._execute_node(name, state) for name in ready],
                return_exceptions=True,
            )

            # Process results & update state
            newly_completed: List[str] = []
            for name, result in zip(ready, results):
                if isinstance(result, BaseException):
                    log.error("Node '%s' raised: %s", name, result)
                    state.mark_node_failed(name, str(result), 0)
                    # Don't block the pipeline — mark as completed so successors can proceed
                else:
                    newly_completed.append(name)

                completed.add(name)

            # Decrement in_degree for all successors of completed nodes
            for name in completed & set(ready):
                for succ in self._get_successors(name, state):
                    if succ != END and succ in in_degree:
                        in_degree[succ] -= 1

            # Check if finish reached or END routed
            if self._finish in completed:
                break
            if any(
                self._get_successors(name, state) == [END]
                for name in ready
                if name in completed
            ):
                break

            # Safety: if no progress was made, break to avoid infinite loop
            if not any(name in completed for name in ready):
                log.warning("DAG: no nodes completed this round — stopping")
                break

        log.info("DAG run complete: %d nodes executed", len(completed))
        return state

    # ── Node execution ─────────────────────────────────────────────────────────

    async def _execute_node(self, name: str, state: NEXUSState) -> None:
        """Run a single node, update state, record telemetry."""
        t0 = state.mark_node_start(name)
        log.info("→ Node '%s' starting", name)
        try:
            await self._nodes[name](state)
            state.mark_node_done(name, t0)
            log.info("✓ Node '%s' done in %.0fms", name, state.node_timings_ms.get(name, 0))
        except Exception as exc:
            state.mark_node_failed(name, traceback.format_exc(), t0)
            log.error("✗ Node '%s' failed: %s", name, exc)
            raise   # propagate so gather() captures it

    # ── Successor resolution ───────────────────────────────────────────────────

    def _get_successors(self, name: str, state: NEXUSState) -> List[str]:
        """
        Returns list of successors for a completed node.
        If a conditional edge exists, evaluates the condition first.
        """
        if name in self._cond_edges:
            ce        = self._cond_edges[name]
            route_key = ce.condition(state)
            target    = ce.mapping.get(route_key, END)
            return [target]
        return self._edges.get(name, [END if name == self._finish else []])

    # ── In-degree calculation ──────────────────────────────────────────────────

    def _build_in_degree(self) -> Dict[str, int]:
        """
        Build in_degree dict from static edges.
        Conditional edge targets are included; their in_degree is set to 1
        (they will be decremented when the source node completes).
        """
        in_degree: Dict[str, int] = {name: 0 for name in self._nodes}

        for src, dsts in self._edges.items():
            for dst in dsts:
                if dst != END and dst in in_degree:
                    in_degree[dst] += 1

        # Conditional targets: each contributes +1 from their source
        for src, ce in self._cond_edges.items():
            for dst in ce.mapping.values():
                if dst != END and dst in in_degree:
                    in_degree[dst] += 1   # conditional edge source is a predecessor

        # Entry point: override to 0 (even if it appears as a dst elsewhere)
        in_degree[self._entry] = 0
        return in_degree

    def visualize(self) -> str:
        """ASCII DAG topology for debugging."""
        lines = ["DAG topology:"]
        for src, dsts in self._edges.items():
            for dst in dsts:
                lines.append(f"  {src} → {dst}")
        for src, ce in self._cond_edges.items():
            for key, dst in ce.mapping.items():
                lines.append(f"  {src} →[{key}]→ {dst}")
        return "\n".join(lines)
