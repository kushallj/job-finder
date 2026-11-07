"""
tests/test_portfolio_rag.py
Comprehensive test suite for Public Hosted Candidate Portfolio and Recruiter RAG Chatbot.

Verifies:
1. Resume and GitHub README semantic vector chunking and indexing
2. Cosine similarity semantic search over candidate knowledge base
3. Recruiter inquiry "Does Kushal have experience with distributed vector indexing?" retrieval & grounded answer synthesis
4. Verifiable citations from resume & GitHub READMEs
5. Live GitHub contribution activity heatmap generation (kibo-ui compatible levels 0-4)
6. REST & Streaming API endpoints (/api/portfolio/:username, /api/portfolio/:username/chat)
"""
import json
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.models import (
    Base,
    CandidateProfile,
    CandidateExperience,
    CandidateProject,
    CandidateKnowledgeChunk,
    PortfolioChatLog,
)
from src.database import get_db
from src.services.portfolio_rag_service import PortfolioRAGService, cosine_similarity
from src.services.github_activity_service import GitHubActivityService
from src.services.portfolio_service import PortfolioService
from src.attention.embeddings import DenseSemanticEmbedder
from fastapi import FastAPI
from src.api.routers.portfolio_router import router as legacy_portfolio_router

# The legacy router is no longer mounted on main.app (Jobify Phase 5 owns /api/portfolio);
# its RAG/heatmap behaviour is still exercised on a standalone app.
app = FastAPI()
app.include_router(legacy_portfolio_router)


