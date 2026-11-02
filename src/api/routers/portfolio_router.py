"""
src/api/routers/portfolio_router.py
FastAPI Router for Public Hosted Candidate Portfolio and Recruiter RAG Chatbot.

Provides endpoints for:
- Hosted portfolio retrieval (/portfolio/:username)
- Recruiter RAG Chatbot querying with verified source citations (JSON & SSE streaming)
- Live GitHub activity heatmap (kibo-ui compatible)
- Candidate portfolio management & reindexing
"""
from typing import Optional
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.portfolio_service import PortfolioService
from src.api_models import (
    PublicPortfolioResponse,
    GitHubActivityResponse,
    PortfolioChatRequest,
    PortfolioChatResponse,
    PortfolioCitationDTO,
)

router = APIRouter(prefix="/api/portfolio", tags=["Public Portfolio & Recruiter Chatbot"])


def get_portfolio_service(db: Session = Depends(get_db)) -> PortfolioService:
    """Dependency injection factory for PortfolioService."""
    return PortfolioService(db)


@router.get("/{username}", response_model=PublicPortfolioResponse)
async def get_public_portfolio(
    username: str,
    service: PortfolioService = Depends(get_portfolio_service),
):
    """
    Retrieve hosted public candidate portfolio page data (/portfolio/:username).
    Returns candidate profile, timeline experiences, verified projects,
    and live GitHub activity heatmap for kibo-ui rendering.
    """
    try:
        return service.get_public_portfolio(username=username)
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio: {str(exc)}")


@router.get("/{username}/github-activity", response_model=GitHubActivityResponse)
async def get_candidate_github_activity(
    username: str,
    days: int = Query(default=365, ge=30, le=730, description="Number of trailing days"),
    service: PortfolioService = Depends(get_portfolio_service),
):
    """
    Retrieve live GitHub contribution activity heatmap data formatted for kibo-ui.
    """
    profile = service.get_profile_by_username(username)
    gh_user = profile.github_username if profile and profile.github_username else username
    from src.services.github_activity_service import GitHubActivityService
    return GitHubActivityService.get_candidate_activity(github_username=gh_user, days_count=days)


@router.post("/{username}/chat")
async def chat_with_candidate_ai(
    username: str,
    req: PortfolioChatRequest,
    request: Request,
    service: PortfolioService = Depends(get_portfolio_service),
):
    """
    Interactive Recruiter RAG Chatbot.
    Recruiters visiting the candidate's portfolio can ask questions:
    "Does Kushal have experience with distributed vector indexing?"
    
    The AI performs semantic vector search over the candidate's resume embeddings
    and GitHub READMEs and returns a concise, verified response with exact citations.
    Supports standard JSON or real-time Server-Sent Events (SSE) streaming.
    """
    profile = service.get_profile_by_username(username)
    if not profile:
        # Auto-seed if kushal or default user
        if username.lower() in ("kushal", "kushalljain", "default_user", "candidate"):
            profile = service.seed_default_portfolio(username=username.lower())
        else:
            raise HTTPException(status_code=404, detail=f"Candidate portfolio for '{username}' not found.")

    session_id = req.session_id or f"recruiter_sess_{uuid.uuid4().hex[:12]}"
    retrieved_chunks = service.rag.retrieve_relevant_chunks(
        profile_id=profile.id,
        query=req.message,
        top_k=4,
    )

    # Handle streaming response via SSE
    if req.stream:
        generator = service.rag.stream_grounded_answer(
            candidate_name=profile.full_name,
            query=req.message,
            retrieved_chunks=retrieved_chunks,
            session_id=session_id,
        )
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Standard JSON response
    answer, raw_citations, confidence = service.rag.synthesize_grounded_answer(
        candidate_name=profile.full_name,
        query=req.message,
        retrieved_chunks=retrieved_chunks,
    )

    # Log chat audit
    client_ip = request.client.host if request.client else "unknown"
    service.rag.record_chat_audit(
        profile_id=profile.id,
        session_id=session_id,
        question=req.message,
        answer=answer,
        citations=raw_citations,
        confidence=confidence,
        ip_hash=client_ip,
    )

    citations = [
        PortfolioCitationDTO(
            source_type=c["source_type"],
            source_title=c["source_title"],
            source_url=c.get("source_url"),
            similarity_score=c["similarity_score"],
            excerpt=c["excerpt"],
        )
        for c in raw_citations
    ]

    return PortfolioChatResponse(
        session_id=session_id,
        question=req.message,
        answer=answer,
        citations=citations,
        confidence_score=confidence,
        created_at=datetime.utcnow(),
    )


@router.post("/seed", response_model=PublicPortfolioResponse)
async def seed_portfolio_data(
    username: str = Query(default="kushal", description="Candidate username slug to seed"),
    service: PortfolioService = Depends(get_portfolio_service),
):
    """
    Seed sample candidate portfolio (for Kushal) with verified projects,
    experience timeline, and pre-indexed resume/GitHub vector embeddings.
    """
    try:
        service.seed_default_portfolio(username=username)
        return service.get_public_portfolio(username=username)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to seed portfolio: {str(exc)}")
