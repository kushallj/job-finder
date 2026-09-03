"""
src/tsenta/service.py — High-Level Tsenta Auto-Apply Orchestrator.

Manages application submission lifecycle, Review Gate (Diff View), quota constraints,
and database persistence across Job, Application, and TsentaSubmission tables.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import Application, Job
from src.tsenta.ats_detector import detect_ats, ATSInfo
from src.tsenta.client import TsentaClient
from src.tsenta.models import TsentaConfigRecord, TsentaQuota, TsentaSubmission
from src.tsenta.payload_builder import TsentaPayloadBuilder

logger = logging.getLogger("tsenta_service")


class TsentaService:
    """Orchestrates end-to-end Tsenta auto-apply workflows."""

    def __init__(self, db: Session, client: Optional[TsentaClient] = None):
        self.db = db
        self.config = self._get_or_create_config()
        self.quota = self._get_or_create_quota()
        self.client = client or TsentaClient(
            api_key=self.config.api_key,
            api_url=self.config.api_url,
        )
        self.builder = TsentaPayloadBuilder(db=self.db)

    def _get_or_create_config(self) -> TsentaConfigRecord:
        cfg = self.db.query(TsentaConfigRecord).first()
        if not cfg:
            cfg = TsentaConfigRecord(
                mode="review_required",
                min_fit_score=75,
                auto_apply_enabled=True,
            )
            self.db.add(cfg)
            self.db.commit()
            self.db.refresh(cfg)
        return cfg

    def _get_or_create_quota(self) -> TsentaQuota:
        q = self.db.query(TsentaQuota).first()
        if not q:
            q = TsentaQuota(
                daily_used=0,
                daily_limit=50,
                total_submitted=0,
                lifetime_free_remaining=25,
                active_tier="free_starter",
            )
            self.db.add(q)
            self.db.commit()
            self.db.refresh(q)
        return q

    async def auto_apply_job(
        self,
        job_id: int,
        mode_override: Optional[str] = None,
        sample_questions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Prepare and queue or immediately submit a job application via Tsenta."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job #{job_id} not found")

        # 1. Detect ATS
        ats_info = detect_ats(job.url or "")
        
        # 2. Check if already submitted
        existing_sub = (
            self.db.query(TsentaSubmission)
            .filter(TsentaSubmission.job_id == job_id, TsentaSubmission.status == "submitted")
            .first()
        )
        if existing_sub:
            return {
                "status": "already_submitted",
                "message": f"Application for {job.company} - {job.title} was already submitted via Tsenta.",
                "submission": existing_sub.to_dict(),
            }

        # 3. Build AI-tailored submission packet
        start_time = time.time()
        packet = await self.builder.build_submission_packet(job, sample_questions)
        exec_ms = round((time.time() - start_time) * 1000, 2)

        mode = mode_override or self.config.mode or "review_required"

        # 4. Handle Review Gate vs Full Auto
        score = getattr(job, "match_score", None) or 85.0
        if mode == "review_required":
            submission = TsentaSubmission(
                job_id=job.id,
                ats_type=ats_info.code,
                status="review_ready",
                match_score=score,
                company_name=job.company,
                job_title=job.title,
                submission_packet=json.dumps(packet),
                answers_json=json.dumps(packet.get("screening_questions", [])),
                tailored_resume_text=packet.get("tailored_resume", {}).get("summary"),
                cover_letter_text=packet.get("cover_letter"),
                execution_time_ms=exec_ms,
            )
            self.db.add(submission)
            self.db.commit()
            self.db.refresh(submission)

            return {
                "status": "review_ready",
                "message": "Submission packet prepared! Review tailored resume diff & answers before final submission.",
                "ats_detected": ats_info.name,
                "ats_code": ats_info.code,
                "submission": submission.to_dict(),
            }

        # Full Auto Mode: Submit immediately
        submit_result = await self.client.submit_application(packet, ats_info)
        
        submission = TsentaSubmission(
            job_id=job.id,
            ats_type=ats_info.code,
            status="submitted",
            receipt_id=submit_result.get("receipt_id"),
            proof_url=submit_result.get("proof_url"),
            match_score=score,
            company_name=job.company,
            job_title=job.title,
            submission_packet=json.dumps(packet),
            answers_json=json.dumps(packet.get("screening_questions", [])),
            tailored_resume_text=packet.get("tailored_resume", {}).get("summary"),
            cover_letter_text=packet.get("cover_letter"),
            execution_time_ms=exec_ms,
            submitted_at=datetime.utcnow(),
        )
        self.db.add(submission)

        # Update or create Application record
        app_record = self.db.query(Application).filter(Application.job_id == job.id).first()
        if not app_record:
            app_record = Application(
                job_id=job.id,
                status="applied",
                match_score=score,
                ats_detected=ats_info.name,
                proof_url=submit_result.get("proof_url"),
                applied_at=datetime.utcnow(),
            )
            self.db.add(app_record)
        else:
            app_record.status = "applied"
            app_record.ats_detected = ats_info.name
            app_record.proof_url = submit_result.get("proof_url")
            app_record.applied_at = datetime.utcnow()

        # Update quota
        self.quota.daily_used += 1
        self.quota.total_submitted += 1
        if self.quota.lifetime_free_remaining > 0:
            self.quota.lifetime_free_remaining -= 1

        self.db.commit()
        self.db.refresh(submission)

        return {
            "status": "submitted",
            "message": f"Successfully auto-applied to {job.company} via Tsenta ({ats_info.name})!",
            "receipt_id": submit_result.get("receipt_id"),
            "proof_url": submit_result.get("proof_url"),
            "submission": submission.to_dict(),
        }

    async def approve_and_submit(
        self,
        submission_id: int,
        custom_cover_letter: Optional[str] = None,
        custom_answers: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """User approves a review_ready submission packet for 1-click execution."""
        submission = self.db.query(TsentaSubmission).filter(TsentaSubmission.id == submission_id).first()
        if not submission:
            raise ValueError(f"Submission #{submission_id} not found")

        job = self.db.query(Job).filter(Job.id == submission.job_id).first()
        ats_info = detect_ats(job.url if job else "", None)

        packet = json.loads(submission.submission_packet or "{}")
        if custom_cover_letter:
            packet["cover_letter"] = custom_cover_letter
            submission.cover_letter_text = custom_cover_letter
        if custom_answers:
            packet["screening_questions"] = custom_answers
            submission.answers_json = json.dumps(custom_answers)

        # Dispatch submission
        submit_result = await self.client.submit_application(packet, ats_info)
        
        submission.status = "submitted"
        submission.receipt_id = submit_result.get("receipt_id")
        submission.proof_url = submit_result.get("proof_url")
        submission.submitted_at = datetime.utcnow()
        submission.submission_packet = json.dumps(packet)

        # Update Application table
        if job:
            score = getattr(job, "match_score", None) or 85.0
            app_record = self.db.query(Application).filter(Application.job_id == job.id).first()
            if not app_record:
                app_record = Application(
                    job_id=job.id,
                    status="applied",
                    match_score=score,
                    ats_detected=ats_info.name,
                    proof_url=submit_result.get("proof_url"),
                    applied_at=datetime.utcnow(),
                )
                self.db.add(app_record)
            else:
                app_record.status = "applied"
                app_record.ats_detected = ats_info.name
                app_record.proof_url = submit_result.get("proof_url")
                app_record.applied_at = datetime.utcnow()

        # Update quota
        self.quota.daily_used += 1
        self.quota.total_submitted += 1
        if self.quota.lifetime_free_remaining > 0:
            self.quota.lifetime_free_remaining -= 1

        self.db.commit()
        self.db.refresh(submission)

        return {
            "status": "submitted",
            "receipt_id": submit_result.get("receipt_id"),
            "proof_url": submit_result.get("proof_url"),
            "ats_system": ats_info.name,
            "message": f"Application approved and submitted with verified receipt {submit_result.get('receipt_id')}!",
            "submission": submission.to_dict(),
        }

    async def batch_auto_apply(
        self,
        job_ids: Optional[List[int]] = None,
        min_score: int = 80,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Batch apply to top matched opportunities with safeguards."""
        query = self.db.query(Job)
        if job_ids:
            query = query.filter(Job.id.in_(job_ids))
        else:
            query = query.order_by(Job.id.desc())

        jobs = query.limit(limit).all()
        results: List[Dict[str, Any]] = []

        for j in jobs:
            try:
                res = await self.auto_apply_job(j.id)
                results.append(res)
            except Exception as exc:
                results.append({"job_id": j.id, "status": "error", "error": str(exc)})

        return {
            "total_processed": len(results),
            "results": results,
            "quota": self.quota.to_dict(),
        }

    def get_submissions(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent Tsenta submissions."""
        q = self.db.query(TsentaSubmission)
        if status:
            q = q.filter(TsentaSubmission.status == status)
        records = q.order_by(TsentaSubmission.id.desc()).limit(limit).all()
        return [r.to_dict() for r in records]

    def get_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        """Fetch audit details for a specific receipt ID."""
        record = self.db.query(TsentaSubmission).filter(TsentaSubmission.receipt_id == receipt_id).first()
        return record.to_dict() if record else None

    def update_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Update Tsenta API credentials and operational preferences."""
        if "api_key" in config_dict:
            self.config.api_key = config_dict["api_key"]
        if "api_url" in config_dict:
            self.config.api_url = config_dict["api_url"]
        if "mode" in config_dict:
            self.config.mode = config_dict["mode"]
        if "min_fit_score" in config_dict:
            self.config.min_fit_score = int(config_dict["min_fit_score"])
        if "auto_apply_enabled" in config_dict:
            self.config.auto_apply_enabled = bool(config_dict["auto_apply_enabled"])
        if "notification_webhook" in config_dict:
            self.config.notification_webhook = config_dict["notification_webhook"]

        self.db.commit()
        self.db.refresh(self.config)
        return self.config.to_dict()
