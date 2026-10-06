"""
src/workday/api/workday_router.py — FastAPI Endpoints for Workday Autonomous Profile & Auto-Apply Engine.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.workday.service import WorkdayService
from src.workday.models import (
    WorkdayCandidateProfile,
    WorkdayAccountRecord,
    WorkdayApplicationSubmission,
    WorkdayConfigRecord,
)
from src.answer_bank.models import AnsweredQuestion
from src.models import Job

router = APIRouter(prefix="/api/workday", tags=["workday-auto-apply"])


class WorkdayProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    account_email: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    headline: Optional[str] = None
    years_of_experience: Optional[float] = None
    experience_years: Optional[float] = None
    current_company: Optional[str] = None
    current_title: Optional[str] = None
    skills: Optional[List[str]] = None
    work_history: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    legally_authorized: Optional[bool] = None
    is_authorized_us: Optional[bool] = None
    requires_sponsorship: Optional[bool] = None
    notice_period_days: Optional[int] = None
    target_salary_min: Optional[float] = None
    target_salary_max: Optional[float] = None
    salary_expectation: Optional[float] = None
    gender: Optional[str] = None
    race_ethnicity: Optional[str] = None
    veteran_status: Optional[str] = None
    disability_status: Optional[str] = None
    eeo_gender: Optional[str] = None
    eeo_race: Optional[str] = None
    eeo_veteran: Optional[str] = None
    eeo_disability: Optional[str] = None


class WorkdayBatchApplyRequest(BaseModel):
    target_count: int = Field(default=25, ge=1, le=200)
    min_fit_score: float = Field(default=60.0, ge=0.0, le=100.0)


class WorkdayConfigUpdateRequest(BaseModel):
    account_email: Optional[str] = None
    auto_apply_enabled: Optional[bool] = None
    mode: Optional[str] = None
    min_fit_score: Optional[float] = None
    daily_limit: Optional[int] = Field(default=None, ge=1, le=500)
    tailor_resumes: Optional[bool] = None
    generate_cover_letters: Optional[bool] = None
    batch_concurrency: Optional[int] = Field(default=None, ge=1, le=10)


class WorkdayPreviewTailorRequest(BaseModel):
    job_id: Optional[int] = None
    job_description: Optional[str] = None
    job_title: Optional[str] = None


@router.get("/status")
def get_workday_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns Workday Autopilot status, profile, registered accounts, and submissions telemetry."""
    service = WorkdayService(db)
    return service.get_progress_telemetry()


