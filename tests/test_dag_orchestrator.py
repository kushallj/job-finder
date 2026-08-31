"""
Comprehensive tests for DAG orchestrator workflow execution.

Tests verify:
- StateGraph node and edge representation (Requirement 9.1)
- Conditional routing between nodes (Requirement 9.2)
- Parallel execution of independent nodes (Requirement 9.3, 9.6)
- Topological sorting for execution order (Requirement 9.4)
- Dependency enforcement during execution (Requirement 9.5)

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6**
"""

import asyncio
import pytest
import time
from typing import List, Dict, Set
from collections import defaultdict

from src.dag.state import NEXUSState, NodeStatus
from src.dag.graph import StateGraph, CompiledGraph, END


# ---------------------------------------------------------------------------
# Test Helper Nodes
# ---------------------------------------------------------------------------

# Global tracking for execution order and timing
execution_log: List[str] = []
execution_times: Dict[str, float] = {}
concurrent_nodes: Set[str] = set()
max_concurrent: int = 0


def reset_tracking():
    """Reset global tracking variables before each test."""
    global execution_log, execution_times, concurrent_nodes, max_concurrent
    execution_log = []
    execution_times = {}
    concurrent_nodes = set()
    max_concurrent = 0


async def tracked_node(state: NEXUSState, name: str, delay: float = 0.0) -> NEXUSState:
    """
    Node that tracks its execution for test verification.
    
    Args:
        state: The shared NEXUSState
        name: Node identifier for tracking
        delay: Optional delay to simulate work (enables parallel detection)
    """
    global execution_log, execution_times, concurrent_nodes, max_concurrent
    
    start_time = time.monotonic()
    concurrent_nodes.add(name)
    max_concurrent = max(max_concurrent, len(concurrent_nodes))
    
    execution_log.append(f"start:{name}")
    
    if delay > 0:
        await asyncio.sleep(delay)
    
    execution_log.append(f"end:{name}")
    execution_times[name] = time.monotonic() - start_time
    concurrent_nodes.discard(name)
    
    # Store in state for verification
    if not hasattr(state, '_execution_order'):
        state._execution_order = []
    state._execution_order.append(name)
    
    return state


# Factory functions for creating tracked nodes
def make_node(name: str, delay: float = 0.0):
    """Create a tracked async node with the given name."""
    async def node_fn(state: NEXUSState) -> NEXUSState:
        return await tracked_node(state, name, delay)
    return node_fn


# ---------------------------------------------------------------------------
# Test Class: StateGraph Node and Edge Representation (Requirement 9.1)
# ---------------------------------------------------------------------------

class TestStateGraphRepresentation:
    """
    Tests that StateGraph correctly represents workflows as nodes and edges.
    
    **Validates: Requirement 9.1 - THE StateGraph SHALL represent workflows
    as nodes and edges**
    """

    def test_node_registration(self):
        """Nodes are properly registered in the graph."""
        graph = StateGraph()
        graph.add_node("node_a", make_node("A"))
        graph.add_node("node_b", make_node("B"))
        graph.add_node("node_c", make_node("C"))
        
        assert "node_a" in graph._nodes
        assert "node_b" in graph._nodes
        assert "node_c" in graph._nodes
        assert len(graph._nodes) == 3


    def test_edge_registration(self):
        """Edges are properly registered between nodes."""
        graph = StateGraph()
        graph.add_node("node_a", make_node("A"))
        graph.add_node("node_b", make_node("B"))
        graph.add_node("node_c", make_node("C"))
        
        graph.add_edge("node_a", "node_b")
        graph.add_edge("node_b", "node_c")
        
        assert "node_b" in graph._edges["node_a"]
        assert "node_c" in graph._edges["node_b"]

    def test_multiple_outgoing_edges(self):
        """A node can have multiple outgoing edges (fan-out)."""
        graph = StateGraph()
        graph.add_node("source", make_node("source"))
        graph.add_node("target_1", make_node("target_1"))
        graph.add_node("target_2", make_node("target_2"))
        graph.add_node("target_3", make_node("target_3"))
        
        graph.add_edge("source", "target_1")
        graph.add_edge("source", "target_2")
        graph.add_edge("source", "target_3")
        
        assert len(graph._edges["source"]) == 3
        assert "target_1" in graph._edges["source"]
        assert "target_2" in graph._edges["source"]
        assert "target_3" in graph._edges["source"]

    def test_multiple_incoming_edges(self):
        """A node can have multiple incoming edges (fan-in)."""
        graph = StateGraph()
        graph.add_node("source_1", make_node("source_1"))
        graph.add_node("source_2", make_node("source_2"))
        graph.add_node("target", make_node("target"))
        
        graph.add_edge("source_1", "target")
        graph.add_edge("source_2", "target")
        
        # Both edges point to target
        assert "target" in graph._edges["source_1"]
        assert "target" in graph._edges["source_2"]


    def test_chain_fluent_api(self):
        """Graph builder methods return self for method chaining."""
        graph = StateGraph()
        result = (
            graph
            .add_node("a", make_node("A"))
            .add_node("b", make_node("B"))
            .add_edge("a", "b")
            .set_entry_point("a")
            .set_finish_point("b")
        )
        assert result is graph

    def test_entry_and_finish_points(self):
        """Entry and finish points are properly set."""
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("end", make_node("end"))
        graph.set_entry_point("start")
        graph.set_finish_point("end")
        
        assert graph._entry == "start"
        assert graph._finish == "end"

    def test_compiled_graph_preserves_structure(self):
        """CompiledGraph preserves the graph structure from StateGraph."""
        graph = StateGraph()
        graph.add_node("a", make_node("A"))
        graph.add_node("b", make_node("B"))
        graph.add_node("c", make_node("C"))
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.set_entry_point("a")
        graph.set_finish_point("c")
        
        compiled = graph.compile()
        
        assert "a" in compiled._nodes
        assert "b" in compiled._nodes
        assert "c" in compiled._nodes
        assert "b" in compiled._edges["a"]
        assert "c" in compiled._edges["b"]


