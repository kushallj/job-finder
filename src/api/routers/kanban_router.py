"""
src/api/routers/kanban_router.py
FastAPI Router for Kanban Application Tracker with Countdown Timers and Recruiter Email Provenance Badges.
Enforces multi-tenant isolation so users can only view and manage their own cards.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import User
from src.auth.dependencies import get_current_user
from src.services.kanban_service import KanbanService
from src.api_models import (
    KanbanBoardResponse,
    KanbanCardResponse,
    KanbanNextActionRequest,
    KanbanEmailProvenanceRequest,
    KanbanStageTransitionRequest,
)

router = APIRouter(prefix="/api/kanban", tags=["Kanban Tracker"])


def get_kanban_service(db: Session = Depends(get_db)) -> KanbanService:
    """Dependency injection factory for KanbanService."""
    return KanbanService(db)


@router.get("/board", response_model=KanbanBoardResponse)
async def get_kanban_board(
    user_id: Optional[int] = Query(default=None, description="Optional user ID filter (superusers only)"),
    current_user: User = Depends(get_current_user),
    service: KanbanService = Depends(get_kanban_service),
):
    """
    Retrieve full Kanban Application Tracker board partitioned into columns.
    Every card includes dynamic countdown timers (🟡 Amber 1-3d, 🔵 Blue 4-7d, 🔴 Red overdue)
    and Recruiter Email Thread Provenance badges.
    Strictly isolated per tenant.
    """
    try:
        effective_user_id = user_id if (user_id is not None and current_user.is_superuser) else current_user.id
        return service.get_board(user_id=effective_user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Kanban board: {str(exc)}")


@router.get("/cards", response_model=List[KanbanCardResponse])
async def get_kanban_cards(
    stage: Optional[str] = Query(default=None, description="Filter by column stage e.g. applied, technical_interview"),
    alert_severity: Optional[str] = Query(default=None, description="Filter by alert severity: amber, blue, red"),
    overdue_only: bool = Query(default=False, description="Filter only overdue items (red alert)"),
    current_user: User = Depends(get_current_user),
    service: KanbanService = Depends(get_kanban_service),
):
    """
    Retrieve flat list of Kanban application cards with filtering by alert severity or column stage.
    Strictly isolated per tenant.
    """
    try:
        return service.get_cards(
            stage=stage,
            alert_severity=alert_severity,
            overdue_only=overdue_only,
            user_id=current_user.id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Kanban cards: {str(exc)}")


@router.patch("/cards/{application_id}/stage", response_model=KanbanCardResponse)
async def update_card_stage(
    application_id: int,
    request: KanbanStageTransitionRequest,
    current_user: User = Depends(get_current_user),
    service: KanbanService = Depends(get_kanban_service),
):
    """
    Move an application card to a different Kanban column stage (with optional reorder index).
    Enforces ownership validation.
    """
    try:
        effective_user_id = None if current_user.is_superuser else current_user.id
        return service.transition_stage(
            application_id=application_id,
            target_stage=request.stage,
            order=request.order or 0,
            user_id=effective_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update card stage: {str(exc)}")


@router.post("/cards/{application_id}/next-action", response_model=KanbanCardResponse)
async def set_next_action(
    application_id: int,
    request: KanbanNextActionRequest,
    current_user: User = Depends(get_current_user),
    service: KanbanService = Depends(get_kanban_service),
):
    """
    Schedule or reschedule a time-sensitive next action countdown deadline on the card.
    Triggers 🟡 Amber (1-3d), 🔵 Blue (4-7d), or 🔴 Red (overdue) countdown badges.
    Enforces ownership validation.
    """
    try:
        effective_user_id = None if current_user.is_superuser else current_user.id
        return service.set_next_action(
            application_id=application_id,
            action_type=request.next_action_type,
            action_title=request.next_action_title,
            due_at=request.next_action_due_at,
            user_id=effective_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to set next action: {str(exc)}")


@router.post("/cards/{application_id}/email-provenance", response_model=KanbanCardResponse)
async def set_email_provenance(
    application_id: int,
    request: KanbanEmailProvenanceRequest,
    current_user: User = Depends(get_current_user),
    service: KanbanService = Depends(get_kanban_service),
):
    """
    Attach or update recruiter email thread provenance directly on the application card.
    Generates exact badge string e.g. '"Re: Interview invitation..." from recruiter@tessellate.io'.
    Enforces ownership validation.
    """
    try:
        effective_user_id = None if current_user.is_superuser else current_user.id
        return service.set_email_provenance(
            application_id=application_id,
            recruiter_email=request.recruiter_email,
            email_subject=request.email_subject,
            recruiter_name=request.recruiter_name,
            recruiter_company=request.recruiter_company,
            thread_id=request.email_thread_id,
            received_at=request.last_email_received_at,
            user_id=effective_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to set email provenance: {str(exc)}")


@router.post("/seed", response_model=KanbanBoardResponse)
async def seed_sample_kanban_board(
    current_user: User = Depends(get_current_user),
    service: KanbanService = Depends(get_kanban_service),
):
    """
    Seed realistic sample cards demonstrating 🟡 Amber (Technical Interview in 3 days),
    🔵 Blue (Take-home in 6 days), and 🔴 Red (Overdue follow-up) alerts with Tessellate recruiter provenance.
    Scoped to the calling user.
    """
    try:
        return service.seed_sample_kanban(user_id=current_user.id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to seed sample Kanban board: {str(exc)}")
