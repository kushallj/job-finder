"""
src/api/routers/telegram_connector_router.py
FastAPI Router for Telegram Instant Push Notification Bot Connector.

Endpoints:
- GET /api/connectors/telegram/pairing: One-click deep link pairing
- POST /api/connectors/telegram/pair: Manual verification/pairing
- DELETE /api/connectors/telegram/pair: Disconnect bot
- GET /api/connectors/telegram/status: Connection state and push metrics
- PATCH /api/connectors/telegram/preferences: Notification thresholds
- POST /api/connectors/telegram/test-alert: Live test alert dispatch
- POST /api/connectors/telegram/webhook: Telegram Bot API update webhook
"""
from typing import Any, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Job, Application, TelegramConnector
from src.services.telegram_push_service import TelegramPushService
from src.api_models import (
    TelegramPairingResponse,
    TelegramManualPairRequest,
    TelegramPreferencesRequest,
    TelegramAlertDispatchDTO,
    TelegramTestAlertRequest,
)

router = APIRouter(prefix="/api/connectors/telegram", tags=["Telegram Instant Alert Connector"])


def get_telegram_service(db: Session = Depends(get_db)) -> TelegramPushService:
    """Dependency injection factory for TelegramPushService."""
    return TelegramPushService(db)


@router.get("/pairing", response_model=TelegramPairingResponse)
async def get_telegram_pairing_link(
    user_identifier: str = Query(default="default_user", description="Candidate user identifier"),
    service: TelegramPushService = Depends(get_telegram_service),
):
    """
    Generate a 1-click Telegram pairing deep link:
    https://t.me/JobFinderAlertBot?start=pair_<token>
    """
    try:
        return service.generate_pairing_details(user_identifier=user_identifier)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate Telegram pairing link: {str(exc)}")


@router.get("/status", response_model=TelegramPairingResponse)
async def get_telegram_status(
    user_identifier: str = Query(default="default_user", description="Candidate user identifier"),
    service: TelegramPushService = Depends(get_telegram_service),
):
    """
    Check live connection state, paired chat ID, and alert metrics.
    """
    conn = service.get_or_create_connector(user_identifier=user_identifier)
    return TelegramPairingResponse(
        status="success",
        is_connected=conn.is_connected,
        bot_username=service.bot_username,
        pairing_code=conn.pairing_code,
        pairing_url=f"https://t.me/{service.bot_username}?start={conn.pairing_code}" if conn.pairing_code else None,
        instructions="Open the link in Telegram and tap 'Start' to pair your account.",
        paired_chat_id=conn.telegram_chat_id,
        telegram_username=conn.telegram_username,
        paired_at=conn.paired_at,
        min_match_score=conn.min_match_score or 90.0,
        alerts_sent_count=conn.alerts_sent_count or 0,
        actions_taken_count=conn.actions_taken_count or 0,
    )


@router.post("/pair", response_model=TelegramPairingResponse)
async def manual_pair_telegram(
    req: TelegramManualPairRequest,
    user_identifier: str = Query(default="default_user"),
    service: TelegramPushService = Depends(get_telegram_service),
):
    """
    Manually complete pairing using a chat ID or pairing code.
    """
    conn = service.get_or_create_connector(user_identifier=user_identifier)
    code = req.pairing_code or conn.pairing_code or "pair_manual"
    chat_id = req.chat_id or "12345678"

    paired = service.complete_pairing(
        pairing_code=code,
        chat_id=chat_id,
        telegram_username=req.telegram_username,
        first_name=req.first_name,
    )
    if not paired:
        raise HTTPException(status_code=400, detail="Invalid pairing code.")

    return await get_telegram_status(user_identifier=user_identifier, service=service)


@router.delete("/pair")
async def unpair_telegram(
    user_identifier: str = Query(default="default_user"),
    service: TelegramPushService = Depends(get_telegram_service),
):
    """
    Disconnect candidate's Telegram bot connector.
    """
    service.unpair_connector(user_identifier=user_identifier)
    return {"status": "success", "message": "Telegram bot disconnected successfully."}


@router.patch("/preferences")
async def update_telegram_preferences(
    req: TelegramPreferencesRequest,
    user_identifier: str = Query(default="default_user"),
    service: TelegramPushService = Depends(get_telegram_service),
):
    """
    Update minimum match percentage threshold (e.g. >= 90%) and alert triggers.
    """
    updated = service.update_preferences(
        min_match_score=req.min_match_score,
        notify_high_match_jobs=req.notify_high_match_jobs,
        notify_interview_requests=req.notify_interview_requests,
        user_identifier=user_identifier,
    )
    return {
        "status": "success",
        "min_match_score": updated.min_match_score,
        "notify_high_match_jobs": updated.notify_high_match_jobs,
        "notify_interview_requests": updated.notify_interview_requests,
    }


