"""
src/services/portfolio_service.py
High-level orchestrator for Public Hosted Candidate Portfolios and Recruiter RAG.

Handles profile resolution, verified projects, timeline experiences,
GitHub activity integration, and automatic vector indexing.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_, and_, desc, asc, text
from sqlalchemy.orm import Session

from src.models import (
    Base,
    CandidateProfile,
    CandidateExperience,
    CandidateProject,
    CandidateKnowledgeChunk,
    PortfolioChatLog,
)
from src.api_models import (
    CandidateExperienceDTO,
    CandidateProjectDTO,
    CandidateProfileOverviewDTO,
    PublicPortfolioResponse,
    GitHubActivityResponse,
)
from src.services.portfolio_rag_service import PortfolioRAGService
from src.services.github_activity_service import GitHubActivityService

logger = logging.getLogger("portfolio_service")


def ensure_portfolio_schema(db: Session) -> None:
    """Ensure all portfolio tables and columns exist in database."""
    try:
        bind = db.get_bind()
        Base.metadata.create_all(
            bind=bind,
            tables=[
                CandidateExperience.__table__,
                CandidateProject.__table__,
                CandidateKnowledgeChunk.__table__,
                PortfolioChatLog.__table__,
            ],
            checkfirst=True,
        )

        # Check candidate_profiles columns for SQLite
        cursor = db.connection().connection.cursor()
        cursor.execute("PRAGMA table_info(candidate_profiles)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        needed_cols = [
            ("username", "VARCHAR(100)"),
            ("headline", "VARCHAR(500)"),
            ("github_username", "VARCHAR(100)"),
            ("avatar_url", "VARCHAR(500)"),
            ("custom_domain", "VARCHAR(255)"),
            ("is_public", "BOOLEAN DEFAULT 1"),
        ]
        for col_name, col_type in needed_cols:
            if col_name not in existing_cols:
                db.execute(text(f"ALTER TABLE candidate_profiles ADD COLUMN {col_name} {col_type}"))
                logger.info("Migrated candidate_profiles table: added column %s", col_name)

        db.commit()
    except Exception as exc:
        logger.warning("Portfolio schema check note: %s", exc)


class PortfolioService:
    """Orchestrates candidate portfolio assembly, verification, and RAG knowledge indexing."""

    def __init__(self, db: Session):
        self.db = db
        ensure_portfolio_schema(db)
        self.rag = PortfolioRAGService(db)

    def get_profile_by_username(self, username: str) -> Optional[CandidateProfile]:
        """Fetch profile by username slug or user_identifier."""
        clean = (username or "").strip().lower()
        if not clean:
            return None

        profile = (
            self.db.query(CandidateProfile)
            .filter(
                or_(
                    CandidateProfile.username.ilike(clean),
                    CandidateProfile.user_identifier.ilike(clean),
                )
            )
            .first()
        )
        return profile

    def get_public_portfolio(self, username: str) -> PublicPortfolioResponse:
        """
        Assemble full hosted portfolio for public viewing at /portfolio/:username.
        Includes profile overview, verified projects, timeline experiences,
        and kibo-ui compatible GitHub contribution heatmap.
        """
        profile = self.get_profile_by_username(username)
        if not profile:
            # If requesting default user or kushal, seed it on demand
            if username.lower() in ("kushal", "kushalljain", "default_user", "candidate"):
                profile = self.seed_default_portfolio(username=username.lower())
            else:
                raise ValueError(f"Candidate portfolio for '{username}' not found.")

        # Parse skills
        skills_list = []
        if profile.skills:
            try:
                skills_list = json.loads(profile.skills) if profile.skills.startswith("[") else [s.strip() for s in profile.skills.split(",")]
            except Exception:
                skills_list = []

        overview = CandidateProfileOverviewDTO(
            username=profile.username or username,
            full_name=profile.full_name,
            headline=profile.headline or profile.current_title,
            email=profile.email if profile.is_public else None,
            location=profile.location or "Remote",
            years_of_experience=profile.years_of_experience or 4.0,
            bio_summary=profile.bio_summary,
            linkedin_url=profile.linkedin_url,
            github_url=profile.github_url,
            github_username=profile.github_username or profile.username,
            portfolio_url=profile.portfolio_url or f"https://jobfinder.io/portfolio/{profile.username}",
            avatar_url=profile.avatar_url,
            skills=skills_list,
            is_public=profile.is_public,
        )

        # Query experiences
        experiences_db = (
            self.db.query(CandidateExperience)
            .filter(CandidateExperience.profile_id == profile.id)
            .order_by(asc(CandidateExperience.display_order), desc(CandidateExperience.id))
            .all()
        )
        experiences_dto: List[CandidateExperienceDTO] = []
        for e in experiences_db:
            techs = json.loads(e.technologies) if e.technologies and e.technologies.startswith("[") else []
            achieves = json.loads(e.achievements) if e.achievements and e.achievements.startswith("[") else []
            experiences_dto.append(
                CandidateExperienceDTO(
                    id=e.id,
                    company=e.company,
                    title=e.title,
                    location=e.location,
                    employment_type=e.employment_type,
                    start_date=e.start_date,
                    end_date=e.end_date,
                    is_current=e.is_current,
                    description=e.description,
                    technologies=techs,
                    achievements=achieves,
                    display_order=e.display_order,
                )
            )

        # Query projects
        projects_db = (
            self.db.query(CandidateProject)
            .filter(CandidateProject.profile_id == profile.id)
            .order_by(asc(CandidateProject.display_order), desc(CandidateProject.stars_count))
            .all()
        )
        projects_dto: List[CandidateProjectDTO] = []
        for p in projects_db:
            techs = json.loads(p.tech_stack) if p.tech_stack and p.tech_stack.startswith("[") else []
            projects_dto.append(
                CandidateProjectDTO(
                    id=p.id,
                    title=p.title,
                    tagline=p.tagline,
                    description=p.description,
                    github_repo_url=p.github_repo_url,
                    demo_url=p.demo_url,
                    tech_stack=techs,
                    stars_count=p.stars_count,
                    is_verified=p.is_verified,
                    display_order=p.display_order,
                )
            )

        # Generate live GitHub contribution activity heatmap for kibo-ui
        gh_activity = GitHubActivityService.get_candidate_activity(
            github_username=profile.github_username or profile.username
        )

        # Count total indexed vector chunks
        chunk_count = (
            self.db.query(CandidateKnowledgeChunk)
            .filter(CandidateKnowledgeChunk.profile_id == profile.id)
            .count()
        )

        return PublicPortfolioResponse(
            status="success",
            profile=overview,
            experiences=experiences_dto,
            projects=projects_dto,
            github_activity=gh_activity,
            portfolio_url=f"https://jobfinder.io/portfolio/{profile.username}",
            indexed_chunks_count=chunk_count,
        )

    def seed_default_portfolio(self, username: str = "kushal") -> CandidateProfile:
        """Seeds a verified candidate profile for Kushal with realistic projects, experience, and RAG knowledge."""
        clean_user = username.lower().strip()
        profile = self.get_profile_by_username(clean_user)

        if not profile:
            profile = CandidateProfile(
                user_identifier=clean_user,
                username=clean_user,
                full_name="Kushal Jain",
                headline="Staff AI & Frontend Engineer — Distributed Vector Search & Intelligent Agents",
                email="kushal@example.com",
                location="Bengaluru / Remote",
                github_username="kushalljain",
                github_url="https://github.com/kushalljain",
                linkedin_url="https://linkedin.com/in/kushal-jain",
                portfolio_url=f"https://jobfinder.io/portfolio/{clean_user}",
                avatar_url="https://avatars.githubusercontent.com/u/10293847?v=4",
                years_of_experience=5.0,
                current_title="Staff Frontend & AI Systems Engineer",
                bio_summary=(
                    "Senior / Staff engineer specializing in distributed vector indexing, RAG systems, "
                    "high-throughput agentic workflows, and latency-optimized React/TypeScript user interfaces. "
                    "Passionate about building scalable AI architectures and sub-millisecond retrieval tooling."
                ),
                skills=json.dumps([
                    "React", "TypeScript", "Vite", "Python", "FastAPI", "Distributed Systems",
                    "Vector Databases", "HNSW", "RAG", "LLM Integration", "Model Context Protocol (MCP)",
                    "PostgreSQL", "Docker", "TailwindCSS", "PyTorch"
                ]),
                is_public=True,
                resume_raw_text=(
                    "KUSHAL JAIN — Senior / Staff Frontend & AI Engineer\n\n"
                    "SUMMARY:\n"
                    "5+ years architecting enterprise SaaS platforms and real-time AI systems. Expert in distributed vector indexing, "
                    "retrieval-augmented generation (RAG), and high-frequency frontend web architectures.\n\n"
                    "EXPERIENCE:\n"
                    "• Staff Frontend Engineer at Tessellate (2023 - Present): Spearheaded the frontend architecture for real-time analytics. "
                    "Engineered sub-millisecond vector querying tools and automated candidate ranking engines.\n"
                    "• Senior Full-Stack Engineer at Vercel (2021 - 2023): Designed developer tooling for Edge runtime deployments. "
                    "Optimized bundle size by 35% and introduced streaming SSR pipelines.\n\n"
                    "TECHNICAL SKILLS:\n"
                    "Languages: TypeScript, JavaScript, Python, Rust, SQL\n"
                    "Frameworks: React, Next.js, Vite, FastAPI, Node.js\n"
                    "AI/Data: Vector Indexing (HNSW), RAG, Model Context Protocol (MCP), PyTorch, Chroma, Redis"
                ),
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)

        # Seed experiences if none exist
        if not profile.experiences:
            exp1 = CandidateExperience(
                profile_id=profile.id,
                company="Tessellate",
                title="Staff Frontend Engineer",
                location="Bengaluru / Remote",
                employment_type="Full-time",
                start_date="Jan 2023",
                end_date="Present",
                is_current=True,
                description="Leading front-end platform engineering and AI integration workflows.",
                technologies=json.dumps(["React", "TypeScript", "Vite", "FastAPI", "Vector DBs", "RAG"]),
                achievements=json.dumps([
                    "Architected high-throughput reactive UI handling 100k+ concurrent search queries",
                    "Integrated distributed vector indexing pipeline reducing search latency by 68%",
                    "Built explainable match scoring engine with multi-facet validation reasons"
                ]),
                display_order=1,
            )
            exp2 = CandidateExperience(
                profile_id=profile.id,
                company="Vercel",
                title="Senior Full-Stack Engineer",
                location="Remote",
                employment_type="Full-time",
                start_date="Feb 2021",
                end_date="Dec 2022",
                is_current=False,
                description="Engineered Edge developer platform and streaming SSR infrastructure.",
                technologies=json.dumps(["TypeScript", "Next.js", "Node.js", "Rust", "Turbopack"]),
                achievements=json.dumps([
                    "Improved edge execution cold starts by 40% across distributed serverless regions",
                    "Authored developer documentation and CLI tooling utilized by 200k+ developers"
                ]),
                display_order=2,
            )
            self.db.add_all([exp1, exp2])
            self.db.commit()

        # Seed projects if none exist
        if not profile.projects:
            p1 = CandidateProject(
                profile_id=profile.id,
                title="Distributed Vector Indexer",
                tagline="Sub-millisecond HNSW vector search over partitioned object storage",
                description=(
                    "A distributed, lock-free vector indexing engine built for high-dimensional embeddings. "
                    "Features dynamic graph partitioning, SIMD-accelerated distance metrics, and horizontal scaling."
                ),
                github_repo_url="https://github.com/kushalljain/distributed-vector-indexer",
                demo_url="https://vector-indexer-demo.dev",
                tech_stack=json.dumps(["Python", "Rust", "HNSW", "Vector Indexing", "FastAPI", "SIMD"]),
                stars_count=184,
                is_verified=True,
                readme_content=(
                    "# Distributed Vector Indexer\n\n"
                    "High-performance vector search engine designed for scalable LLM embedding retrieval and semantic search.\n\n"
                    "## Architecture & Design\n"
                    "- Implements Hierarchical Navigable Small World (HNSW) graph indexing with dynamic multi-tier sharding.\n"
                    "- Leverages SIMD (AVX-512) distance kernels for inner-product and cosine distance computations.\n"
                    "- Benchmarked at 0.8ms p99 latency across 10M 1536-dimensional vectors.\n"
                    "- Built with Python, Rust FFI, and FastAPI async workers.\n\n"
                    "## Recruiter Q&A Evidence\n"
                    "Kushal designed the core partitioning logic and benchmarked throughput under production load."
                ),
                display_order=1,
            )
            p2 = CandidateProject(
                profile_id=profile.id,
                title="Autonomous Job Finder & Agentic Outreach",
                tagline="Multi-agent search, email personalization, and Kanban tracking engine",
                description=(
                    "Production system that automates job discovery, cross-attention resume matching, "
                    "inbound recruiter email synchronization, and real-time pipeline auto-advancement."
                ),
                github_repo_url="https://github.com/kushalljain/job-finder",
                demo_url="https://jobfinder.io",
                tech_stack=json.dumps(["Python", "FastAPI", "React", "TypeScript", "Vite", "SQLAlchemy"]),
                stars_count=312,
                is_verified=True,
                readme_content=(
                    "# Autonomous Job Finder & Agentic Outreach\n\n"
                    "Enterprise recruiting and application orchestration engine.\n"
                    "- Features Explainable Match Scoring with modern tech skill chips (RAG, MCP, AI Agents).\n"
                    "- Real-time Kanban Application Tracker with Amber (3d), Blue (6d), and Red (Overdue) countdown alerts.\n"
                    "- IMAP Inbound Recruiter Email Sync auto-advancing cards without manual dragging."
                ),
                display_order=2,
            )
            self.db.add_all([p1, p2])
            self.db.commit()

        # Index knowledge base into vector store for RAG
        self.rag.index_resume(profile)
        for proj in profile.projects:
            self.rag.index_project_and_readme(profile.id, proj)
        self.rag.index_experiences(profile.id, profile.experiences)

        return profile