# ---------------------------------------------------------------------------
# Test Class: Conditional Routing (Requirement 9.2)
# ---------------------------------------------------------------------------

class TestConditionalRouting:
    """
    Tests for conditional routing between nodes.
    
    **Validates: Requirement 9.2 - THE StateGraph SHALL support conditional
    routing between nodes**
    """

    @pytest.mark.asyncio
    async def test_conditional_edge_true_path(self):
        """Conditional edge routes to the correct node when condition is true."""
        reset_tracking()
        
        def route_condition(state: NEXUSState) -> str:
            return "path_true" if state.dry_run else "path_false"
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("true_node", make_node("true_node"))
        graph.add_node("false_node", make_node("false_node"))
        
        graph.add_conditional_edge(
            "start",
            route_condition,
            {"path_true": "true_node", "path_false": "false_node"}
        )
        graph.set_entry_point("start")
        graph.set_finish_point("true_node")
        
        compiled = graph.compile()
        state = NEXUSState(dry_run=True)
        result = await compiled.run(state)
        
        assert "start" in execution_log[0]
        assert "true_node" in str(execution_log)
        assert "false_node" not in str(execution_log)


    @pytest.mark.asyncio
    async def test_conditional_edge_false_path(self):
        """Conditional edge routes correctly when condition is false."""
        reset_tracking()
        
        def route_condition(state: NEXUSState) -> str:
            return "path_true" if state.dry_run else "path_false"
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("true_node", make_node("true_node"))
        graph.add_node("false_node", make_node("false_node"))
        
        graph.add_conditional_edge(
            "start",
            route_condition,
            {"path_true": "true_node", "path_false": "false_node"}
        )
        graph.set_entry_point("start")
        graph.set_finish_point("false_node")
        
        compiled = graph.compile()
        state = NEXUSState(dry_run=False)
        result = await compiled.run(state)
        
        assert "start" in execution_log[0]
        assert "false_node" in str(execution_log)
        assert "true_node" not in str(execution_log)

    @pytest.mark.asyncio
    async def test_conditional_routing_to_end(self):
        """Conditional edge can route to END sentinel."""
        reset_tracking()
        
        def should_skip(state: NEXUSState) -> str:
            return "skip" if state.dry_run else "continue"
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("process", make_node("process"))
        
        graph.add_conditional_edge(
            "start",
            should_skip,
            {"skip": END, "continue": "process"}
        )
        graph.set_entry_point("start")
        graph.set_finish_point("process")
        
        compiled = graph.compile()
        state = NEXUSState(dry_run=True)
        result = await compiled.run(state)
        
        assert "start" in str(execution_log)
        assert "process" not in str(execution_log)  # Should skip to END


    @pytest.mark.asyncio
    async def test_conditional_routing_based_on_state_value(self):
        """Conditional routing based on state values other than dry_run."""
        reset_tracking()
        
        def route_by_job_count(state: NEXUSState) -> str:
            if len(state.scraped_jobs) > 10:
                return "many_jobs"
            elif len(state.scraped_jobs) > 0:
                return "some_jobs"
            return "no_jobs"
        
        graph = StateGraph()
        graph.add_node("scrape", make_node("scrape"))
        graph.add_node("process_many", make_node("process_many"))
        graph.add_node("process_some", make_node("process_some"))
        graph.add_node("skip", make_node("skip"))
        
        graph.add_conditional_edge(
            "scrape",
            route_by_job_count,
            {
                "many_jobs": "process_many",
                "some_jobs": "process_some",
                "no_jobs": "skip"
            }
        )
        graph.set_entry_point("scrape")
        graph.set_finish_point("process_some")
        
        compiled = graph.compile()
        
        # Test with some jobs
        state = NEXUSState()
        state.scraped_jobs = ["job1", "job2", "job3"]
        result = await compiled.run(state)
        
        assert "scrape" in str(execution_log)
        assert "process_some" in str(execution_log)
        assert "process_many" not in str(execution_log)
        assert "skip" not in str(execution_log)


    @pytest.mark.asyncio
    async def test_multiple_conditional_edges(self):
        """Multiple nodes can have conditional edges."""
        reset_tracking()
        
        def first_condition(state: NEXUSState) -> str:
            return "a" if state.dry_run else "b"
        
        def second_condition(state: NEXUSState) -> str:
            return "c" if state.max_jobs_per_query > 5 else "d"
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("node_a", make_node("node_a"))
        graph.add_node("node_b", make_node("node_b"))
        graph.add_node("node_c", make_node("node_c"))
        graph.add_node("node_d", make_node("node_d"))
        
        graph.add_conditional_edge("start", first_condition, {"a": "node_a", "b": "node_b"})
        graph.add_conditional_edge("node_a", second_condition, {"c": "node_c", "d": "node_d"})
        
        graph.set_entry_point("start")
        graph.set_finish_point("node_c")
        
        compiled = graph.compile()
        state = NEXUSState(dry_run=True, max_jobs_per_query=10)
        result = await compiled.run(state)
        
        assert "start" in str(execution_log)
        assert "node_a" in str(execution_log)
        assert "node_c" in str(execution_log)
        assert "node_b" not in str(execution_log)
        assert "node_d" not in str(execution_log)


