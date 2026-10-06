#!/usr/bin/env python3
"""
scripts/dispatch_nextraise_daily_volume.py — High-Volume NextRaise Live Auto-Apply Dispatcher.
Dispatches 200–300 applications directly into the user's NextRaise account (canaby007@gmail.com),
registering them in https://nextraise.ai/applications and updating local SQLite database.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.database import db_session
from src.models import Job, Application
from src.nextraise.client import NextRaiseClient
from src.nextraise.models import NextRaiseSubmission, NextRaiseQuota, NextRaiseConfigRecord
from src.tsenta.ats_detector import detect_ats


async def run_high_volume_dispatch(target_count: int = 250, concurrency: int = 8):
    print("=" * 70)
    print("  🚀 NEXTRAISE HIGH-VOLUME LIVE APPLICATION DISPATCHER (200-300 DAILY)")
    print("=" * 70)

    session_token = os.getenv("NEXTRAISE_SESSION_TOKEN")
    account_email = os.getenv("NEXTRAISE_EMAIL", "canaby007@gmail.com")

    if not session_token:
        print("❌ Error: NEXTRAISE_SESSION_TOKEN not found in environment.")
        return

    client = NextRaiseClient(
        account_email=account_email,
        session_token=session_token,
        api_url="https://nextraise.ai",
    )

    # 1. Verify session
    sess_check = await client.validate_live_session()
    print(f"🔐 NextRaise Session Validation: {sess_check}")
    if not sess_check.get("connected"):
        print("❌ Live session invalid or expired on nextraise.ai")
        return

    # 2. Get jobs
    with db_session() as db:
        all_jobs = db.query(Job).order_by(Job.id.desc()).all()
        candidate_jobs = []
        for j in all_jobs:
            if not j.title or not j.company:
                continue
            candidate_jobs.append(j)
            if len(candidate_jobs) >= target_count:
                break

    print(f"📋 Candidate Jobs to Dispatch: {len(candidate_jobs)}")

    sem = asyncio.Semaphore(concurrency)
    success_count = 0
    fail_count = 0
    dispatched_receipts = []

    async def _dispatch_single_job(job_obj):
        nonlocal success_count, fail_count
        async with sem:
            ats = detect_ats(job_obj.url or "", job_obj.description or "")
            packet = {
                "job": {
                    "id": job_obj.id,
                    "title": job_obj.title,
                    "company": job_obj.company,
                    "url": job_obj.url or f"https://nextraise.ai/jobs/{job_obj.id}",
                    "description": job_obj.description or f"Role: {job_obj.title} at {job_obj.company}",
                    "location": job_obj.location or "Remote",
                },
                "match_score": getattr(job_obj, "match_score", 88) or 88,
            }
            try:
                res = await client.submit_application(packet, ats, dry_run=False)
                if res.get("success"):
                    success_count += 1
                    receipt = res.get("receipt_id")
                    dispatched_receipts.append(receipt)
                    print(f"  [✓] Applied #{success_count}: {job_obj.title[:35]} @ {job_obj.company[:20]} | Receipt: {receipt}")
                else:
                    fail_count += 1
                    print(f"  [✗] Failed: {job_obj.title} @ {job_obj.company}")
            except Exception as e:
                fail_count += 1
                print(f"  [✗] Error on job {job_obj.id}: {e}")
            await asyncio.sleep(0.12)

    t0 = time.time()
    tasks = [_dispatch_single_job(j) for j in candidate_jobs]
    await asyncio.gather(*tasks)
    elapsed = time.time() - t0

    # 3. Update database quota & telemetry
    with db_session() as db:
        quota = db.query(NextRaiseQuota).first()
        if quota:
            quota.daily_used = min(quota.daily_limit, quota.daily_used + success_count)
            quota.total_submitted += success_count
            db.commit()

    print("\n" + "=" * 70)
    print(f"  🎉 BATCH DISPATCH COMPLETED IN {elapsed:.1f}s")
    print(f"  • Account: {account_email}")
    print(f"  • Successful Live Applications: {success_count}")
    print(f"  • Failed Applications: {fail_count}")
    print(f"  • Total Submissions Recorded: {len(dispatched_receipts)}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 230
    asyncio.run(run_high_volume_dispatch(target_count=count, concurrency=8))
