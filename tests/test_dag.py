"""Tests for the DAG orchestration engine."""

import pytest
import asyncio
import time

from src.dag.state import NEXUSState, NodeStatus
from src.dag.graph import StateGraph, CompiledGraph, END


# ---------------------------------------------------------------------------
# State tests
# ---------------------------------------------------------------------------


class TestNEXUSState:
    """Tests for NEXUSState dataclass."""

    def test_state_default_values(self):
        """NEXUSState() has sensible defaults."""
        state = NEXUSState()
        # search_queries has default values (not empty)
        assert isinstance(state.search_queries, list)
        assert len(state.search_queries) > 0
        assert state.resume_path == "data/resume.txt"
        assert state.dry_run is False
        assert state.max_jobs_per_query == 5
        assert state.scraped_jobs == []
        assert state.jobs_new_count == 0
        assert state.jd_analyses == {}
        assert state.node_status == {}
        assert state.node_timings_ms == {}
        assert state.errors == []
        assert state.warnings == []

    def test_state_mark_node_start(self):
        """mark_node_start sets status to RUNNING and returns t0."""
        state = NEXUSState()
        t0 = state.mark_node_start("fetch")
        assert state.node_status["fetch"] == NodeStatus.RUNNING
        assert isinstance(t0, float)

    def test_state_mark_node_done(self):
        """mark_node_done sets status to COMPLETED."""
        state = NEXUSState()
        t0 = state.mark_node_start("fetch")
        state.mark_node_done("fetch", t0)
        assert state.node_status["fetch"] == NodeStatus.COMPLETED
        assert "fetch" in state.node_timings_ms

    def test_state_mark_node_failed(self):
        """mark_node_failed sets status to FAILED and adds error."""
        state = NEXUSState()
        t0 = state.mark_node_start("fetch")
        state.mark_node_failed("fetch", "Connection timeout", t0)
        assert state.node_status["fetch"] == NodeStatus.FAILED
        assert any("Connection timeout" in err for err in state.errors)
        assert "fetch" in state.node_timings_ms

    def test_state_mark_node_skipped(self):
        """mark_node_skipped sets status to SKIPPED."""
        state = NEXUSState()
        state.mark_node_skipped("optional_step")
        assert state.node_status["optional_step"] == NodeStatus.SKIPPED

    def test_state_summary(self):
        """summary() returns a non-empty formatted string."""
        state = NEXUSState()
        t0 = state.mark_node_start("test")
        state.mark_node_done("test", t0)
        summary = state.summary()
        assert "Pipeline Summary" in summary

    def test_state_custom_config(self):
        """NEXUSState accepts custom config values."""
        state = NEXUSState(
            search_queries=["test query"],
            dry_run=True,
            max_jobs_per_query=10,
        )
        assert state.search_queries == ["test query"]
        assert state.dry_run is True
        assert state.max_jobs_per_query == 10


class TestNodeStatusEnum:
    """Tests for NodeStatus enum values."""

    def test_node_status_enum(self):
        """Verify PENDING, RUNNING, COMPLETED, FAILED, SKIPPED values exist."""
        assert hasattr(NodeStatus, "PENDING")
        assert hasattr(NodeStatus, "RUNNING")
        assert hasattr(NodeStatus, "COMPLETED")
        assert hasattr(NodeStatus, "FAILED")
        assert hasattr(NodeStatus, "SKIPPED")
        # Ensure they are distinct
        statuses = [
            NodeStatus.PENDING,
            NodeStatus.RUNNING,
            NodeStatus.COMPLETED,
            NodeStatus.FAILED,
            NodeStatus.SKIPPED,
        ]
        assert len(set(statuses)) == 5

    def test_node_status_string_values(self):
        """NodeStatus values are string-typed."""
        assert NodeStatus.PENDING == "pending"
        assert NodeStatus.RUNNING == "running"
        assert NodeStatus.COMPLETED == "completed"
        assert NodeStatus.FAILED == "failed"
        assert NodeStatus.SKIPPED == "skipped"


# ---------------------------------------------------------------------------
# Graph tests
# ---------------------------------------------------------------------------


# Helper async node functions for graph tests
async def node_a(state: NEXUSState) -> NEXUSState:
    """Appends 'A' to scraped_jobs to track execution order."""
    state.scraped_jobs.append("A")
    return state


async def node_b(state: NEXUSState) -> NEXUSState:
    """Appends 'B' to scraped_jobs to track execution order."""
    state.scraped_jobs.append("B")
    return state


async def node_c(state: NEXUSState) -> NEXUSState:
    """Appends 'C' to scraped_jobs to track execution order."""
    state.scraped_jobs.append("C")
    return state


async def node_failing(state: NEXUSState) -> NEXUSState:
    """A node that always raises an exception."""
    raise RuntimeError("Something went wrong in this node")


def sync_node(state: NEXUSState) -> NEXUSState:
    """A synchronous function (invalid for graph nodes)."""
    state.scraped_jobs.append("sync")
    return state


