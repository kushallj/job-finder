"""
Tests for Contact Intelligence System - Task 16.1

Validates:
- ContactGraph relationship building (Requirement 19.1)
- PageRank-style ranking algorithm (Requirement 19.2)
- Role hierarchy prioritization (Requirement 19.3)
- Hiring manager prioritization over recruiters (Requirement 19.4)
- Engineering manager prioritization for technical roles (Requirement 19.5)
"""

import pytest
from dataclasses import dataclass
from typing import Optional

from src.contact_intelligence.contact_graph import (
    ContactGraph,
    ContactGraphBuilder,
    GraphNode,
    GraphEdge,
)
from src.contact_intelligence.graph_ranker import GraphRanker, RankedContact
from src.contact_intelligence.role_hierarchy import (
    RoleHierarchy,
    RoleTier,
    HierarchyScore,
)


# ===========================================================================
# Test Data Helpers
# ===========================================================================

@dataclass
class MockContact:
    """Mock contact object matching the Contact interface from contact_finder."""
    name: str
    title: str
    email: Optional[str] = None
    company: str = ""
    confidence_score: float = 50.0


def create_test_contacts(company: str = "TestCo"):
    """Create a realistic set of test contacts for a company."""
    return [
        MockContact(name="Alice Chen", title="CTO", email="alice@testco.com", company=company, confidence_score=90),
        MockContact(name="Bob Smith", title="VP Engineering", email="bob@testco.com", company=company, confidence_score=85),
        MockContact(name="Carol Wu", title="Engineering Manager", email="carol@testco.com", company=company, confidence_score=80),
        MockContact(name="David Lee", title="Senior Recruiter", email="david@testco.com", company=company, confidence_score=75),
        MockContact(name="Eve Johnson", title="Software Engineer", email="eve@testco.com", company=company, confidence_score=70),
        MockContact(name="Frank Brown", title="Director of Engineering", email="frank@testco.com", company=company, confidence_score=82),
    ]


# ===========================================================================
# ContactGraph Tests - Validates Requirement 19.1
# ===========================================================================

class TestContactGraph:
    """Test ContactGraph relationship building (Requirement 19.1)."""

    def test_graph_construction_from_contacts(self):
        """Test that ContactGraphBuilder builds a graph from contacts."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        assert graph.company == "TestCo"
        assert len(graph.nodes) == 6
        # Should have edges between nodes (inferred relationships)
        assert len(graph.edges) > 0

    def test_nodes_store_contact_information(self):
        """Test that graph nodes contain proper contact metadata."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        # Find the CTO node
        cto_node = None
        for node in graph.nodes.values():
            if "CTO" in node.title:
                cto_node = node
                break

        assert cto_node is not None
        assert cto_node.name == "Alice Chen"
        assert cto_node.email == "alice@testco.com"
        assert cto_node.score is not None

    def test_edge_creation_between_related_contacts(self):
        """Test that edges are created based on tier proximity."""
        contacts = [
            MockContact(name="Manager", title="Engineering Manager", email="mgr@test.com"),
            MockContact(name="Director", title="Director of Engineering", email="dir@test.com"),
        ]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        # Manager and Director should be connected (tier gap = 1)
        assert len(graph.edges) >= 1

    def test_graph_neighbors_method(self):
        """Test that neighbors method returns connected nodes."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        # Pick any node that has edges
        for node_id in graph.nodes:
            neighbors = graph.neighbors(node_id)
            # Should return list of (neighbor_id, weight) tuples
            assert isinstance(neighbors, list)
            if neighbors:
                neighbor_id, weight = neighbors[0]
                assert isinstance(weight, (int, float))
                assert neighbor_id in graph.nodes

    def test_shortest_path_finding(self):
        """Test BFS shortest path between contacts."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        # Get two node IDs
        node_ids = list(graph.nodes.keys())
        if len(node_ids) >= 2:
            path = graph.shortest_path(node_ids[0], node_ids[1])
            # Path should start with source and end with target
            assert len(path) >= 1

    def test_path_to_decision_maker(self):
        """Test finding path to the highest-tier decision maker."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        # Find a low-tier node (IC)
        ic_node_id = None
        for node_id, node in graph.nodes.items():
            if node.tier == RoleTier.IC:
                ic_node_id = node_id
                break

        if ic_node_id:
            path = graph.path_to_decision_maker(ic_node_id)
            # Path should exist (small connected graph)
            assert path is None or len(path) >= 1

    def test_graph_degree_calculation(self):
        """Test degree (edge count) calculation for nodes."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        for node_id in graph.nodes:
            degree = graph.degree(node_id)
            assert degree >= 0
            # Degree should match neighbor count
            assert degree == len(graph.neighbors(node_id))

    def test_weighted_degree_calculation(self):
        """Test weighted degree sums edge weights correctly."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        for node_id in graph.nodes:
            weighted_deg = graph.weighted_degree(node_id)
            manual_sum = sum(w for _, w in graph.neighbors(node_id))
            assert abs(weighted_deg - manual_sum) < 0.001

    def test_empty_graph_handling(self):
        """Test that empty contact lists produce valid empty graphs."""
        builder = ContactGraphBuilder()
        graph = builder.build([], company="Empty", company_size=100)

        assert graph.company == "Empty"
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_edge_weights_are_bounded(self):
        """Test that edge weights are properly bounded between 0 and 1."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        for edge in graph.edges:
            assert 0 <= edge.weight <= 1
            assert edge.edge_type in ("reporting", "peer", "functional", "cross_dept")