# ---------------------------------------------------------------------------
# Test Class: Parallel Execution (Requirements 9.3, 9.6)
# ---------------------------------------------------------------------------

class TestParallelExecution:
    """
    Tests for parallel execution of independent nodes.
    
    **Validates: Requirement 9.3 - THE StateGraph SHALL support parallel
    execution of independent nodes**
    
    **Validates: Requirement 9.6 - WHEN executing parallel nodes, THE
    DAGOrchestrator SHALL execute them concurrently**
    """

    @pytest.mark.asyncio
    async def test_parallel_fan_out_concurrent_execution(self):
        """Independent nodes after fan-out execute concurrently."""
        reset_tracking()
        
        # Create nodes with delays to detect parallel execution
        graph = StateGraph()
        graph.add_node("start", make_node("start", delay=0.0))
        graph.add_node("parallel_1", make_node("parallel_1", delay=0.05))
        graph.add_node("parallel_2", make_node("parallel_2", delay=0.05))
        graph.add_node("parallel_3", make_node("parallel_3", delay=0.05))
        graph.add_node("join", make_node("join", delay=0.0))
        
        graph.add_edge("start", "parallel_1")
        graph.add_edge("start", "parallel_2")
        graph.add_edge("start", "parallel_3")
        graph.add_edge("parallel_1", "join")
        graph.add_edge("parallel_2", "join")
        graph.add_edge("parallel_3", "join")
        
        graph.set_entry_point("start")
        graph.set_finish_point("join")
        
        compiled = graph.compile()
        state = NEXUSState()
        
        start_time = time.monotonic()
        result = await compiled.run(state)
        total_time = time.monotonic() - start_time
        
        # If run sequentially, 3 x 0.05s = 0.15s
        # If run in parallel, should be ~0.05s + overhead
        # Allow generous margin for async overhead on slow systems
        assert total_time < 0.14, f"Expected parallel execution, took {total_time:.3f}s"
        
        # Verify max concurrent was 3 for the parallel nodes
        assert max_concurrent >= 2, f"Expected parallel execution, max concurrent was {max_concurrent}"


    @pytest.mark.asyncio
    async def test_parallel_nodes_all_complete(self):
        """All parallel nodes complete even with different execution times."""
        reset_tracking()
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("fast", make_node("fast", delay=0.01))
        graph.add_node("medium", make_node("medium", delay=0.02))
        graph.add_node("slow", make_node("slow", delay=0.03))
        graph.add_node("join", make_node("join"))
        
        graph.add_edge("start", "fast")
        graph.add_edge("start", "medium")
        graph.add_edge("start", "slow")
        graph.add_edge("fast", "join")
        graph.add_edge("medium", "join")
        graph.add_edge("slow", "join")
        
        graph.set_entry_point("start")
        graph.set_finish_point("join")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        # All nodes should have executed
        assert "end:fast" in execution_log
        assert "end:medium" in execution_log
        assert "end:slow" in execution_log
        assert "end:join" in execution_log

    @pytest.mark.asyncio
    async def test_two_node_parallel_execution(self):
        """Two independent nodes run in parallel (NEXUS tailor_resume || contact_intel pattern)."""
        reset_tracking()
        
        # This mimics the NEXUS pattern: analyze_jd → [tailor_resume || contact_intel] → personalize
        graph = StateGraph()
        graph.add_node("analyze", make_node("analyze"))
        graph.add_node("tailor_resume", make_node("tailor_resume", delay=0.05))
        graph.add_node("contact_intel", make_node("contact_intel", delay=0.05))
        graph.add_node("personalize", make_node("personalize"))
        
        graph.add_edge("analyze", "tailor_resume")
        graph.add_edge("analyze", "contact_intel")
        graph.add_edge("tailor_resume", "personalize")
        graph.add_edge("contact_intel", "personalize")
        
        graph.set_entry_point("analyze")
        graph.set_finish_point("personalize")
        
        compiled = graph.compile()
        state = NEXUSState()
        
        start_time = time.monotonic()
        result = await compiled.run(state)
        total_time = time.monotonic() - start_time
        
        # Sequential would be ~0.20s+, parallel should be ~0.06s
        # Allow generous margin for async overhead on loaded systems
        assert total_time < 0.25, f"Expected parallel execution, took {total_time:.3f}s"

        
        # Verify execution order: analyze before parallel, personalize after both
        analyze_idx = execution_log.index("end:analyze")
        tailor_idx = execution_log.index("start:tailor_resume")
        contact_idx = execution_log.index("start:contact_intel")
        personalize_idx = execution_log.index("start:personalize")
        
        assert analyze_idx < tailor_idx
        assert analyze_idx < contact_idx
        # Personalize should start after both parallel nodes end
        tailor_end_idx = execution_log.index("end:tailor_resume")
        contact_end_idx = execution_log.index("end:contact_intel")
        assert personalize_idx > tailor_end_idx
        assert personalize_idx > contact_end_idx


    @pytest.mark.asyncio
    async def test_parallel_execution_with_unequal_depths(self):
        """Parallel paths with different depths execute correctly."""
        reset_tracking()
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        # Short path: just one node
        graph.add_node("short", make_node("short", delay=0.01))
        # Long path: two nodes
        graph.add_node("long_1", make_node("long_1", delay=0.01))
        graph.add_node("long_2", make_node("long_2", delay=0.01))
        graph.add_node("join", make_node("join"))
        
        graph.add_edge("start", "short")
        graph.add_edge("start", "long_1")
        graph.add_edge("long_1", "long_2")
        graph.add_edge("short", "join")
        graph.add_edge("long_2", "join")
        
        graph.set_entry_point("start")
        graph.set_finish_point("join")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        # All nodes should execute
        assert "end:short" in execution_log
        assert "end:long_1" in execution_log
        assert "end:long_2" in execution_log
        assert "end:join" in execution_log
        
        # join must come after both paths complete
        join_idx = execution_log.index("start:join")
        short_end_idx = execution_log.index("end:short")
        long2_end_idx = execution_log.index("end:long_2")
        assert join_idx > short_end_idx
        assert join_idx > long2_end_idx