@router.get("/profile")
def get_workday_candidate_profile(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns candidate Workday autofill profile."""
    service = WorkdayService(db)
    return service.profile.to_dict()


@router.post("/profile")
def update_workday_candidate_profile(
    req: WorkdayProfileUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Updates candidate Workday profile and form autofill preferences."""
    service = WorkdayService(db)
    profile = service.profile

    update_dict = req.model_dump(exclude_unset=True) if hasattr(req, "model_dump") else req.dict(exclude_unset=True)
    for field, val in update_dict.items():
        if val is None:
            continue
        if field == "skills":
            profile.skills_json = json.dumps(val)
        elif field == "work_history":
            profile.work_history_json = json.dumps(val)
        elif field == "education":
            profile.education_json = json.dumps(val)
        elif field == "full_name":
            parts = str(val).split(" ", 1)
            profile.first_name = parts[0]
            profile.last_name = parts[1] if len(parts) > 1 else ""
        elif field in ("experience_years", "years_of_experience"):
            profile.years_of_experience = float(val)
        elif field in ("is_authorized_us", "legally_authorized"):
            profile.legally_authorized = bool(val)
        elif field == "salary_expectation":
            profile.target_salary_min = float(val)
            profile.target_salary_max = float(val)
        elif field in ("eeo_gender", "gender"):
            profile.gender = str(val)
        elif field in ("eeo_race", "race_ethnicity"):
            profile.race_ethnicity = str(val)
        elif field in ("eeo_veteran", "veteran_status"):
            profile.veteran_status = str(val)
        elif field in ("eeo_disability", "disability_status"):
            profile.disability_status = str(val)
        elif field == "state":
            profile.state_province = str(val)
        elif field in ("email", "account_email"):
            profile.account_email = str(val)
        elif hasattr(profile, field):
            setattr(profile, field, val)

    db.commit()
    db.refresh(profile)

    return {
        "status": "updated",
        "profile": profile.to_dict(),
        "message": "Candidate Workday profile successfully updated.",
    }


@router.post("/apply/{job_id}")
async def apply_single_workday_job(job_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Applies to a specific job via Workday Autopilot (account creation + resume tailoring + submission)."""
    service = WorkdayService(db)
    res = await service.auto_apply_job(job_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Application failed"))
    return res


@router.post("/batch-apply")
async def trigger_workday_batch_apply(
    req: Optional[WorkdayBatchApplyRequest] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Launches high-volume batch auto-apply for unapplied Workday jobs."""
    target = req.target_count if req else 25
    min_score = req.min_fit_score if req else 60.0
    service = WorkdayService(db)
    return await service.batch_auto_apply(target_count=target, min_score=min_score)


@router.post("/preview-tailor")
def preview_tailored_resume_for_job(
    req: WorkdayPreviewTailorRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Generates preview of tailored resume PDF and ATS match score for a job without applying."""
    service = WorkdayService(db)
    if req.job_id:
        job = db.query(Job).filter(Job.id == req.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {req.job_id} not found")
        tailored = service.tailorer.tailor_for_job(service.profile, job)
        return {
            "job_id": job.id,
            "job_title": job.title,
            "company": job.company,
            "ats_match_score": tailored.get("ats_match_score"),
            "ats_score": tailored.get("ats_match_score"),
            "matched_keywords": tailored.get("matched_keywords"),
            "tailored_resume_path": tailored.get("tailored_resume_path"),
            "tailored_resume_text": tailored.get("tailored_resume_text"),
            "cover_letter_text": tailored.get("cover_letter_text"),
            "tailored_profile": service.profile.to_dict(),
        }
    elif req.job_description:
        tailored = service.tailorer.tailor_for_workday(
            req.job_description,
            service.profile,
            job_title=req.job_title or "Senior Engineer",
        )
        return {
            "job_title": req.job_title or "Senior Engineer",
            "ats_match_score": tailored.get("ats_match_score"),
            "ats_score": tailored.get("ats_match_score"),
            "matched_keywords": tailored.get("matched_keywords"),
            "tailored_profile": service.profile.to_dict(),
            "skills": tailored.get("skills"),
            "recommended_focus": tailored.get("recommended_focus"),
        }
    else:
        raise HTTPException(status_code=400, detail="Must provide either job_id or job_description")


@router.get("/accounts")
def list_workday_accounts(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Lists registered Workday tenant accounts."""
    accounts = db.query(WorkdayAccountRecord).order_by(WorkdayAccountRecord.id.desc()).limit(limit).all()
    return {
        "total_count": len(accounts),
        "accounts": [a.to_dict() for a in accounts],
    }


@router.get("/submissions")
def list_workday_submissions(
    limit: int = Query(50, ge=1, le=300),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Lists Workday application submissions and cryptographic receipts."""
    q = db.query(WorkdayApplicationSubmission)
    if status:
        q = q.filter(WorkdayApplicationSubmission.status == status)
    subs = q.order_by(WorkdayApplicationSubmission.id.desc()).limit(limit).all()
    return {
        "total_count": len(subs),
        "submissions": [s.to_dict() for s in subs],
    }


@router.post("/config")
def update_workday_config(
    req: WorkdayConfigUpdateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Updates Workday configuration settings."""
    service = WorkdayService(db)
    cfg = service.config

    update_dict = req.model_dump(exclude_unset=True) if hasattr(req, "model_dump") else req.dict(exclude_unset=True)
    for field, val in update_dict.items():
        if val is not None and hasattr(cfg, field):
            setattr(cfg, field, val)

    db.commit()
    db.refresh(cfg)
    return {"status": "updated", "config": cfg.to_dict()}


class QuestionResolveRequest(BaseModel):
    question: str
    job_title: Optional[str] = "Software Engineer"
    company: Optional[str] = "Company"
    job_description: Optional[str] = ""
    category: Optional[str] = None


@router.post("/resolve-question")
async def resolve_form_question(
    req: QuestionResolveRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Cognitive Answer Bank Bridge for Chrome Extension and Browser Automation.
    Finds exact or fuzzy answers in answered_questions database, or generates
    in-flight using UnifiedAIService.
    """
    service = WorkdayService(db)
    full_name = f"{service.profile.first_name} {service.profile.last_name}".strip() or "Kushall Jain"
    candidate_ctx = {
        "name": full_name,
        "resume_summary": (
            f"{service.profile.headline}. Skills: {service.profile.skills_json}. "
            f"Experience: {service.profile.years_of_experience} years. Current title: {service.profile.current_title}."
        ),
    }
    result = await service.answer_bank.get_answer_for_question(
        question=req.question,
        job_title=req.job_title or "Software Engineer",
        company=req.company or "Company",
        job_description=req.job_description or "",
        category=req.category,
        candidate_context=candidate_ctx,
    )
    return result


class SaveAnswerRequest(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None
    source: Optional[str] = "user_edited"
    approved: Optional[bool] = True


@router.post("/save-answer")
async def save_form_answer(
    req: SaveAnswerRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Bi-Directional Learning Loop:
    Saves or updates user corrections/answers in answered_questions (Answer Bank)
    and synchronizes candidate profile if the category matches standard profile fields.
    """
    service = WorkdayService(db)

    # 1. Upsert into Answer Bank
    answered_q = service.answer_bank.save_or_update_answer(
        question_text=req.question,
        answer_text=req.answer,
        source=req.source or "user_edited",
        category=req.category,
        approved=req.approved if req.approved is not None else True,
    )

    # 2. If it corresponds to standard candidate profile fields, update profile as well
    profile_updated = False
    if req.category:
        profile = service.profile
        cat = req.category.lower().strip()
        ans = req.answer.strip()
        if cat == "phone":
            profile.phone = ans
            profile_updated = True
        elif cat == "linkedin_url":
            profile.linkedin_url = ans
            profile_updated = True
        elif cat == "github_url":
            profile.github_url = ans
            profile_updated = True
        elif cat == "portfolio_url":
            profile.portfolio_url = ans
            profile_updated = True
        elif cat == "city":
            profile.city = ans
            profile_updated = True
        elif cat in ("state", "state_province"):
            profile.state_province = ans
            profile_updated = True
        elif cat == "current_title":
            profile.current_title = ans
            profile_updated = True
        elif cat == "current_company":
            profile.current_company = ans
            profile_updated = True
        elif cat in ("years_of_experience", "experience_years"):
            try:
                nums = re.findall(r"\d+(?:\.\d+)?", ans)
                if nums:
                    profile.years_of_experience = float(nums[0])
                    profile_updated = True
            except Exception:
                pass

        if profile_updated:
            db.commit()
            db.refresh(profile)

    return {
        "status": "saved",
        "id": answered_q.id,
        "question": answered_q.question_text,
        "normalized": answered_q.normalized_question,
        "answer": answered_q.answer_text,
        "source": answered_q.source,
        "category": answered_q.category,
        "profile_updated": profile_updated,
        "message": "Answer successfully learned into Answer Bank.",
    }


class SaveAnswersBatchRequest(BaseModel):
    answers: List[SaveAnswerRequest]


@router.post("/save-answers-batch")
async def save_form_answers_batch(
    req: SaveAnswersBatchRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Batch learning for form edits. Learns multiple user-corrected answers
    and updates candidate profile attributes in a single roundtrip.
    """
    service = WorkdayService(db)
    saved_items = []

    for item in req.answers:
        answered_q = service.answer_bank.save_or_update_answer(
            question_text=item.question,
            answer_text=item.answer,
            source=item.source or "user_edited",
            category=item.category,
            approved=item.approved if item.approved is not None else True,
        )
        saved_items.append({
            "id": answered_q.id,
            "question": answered_q.question_text,
            "answer": answered_q.answer_text,
            "category": answered_q.category,
            "source": answered_q.source,
        })

    return {
        "status": "saved",
        "saved_count": len(saved_items),
        "answers": saved_items,
        "message": f"Successfully learned {len(saved_items)} answers into Answer Bank.",
    }


@router.get("/answers")
def list_learned_answers(
    query: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Lists learned & cached questions and answers from the cognitive Answer Bank.
    """
    q = db.query(AnsweredQuestion)
    if category:
        q = q.filter(AnsweredQuestion.category == category)
    if source:
        q = q.filter(AnsweredQuestion.source == source)
    if query:
        search_term = f"%{query.strip().lower()}%"
        q = q.filter(
            (AnsweredQuestion.normalized_question.like(search_term))
            | (AnsweredQuestion.question_text.ilike(search_term))
            | (AnsweredQuestion.answer_text.ilike(search_term))
        )
    total_count = q.count()
    items = q.order_by(AnsweredQuestion.times_used.desc(), AnsweredQuestion.id.desc()).limit(limit).all()

    return {
        "total_count": total_count,
        "answers": [item.to_dict() for item in items],
    }


@router.delete("/answers/{answer_id}")
def delete_learned_answer(
    answer_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Deletes an answer from the Answer Bank.
    """
    entry = db.query(AnsweredQuestion).filter(AnsweredQuestion.id == answer_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Answer not found in Answer Bank.")
    db.delete(entry)
    db.commit()
    return {"status": "deleted", "id": answer_id, "message": "Answer removed from Answer Bank."}


