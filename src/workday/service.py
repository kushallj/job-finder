"""
src/workday/service.py — High-Level Orchestration Service for Workday Candidate Profile & Auto-Apply.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import Application, Job
from src.answer_bank.service import AnswerBankService
from src.ai.unified_ai_service import UnifiedAIService
from src.workday.client import WorkdayClient
from src.workday.models import (
    WorkdayCandidateProfile,
    WorkdayAccountRecord,
    WorkdayApplicationSubmission,
    WorkdayConfigRecord,
)
from src.workday.resume_tailorer import WorkdayResumeTailorer

logger = logging.getLogger("workday_service")


class WorkdayService:
    """Orchestrates Workday multi-tenant account provisioning, dynamic resume tailoring, and multi-step auto-apply."""

    def __init__(
        self,
        db: Session,
        client: Optional[WorkdayClient] = None,
        tailorer: Optional[WorkdayResumeTailorer] = None,
        ai_service: Optional[UnifiedAIService] = None,
    ):
        self.db = db
        self.client = client or WorkdayClient()
        self.tailorer = tailorer or WorkdayResumeTailorer()
        self.ai_service = ai_service or UnifiedAIService()
        self.answer_bank = AnswerBankService(db=self.db, ai_service=self.ai_service)
        self.config = self._get_or_create_config()
        self.profile = self._get_or_create_candidate_profile()

    def _get_or_create_config(self) -> WorkdayConfigRecord:
        cfg = self.db.query(WorkdayConfigRecord).first()
        today = date.today()
        if not cfg:
            cfg = WorkdayConfigRecord(
                account_email=os.getenv("NEXTRAISE_EMAIL", os.getenv("GMAIL_ADDRESS", "canaby007@gmail.com")),
                auto_apply_enabled=True,
                mode="instant_auto",
                min_fit_score=60.0,
                daily_limit=100,
                daily_used=0,
                total_submitted=0,
                total_failed=0,
                tailor_resumes=True,
                generate_cover_letters=True,
                batch_concurrency=4,
                last_reset_date=today,
            )
            self.db.add(cfg)
            self.db.commit()
            self.db.refresh(cfg)
        elif cfg.last_reset_date != today:
            cfg.daily_used = 0
            cfg.last_reset_date = today
            self.db.commit()
            self.db.refresh(cfg)
        return cfg

    def _get_or_create_candidate_profile(self) -> WorkdayCandidateProfile:
        email = self.config.account_email or "canaby007@gmail.com"
        profile = self.db.query(WorkdayCandidateProfile).filter(WorkdayCandidateProfile.account_email == email).first()
        if not profile:
            profile = WorkdayCandidateProfile(
                account_email=email,
                first_name="Kushall",
                last_name="Jain",
                preferred_name="Kushall",
                phone="+91 9876543210",
                country="India",
                city="Bengaluru",
                state_province="Karnataka",
                postal_code="560100",
                linkedin_url="https://www.linkedin.com/in/kushall-jain",
                github_url="https://github.com/kushallj",
                portfolio_url="https://kushallj.github.io",
                headline="Software Development Engineer – Full Stack Web Development • RESTful APIs • Cloud & IoT Architecture",
                years_of_experience=4.0,
                current_company="Tech Innovations",
                current_title="Senior Software Engineer",
                legally_authorized=True,
                requires_sponsorship=False,
                notice_period_days=30,
                target_salary_min=120000.0,
                target_salary_max=180000.0,
                gender="Male",
                race_ethnicity="Asian",
                veteran_status="I am not a protected veteran",
                disability_status="No, I do not have a disability",
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    async def ensure_tenant_account(
        self,
        tenant_info: Dict[str, str],
        company_name: str,
    ) -> WorkdayAccountRecord:
        """Finds or registers a candidate account for the target company Workday tenant."""
        tenant = tenant_info.get("tenant", "generic")
        site = tenant_info.get("site", "EXT")
        hostname = tenant_info.get("hostname", f"{tenant}.myworkdayjobs.com")
        email = self.profile.account_email

        account = (
            self.db.query(WorkdayAccountRecord)
            .filter(WorkdayAccountRecord.tenant_domain == hostname)
            .first()
        )
        if account:
            return account

        # Generate secure tenant-specific password
        pwd_seed = f"Workday!2026_{tenant}_{email}"
        pwd_hash = hashlib.sha256(pwd_seed.encode()).hexdigest()[:16] + "!Aa1"

        # Register via client
        reg_result = await self.client.register_candidate_account(tenant_info, email, pwd_hash)

        account = WorkdayAccountRecord(
            tenant_domain=hostname,
            career_site_name=site,
            company_name=company_name,
            account_email=email,
            password_hash=hashlib.sha256(pwd_hash.encode()).hexdigest(),
            status="active",
            session_cookies_json=json.dumps(reg_result.get("session_cookies", {})),
            auth_token=reg_result.get("auth_token"),
            last_login_at=datetime.utcnow(),
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        logger.info(f"Provisioned Workday tenant account for {company_name} ({hostname})")
        return account

    async def resolve_screening_questions(
        self,
        job: Job,
        custom_questions: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """Answers Workday screening and compliance questions using AnswerBank & AI."""
        questions = custom_questions or [
            "Are you legally authorized to work in this country?",
            "Will you now or in the future require visa sponsorship?",
            "How many years of relevant software engineering experience do you have?",
            "What is your expected salary range?",
            "What is your standard notice period / availability?",
            "Why are you interested in this role and company?",
        ]

        answers = []
        for q in questions:
            q_lower = q.lower()
            if "authorized" in q_lower or "legally" in q_lower:
                ans = "Yes, I am fully authorized to work."
            elif "sponsorship" in q_lower or "visa" in q_lower:
                ans = "No, I do not require sponsorship."
            elif "years" in q_lower or "experience" in q_lower:
                ans = f"{self.profile.years_of_experience} years of hands-on software development and cloud architecture experience."
            elif "salary" in q_lower or "compensation" in q_lower:
                ans = f"${int(self.profile.target_salary_min):,} - ${int(self.profile.target_salary_max):,} USD depending on total package and equity."
            elif "notice" in q_lower or "start" in q_lower or "availability" in q_lower:
                ans = f"{self.profile.notice_period_days} days notice period."
            else:
                # Answer via AnswerBank / AI
                try:
                    ans_data = await self.answer_bank.get_answer_for_question(
                        question=q,
                        job_title=job.title or "Software Engineer",
                        company=job.company or "Company",
                        job_description=job.description or "",
                    )
                    ans = ans_data.get("answer", "Experienced engineer with a strong track record of scalable delivery.")
                except Exception:
                    ans = f"Excited about {job.company}'s engineering roadmap and applying my {self.profile.years_of_experience} years of software engineering expertise."

            answers.append({"question": q, "answer": ans})

        return answers

    async def auto_apply_job(self, job_id: int) -> Dict[str, Any]:
        """
        Executes complete autonomous 5-step Workday application:
        1. Tenant Discovery & Account Provisioning
        2. Dynamic Resume Tailoring & PDF Building
        3. Screening Q&A Resolution
        4. Multi-Step Form Submission
        5. Proof Receipt Generation & Database Audit Sync
        """
        t0 = time.perf_counter()
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"success": False, "error": f"Job ID {job_id} not found."}

        # Check existing submission
        existing = (
            self.db.query(WorkdayApplicationSubmission)
            .filter(WorkdayApplicationSubmission.job_id == job_id)
            .first()
        )
        if existing and existing.status in ("submitted", "applied"):
            return {
                "success": True,
                "already_applied": True,
                "job_id": job_id,
                "receipt_id": existing.receipt_id,
                "proof_url": existing.proof_url,
                "message": f"Job '{job.title}' at '{job.company}' already submitted via Workday Autopilot.",
            }

        # 1. Parse URL & Tenant Info
        tenant_info = self.client.parse_workday_url(job.url or "")
        company = job.company or tenant_info.get("tenant", "Company").title()

        # 2. Ensure Tenant Account
        account = await self.ensure_tenant_account(tenant_info, company)

        # 3. Dynamically Tailor Resume & Build PDF
        tailored = self.tailorer.tailor_for_job(self.profile, job)

        # 4. Resolve Screening Questions
        answers = await self.resolve_screening_questions(job)

        # 5. Build full submission packet
        packet = {
            "job": {
                "id": job.id,
                "title": job.title,
                "company": company,
                "url": job.url,
                "location": job.location,
            },
            "profile": self.profile.to_dict(),
            "tenant_info": tenant_info,
            "tailored_resume_path": tailored.get("tailored_resume_path"),
            "tailored_resume_text": tailored.get("tailored_resume_text"),
            "cover_letter_text": tailored.get("cover_letter_text"),
            "match_score": tailored.get("ats_match_score", 88.0),
            "answers": answers,
        }

        # 6. Execute Multi-Step Form Submission
        sub_record = existing or WorkdayApplicationSubmission(job_id=job_id, tenant_domain=account.tenant_domain)
        sub_record.company_name = company
        sub_record.job_title = job.title
        sub_record.account_email = self.profile.account_email
        sub_record.tailored_resume_path = tailored.get("tailored_resume_path")
        sub_record.tailored_resume_text = tailored.get("tailored_resume_text")
        sub_record.cover_letter_text = tailored.get("cover_letter_text")
        sub_record.match_score = tailored.get("ats_match_score", 88.0)
        sub_record.answers_json = json.dumps(answers)
        sub_record.submission_packet_json = json.dumps(packet)

        try:
            exec_result = await self.client.execute_multi_step_submission(packet, dry_run=False)
            
            sub_record.status = "submitted"
            sub_record.receipt_id = exec_result.get("receipt_id")
            sub_record.proof_url = exec_result.get("proof_url")
            sub_record.confirmation_number = exec_result.get("confirmation_number")
            sub_record.submitted_at = datetime.utcnow()
            sub_record.execution_time_ms = (time.perf_counter() - t0) * 1000

            # Central Application record sync
            app_rec = self.db.query(Application).filter(Application.job_id == job_id).first()
            if not app_rec:
                app_rec = Application(
                    job_id=job_id,
                    status="applied",
                    applied_at=datetime.utcnow(),
                    ats_detected="workday",
                    match_score=tailored.get("ats_match_score", 88.0),
                    customized_resume_path=tailored.get("tailored_resume_path"),
                    proof_url=sub_record.proof_url,
                )
                self.db.add(app_rec)
            else:
                app_rec.status = "applied"
                app_rec.applied_at = datetime.utcnow()
                app_rec.ats_detected = "workday"
                app_rec.customized_resume_path = tailored.get("tailored_resume_path")
                app_rec.proof_url = sub_record.proof_url

            # Increment quota
            self.config.daily_used += 1
            self.config.total_submitted += 1

            self.db.add(sub_record)
            self.db.commit()
            self.db.refresh(sub_record)

            return {
                "success": True,
                "job_id": job.id,
                "job_title": job.title,
                "company": company,
                "tenant": tenant_info.get("tenant"),
                "tenant_domain": account.tenant_domain,
                "receipt_id": sub_record.receipt_id,
                "proof_url": sub_record.proof_url,
                "confirmation_number": sub_record.confirmation_number,
                "ats_score": tailored.get("ats_match_score"),
                "ats_match_score": tailored.get("ats_match_score"),
                "resume_path": tailored.get("tailored_resume_path"),
                "tailored_resume_path": tailored.get("tailored_resume_path"),
                "answers_count": len(answers),
                "daily_progress": f"{self.config.daily_used}/{self.config.daily_limit}",
            }
        except Exception as e:
            sub_record.status = "failed"
            sub_record.error_detail = str(e)
            self.config.total_failed += 1
            self.db.add(sub_record)
            self.db.commit()
            return {"success": False, "error": str(e), "job_id": job_id}

    async def batch_auto_apply(
        self,
        target_count: int = 50,
        min_score: float = 60.0,
    ) -> Dict[str, Any]:
        """High-Volume Batch Auto-Apply for all unapplied Workday jobs."""
        self._get_or_create_config()
        remaining = max(0, self.config.daily_limit - self.config.daily_used)
        count_to_apply = min(target_count, remaining)

        if count_to_apply <= 0:
            return {
                "status": "quota_reached",
                "message": f"Daily target of {self.config.daily_limit} reached for today ({self.config.daily_used}/{self.config.daily_limit}).",
                "daily_used": self.config.daily_used,
            }

        # Query eligible Workday jobs
        applied_job_ids = {
            s.job_id for s in self.db.query(WorkdayApplicationSubmission.job_id)
            .filter(WorkdayApplicationSubmission.status == "submitted").all()
        }

        # Find Workday jobs by URL or description
        eligible_jobs = (
            self.db.query(Job)
            .filter(
                (Job.url.ilike("%myworkdayjobs.com%") | Job.url.ilike("%workday%")),
                ~Job.id.in_(applied_job_ids) if applied_job_ids else True,
            )
            .limit(count_to_apply)
            .all()
        )

        # Fallback: if specific workday jobs count is low, include general unapplied jobs
        if len(eligible_jobs) < count_to_apply:
            extra_jobs = (
                self.db.query(Job)
                .filter(~Job.id.in_(applied_job_ids) if applied_job_ids else True)
                .order_by(Job.id.desc())
                .limit(count_to_apply - len(eligible_jobs))
                .all()
            )
            eligible_jobs.extend(extra_jobs)

        if not eligible_jobs:
            return {
                "status": "no_jobs_found",
                "message": "No unapplied jobs found in database.",
                "daily_used": self.config.daily_used,
            }

        logger.info(f"🚀 Launching Workday Batch Apply for {len(eligible_jobs)} jobs...")

        concurrency = self.config.batch_concurrency or 4
        sem = asyncio.Semaphore(concurrency)

        async def _apply_with_sem(job_obj):
            async with sem:
                res = await self.auto_apply_job(job_obj.id)
                await asyncio.sleep(0.1)
                return res

        tasks = [_apply_with_sem(j) for j in eligible_jobs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = 0
        failed = 0
        receipts = []
        for r in results:
            if isinstance(r, dict) and r.get("success"):
                successful += 1
                if r.get("receipt_id"):
                    receipts.append(r.get("receipt_id"))
            else:
                failed += 1

        return {
            "status": "completed",
            "account_email": self.profile.account_email,
            "jobs_targeted": len(eligible_jobs),
            "successful_submissions": successful,
            "failed_submissions": failed,
            "daily_progress": f"{self.config.daily_used}/{self.config.daily_limit}",
            "recent_receipts": receipts[:10],
        }

    def get_progress_telemetry(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry, profile, tenant accounts, and submissions."""
        self._get_or_create_config()
        self._get_or_create_candidate_profile()

        recent_submissions = (
            self.db.query(WorkdayApplicationSubmission)
            .order_by(WorkdayApplicationSubmission.id.desc())
            .limit(50)
            .all()
        )
        accounts = (
            self.db.query(WorkdayAccountRecord)
            .order_by(WorkdayAccountRecord.id.desc())
            .limit(50)
            .all()
        )

        return {
            "config": self.config.to_dict(),
            "profile": self.profile.to_dict(),
            "total_accounts_registered": len(accounts),
            "accounts": [a.to_dict() for a in accounts],
            "recent_submissions": [s.to_dict() for s in recent_submissions],
        }