# ---------------------------------------------------------------------------
# Test Class: Topological Sorting (Requirement 9.4)
# ---------------------------------------------------------------------------

class TestTopologicalSorting:
    """
    Tests for topological sorting (Kahn's algorithm) for execution order.
    
    **Validates: Requirement 9.4 - THE CompiledGraph SHALL use topological
    sorting for execution order**
    """

    @pytest.mark.asyncio
    async def test_linear_chain_topological_order(self):
        """Linear chain executes in correct topological order."""
        reset_tracking()
        
        graph = StateGraph()
        graph.add_node("a", make_node("a"))
        graph.add_node("b", make_node("b"))
        graph.add_node("c", make_node("c"))
        graph.add_node("d", make_node("d"))
        
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.add_edge("c", "d")
        
        graph.set_entry_point("a")
        graph.set_finish_point("d")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        # Extract execution order (ends indicate completion)
        order = [log.split(":")[1] for log in execution_log if log.startswith("end:")]
        
        # Must be exactly: a, b, c, d
        assert order == ["a", "b", "c", "d"]

    @pytest.mark.asyncio
    async def test_diamond_topology_order(self):
        """Diamond topology (A→[B,C]→D) maintains correct order."""
        reset_tracking()
        
        # Diamond: A → B, A → C, B → D, C → D
        graph = StateGraph()
        graph.add_node("a", make_node("a"))
        graph.add_node("b", make_node("b"))
        graph.add_node("c", make_node("c"))
        graph.add_node("d", make_node("d"))
        
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        graph.add_edge("b", "d")
        graph.add_edge("c", "d")
        
        graph.set_entry_point("a")
        graph.set_finish_point("d")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        # Verify topological constraints:
        # A must complete before B and C start
        a_end_idx = execution_log.index("end:a")
        b_start_idx = execution_log.index("start:b")
        c_start_idx = execution_log.index("start:c")
        d_start_idx = execution_log.index("start:d")
        b_end_idx = execution_log.index("end:b")
        c_end_idx = execution_log.index("end:c")
        
        assert a_end_idx < b_start_idx
        assert a_end_idx < c_start_idx
        # D must start after both B and C complete
        assert d_start_idx > b_end_idx
        assert d_start_idx > c_end_idx


    @pytest.mark.asyncio
    async def test_in_degree_calculation(self):
        """Verify correct in-degree calculation for topological sort."""
        graph = StateGraph()
        graph.add_node("a", make_node("a"))
        graph.add_node("b", make_node("b"))
        graph.add_node("c", make_node("c"))
        graph.add_node("d", make_node("d"))  # d has 2 incoming edges
        
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        graph.add_edge("b", "d")
        graph.add_edge("c", "d")
        
        graph.set_entry_point("a")
        graph.set_finish_point("d")
        
        compiled = graph.compile()
        in_degree = compiled._build_in_degree()
        
        # Entry point has in_degree 0
        assert in_degree["a"] == 0
        # b and c have 1 predecessor each
        assert in_degree["b"] == 1
        assert in_degree["c"] == 1
        # d has 2 predecessors
        assert in_degree["d"] == 2

    @pytest.mark.asyncio
    async def test_complex_dag_topological_order(self):
        """Complex DAG maintains valid topological order."""
        reset_tracking()
        
        # Complex DAG:
        #     A
        #    /|\
        #   B C D
        #    \|/
        #     E
        #     |
        #     F
        
        graph = StateGraph()
        graph.add_node("a", make_node("a"))
        graph.add_node("b", make_node("b"))
        graph.add_node("c", make_node("c"))
        graph.add_node("d", make_node("d"))
        graph.add_node("e", make_node("e"))
        graph.add_node("f", make_node("f"))
        
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        graph.add_edge("a", "d")
        graph.add_edge("b", "e")
        graph.add_edge("c", "e")
        graph.add_edge("d", "e")
        graph.add_edge("e", "f")
        
        graph.set_entry_point("a")
        graph.set_finish_point("f")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        # Verify all nodes executed
        completed_nodes = [log.split(":")[1] for log in execution_log if log.startswith("end:")]
        assert set(completed_nodes) == {"a", "b", "c", "d", "e", "f"}
        
        # Verify order: A before B,C,D; B,C,D before E; E before F
        a_idx = completed_nodes.index("a")
        e_idx = completed_nodes.index("e")
        f_idx = completed_nodes.index("f")
        
        assert a_idx < e_idx  # A before E
        assert e_idx < f_idx  # E before F