@pytest.fixture
def test_engine():
    """Create isolated in-memory engine with StaticPool and thread sharing enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_db_session(test_engine):
    """Create fresh database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client(test_engine):
    """FastAPI TestClient with overridden database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_dense_semantic_embedder_cosine_similarity():
    """Verify that vector embedder yields high similarity for matching tech domains."""
    embedder = DenseSemanticEmbedder()
    v_query = embedder.embed_text("distributed vector indexing hnsw")
    v_target = embedder.embed_text("sub-millisecond HNSW vector search over partitioned storage")
    v_unrelated = embedder.embed_text("baking artisan sourdough bread with whole wheat flour")

    sim_target = cosine_similarity(v_query, v_target)
    sim_unrelated = cosine_similarity(v_query, v_unrelated)

    assert sim_target > 0.25
    assert sim_target > sim_unrelated


def test_resume_and_project_vector_indexing(test_db_session):
    """Test chunking and embedding resume and project READMEs into database."""
    rag = PortfolioRAGService(test_db_session)

    profile = CandidateProfile(
        username="kushal",
        full_name="Kushal Jain",
        email="kushal@example.com",
        location="Bengaluru / Remote",
        headline="Staff AI & Frontend Engineer",
        resume_raw_text=(
            "KUSHAL JAIN — Staff AI & Systems Engineer\n\n"
            "EXPERIENCE:\n"
            "Staff Frontend Engineer at Tessellate: Built distributed vector indexing pipeline reducing search latency by 68%.\n"
            "Integrated HNSW vector indices and sub-millisecond retrieval tooling across 10M vectors.\n\n"
            "SKILLS:\n"
            "Vector DBs, HNSW, Python, FastAPI, React, TypeScript, Vite, PyTorch, RAG"
        ),
    )
    test_db_session.add(profile)
    test_db_session.commit()

    # Index Resume
    resume_chunks_count = rag.index_resume(profile)
    assert resume_chunks_count >= 1

    # Index Project
    project = CandidateProject(
        profile_id=profile.id,
        title="Distributed Vector Indexer",
        tagline="Sub-millisecond HNSW vector search",
        description="Scalable vector index partitioned across object storage.",
        tech_stack=json.dumps(["Python", "Rust", "HNSW", "Vector Indexing"]),
        readme_content=(
            "# Distributed Vector Indexer\n\n"
            "Core Architecture:\n"
            "- Implements Hierarchical Navigable Small World (HNSW) graph indexing.\n"
            "- Benchmarked at 0.8ms p99 latency across 10M vectors.\n"
            "- SIMD AVX-512 distance kernels."
        ),
    )
    test_db_session.add(project)
    test_db_session.commit()

    proj_chunks_count = rag.index_project_and_readme(profile.id, project)
    assert proj_chunks_count >= 2

    # Verify retrieval
    query = "Does Kushal have experience with distributed vector indexing?"
    retrieved = rag.retrieve_relevant_chunks(profile.id, query, top_k=3)
    assert len(retrieved) >= 1
    top_chunk, score = retrieved[0]
    assert score > 0.25
    assert any(term in top_chunk.chunk_text.lower() for term in ["vector", "indexing", "hnsw"])

    # Grounded answer synthesis
    answer, citations, confidence = rag.synthesize_grounded_answer(
        candidate_name="Kushal Jain",
        query=query,
        retrieved_chunks=retrieved,
    )
    assert "distributed vector indexing" in answer.lower()
    assert len(citations) >= 1
    assert "Vector" in citations[0]["source_title"]
    assert confidence >= 0.80


def test_github_activity_heatmap_generation():
    """Verify kibo-ui compatible GitHub contribution heatmap output."""
    activity = GitHubActivityService.get_candidate_activity("kushalljain", days_count=365)

    assert activity.username == "kushalljain"
    assert activity.total_contributions > 0
    assert len(activity.days) == 365
    assert activity.streak_days >= 0
    assert activity.longest_streak >= activity.streak_days

    # Verify heatmap structure
    sample_day = activity.days[-1]
    assert sample_day.level in (0, 1, 2, 3, 4)
    assert len(sample_day.date) == 10  # YYYY-MM-DD

    # Verify languages
    lang_names = [l["name"] for l in activity.top_languages]
    assert "TypeScript" in lang_names
    assert "Python" in lang_names


def test_public_portfolio_endpoints(test_client, test_engine):
    """Test full public portfolio view and recruiter chatbot via FastAPI TestClient."""
    # 1. Seed portfolio data
    seed_res = test_client.post("/api/portfolio/seed?username=kushal")
    assert seed_res.status_code == 200
    portfolio_data = seed_res.json()
    assert portfolio_data["status"] == "success"
    assert portfolio_data["profile"]["full_name"] == "Kushal Jain"
    assert len(portfolio_data["projects"]) >= 2
    assert len(portfolio_data["experiences"]) >= 2
    assert portfolio_data["github_activity"] is not None
    assert len(portfolio_data["github_activity"]["days"]) == 365

    # 2. Get public portfolio page (/api/portfolio/kushal)
    get_res = test_client.get("/api/portfolio/kushal")
    assert get_res.status_code == 200
    res_data = get_res.json()
    assert res_data["profile"]["username"] == "kushal"
    assert res_data["indexed_chunks_count"] >= 3

    # 3. Recruiter Q&A Query (Standard JSON)
    chat_res = test_client.post(
        "/api/portfolio/kushal/chat",
        json={
            "message": "Does Kushal have experience with distributed vector indexing?",
            "stream": False,
        },
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "vector" in chat_data["answer"].lower()
    assert len(chat_data["citations"]) >= 1
    assert chat_data["confidence_score"] >= 0.80

    # 4. Recruiter Q&A Query (SSE Streaming)
    stream_res = test_client.post(
        "/api/portfolio/kushal/chat",
        json={
            "message": "What verified projects has Kushal built?",
            "stream": True,
        },
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers.get("content-type", "")
    stream_content = stream_res.text
    assert "data: " in stream_content
    assert "done" in stream_content

    # 5. Direct GitHub activity endpoint
    gh_res = test_client.get("/api/portfolio/kushal/github-activity?days=90")
    assert gh_res.status_code == 200
    gh_data = gh_res.json()
    assert len(gh_data["days"]) == 90