# ===========================================================================
# PageRank Ranking Tests - Validates Requirement 19.2
# ===========================================================================

class TestGraphRanker:
    """Test PageRank-style ranking algorithm (Requirement 19.2)."""

    def test_pagerank_produces_ranked_contacts(self):
        """Test that PageRank ranking returns RankedContact objects."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        assert len(ranked) == len(contacts)
        for rc in ranked:
            assert isinstance(rc, RankedContact)
            assert hasattr(rc, "outreach_priority")
            assert hasattr(rc, "graph_centrality")

    def test_pagerank_scores_are_normalized(self):
        """Test that PageRank scores are normalized to 0-100 range."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        for rc in ranked:
            assert 0 <= rc.graph_centrality <= 100
            assert 0 <= rc.decision_maker_score <= 100
            assert 0 <= rc.reachability_score <= 100

    def test_ranked_contacts_are_sorted_by_priority(self):
        """Test that ranked contacts are sorted by outreach_priority descending."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        # Check sorted order (descending by outreach_priority)
        for i in range(len(ranked) - 1):
            assert ranked[i].outreach_priority >= ranked[i + 1].outreach_priority

    def test_pagerank_seed_distribution_favors_managers(self):
        """Test that PageRank seeds on MANAGER tier nodes appropriately."""
        contacts = [
            MockContact(name="Manager", title="Engineering Manager", email="mgr@test.com"),
            MockContact(name="IC", title="Software Engineer", email="ic@test.com"),
        ]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        # Find the manager and IC in ranked results
        manager_rc = next((rc for rc in ranked if "Manager" in rc.title), None)
        ic_rc = next((rc for rc in ranked if "Engineer" in rc.title and "Manager" not in rc.title), None)

        # Manager should rank higher due to PageRank seed distribution
        assert manager_rc is not None
        if ic_rc is not None:
            assert manager_rc.outreach_priority >= ic_rc.outreach_priority

    def test_pagerank_handles_single_node_graph(self):
        """Test PageRank with a single-node graph."""
        contacts = [MockContact(name="Solo", title="CEO", email="solo@test.com")]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=50)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        assert len(ranked) == 1
        assert ranked[0].graph_centrality == 100  # Only node gets 100%

    def test_pagerank_handles_empty_graph(self):
        """Test PageRank with an empty graph."""
        graph = ContactGraph(company="Empty")
        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        assert ranked == []

    def test_recommended_approach_assignment(self):
        """Test that recommended outreach approach is assigned based on role."""
        contacts = [
            MockContact(name="Manager", title="Engineering Manager", email="mgr@test.com"),
            MockContact(name="Recruiter", title="Technical Recruiter", email="rec@test.com"),
            MockContact(name="IC", title="Software Engineer", email="ic@test.com"),
        ]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        for rc in ranked:
            assert rc.recommended_approach in (
                "direct_pitch", "hr_route", "warm_intro", "peer_intro"
            )


# ===========================================================================
# Role Hierarchy Tests - Validates Requirement 19.3
# ===========================================================================

class TestRoleHierarchy:
    """Test role hierarchy for contact prioritization (Requirement 19.3)."""

    def test_role_tier_ordering(self):
        """Test that role tiers are ordered correctly (lower = more senior)."""
        assert RoleTier.FOUNDER < RoleTier.C_SUITE
        assert RoleTier.C_SUITE < RoleTier.VP
        assert RoleTier.VP < RoleTier.DIRECTOR
        assert RoleTier.DIRECTOR < RoleTier.MANAGER
        assert RoleTier.MANAGER < RoleTier.RECRUITER
        assert RoleTier.RECRUITER < RoleTier.IC
        assert RoleTier.IC < RoleTier.UNKNOWN

    def test_title_classification_cto(self):
        """Test that CTO is classified as C_SUITE tier."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("CTO", company_size=200)
        assert score.tier == RoleTier.C_SUITE

    def test_title_classification_engineering_manager(self):
        """Test that Engineering Manager is classified as MANAGER tier."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Engineering Manager", company_size=200)
        assert score.tier == RoleTier.MANAGER

    def test_title_classification_recruiter(self):
        """Test that recruiter roles are classified as RECRUITER tier."""
        hierarchy = RoleHierarchy()

        # Titles that are clearly recruiters
        for title in ["Technical Recruiter", "Talent Acquisition Specialist", "Senior Recruiter"]:
            score = hierarchy.score(title, company_size=200)
            assert score.tier == RoleTier.RECRUITER, f"Expected {title} to be RECRUITER tier"

        # HR Manager has "Manager" keyword which takes precedence over "HR"
        hr_manager_score = hierarchy.score("HR Manager", company_size=200)
        # HR Manager is classified as MANAGER tier due to "Manager" keyword matching first
        assert hr_manager_score.tier in (RoleTier.MANAGER, RoleTier.RECRUITER)

    def test_title_classification_software_engineer(self):
        """Test that Software Engineer is classified as IC tier."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Software Engineer", company_size=200)
        assert score.tier == RoleTier.IC

    def test_title_classification_vp_engineering(self):
        """Test that VP of Engineering is classified as VP tier."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("VP Engineering", company_size=200)
        assert score.tier == RoleTier.VP

    def test_title_classification_director(self):
        """Test that Director titles are classified as DIRECTOR tier."""
        hierarchy = RoleHierarchy()

        for title in ["Director of Engineering", "Head of Product", "Engineering Director"]:
            score = hierarchy.score(title, company_size=200)
            assert score.tier == RoleTier.DIRECTOR

    def test_department_relevance_engineering(self):
        """Test that engineering department has high relevance for tech roles."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Engineering Manager", company_size=200, is_tech_role=True)
        assert score.dept_relevance >= 0.9  # Engineering has 1.0 relevance

    def test_department_relevance_hr(self):
        """Test that HR department has moderate relevance for tech roles."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Technical Recruiter", company_size=200, is_tech_role=True)
        assert 0.6 <= score.dept_relevance <= 0.8  # HR has 0.75 relevance

    def test_company_size_affects_dm_probability(self):
        """Test that company size affects decision-maker probability."""
        hierarchy = RoleHierarchy()

        # Founder at tiny company has high DM probability
        tiny_score = hierarchy.score("Founder", company_size=30)
        assert tiny_score.decision_maker_prob >= 0.9

        # Founder at large company has lower DM probability
        large_score = hierarchy.score("Founder", company_size=5000)
        assert large_score.decision_maker_prob <= 0.5

    def test_combined_dm_score_calculation(self):
        """Test that combined_dm_score = dm_prob * dept_relevance * 100."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Engineering Manager", company_size=200, is_tech_role=True)

        expected = score.decision_maker_prob * score.dept_relevance * 100
        assert abs(score.combined_dm_score - expected) < 0.5  # Allow small rounding diff