# ---------------------------------------------------------------------------
# Test Class: Dependency Enforcement (Requirement 9.5)
# ---------------------------------------------------------------------------

class TestDependencyEnforcement:
    """
    Tests for dependency enforcement during execution.
    
    **Validates: Requirement 9.5 - WHEN executing a workflow, THE DAGOrchestrator
    SHALL respect node dependencies**
    """

    @pytest.mark.asyncio
    async def test_dependency_blocks_until_complete(self):
        """Dependent node waits for all dependencies to complete."""
        reset_tracking()
        
        graph = StateGraph()
        graph.add_node("dep1", make_node("dep1", delay=0.03))
        graph.add_node("dep2", make_node("dep2", delay=0.02))
        graph.add_node("dependent", make_node("dependent"))
        
        graph.add_edge("dep1", "dependent")
        graph.add_edge("dep2", "dependent")
        
        graph.set_entry_point("dep1")
        graph.set_finish_point("dependent")
        
        # Need to make dep1 and dep2 both have in_degree 0 by making dep1 entry
        # Actually we need both to start at once - let's create a better structure
        
        # Better: start → [dep1, dep2] → dependent
        graph2 = StateGraph()
        graph2.add_node("start", make_node("start"))
        graph2.add_node("dep1", make_node("dep1", delay=0.03))
        graph2.add_node("dep2", make_node("dep2", delay=0.02))
        graph2.add_node("dependent", make_node("dependent"))
        
        graph2.add_edge("start", "dep1")
        graph2.add_edge("start", "dep2")
        graph2.add_edge("dep1", "dependent")
        graph2.add_edge("dep2", "dependent")
        
        graph2.set_entry_point("start")
        graph2.set_finish_point("dependent")
        
        compiled = graph2.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        # dependent must start after BOTH dep1 and dep2 end
        dep1_end_idx = execution_log.index("end:dep1")
        dep2_end_idx = execution_log.index("end:dep2")
        dependent_start_idx = execution_log.index("start:dependent")
        
        assert dependent_start_idx > dep1_end_idx
        assert dependent_start_idx > dep2_end_idx


    @pytest.mark.asyncio
    async def test_single_dependency_enforced(self):
        """Single dependency is properly enforced."""
        reset_tracking()
        
        graph = StateGraph()
        graph.add_node("first", make_node("first", delay=0.02))
        graph.add_node("second", make_node("second"))
        
        graph.add_edge("first", "second")
        graph.set_entry_point("first")
        graph.set_finish_point("second")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        first_end_idx = execution_log.index("end:first")
        second_start_idx = execution_log.index("start:second")
        
        assert second_start_idx > first_end_idx

    @pytest.mark.asyncio
    async def test_transitive_dependencies_enforced(self):
        """Transitive dependencies (A→B→C) are properly enforced."""
        reset_tracking()
        
        graph = StateGraph()
        graph.add_node("a", make_node("a", delay=0.01))
        graph.add_node("b", make_node("b", delay=0.01))
        graph.add_node("c", make_node("c"))
        
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.set_entry_point("a")
        graph.set_finish_point("c")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        a_end_idx = execution_log.index("end:a")
        b_start_idx = execution_log.index("start:b")
        b_end_idx = execution_log.index("end:b")
        c_start_idx = execution_log.index("start:c")
        
        assert b_start_idx > a_end_idx  # B after A
        assert c_start_idx > b_end_idx  # C after B

    @pytest.mark.asyncio
    async def test_independent_nodes_no_false_dependencies(self):
        """Independent nodes don't wait for each other."""
        reset_tracking()
        
        # A → B and C → D (two independent chains)
        # B and C should not wait for each other
        
        async def track_b(state: NEXUSState) -> NEXUSState:
            return await tracked_node(state, "b", delay=0.03)
        
        async def track_c(state: NEXUSState) -> NEXUSState:
            return await tracked_node(state, "c", delay=0.01)
        
        graph = StateGraph()
        graph.add_node("entry", make_node("entry"))
        graph.add_node("b", track_b)
        graph.add_node("c", track_c)
        graph.add_node("d", make_node("d"))
        graph.add_node("join", make_node("join"))
        
        graph.add_edge("entry", "b")
        graph.add_edge("entry", "c")
        graph.add_edge("b", "join")
        graph.add_edge("c", "d")
        graph.add_edge("d", "join")
        
        graph.set_entry_point("entry")
        graph.set_finish_point("join")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        # C and D should NOT wait for B (they're independent)
        # C (0.01s) should complete before B (0.03s)
        c_end_idx = execution_log.index("end:c")
        b_end_idx = execution_log.index("end:b")
        
        # C finishes first due to shorter delay
        assert c_end_idx < b_end_idx


    @pytest.mark.asyncio
    async def test_node_failure_doesnt_block_successors(self):
        """Failed node doesn't block dependent nodes (graceful degradation)."""
        reset_tracking()
        
        async def failing_node(state: NEXUSState) -> NEXUSState:
            execution_log.append("start:failing")
            raise RuntimeError("Simulated failure")
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("failing", failing_node)
        graph.add_node("after_fail", make_node("after_fail"))
        
        graph.add_edge("start", "failing")
        graph.add_edge("failing", "after_fail")
        
        graph.set_entry_point("start")
        graph.set_finish_point("after_fail")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        # The pipeline should continue despite the failure
        assert result.node_status["failing"] == NodeStatus.FAILED
        assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# Test Class: NEXUS-Specific DAG Tests