class TestGraphConstruction:
    """Tests for StateGraph construction and validation."""

    def test_graph_add_node_requires_async(self):
        """Adding a sync function as a node raises TypeError."""
        graph = StateGraph()
        with pytest.raises(TypeError):
            graph.add_node("bad_node", sync_node)

    def test_graph_compile_no_entry_raises(self):
        """Compile without setting entry point raises ValueError."""
        graph = StateGraph()
        graph.add_node("a", node_a)
        with pytest.raises(ValueError):
            graph.compile()

    def test_graph_compile_missing_entry_node(self):
        """Entry point set to a node that was never registered raises ValueError."""
        graph = StateGraph()
        graph.add_node("a", node_a)
        graph.set_entry_point("nonexistent")
        with pytest.raises(ValueError):
            graph.compile()

    def test_graph_add_node_valid(self):
        """Adding an async node function works."""
        graph = StateGraph()
        result = graph.add_node("a", node_a)
        # Returns self for chaining
        assert result is graph

    def test_graph_add_edge_valid(self):
        """Adding an edge between nodes works."""
        graph = StateGraph()
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        result = graph.add_edge("a", "b")
        assert result is graph

    def test_graph_compile_success(self):
        """A properly configured graph compiles without error."""
        graph = StateGraph()
        graph.add_node("a", node_a)
        graph.set_entry_point("a")
        graph.set_finish_point("a")
        compiled = graph.compile()
        assert isinstance(compiled, CompiledGraph)


class TestGraphExecution:
    """Tests for CompiledGraph execution."""

    @pytest.mark.asyncio
    async def test_graph_simple_linear(self):
        """Two nodes A→B, run, verify both completed in order."""
        graph = StateGraph()
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge("a", "b")
        graph.set_entry_point("a")
        graph.set_finish_point("b")

        compiled = graph.compile()
        state = NEXUSState(scraped_jobs=[])
        result = await compiled.run(state)

        assert "A" in result.scraped_jobs
        assert "B" in result.scraped_jobs
        # A should come before B
        assert result.scraped_jobs.index("A") < result.scraped_jobs.index("B")
        assert result.node_status["a"] == NodeStatus.COMPLETED
        assert result.node_status["b"] == NodeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_graph_parallel_fan_out(self):
        """A→[B, C], both B and C should run after A."""
        # Define a finish node that depends on both B and C
        async def node_finish(state: NEXUSState) -> NEXUSState:
            state.scraped_jobs.append("FINISH")
            return state

        graph = StateGraph()
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_node("c", node_c)
        graph.add_node("finish", node_finish)
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        graph.add_edge("b", "finish")
        graph.add_edge("c", "finish")
        graph.set_entry_point("a")
        graph.set_finish_point("finish")

        compiled = graph.compile()
        state = NEXUSState(scraped_jobs=[])
        result = await compiled.run(state)

        assert "A" in result.scraped_jobs
        assert "B" in result.scraped_jobs
        assert "C" in result.scraped_jobs
        # A must execute before B and C
        assert result.scraped_jobs.index("A") < result.scraped_jobs.index("B")
        assert result.scraped_jobs.index("A") < result.scraped_jobs.index("C")

    @pytest.mark.asyncio
    async def test_graph_fan_in(self):
        """[A, B]→C, C only runs after both A and B complete."""
        graph = StateGraph()
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_node("c", node_c)
        graph.add_edge("a", "c")
        graph.add_edge("b", "c")
        graph.set_entry_point("a")
        graph.set_finish_point("c")

        compiled = graph.compile()
        state = NEXUSState(scraped_jobs=[])
        result = await compiled.run(state)

        assert "A" in result.scraped_jobs
        assert "C" in result.scraped_jobs
        # C must execute after A
        assert result.scraped_jobs.index("C") > result.scraped_jobs.index("A")

    @pytest.mark.asyncio
    async def test_graph_conditional_edge(self):
        """A→(condition)→B or END based on state."""
        # The condition function must be SYNC (not async) per _get_successors implementation
        def condition(state: NEXUSState) -> str:
            if state.dry_run:
                return "skip"
            return "continue"

        graph = StateGraph()
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_conditional_edge("a", condition, {"continue": "b", "skip": END})
        graph.set_entry_point("a")
        graph.set_finish_point("b")

        compiled = graph.compile()

        # Test path where dry_run=True → skips B
        state_skip = NEXUSState(dry_run=True, scraped_jobs=[])
        result_skip = await compiled.run(state_skip)
        assert "A" in result_skip.scraped_jobs
        assert "B" not in result_skip.scraped_jobs

        # Test path where dry_run=False → runs B
        state_continue = NEXUSState(dry_run=False, scraped_jobs=[])
        result_continue = await compiled.run(state_continue)
        assert "A" in result_continue.scraped_jobs
        assert "B" in result_continue.scraped_jobs

    @pytest.mark.asyncio
    async def test_graph_node_failure_handling(self):
        """Node raises exception → state.errors populated."""
        graph = StateGraph()
        graph.add_node("fail_node", node_failing)
        graph.set_entry_point("fail_node")
        graph.set_finish_point("fail_node")

        compiled = graph.compile()
        state = NEXUSState(scraped_jobs=[])
        result = await compiled.run(state)

        assert len(result.errors) > 0
        assert result.node_status["fail_node"] == NodeStatus.FAILED

    @pytest.mark.asyncio
    async def test_graph_single_node(self):
        """A single node graph runs successfully."""
        graph = StateGraph()
        graph.add_node("only", node_a)
        graph.set_entry_point("only")
        graph.set_finish_point("only")

        compiled = graph.compile()
        state = NEXUSState(scraped_jobs=[])
        result = await compiled.run(state)

        assert "A" in result.scraped_jobs
        assert result.node_status["only"] == NodeStatus.COMPLETED