@router.post("/test-alert", response_model=TelegramAlertDispatchDTO)
async def send_test_telegram_alert(
    req: TelegramTestAlertRequest,
    user_identifier: str = Query(default="default_user"),
    db: Session = Depends(get_db),
    service: TelegramPushService = Depends(get_telegram_service),
):
    """
    Simulate and dispatch a real-time push alert with 1-click action buttons:
    - [⚡ Apply Now]
    - [📝 Draft Pitch]
    """
    conn = service.get_or_create_connector(user_identifier=user_identifier)

    # If testing interview request alert
    if req.alert_type == "interview_request":
        # Find or create sample Application
        app = db.query(Application).first()
        if not app:
            job = db.query(Job).first()
            if not job:
                job = Job(
                    job_id="job_tessellate_tg_test",
                    title="Senior Frontend Engineer",
                    company="Tessellate",
                    location="Bengaluru / Remote",
                    salary_min=180000,
                    salary_max=220000,
                    salary_currency="USD",
                )
                db.add(job)
                db.commit()
            app = Application(
                job_id=job.id,
                user_id=1,
                status="interviewing",
                kanban_stage="technical_interview",
                recruiter_name="Sarah Jenkins",
                recruiter_email="recruiter@tessellate.io",
                email_subject="Re: Interview invitation — Senior Frontend Engineer",
                next_action_title="Technical Interview",
            )
            db.add(app)
            db.commit()

        return service.push_interview_alert(application=app, connector=conn)

    # Default: High-Match Job Alert (>= 90%)
    job = None
    if req.job_id:
        job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        job = db.query(Job).first()
    if not job:
        job = Job(
            job_id="job_tessellate_tg_match",
            title="Senior Frontend Engineer",
            company="Tessellate",
            location="Bengaluru / Remote",
            salary_min=180000,
            salary_max=220000,
            salary_currency="USD",
            url="https://jobfinder.io/jobs/tessellate-frontend",
        )
        db.add(job)
        db.commit()

    return service.push_high_match_job_alert(
        job=job,
        match_score=req.match_score,
        matched_skills=["React", "TypeScript", "Vite", "LLM Integration"],
        reasons=[
            "Matches 3 of your top verified skills: React, TypeScript, Vite",
            "Seniority: Matches your 4+ years frontend experience",
            "Location: Remote / Bengaluru hybrid as preferred",
        ],
        connector=conn,
    )


@router.post("/webhook")
async def telegram_bot_webhook(
    request: Request,
    service: TelegramPushService = Depends(get_telegram_service),
):
    """
    Webhook handler for Telegram Bot API updates.
    Handles:
    - User taps Start with deep link: `/start pair_<token>`
    - 1-click button callbacks: `apply_job_<id>`, `pitch_job_<id>`, `draft_reply_app_<id>`
    """
    try:
        data = await request.json()
    except Exception:
        return {"status": "ok", "message": "Empty or invalid body"}

    # 1. Handle Inline Keyboard Button Callbacks
    if "callback_query" in data:
        cb = data["callback_query"]
        cb_data = cb.get("data", "")
        message = cb.get("message", {})
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))

        reply_text, action_type = service.handle_callback_query(
            callback_data=cb_data,
            chat_id=chat_id,
            message_id=str(message.get("message_id", "")),
        )
        return {"status": "success", "action": action_type, "reply": reply_text}

    # 2. Handle Text Messages (/start pair_<token>)
    if "message" in data:
        msg = data["message"]
        text_content = msg.get("text", "")
        chat = msg.get("chat", {})
        chat_id = str(chat.get("id", ""))
        user = msg.get("from", {})
        username = user.get("username")
        first_name = user.get("first_name", "Candidate")

        if text_content.startswith("/start"):
            parts = text_content.split()
            if len(parts) > 1 and parts[1].startswith("pair_"):
                pairing_code = parts[1]
                paired = service.complete_pairing(
                    pairing_code=pairing_code,
                    chat_id=chat_id,
                    telegram_username=username,
                    first_name=first_name,
                )
                return {
                    "status": "success",
                    "paired": bool(paired),
                    "chat_id": chat_id,
                    "message": "Telegram connector paired successfully",
                }

    return {"status": "ok"}
