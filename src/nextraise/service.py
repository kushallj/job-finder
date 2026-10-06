"""
src/nextraise/service.py — High-Volume NextRaise Auto-Apply & Daily Quota Orchestrator.
Applies to 200–300 jobs daily across Workday, Greenhouse, Lever, Ashby, BambooHR, and Custom ATS portals.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.orm import Session

from src.models import Application, Job
from src.tsenta.ats_detector import detect_ats, ATSInfo
from src.nextraise.client import NextRaiseClient
from src.nextraise.models import NextRaiseConfigRecord, NextRaiseQuota, NextRaiseSubmission
from src.nextraise.payload_builder import NextRaisePayloadBuilder

logger = logging.getLogger("nextraise_service")


class NextRaiseService:
    """Orchestrates high-throughput automated job applications (200-300 daily target) via NextRaise."""

    def __init__(self, db: Session, client: Optional[NextRaiseClient] = None):
        self.db = db
        self.config = self._get_or_create_config()
        self.quota = self._get_or_create_quota()
        session_token = self.config.session_token or os.getenv("NEXTRAISE_SESSION_TOKEN")
        oauth_token = self.config.oauth_access_token or os.getenv("NEXTRAISE_OAUTH_TOKEN")
        api_url = self.config.api_url or os.getenv("NEXTRAISE_API_URL", "https://nextraise.ai")
        self.client = client or NextRaiseClient(
            account_email=self.config.account_email or "canaby007@gmail.com",
            oauth_token=oauth_token,
            session_token=session_token,
            widget_session_id=session_token,
            api_url=api_url,
        )
        self.builder = NextRaisePayloadBuilder(db=self.db)

    def _get_or_create_config(self) -> NextRaiseConfigRecord:
        cfg = self.db.query(NextRaiseConfigRecord).first()
        env_token = os.getenv("NEXTRAISE_SESSION_TOKEN")
        if not cfg:
            cfg = NextRaiseConfigRecord(
                account_email="canaby007@gmail.com",
                oauth_connected=True,
                session_token=env_token,
                oauth_access_token=env_token,
                mode="instant_auto",
                daily_target=300,
                min_fit_score=60.0,
                auto_batch_enabled=True,
                batch_concurrency=5,
                api_url="https://nextraise.ai",
            )
            self.db.add(cfg)
            self.db.commit()
            self.db.refresh(cfg)
        elif not cfg.session_token and env_token:
            cfg.session_token = env_token
            cfg.oauth_access_token = env_token
            cfg.api_url = "https://nextraise.ai"
            self.db.commit()
            self.db.refresh(cfg)
        return cfg

    def _get_or_create_quota(self) -> NextRaiseQuota:
        q = self.db.query(NextRaiseQuota).first()
        today = date.today()
        if not q:
            q = NextRaiseQuota(
                daily_used=0,
                daily_limit=300,
                total_submitted=0,
                total_failed=0,
                active_tier="nextraise_pro_unlimited",
                last_reset_date=today,
            )
            self.db.add(q)
            self.db.commit()
            self.db.refresh(q)
        elif q.last_reset_date != today:
            # Auto-reset daily quota for a new day
            q.daily_used = 0
            q.last_reset_date = today
            self.db.commit()
            self.db.refresh(q)
        return q

    async def auto_apply_job(
        self,
        job_id: int,
        mode_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Applies to a single job via NextRaise, updating Job, Application, and NextRaiseSubmission."""
        t0 = time.perf_counter()
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"success": False, "error": f"Job ID {job_id} not found."}

        ats_info = detect_ats(job.url or "", job.description or "")
        mode = mode_override or self.config.mode

        # Check existing submission
        existing = (
            self.db.query(NextRaiseSubmission)
            .filter(NextRaiseSubmission.job_id == job_id)
            .first()
        )
        if existing and existing.status in ("applied", "submitted"):
            return {
                "success": True,
                "already_applied": True,
                "receipt_id": existing.receipt_id,
                "proof_url": existing.proof_url,
                "message": f"Job '{job.title}' already submitted via NextRaise.",
            }

        # Build application packet
        packet = self.builder.build_packet(job, ats_info, self.config.account_email)

        # Create or update NextRaise submission record
        sub = existing or NextRaiseSubmission(job_id=job_id)
        sub.ats_type = ats_info.code
        sub.company_name = job.company
        sub.job_title = job.title
        sub.account_email = self.config.account_email
        sub.submission_packet = json.dumps(packet)
        sub.answers_json = json.dumps(packet.get("answers", []))
        sub.tailored_resume_text = packet.get("tailored_resume_text")
        sub.cover_letter_text = packet.get("cover_letter_text")

        # Execute submission
        try:
            result = await self.client.submit_application(packet, ats_info, dry_run=False)
            sub.status = "applied" if result.get("success") else "failed"
            sub.receipt_id = result.get("receipt_id")
            sub.proof_url = result.get("proof_url")
            sub.submitted_at = datetime.now(timezone.utc)
            sub.execution_time_ms = (time.perf_counter() - t0) * 1000

            # Update or create Application record
            app_rec = self.db.query(Application).filter(Application.job_id == job_id).first()
            if not app_rec:
                app_rec = Application(
                    job_id=job_id,
                    status="applied",
                    applied_at=datetime.utcnow(),
                    ats_detected=ats_info.code,
                    match_score=getattr(job, "match_score", 85.0) or 85.0,
                )
                self.db.add(app_rec)
            else:
                app_rec.status = "applied"
                app_rec.applied_at = datetime.utcnow()
                app_rec.ats_detected = ats_info.code

            # Update daily quota
            self.quota.daily_used += 1
            self.quota.total_submitted += 1

            self.db.add(sub)
            self.db.commit()
            self.db.refresh(sub)

            return {
                "success": True,
                "job_id": job_id,
                "job_title": job.title,
                "company": job.company,
                "ats_type": ats_info.code,
                "receipt_id": sub.receipt_id,
                "proof_url": sub.proof_url,
                "daily_progress": f"{self.quota.daily_used}/{self.quota.daily_limit}",
            }
        except Exception as exc:
            sub.status = "failed"
            sub.error_detail = str(exc)
            self.quota.total_failed += 1
            self.db.add(sub)
            self.db.commit()
            return {"success": False, "error": str(exc), "job_id": job_id}

    async def batch_auto_apply(
        self,
        target_count: int = 250,
        min_score: float = 50.0,
    ) -> Dict[str, Any]:
        """
        High-Volume Batch Auto-Apply: Dispatches 200–300 applications in automated batches.
        """
        self._get_or_create_quota()
        remaining_today = max(0, self.quota.daily_limit - self.quota.daily_used)
        count_to_apply = min(target_count, remaining_today)

        if count_to_apply <= 0:
            return {
                "status": "quota_reached",
                "message": f"Daily target of {self.quota.daily_limit} applications reached for today ({self.quota.daily_used}/{self.quota.daily_limit}).",
                "daily_used": self.quota.daily_used,
                "daily_limit": self.quota.daily_limit,
            }

        # Query eligible unapplied jobs
        applied_job_ids = {
            s.job_id for s in self.db.query(NextRaiseSubmission.job_id)
            .filter(NextRaiseSubmission.status == "applied").all()
        }

        eligible_jobs = (
            self.db.query(Job)
            .filter(~Job.id.in_(applied_job_ids) if applied_job_ids else True)
            .order_by(Job.id.desc())
            .limit(count_to_apply)
            .all()
        )

        if not eligible_jobs:
            return {
                "status": "no_jobs_found",
                "message": "No new unapplied jobs found in database. Run job crawler sweep first.",
                "daily_used": self.quota.daily_used,
            }

        logger.info(f"🚀 Launching NextRaise high-volume batch apply for {len(eligible_jobs)} jobs for {self.config.account_email}...")

        results = []
        concurrency = self.config.batch_concurrency or 5
        sem = asyncio.Semaphore(concurrency)

        async def _apply_with_sem(job_obj):
            async with sem:
                res = await self.auto_apply_job(job_obj.id)
                await asyncio.sleep(0.2)  # Gentle rate spacing
                return res

        tasks = [_apply_with_sem(j) for j in eligible_jobs]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = 0
        failed = 0
        for r in batch_results:
            if isinstance(r, dict) and r.get("success"):
                successful += 1
                results.append(r)
            else:
                failed += 1

        return {
            "status": "completed",
            "account_email": self.config.account_email,
            "jobs_targeted": len(eligible_jobs),
            "successful_submissions": successful,
            "failed_submissions": failed,
            "daily_progress": f"{self.quota.daily_used}/{self.quota.daily_limit}",
            "daily_percent": round((self.quota.daily_used / max(1, self.quota.daily_limit)) * 100, 1),
            "recent_receipts": [r.get("receipt_id") for r in results[:10]],
        }

    def get_progress_telemetry(self) -> Dict[str, Any]:
        """Returns comprehensive quota, telemetry, and submission audit for the dashboard."""
        self._get_or_create_quota()
        recent_subs = (
            self.db.query(NextRaiseSubmission)
            .order_by(NextRaiseSubmission.id.desc())
            .limit(50)
            .all()
        )

        return {
            "account": self.config.to_dict(),
            "quota": self.quota.to_dict(),
            "recent_submissions": [s.to_dict() for s in recent_subs],
        }