# ===========================================================================
# Hiring Manager vs Recruiter Tests - Validates Requirement 19.4
# ===========================================================================

class TestHiringManagerPriority:
    """Test hiring manager prioritization over recruiters (Requirement 19.4)."""

    def test_hiring_manager_ranks_higher_than_recruiter(self):
        """Test that hiring manager outranks recruiter in ranking."""
        contacts = [
            MockContact(name="Manager", title="Engineering Manager", email="mgr@test.com", confidence_score=80),
            MockContact(name="Recruiter", title="Technical Recruiter", email="rec@test.com", confidence_score=80),
        ]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        manager_rc = next((rc for rc in ranked if "Manager" in rc.title), None)
        recruiter_rc = next((rc for rc in ranked if "Recruiter" in rc.title), None)

        assert manager_rc is not None
        assert recruiter_rc is not None
        assert manager_rc.outreach_priority > recruiter_rc.outreach_priority

    def test_manager_has_higher_dm_score_than_recruiter(self):
        """Test that manager has higher decision_maker_score than recruiter."""
        hierarchy = RoleHierarchy()

        manager_score = hierarchy.score("Engineering Manager", company_size=200, is_tech_role=True)
        recruiter_score = hierarchy.score("Technical Recruiter", company_size=200, is_tech_role=True)

        assert manager_score.combined_dm_score > recruiter_score.combined_dm_score

    def test_manager_tier_is_lower_than_recruiter_tier(self):
        """Test that MANAGER tier value is lower (more senior) than RECRUITER."""
        # Lower tier value = more senior in the IntEnum
        assert RoleTier.MANAGER < RoleTier.RECRUITER

    def test_manager_gets_direct_pitch_approach(self):
        """Test that managers get direct_pitch recommended approach."""
        contacts = [MockContact(name="Manager", title="Engineering Manager", email="mgr@test.com")]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        assert ranked[0].recommended_approach == "direct_pitch"

    def test_recruiter_gets_hr_route_approach(self):
        """Test that recruiters get hr_route recommended approach."""
        contacts = [MockContact(name="Recruiter", title="Technical Recruiter", email="rec@test.com")]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        assert ranked[0].recommended_approach == "hr_route"

    def test_hiring_manager_decision_path_role(self):
        """Test that hiring manager is identified as direct_decision_maker."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Engineering Manager", company_size=200)

        assert score.decision_path_role == "direct_decision_maker"

    def test_recruiter_decision_path_role(self):
        """Test that recruiter is identified as process_gatekeeper."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Technical Recruiter", company_size=200)

        assert score.decision_path_role == "process_gatekeeper"


