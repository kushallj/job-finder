"""
tests/test_explainable_matcher.py
Unit tests for Explainable Match Scoring Engine & API integration.
"""
import pytest
from src.services.explainable_matcher import ExplainableMatcherService, get_explainable_matcher, TECH_TAXONOMY
from src.api_models import JobData
from src.models import Job
from main import _to_job_data
from datetime import datetime


def test_taxonomy_contains_modern_high_demand_skills():
    """Ensure modern high-demand AI, LLM, agentic, and web tech are part of the taxonomy."""
    assert "LLM Integration" in TECH_TAXONOMY
    assert "Model Context Protocol (MCP)" in TECH_TAXONOMY
    assert "Retrieval-Augmented Generation (RAG)" in TECH_TAXONOMY
    assert "Vector Databases" in TECH_TAXONOMY
    assert "AI Agents" in TECH_TAXONOMY
    assert "LangChain" in TECH_TAXONOMY
    assert "PyTorch" in TECH_TAXONOMY
    assert "React" in TECH_TAXONOMY
    assert "TypeScript" in TECH_TAXONOMY
    assert "Vite" in TECH_TAXONOMY
    assert "FastAPI" in TECH_TAXONOMY
    assert "Python" in TECH_TAXONOMY


def test_explainable_matcher_skill_partition():
    """Verify matched vs missing skills are correctly partitioned."""
    matcher = ExplainableMatcherService()
    
    # Job requires React, TypeScript, Vite, CSS3, Figma
    result = matcher.compute_match(
        title="Senior Frontend Engineer",
        description="Looking for expertise in React, TypeScript, Vite, CSS3, and Figma designs.",
        tags=["Frontend", "Web"],
        location="Bengaluru, India",
        has_remote=False,
    )
    
    matched = result["matched_skills"]
    missing = result["missing_skills"]
    reasons = result["reasons"]
    score = result["score"]

    # Candidate has React, TypeScript, Vite in profile
    assert "React" in matched
    assert "TypeScript" in matched
    assert "Vite" in matched
    assert "CSS3" in missing or "Figma" in missing
    assert len(reasons) == 3
    assert 50 <= score <= 98


def test_explainable_matcher_ai_skills():
    """Verify modern AI skills (LLM Integration, MCP, RAG, Vector DBs) are matched."""
    matcher = ExplainableMatcherService()
    
    result = matcher.compute_match(
        title="AI Engineer - Autonomous Agents & LLMs",
        description="Build agentic systems using LLM integration, Model Context Protocol (MCP), and RAG with Pinecone vector DB.",
        tags=["AI", "LLM", "MCP"],
        location="Remote",
        has_remote=True,
    )
    
    matched = result["matched_skills"]
    assert "LLM Integration" in matched
    assert "Model Context Protocol (MCP)" in matched
    assert "Retrieval-Augmented Generation (RAG)" in matched
    assert "Vector Databases" in matched
    assert result["score"] >= 80

    reasons = result["reasons"]
    assert len(reasons) == 3
    # First reason should mention verified skills
    assert "verified skills" in reasons[0]
    # Second reason should mention seniority
    assert "Seniority" in reasons[1]
    # Third reason should mention remote location
    assert "Location: 100% Global Remote" in reasons[2]


def test_explainable_matcher_location_reasons():
    """Verify location reason adapts to remote, Bengaluru, or other locations."""
    matcher = ExplainableMatcherService()

    # Remote
    res_remote = matcher.compute_match(title="Dev", location="Remote", has_remote=True)
    assert "Global Remote" in res_remote["reasons"][2]

    # Bengaluru
    res_blr = matcher.compute_match(title="Dev", location="Bengaluru, Karnataka", has_remote=False)
    assert "Bengaluru" in res_blr["reasons"][2]


def test_to_job_data_populates_explainable_fields():
    """Verify _to_job_data in main.py populates matched_skills, missing_skills, and reasons."""
    mock_job = Job(
        id=101,
        job_id="test_job_101",
        title="Full Stack Engineer (React, Python, FastAPI)",
        company="Aarivi AI",
        location="Remote",
        description="Looking for an engineer with React, Python, FastAPI, and Kubernetes.",
        tags='["Python", "React"]',
        has_remote=True,
        work_mode="remote",
        fetched_at=datetime.utcnow(),
    )
    
    job_data = _to_job_data(mock_job)
    assert isinstance(job_data, JobData)
    assert job_data.match_score is not None
    assert job_data.match_score > 50
    assert "React" in job_data.matched_skills
    assert "Python" in job_data.matched_skills
    assert "FastAPI" in job_data.matched_skills
    assert len(job_data.reasons) == 3
    assert any("verified skills" in r for r in job_data.reasons)
