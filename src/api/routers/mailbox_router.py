"""
src/api/routers/mailbox_router.py
FastAPI Router for Inbound Recruiter Email Sync & Auto-Advancing Pipeline.

Connects user's Gmail/Outlook mailbox, scans incoming recruiter messages,
classifies intent (INTERVIEW_INVITATION, ASSESSMENT, OFFER, REJECTION, FOLLOW_UP_REQUIRED),
and automatically moves the Kanban card to the right column with countdown timers
and email provenance badges.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import MailboxAccount, InboundRecruiterMessage
from src.services.inbound_email_sync_service import InboundEmailSyncService
from src.api_models import (
    MailboxConnectRequest,
    MailboxAccountResponse,
    MailboxSyncResponse,
    InboundSimulationRequest,
    InboundAdvancementResult,
    InboundMessageResponse,
)

router = APIRouter(prefix="/api/mailbox", tags=["Inbound Email Sync & Auto-Advancement"])


def get_sync_service(db: Session = Depends(get_db)) -> InboundEmailSyncService:
    """Dependency injection factory for InboundEmailSyncService."""
    return InboundEmailSyncService(db)


@router.post("/connect", response_model=MailboxAccountResponse)
async def connect_mailbox(
    req: MailboxConnectRequest,
    service: InboundEmailSyncService = Depends(get_sync_service),
):
    """
    Connect a user's Gmail or Outlook mailbox to enable automatic
    recruiter email scanning and pipeline card advancement.
    """
    try:
        account = service.connect_mailbox(
            provider=req.provider,
            email_address=req.email_address,
            password=req.password,
            imap_host=req.imap_host,
            imap_port=req.imap_port,
            use_ssl=req.use_ssl,
            auto_advance_pipeline=req.auto_advance_pipeline,
        )
        return account
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to connect mailbox: {str(exc)}")


@router.get("/status", response_model=MailboxAccountResponse)
async def get_mailbox_status(
    mailbox_id: Optional[int] = Query(default=None, description="Optional mailbox ID"),
    service: InboundEmailSyncService = Depends(get_sync_service),
):
    """
    Retrieve connection status, last sync timestamp, and advancement metrics.
    """
    account = (
        service.get_mailbox(mailbox_id)
        if mailbox_id
        else service.get_primary_mailbox()
    )
    if not account:
        raise HTTPException(status_code=404, detail="No active mailbox found. Please connect your Gmail or Outlook account.")
    return account


@router.post("/sync", response_model=MailboxSyncResponse)
async def sync_mailbox_messages(
    mailbox_id: Optional[int] = Query(default=None, description="Mailbox ID to sync"),
    limit: int = Query(default=25, ge=1, le=100, description="Max messages to scan"),
    service: InboundEmailSyncService = Depends(get_sync_service),
):
    """
    Scan incoming recruiter emails via IMAP, classify intent,
    and automatically advance matching Kanban cards.
    """
    target_id = mailbox_id
    if not target_id:
        primary = service.get_primary_mailbox()
        if not primary:
            # Auto-connect a default mailbox account if none exists yet
            primary = service.connect_mailbox(
                provider="gmail",
                email_address="candidate@gmail.com",
            )
        target_id = primary.id

    try:
        return service.sync_mailbox(mailbox_id=target_id, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Mailbox sync failed: {str(exc)}")


@router.post("/simulate-inbound", response_model=InboundAdvancementResult)
async def simulate_inbound_recruiter_email(
    req: InboundSimulationRequest,
    auto_advance: bool = Query(default=True, description="Whether to auto-advance the pipeline card"),
    service: InboundEmailSyncService = Depends(get_sync_service),
):
    """
    Simulate an inbound recruiter message (e.g. from recruiter@tessellate.io)
    to classify intent and auto-advance the Kanban application card in real time.
    """
    try:
        primary = service.get_primary_mailbox()
        mailbox_id = primary.id if primary else None

        result = service.process_inbound_message(
            sender_email=req.sender_email,
            subject=req.subject,
            body_text=req.body_text,
            sender_name=req.sender_name,
            company=req.company,
            application_id=req.application_id,
            mailbox_id=mailbox_id,
            auto_advance=auto_advance,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inbound simulation failed: {str(exc)}")


@router.get("/messages", response_model=List[InboundMessageResponse])
async def list_inbound_messages(
    mailbox_id: Optional[int] = Query(default=None, description="Filter by mailbox ID"),
    application_id: Optional[int] = Query(default=None, description="Filter by application ID"),
    intent: Optional[str] = Query(default=None, description="Filter by classified intent"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    db: Session = Depends(get_db),
):
    """
    List audit trail of scanned and classified recruiter messages.
    """
    query = db.query(InboundRecruiterMessage)
    if mailbox_id is not None:
        query = query.filter(InboundRecruiterMessage.mailbox_id == mailbox_id)
    if application_id is not None:
        query = query.filter(InboundRecruiterMessage.application_id == application_id)
    if intent:
        query = query.filter(InboundRecruiterMessage.classified_intent == intent.upper())

    messages = query.order_by(desc(InboundRecruiterMessage.received_at)).limit(limit).all()
    return messages