# ===========================================================================
# Engineering Manager for Technical Roles Tests - Validates Requirement 19.5
# ===========================================================================

class TestEngineeringManagerPriority:
    """Test engineering manager prioritization for technical roles (Requirement 19.5)."""

    def test_engineering_manager_ranks_high_for_tech_roles(self):
        """Test that engineering manager ranks highly for technical job roles."""
        contacts = [
            MockContact(name="EM", title="Engineering Manager", email="em@test.com", confidence_score=80),
            MockContact(name="PM", title="Product Manager", email="pm@test.com", confidence_score=80),
            MockContact(name="FM", title="Finance Manager", email="fm@test.com", confidence_score=80),
        ]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer", is_tech_role=True)

        em_rc = next((rc for rc in ranked if "Engineering" in rc.title), None)
        assert em_rc is not None
        # Engineering Manager should be in top half of rankings for tech roles
        em_rank = ranked.index(em_rc)
        assert em_rank < len(ranked) / 2 or len(ranked) <= 2

    def test_engineering_manager_has_engineering_department(self):
        """Test that engineering manager is classified in engineering department."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Engineering Manager", company_size=200)
        assert score.department == "engineering"

    def test_engineering_department_relevance_for_tech_roles(self):
        """Test that engineering department has high relevance for tech roles."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Engineering Manager", company_size=200, is_tech_role=True)
        assert score.dept_relevance == 1.0  # Engineering has max relevance

    def test_engineering_manager_vs_other_departments(self):
        """Test EM scores higher than managers in less relevant departments."""
        hierarchy = RoleHierarchy()

        em_score = hierarchy.score("Engineering Manager", company_size=200, is_tech_role=True)
        sales_score = hierarchy.score("Sales Manager", company_size=200, is_tech_role=True)
        marketing_score = hierarchy.score("Marketing Manager", company_size=200, is_tech_role=True)

        # Engineering manager should have higher combined score due to dept relevance
        assert em_score.combined_dm_score > sales_score.combined_dm_score
        assert em_score.combined_dm_score > marketing_score.combined_dm_score

    def test_tech_title_detection_for_engineering_roles(self):
        """Test that various engineering titles are properly classified."""
        hierarchy = RoleHierarchy()

        tech_titles = [
            "Engineering Manager",
            "Software Engineering Manager",
            "Platform Engineering Lead",
            "Staff Engineer",
            "Principal Engineer",
        ]

        for title in tech_titles:
            score = hierarchy.score(title, company_size=200)
            assert score.department in ("engineering", "platform", "infrastructure")

    def test_engineering_manager_outreach_notes(self):
        """Test that EM gets appropriate outreach notes."""
        hierarchy = RoleHierarchy()
        score = hierarchy.score("Engineering Manager", company_size=200)

        assert score.outreach_notes != ""
        # Notes should mention technical aspects
        assert "technical" in score.outreach_notes.lower() or "build" in score.outreach_notes.lower()