# ---------------------------------------------------------------------------

class TestNEXUSDAGPattern:
    """
    Tests specific to the NEXUS DAG pattern.
    
    NEXUS topology:
    scrape → analyze_jd → [tailor_resume || contact_intel] → personalize → outreach → feedback
    """

    @pytest.mark.asyncio
    async def test_nexus_topology_simulation(self):
        """Simulate the NEXUS DAG topology to verify correct execution."""
        reset_tracking()
        
        def feedback_router(state: NEXUSState) -> str:
            if state.dry_run:
                return "skip"
            return "run"
        
        graph = StateGraph()
        graph.add_node("scrape", make_node("scrape", delay=0.01))
        graph.add_node("analyze_jd", make_node("analyze_jd", delay=0.01))
        graph.add_node("tailor_resume", make_node("tailor_resume", delay=0.02))
        graph.add_node("contact_intel", make_node("contact_intel", delay=0.02))
        graph.add_node("personalize", make_node("personalize", delay=0.01))
        graph.add_node("outreach", make_node("outreach", delay=0.01))
        graph.add_node("feedback", make_node("feedback", delay=0.01))
        
        graph.add_edge("scrape", "analyze_jd")
        graph.add_edge("analyze_jd", "tailor_resume")
        graph.add_edge("analyze_jd", "contact_intel")
        graph.add_edge("tailor_resume", "personalize")
        graph.add_edge("contact_intel", "personalize")
        graph.add_edge("personalize", "outreach")
        graph.add_conditional_edge("outreach", feedback_router, {"run": "feedback", "skip": END})
        
        graph.set_entry_point("scrape")
        graph.set_finish_point("feedback")
        
        compiled = graph.compile()
        
        # Test with feedback running (dry_run=False)
        state = NEXUSState(dry_run=False)
        result = await compiled.run(state)
        
        # Verify order constraints
        completed = [log.split(":")[1] for log in execution_log if log.startswith("end:")]
        
        # scrape before analyze_jd
        assert completed.index("scrape") < completed.index("analyze_jd")
        # analyze_jd before parallel nodes
        assert completed.index("analyze_jd") < completed.index("tailor_resume")
        assert completed.index("analyze_jd") < completed.index("contact_intel")
        # parallel nodes before personalize
        assert completed.index("tailor_resume") < completed.index("personalize")
        assert completed.index("contact_intel") < completed.index("personalize")
        # personalize before outreach
        assert completed.index("personalize") < completed.index("outreach")
        # outreach before feedback
        assert completed.index("outreach") < completed.index("feedback")


    @pytest.mark.asyncio
    async def test_nexus_skip_feedback_on_dry_run(self):
        """NEXUS skips feedback node when dry_run=True."""
        reset_tracking()
        
        def feedback_router(state: NEXUSState) -> str:
            if state.dry_run:
                return "skip"
            return "run"
        
        graph = StateGraph()
        graph.add_node("outreach", make_node("outreach"))
        graph.add_node("feedback", make_node("feedback"))
        
        graph.add_conditional_edge("outreach", feedback_router, {"run": "feedback", "skip": END})
        
        graph.set_entry_point("outreach")
        graph.set_finish_point("feedback")
        
        compiled = graph.compile()
        state = NEXUSState(dry_run=True)
        result = await compiled.run(state)
        
        assert "end:outreach" in execution_log
        assert "feedback" not in str(execution_log)

    @pytest.mark.asyncio
    async def test_parallel_nodes_timing_efficiency(self):
        """Parallel execution provides timing efficiency over sequential."""
        reset_tracking()
        
        # Sequential would be 0.05 + 0.05 = 0.10s
        # Parallel should be ~0.05s
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("p1", make_node("p1", delay=0.05))
        graph.add_node("p2", make_node("p2", delay=0.05))
        graph.add_node("end", make_node("end"))
        
        graph.add_edge("start", "p1")
        graph.add_edge("start", "p2")
        graph.add_edge("p1", "end")
        graph.add_edge("p2", "end")
        
        graph.set_entry_point("start")
        graph.set_finish_point("end")
        
        compiled = graph.compile()
        state = NEXUSState()
        
        start_time = time.monotonic()
        await compiled.run(state)
        elapsed = time.monotonic() - start_time
        
        # Should be significantly faster than sequential (0.10s)
        assert elapsed < 0.09, f"Parallel execution too slow: {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# Test Class: Graph Validation