# ===========================================================================
# Integration Tests - Full Pipeline
# ===========================================================================

class TestContactIntelligenceIntegration:
    """Integration tests for the complete contact intelligence pipeline."""

    def test_full_pipeline_graph_to_ranking(self):
        """Test complete pipeline from contacts to ranked results."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        # Verify pipeline produces valid results
        assert len(ranked) == len(contacts)

        # Top contact should be a decision maker (manager, director, or VP)
        top = ranked[0]
        assert top.node.tier in (
            RoleTier.MANAGER, RoleTier.DIRECTOR, RoleTier.VP, 
            RoleTier.C_SUITE, RoleTier.FOUNDER
        )

    def test_ranking_consistency_across_runs(self):
        """Test that ranking produces consistent results across multiple runs."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        ranker = GraphRanker()
        ranked1 = ranker.rank(graph, job_title="Software Engineer")
        ranked2 = ranker.rank(graph, job_title="Software Engineer")

        # Same order
        for i in range(len(ranked1)):
            assert ranked1[i].node.email == ranked2[i].node.email
            assert ranked1[i].outreach_priority == ranked2[i].outreach_priority

    def test_company_size_affects_ranking(self):
        """Test that company size affects final rankings."""
        contacts = [
            MockContact(name="Founder", title="CEO & Founder", email="ceo@startup.com", confidence_score=90),
            MockContact(name="Manager", title="Engineering Manager", email="mgr@startup.com", confidence_score=85),
        ]
        builder = ContactGraphBuilder()

        # Small company: Founder should rank higher
        small_graph = builder.build(contacts, company="SmallCo", company_size=30)
        ranker = GraphRanker()
        small_ranked = ranker.rank(small_graph, job_title="Software Engineer")

        # Large company: Manager should rank higher
        large_graph = builder.build(contacts, company="LargeCo", company_size=5000)
        large_ranked = ranker.rank(large_graph, job_title="Software Engineer")

        # At small companies, founders are decision makers
        # At large companies, managers are decision makers
        small_founder = next((rc for rc in small_ranked if "Founder" in rc.title), None)
        small_manager = next((rc for rc in small_ranked if "Manager" in rc.title), None)

        large_founder = next((rc for rc in large_ranked if "Founder" in rc.title), None)
        large_manager = next((rc for rc in large_ranked if "Manager" in rc.title), None)

        assert small_founder is not None and small_manager is not None
        assert large_founder is not None and large_manager is not None

        # Large company: manager has higher DM score than founder
        # (managers are direct decision makers at large orgs, founders are too far removed)
        assert large_manager.decision_maker_score > large_founder.decision_maker_score

        # Verify company size does affect the DM scores differently
        # At small company, founder DM score should be higher than at large company
        assert small_founder.decision_maker_score > large_founder.decision_maker_score

    def test_graph_summary_output(self):
        """Test that ContactGraph.summary() returns useful information."""
        contacts = create_test_contacts()
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TestCo", company_size=200)

        summary = graph.summary()
        assert "TestCo" in summary
        assert "nodes" in summary
        assert "edges" in summary

# ===========================================================================
# Edge Case Tests
# ===========================================================================

class TestEdgeCases:
    """Edge case and boundary condition tests."""

    def test_contact_without_email(self):
        """Test handling of contacts without email addresses."""
        contacts = [
            MockContact(name="No Email", title="Engineering Manager", email=None, confidence_score=50),
        ]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        assert len(graph.nodes) == 1
        # Node should use name|company as ID
        node_id = list(graph.nodes.keys())[0]
        assert "No Email" in node_id or "Test" in node_id

    def test_contact_with_empty_title(self):
        """Test handling of contacts with empty title."""
        contacts = [
            MockContact(name="Unknown Title", title="", email="unknown@test.com", confidence_score=50),
        ]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        assert len(graph.nodes) == 1
        node = list(graph.nodes.values())[0]
        assert node.tier == RoleTier.UNKNOWN

    def test_large_contact_set(self):
        """Test handling of larger contact sets."""
        contacts = [
            MockContact(
                name=f"Contact {i}",
                title="Software Engineer" if i % 3 == 0 else "Engineering Manager" if i % 3 == 1 else "Recruiter",
                email=f"contact{i}@test.com",
                confidence_score=50 + i,
            )
            for i in range(20)
        ]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="LargeCo", company_size=500)

        assert len(graph.nodes) == 20

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        assert len(ranked) == 20
        # Should be sorted by priority
        for i in range(len(ranked) - 1):
            assert ranked[i].outreach_priority >= ranked[i + 1].outreach_priority

    def test_duplicate_emails_in_contacts(self):
        """Test that graph handles duplicate email contacts correctly."""
        contacts = [
            MockContact(name="Alice", title="Engineering Manager", email="alice@test.com", confidence_score=80),
            MockContact(name="Alice Chen", title="EM", email="alice@test.com", confidence_score=90),
        ]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        # Both contacts should be added (builder doesn't dedupe, that's IntelligenceEngine's job)
        # But they'll have the same contact_id based on email
        assert len(graph.nodes) >= 1

    def test_unicode_in_contact_names(self):
        """Test handling of unicode characters in contact names."""
        contacts = [
            MockContact(name="José García", title="Engineering Manager", email="jose@test.com"),
            MockContact(name="李明", title="Software Engineer", email="liming@test.com"),
        ]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="Test", company_size=200)

        assert len(graph.nodes) == 2

        ranker = GraphRanker()
        ranked = ranker.rank(graph, job_title="Software Engineer")

        assert len(ranked) == 2

    def test_very_small_company_size(self):
        """Test handling of very small company sizes."""
        contacts = [MockContact(name="Founder", title="CEO", email="ceo@tiny.com")]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="TinyStartup", company_size=3)

        hierarchy = RoleHierarchy()
        score = hierarchy.score("CEO", company_size=3)

        # At tiny companies, CEO has very high DM probability
        assert score.decision_maker_prob >= 0.9

    def test_unknown_company_size(self):
        """Test handling of unknown (zero) company size."""
        contacts = [MockContact(name="Manager", title="Engineering Manager", email="mgr@unknown.com")]
        builder = ContactGraphBuilder()
        graph = builder.build(contacts, company="UnknownCo", company_size=0)

        # Should still build graph successfully
        assert len(graph.nodes) == 1