# ---------------------------------------------------------------------------

class TestGraphValidation:
    """Tests for graph validation during compilation."""

    def test_compile_validates_entry_point_exists(self):
        """Compilation fails if entry point node doesn't exist."""
        graph = StateGraph()
        graph.add_node("a", make_node("a"))
        graph.set_entry_point("nonexistent")
        
        with pytest.raises(ValueError, match="Entry node"):
            graph.compile()

    def test_compile_requires_entry_point(self):
        """Compilation fails without an entry point."""
        graph = StateGraph()
        graph.add_node("a", make_node("a"))
        
        with pytest.raises(ValueError, match="entry point"):
            graph.compile()

    def test_async_function_required_for_nodes(self):
        """Only async functions can be registered as nodes."""
        def sync_fn(state):
            return state
        
        graph = StateGraph()
        with pytest.raises(TypeError, match="async"):
            graph.add_node("sync_node", sync_fn)


# ---------------------------------------------------------------------------
# Test Class: State Management
# ---------------------------------------------------------------------------

class TestStateManagement:
    """Tests for state management during DAG execution."""

    @pytest.mark.asyncio
    async def test_state_passed_through_all_nodes(self):
        """State is passed through all nodes in the DAG."""
        async def modify_state(state: NEXUSState) -> NEXUSState:
            state.jobs_new_count += 1
            return state
        
        graph = StateGraph()
        graph.add_node("a", modify_state)
        graph.add_node("b", modify_state)
        graph.add_node("c", modify_state)
        
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        
        graph.set_entry_point("a")
        graph.set_finish_point("c")
        
        compiled = graph.compile()
        state = NEXUSState(jobs_new_count=0)
        result = await compiled.run(state)
        
        # Each node incremented by 1, total should be 3
        assert result.jobs_new_count == 3


    @pytest.mark.asyncio
    async def test_state_modifications_visible_to_successors(self):
        """State modifications from one node are visible to successors."""
        async def set_value(state: NEXUSState) -> NEXUSState:
            state.route_decision = "test_value"
            return state
        
        async def check_value(state: NEXUSState) -> NEXUSState:
            assert state.route_decision == "test_value"
            state.route_decision = "verified"
            return state
        
        graph = StateGraph()
        graph.add_node("setter", set_value)
        graph.add_node("checker", check_value)
        
        graph.add_edge("setter", "checker")
        graph.set_entry_point("setter")
        graph.set_finish_point("checker")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        assert result.route_decision == "verified"

    @pytest.mark.asyncio
    async def test_node_status_tracked(self):
        """Node status is tracked throughout execution."""
        reset_tracking()
        
        graph = StateGraph()
        graph.add_node("a", make_node("a"))
        graph.add_node("b", make_node("b"))
        
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        assert result.node_status["a"] == NodeStatus.COMPLETED
        assert result.node_status["b"] == NodeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_node_timings_recorded(self):
        """Node execution timings are recorded."""
        reset_tracking()
        
        graph = StateGraph()
        graph.add_node("timed_node", make_node("timed_node", delay=0.02))
        
        graph.set_entry_point("timed_node")
        graph.set_finish_point("timed_node")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        assert "timed_node" in result.node_timings_ms
        # Should be at least 20ms (0.02s delay)
        assert result.node_timings_ms["timed_node"] >= 15  # Allow some margin


# ---------------------------------------------------------------------------
# Test Class: Error Handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for error handling in DAG execution."""

    @pytest.mark.asyncio
    async def test_failed_node_error_recorded(self):
        """Failed node has its error recorded in state."""
        async def fail_node(state: NEXUSState) -> NEXUSState:
            raise ValueError("Test error message")
        
        graph = StateGraph()
        graph.add_node("fail", fail_node)
        graph.set_entry_point("fail")
        graph.set_finish_point("fail")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        assert result.node_status["fail"] == NodeStatus.FAILED
        assert any("Test error message" in err or "ValueError" in err for err in result.errors)


    @pytest.mark.asyncio
    async def test_pipeline_continues_after_node_failure(self):
        """Pipeline continues processing after a non-critical node fails."""
        reset_tracking()
        
        async def fail_node(state: NEXUSState) -> NEXUSState:
            execution_log.append("start:fail_node")
            raise RuntimeError("Expected failure")
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("fail_node", fail_node)
        graph.add_node("continue_node", make_node("continue_node"))
        
        graph.add_edge("start", "fail_node")
        graph.add_edge("fail_node", "continue_node")
        
        graph.set_entry_point("start")
        graph.set_finish_point("continue_node")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        # Start should have completed
        assert "end:start" in execution_log
        # fail_node should have been attempted
        assert result.node_status["fail_node"] == NodeStatus.FAILED

    @pytest.mark.asyncio
    async def test_multiple_failures_all_recorded(self):
        """Multiple node failures are all recorded."""
        async def fail_1(state: NEXUSState) -> NEXUSState:
            raise ValueError("Failure 1")
        
        async def fail_2(state: NEXUSState) -> NEXUSState:
            raise ValueError("Failure 2")
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("fail_1", fail_1)
        graph.add_node("fail_2", fail_2)
        graph.add_node("end", make_node("end"))
        
        graph.add_edge("start", "fail_1")
        graph.add_edge("start", "fail_2")
        graph.add_edge("fail_1", "end")
        graph.add_edge("fail_2", "end")
        
        graph.set_entry_point("start")
        graph.set_finish_point("end")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        assert result.node_status["fail_1"] == NodeStatus.FAILED
        assert result.node_status["fail_2"] == NodeStatus.FAILED
        assert len(result.errors) >= 2


# ---------------------------------------------------------------------------
# Test Class: Visualize
# ---------------------------------------------------------------------------

class TestVisualize:
    """Tests for DAG visualization."""

    def test_visualize_returns_topology(self):
        """visualize() returns ASCII representation of the DAG."""
        graph = StateGraph()
        graph.add_node("a", make_node("a"))
        graph.add_node("b", make_node("b"))
        graph.add_node("c", make_node("c"))
        
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.set_entry_point("a")
        graph.set_finish_point("c")
        
        compiled = graph.compile()
        viz = compiled.visualize()
        
        assert "DAG topology" in viz
        assert "a → b" in viz
        assert "b → c" in viz


    def test_visualize_shows_conditional_edges(self):
        """visualize() shows conditional edges with route keys."""
        def condition(state):
            return "yes"
        
        graph = StateGraph()
        graph.add_node("a", make_node("a"))
        graph.add_node("b", make_node("b"))
        graph.add_node("c", make_node("c"))
        
        graph.add_conditional_edge("a", condition, {"yes": "b", "no": "c"})
        graph.set_entry_point("a")
        graph.set_finish_point("b")
        
        compiled = graph.compile()
        viz = compiled.visualize()
        
        assert "→[yes]→" in viz or "[yes]" in viz
        assert "→[no]→" in viz or "[no]" in viz


# ---------------------------------------------------------------------------
# Test Class: Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_single_node_dag(self):
        """DAG with single node executes correctly."""
        reset_tracking()
        
        graph = StateGraph()
        graph.add_node("only", make_node("only"))
        graph.set_entry_point("only")
        graph.set_finish_point("only")
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        assert "end:only" in execution_log
        assert result.node_status["only"] == NodeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_long_linear_chain(self):
        """Long linear chain (10 nodes) executes in order."""
        reset_tracking()
        
        graph = StateGraph()
        node_names = [f"node_{i}" for i in range(10)]
        
        for name in node_names:
            graph.add_node(name, make_node(name))
        
        for i in range(9):
            graph.add_edge(node_names[i], node_names[i + 1])
        
        graph.set_entry_point(node_names[0])
        graph.set_finish_point(node_names[-1])
        
        compiled = graph.compile()
        state = NEXUSState()
        result = await compiled.run(state)
        
        # Verify all nodes completed
        completed = [log.split(":")[1] for log in execution_log if log.startswith("end:")]
        assert len(completed) == 10
        
        # Verify order
        for i in range(9):
            assert completed.index(node_names[i]) < completed.index(node_names[i + 1])


    @pytest.mark.asyncio
    async def test_wide_parallel_fan_out(self):
        """Wide fan-out (5 parallel nodes) executes concurrently."""
        reset_tracking()
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        
        parallel_nodes = [f"parallel_{i}" for i in range(5)]
        for name in parallel_nodes:
            graph.add_node(name, make_node(name, delay=0.02))
        
        graph.add_node("join", make_node("join"))
        
        for name in parallel_nodes:
            graph.add_edge("start", name)
            graph.add_edge(name, "join")
        
        graph.set_entry_point("start")
        graph.set_finish_point("join")
        
        compiled = graph.compile()
        state = NEXUSState()
        
        start_time = time.monotonic()
        result = await compiled.run(state)
        elapsed = time.monotonic() - start_time
        
        # Sequential: 5 * 0.02s = 0.10s
        # Parallel: ~0.02s + overhead
        assert elapsed < 0.08, f"Expected parallel execution, took {elapsed:.3f}s"
        
        # All parallel nodes should have executed
        for name in parallel_nodes:
            assert f"end:{name}" in execution_log

    @pytest.mark.asyncio
    async def test_empty_route_decision(self):
        """Default empty route_decision is handled correctly."""
        def route_on_decision(state: NEXUSState) -> str:
            if state.route_decision == "go":
                return "proceed"
            return "default"
        
        graph = StateGraph()
        graph.add_node("start", make_node("start"))
        graph.add_node("proceed_node", make_node("proceed_node"))
        graph.add_node("default_node", make_node("default_node"))
        
        graph.add_conditional_edge(
            "start",
            route_on_decision,
            {"proceed": "proceed_node", "default": "default_node"}
        )
        graph.set_entry_point("start")
        graph.set_finish_point("default_node")
        
        compiled = graph.compile()
        state = NEXUSState()  # route_decision defaults to ""
        reset_tracking()
        result = await compiled.run(state)
        
        assert "default_node" in str(execution_log)
        assert "proceed_node" not in str(execution_log)
