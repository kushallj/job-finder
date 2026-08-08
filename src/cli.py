"""
cli.py — NEXUS command-line interface.

Usage:
    python -m src.cli <command> [args]

Commands:
    tracker                     Regenerate data/applications.md
    status <app_id> <Status>    Update an application's status
    scan <query>                Fetch new jobs for a search query
    firecrawl-scan               Scrape top Indian startup career pages → DB + Sheet + outreach
    process-async <query>       Process jobs using async pipeline (NEW)
    pipeline                    List pending entries in data/pipeline.md
    verify                      DB health check (orphans, nulls, integrity)
    dedup                       Remove duplicate job entries
    normalize                   Fix non-canonical status values in DB
    digest                      Print weekly outreach digest

Run `python -m src.cli help` to see this message.
"""

import argparse
import asyncio
import json
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# ---------------------------------------------------------------------------
# Lazy imports — only pull heavy deps when needed
# ---------------------------------------------------------------------------

def _db():
    from src.database import SessionLocal
    return SessionLocal()

TRACKER_PATH   = Path("data/applications.md")
PIPELINE_PATH  = Path("data/pipeline.md")
QUEUE_PATH     = Path("data/outreach_queue.json")

CANONICAL_STATUSES_DB = {
    "pending", "ready", "applied", "interview", "offer", "rejected", "skip", "skipped"
}

# ---------------------------------------------------------------------------
# tracker
# ---------------------------------------------------------------------------

def cmd_tracker(_args):
    """Regenerate data/applications.md from DB."""
    from src.tracker import generate
    content = generate()
    row_count = content.count("\n| ") - 2
    print(f"Tracker written → {TRACKER_PATH}  ({max(row_count, 0)} applications)")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status(args):
    """Update an application's status."""
    from src.tracker import generate, update_status
    try:
        app_id = int(args.app_id)
    except ValueError:
        print(f"ERROR: app_id must be an integer, got: {args.app_id}", file=sys.stderr)
        sys.exit(1)
    try:
        update_status(app_id, args.status)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    generate()
    print(f"Tracker regenerated → {TRACKER_PATH}")


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------

def cmd_scan(args):
    """Fetch new jobs from all scrapers for a query."""
    query = args.query or "software engineer"

    async def _run():
        from src.job_processor import JobProcessor, ProcessorConfig
        cfg = ProcessorConfig(auto_send_emails=False)
        processor = JobProcessor(config=cfg)
        try:
            stored = await processor.fetch_and_store_jobs(query=query)
            print(f"Fetched and stored {stored} new jobs for: '{query}'")
            print("Run `python -m src.cli tracker` to regenerate the tracker.")
        finally:
            await processor.close()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# firecrawl-scan
# ---------------------------------------------------------------------------

def cmd_firecrawl_scan(args):
    """Scrape top Indian startup career pages via Firecrawl, store + outreach."""
    import argparse as _argparse

    from firecrawl_startup_pipeline import run as _pipeline_run

    pipeline_args = _argparse.Namespace(
        query=args.query or "",
        send=args.send,
        max_companies=args.max_companies or 0,
        max_contacts=args.max_contacts or 2,
    )
    asyncio.run(_pipeline_run(pipeline_args))


# ---------------------------------------------------------------------------
# process-async (new async pipeline command)
# ---------------------------------------------------------------------------

def cmd_process_async(args):
    """
    Process jobs using the new async pipeline.
    
    This uses the fully async pipeline with:
    - O(1) memory usage via streaming
    - Concurrent processing with worker pool
    - Automatic retry with exponential backoff
    - Rate limiting for external APIs
    """
    query = args.query or "software engineer"
    resume_path = args.resume or "data/resume.txt"
    
    if not Path(resume_path).exists():
        print(f"ERROR: Resume file not found: {resume_path}", file=sys.stderr)
        print("Create a resume file or specify --resume path", file=sys.stderr)
        sys.exit(1)
    
    resume_text = Path(resume_path).read_text(encoding="utf-8")
    
    async def _run():
        try:
            from src.async_pipeline import AsyncJobPipeline, ProcessorConfig
            from src.async_pipeline.processor import AsyncJobProcessor
            
            # Configure pipeline
            config = ProcessorConfig(
                worker_count=args.workers or 5,
                queue_size=args.queue_size or 100,
                max_concurrent_api_calls=args.max_concurrent or 3,
                llm_rate_limit=args.llm_rate or 10,
                email_rate_limit=args.email_rate or 2,
                scraper_rate_limit=args.scraper_rate or 30,
                log_level=args.log_level or "INFO",
                min_score=args.min_score or 50,
            )
            
            # Create pipeline
            pipeline = AsyncJobPipeline(config=config)
            
            # Create and set processor
            processor = AsyncJobProcessor(
                config=config,
                resume_text=resume_text,
            )
            pipeline.set_processor(processor.process_job)
            
            print(f"\nStarting async pipeline for: '{query}'")
            print(f"  Workers: {config.worker_count}")
            print(f"  Queue size: {config.queue_size}")
            print(f"  Min score: {config.min_score}")
            print(f"  Resume: {resume_path}\n")
            
            # Run pipeline
            import time
            start_time = time.monotonic()
            
            results = await pipeline.run(
                query=query,
                resume_text=resume_text,
                filters={"min_score": config.min_score},
            )
            
            elapsed = time.monotonic() - start_time
            
            # Report results
            completed = sum(1 for r in results if r.status.value == "completed")
            failed = sum(1 for r in results if r.status.value == "failed")
            
            print(f"\n{'='*60}")
            print(f"Pipeline Complete")
            print(f"{'='*60}")
            print(f"  Total jobs: {len(results)}")
            print(f"  Completed: {completed}")
            print(f"  Failed: {failed}")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Throughput: {len(results)/elapsed:.2f} jobs/sec")
            print(f"{'='*60}\n")
            
            # Show metrics if available
            if pipeline.metrics_collector:
                print("Metrics:")
                pipeline.log_metrics_summary()
            
            # Cleanup
            await pipeline.close()
            
            print("\nRun `python -m src.cli tracker` to regenerate the tracker.")
            
        except ImportError as e:
            print(f"ERROR: Async pipeline not available: {e}", file=sys.stderr)
            print("Install required dependencies: pip install aiosqlite httpx", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Pipeline execution failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    asyncio.run(_run())


# ---------------------------------------------------------------------------
# pipeline
# ---------------------------------------------------------------------------

def cmd_pipeline(_args):
    """Show pending entries in data/pipeline.md."""
    if not PIPELINE_PATH.exists():
        print(f"Pipeline file not found: {PIPELINE_PATH}")
        print("Create data/pipeline.md and add job URLs to the Pending table.")
        return

    content = PIPELINE_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()

    pending = []
    in_pending = False
    for line in lines:
        if line.strip().startswith("## Pending"):
            in_pending = True
            continue
        if line.strip().startswith("## ") and in_pending:
            break
        if in_pending and line.startswith("|") and "---" not in line and "Company" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2 and parts[0].lower() != "_example_":
                pending.append(parts)

    if not pending:
        print("No pending jobs in data/pipeline.md")
        print(f"Add rows to the Pending table in {PIPELINE_PATH} then run /nexus pipeline")
        return

    print(f"\n{len(pending)} pending job(s) in pipeline:\n")
    for i, row in enumerate(pending, 1):
        company = row[0] if len(row) > 0 else "?"
        url = row[1] if len(row) > 1 else "?"
        notes = row[2] if len(row) > 2 else ""
        print(f"  {i}. {company}")
        print(f"     {url}")
        if notes:
            print(f"     Notes: {notes}")
    print()
    print("Run `/nexus pipeline` in Claude Code to evaluate all pending entries.")


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def cmd_verify(_args):
    """DB health check — orphaned records, null fields, status integrity."""
    from src.models import Application, Job, OutreachRecord

    db = _db()
    issues = []
    ok = []

    try:
        # 1. Total counts
        total_jobs = db.query(Job).count()
        total_apps = db.query(Application).count()
        total_outreach = db.query(OutreachRecord).count()
        print(f"\nDB Summary")
        print(f"  Jobs:     {total_jobs}")
        print(f"  Apps:     {total_apps}")
        print(f"  Outreach: {total_outreach}\n")

        # 2. Jobs with no application (unprocessed)
        from sqlalchemy.orm import aliased
        unprocessed = (
            db.query(Job)
            .outerjoin(Application, Application.job_id == Job.id)
            .filter(Application.id == None)
            .count()
        )
        if unprocessed > 0:
            issues.append(f"{unprocessed} jobs have no application record (unprocessed)")
        else:
            ok.append("All jobs have application records")

        # 3. Applications with null match_score
        null_scores = db.query(Application).filter(Application.match_score == None).count()
        if null_scores > 0:
            issues.append(f"{null_scores} applications have null match_score")
        else:
            ok.append("All applications have match scores")

        # 4. Jobs with null title or company
        bad_jobs = (
            db.query(Job)
            .filter((Job.title == None) | (Job.company == None))
            .count()
        )
        if bad_jobs > 0:
            issues.append(f"{bad_jobs} jobs have null title or company")
        else:
            ok.append("All jobs have title and company")

        # 5. Non-canonical statuses
        all_statuses = [r[0] for r in db.query(Application.status).all()]
        bad_statuses = [s for s in all_statuses if s and s.lower() not in CANONICAL_STATUSES_DB]
        if bad_statuses:
            unique_bad = set(bad_statuses)
            issues.append(f"{len(bad_statuses)} applications have non-canonical statuses: {unique_bad}")
            issues.append("  → Fix with: python -m src.cli normalize")
        else:
            ok.append("All application statuses are canonical")

        # 6. Outreach records with no job
        orphan_outreach = (
            db.query(OutreachRecord)
            .outerjoin(Job, Job.id == OutreachRecord.job_id)
            .filter(Job.id == None)
            .count()
        )
        if orphan_outreach > 0:
            issues.append(f"{orphan_outreach} outreach records reference deleted jobs")
        else:
            ok.append("All outreach records reference valid jobs")

        # 7. Duplicate job_ids
        from sqlalchemy import func
        dup_job_ids = (
            db.query(Job.job_id, func.count(Job.job_id).label("cnt"))
            .group_by(Job.job_id)
            .having(func.count(Job.job_id) > 1)
            .count()
        )
        if dup_job_ids > 0:
            issues.append(f"{dup_job_ids} duplicate job_id groups found")
            issues.append("  → Fix with: python -m src.cli dedup")
        else:
            ok.append("No duplicate job_ids")

    finally:
        db.close()

    print("Health Check Results")
    print("=" * 40)
    for msg in ok:
        print(f"  OK   {msg}")
    for msg in issues:
        print(f"  WARN {msg}")
    print()
    if issues:
        print(f"{len(issues)} issue(s) found. See WARN lines above.")
        sys.exit(1)
    else:
        print("All checks passed.")


# ---------------------------------------------------------------------------
# dedup
# ---------------------------------------------------------------------------

def cmd_dedup(_args):
    """Remove duplicate job entries (same title + company), keep newest."""
    from sqlalchemy import func
    from src.models import Application, Job, OutreachRecord

    db = _db()
    removed = 0

    try:
        # Find groups with duplicate (title, company)
        dup_groups = (
            db.query(Job.title, Job.company, func.count(Job.id).label("cnt"))
            .group_by(Job.title, Job.company)
            .having(func.count(Job.id) > 1)
            .all()
        )

        if not dup_groups:
            print("No duplicates found.")
            return

        print(f"Found {len(dup_groups)} duplicate group(s). Removing older entries...\n")

        for title, company, cnt in dup_groups:
            dupes = (
                db.query(Job)
                .filter(Job.title == title, Job.company == company)
                .order_by(Job.id.desc())
                .all()
            )
            # Keep the newest (first after desc sort), delete the rest
            to_delete = dupes[1:]
            for job in to_delete:
                # Delete related records first (FK constraint)
                db.query(Application).filter(Application.job_id == job.id).delete()
                db.query(OutreachRecord).filter(OutreachRecord.job_id == job.id).delete()
                db.delete(job)
                removed += 1
                print(f"  Removed: [{job.id}] {company} — {title}")

        db.commit()
        print(f"\nRemoved {removed} duplicate job(s).")
        print("Regenerating tracker...")

    finally:
        db.close()

    from src.tracker import generate
    generate()
    print(f"Tracker updated → {TRACKER_PATH}")


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------

def cmd_normalize(_args):
    """Standardize non-canonical status values in Application table."""
    from src.models import Application

    # Map known variants → canonical DB value
    STATUS_ALIASES = {
        "new":         "pending",
        "evaluating":  "pending",
        "evaluated":   "ready",
        "outreach":    "ready",
        "replied":     "applied",
        "responded":   "applied",
        "interviewing":"interview",
        "hired":       "offer",
        "declined":    "rejected",
        "discarded":   "skip",
        "no apply":    "skip",
        "skip":        "skip",
        "skipped":     "skip",
    }

    db = _db()
    fixed = 0

    try:
        apps = db.query(Application).all()
        for app in apps:
            raw = (app.status or "").lower().strip()
            if raw in CANONICAL_STATUSES_DB:
                continue
            canonical = STATUS_ALIASES.get(raw)
            if canonical:
                print(f"  App {app.id}: '{app.status}' → '{canonical}'")
                app.status = canonical
                app.updated_at = datetime.utcnow()
                fixed += 1
            else:
                print(f"  UNKNOWN status App {app.id}: '{app.status}' — setting to 'pending'")
                app.status = "pending"
                app.updated_at = datetime.utcnow()
                fixed += 1

        if fixed:
            db.commit()
            print(f"\nNormalized {fixed} status value(s).")
            print("Regenerating tracker...")
            from src.tracker import generate
            generate()
            print(f"Tracker updated → {TRACKER_PATH}")
        else:
            print("All statuses are already canonical. Nothing to do.")

    finally:
        db.close()


# ---------------------------------------------------------------------------
# digest
# ---------------------------------------------------------------------------

def cmd_drafts(args):
    """Show pending outreach drafts saved by the pipeline."""
    import json

    if not QUEUE_PATH.exists():
        print("No drafts yet. Run the pipeline first: bash scripts/nexus_cron.sh")
        return

    queue = json.loads(QUEUE_PATH.read_text())
    status_filter = getattr(args, "status", "pending")
    shown = [d for d in queue if d["status"] == status_filter]

    if not shown:
        all_statuses = set(d["status"] for d in queue)
        print(f"No '{status_filter}' drafts. Statuses in queue: {all_statuses}")
        return

    print(f"\n{'='*60}")
    print(f"Outreach Drafts — {status_filter.upper()}  ({len(shown)} of {len(queue)} total)")
    print(f"{'='*60}\n")

    for d in shown:
        score_bar = "█" * int(d["personalization_score"] / 10)
        print(f"ID: {d['id']}  |  {d['company']}  |  Score: {d['personalization_score']:.0f}/100 {score_bar}")
        print(f"To: {d['contact_name']} <{d['contact_email'] or 'email TBD'}>")
        print(f"Subject: {d['subject']}")
        print(f"Created: {d['created_at'][:16]}")
        print()
        print(d["body"])
        if d.get("subject_variants") and len(d["subject_variants"]) > 1:
            print(f"\nAlt subjects:")
            for i, s in enumerate(d["subject_variants"][1:], 2):
                print(f"  [{i}] {s}")
        print(f"\n{'─'*60}\n")

    print(f"To send a draft:  python -m src.cli send <id>")
    print(f"To skip a draft:  python -m src.cli skip <id>")
    print(f"To see sent:      python -m src.cli drafts --status sent\n")


def cmd_send(args):
    """Approve and send a specific draft by ID."""
    import json, asyncio

    if not QUEUE_PATH.exists():
        print("No draft queue found.", file=sys.stderr)
        sys.exit(1)

    queue = json.loads(QUEUE_PATH.read_text())
    draft = next((d for d in queue if d["id"] == args.draft_id), None)

    if not draft:
        print(f"Draft '{args.draft_id}' not found.", file=sys.stderr)
        print(f"Available IDs: {[d['id'] for d in queue if d['status'] == 'pending']}")
        sys.exit(1)

    if draft["status"] != "pending":
        print(f"Draft '{args.draft_id}' is already '{draft['status']}' — nothing to do.")
        return

    # Show what will be sent and ask for confirmation
    print(f"\nAbout to send:")
    print(f"  To:      {draft['contact_name']} <{draft['contact_email'] or 'NO EMAIL — will skip'}>")
    print(f"  Company: {draft['company']}")
    print(f"  Subject: {draft['subject']}")
    print(f"\n{draft['body']}\n")

    if not draft.get("contact_email"):
        print("WARNING: No email address found for this contact. Marking as skipped.")
        draft["status"] = "skipped"
        QUEUE_PATH.write_text(json.dumps(queue, indent=2))
        return

    confirm = input("Send? [y/N] ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    # Send via email outreach
    async def _send():
        try:
            from src.email_outreach import EmailOutreach
            from src.contact_finder import Contact

            outreach = EmailOutreach()
            contact  = Contact(
                name             = draft["contact_name"],
                email            = draft["contact_email"],
                title            = "",
                company          = draft["company"],
                confidence_score = int(draft["personalization_score"]),
            )

            class _JobStub:
                title   = draft.get("subject", "")
                company = draft["company"]
                url     = ""
                id      = 0

            success = await outreach.send_outreach_email(contact, _JobStub())
            return success
        except Exception as e:
            print(f"Send error: {e}", file=sys.stderr)
            return False

    success = asyncio.run(_send())

    # Update queue
    from datetime import datetime
    draft["status"]  = "sent" if success else "failed"
    draft["sent_at"] = datetime.utcnow().isoformat()
    QUEUE_PATH.write_text(json.dumps(queue, indent=2))

    if success:
        print(f"✅ Sent to {draft['contact_name']} at {draft['company']}")
    else:
        print(f"❌ Send failed — check logs. Draft marked 'failed'.")


def cmd_skip(args):
    """Mark a draft as skipped without sending."""
    import json

    if not QUEUE_PATH.exists():
        print("No draft queue found.", file=sys.stderr)
        sys.exit(1)

    queue = json.loads(QUEUE_PATH.read_text())
    draft = next((d for d in queue if d["id"] == args.draft_id), None)

    if not draft:
        print(f"Draft '{args.draft_id}' not found.", file=sys.stderr)
        sys.exit(1)

    draft["status"] = "skipped"
    QUEUE_PATH.write_text(json.dumps(queue, indent=2))
    print(f"Skipped draft {args.draft_id} ({draft['company']})")


def cmd_digest(_args):
    """Print the weekly NEXUS outreach digest."""
    try:
        from src.feedback.feedback_loop import FeedbackLoop
        loop = FeedbackLoop()
        snapshot = loop.run_weekly_analysis()
        print(snapshot.digest_markdown)
    except Exception as e:
        print(f"ERROR generating digest: {e}", file=sys.stderr)
        print("Make sure the feedback loop DB has data (run the pipeline first).")
        sys.exit(1)


# ---------------------------------------------------------------------------
# help
# ---------------------------------------------------------------------------

def cmd_help(_args):
    print(__doc__)


# ---------------------------------------------------------------------------
# CLI router
# ---------------------------------------------------------------------------

COMMANDS = {
    "tracker":   cmd_tracker,
    "status":    cmd_status,
    "scan":      cmd_scan,
    "process-async": cmd_process_async,
    "pipeline":  cmd_pipeline,
    "verify":    cmd_verify,
    "dedup":     cmd_dedup,
    "normalize": cmd_normalize,
    "digest":    cmd_digest,
    "firecrawl-scan": cmd_firecrawl_scan,
    "drafts":    cmd_drafts,
    "send":      cmd_send,
    "skip":      cmd_skip,
    "help":      cmd_help,
}


def main():
    parser = argparse.ArgumentParser(
        prog="python -m src.cli",
        description="NEXUS CLI — job acquisition pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(f"  {k}" for k in COMMANDS),
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("tracker", help="Regenerate data/applications.md")
    subparsers.add_parser("verify",  help="DB health check")
    subparsers.add_parser("dedup",   help="Remove duplicate job entries")
    subparsers.add_parser("normalize", help="Fix non-canonical status values")
    subparsers.add_parser("digest",  help="Print weekly outreach digest")
    subparsers.add_parser("pipeline", help="Show pending pipeline.md entries")
    subparsers.add_parser("help",    help="Show help")

    p_drafts = subparsers.add_parser("drafts", help="Show outreach drafts pending review")
    p_drafts.add_argument("--status", default="pending",
                          choices=["pending", "sent", "skipped", "failed"],
                          help="Filter by status (default: pending)")

    p_send = subparsers.add_parser("send", help="Send an approved draft by ID")
    p_send.add_argument("draft_id", help="Draft ID (from `drafts` command)")

    p_skip = subparsers.add_parser("skip", help="Skip a draft without sending")
    p_skip.add_argument("draft_id", help="Draft ID (from `drafts` command)")

    p_status = subparsers.add_parser("status", help="Update application status")
    p_status.add_argument("app_id", help="Application ID (from App ID column)")
    p_status.add_argument("status", help="New status")

    p_scan = subparsers.add_parser("scan", help="Fetch new jobs for a query")
    p_scan.add_argument("query", nargs="?", default="software engineer",
                        help='Search query (default: "software engineer")')

    p_firecrawl = subparsers.add_parser(
        "firecrawl-scan",
        help="Scrape top Indian startup career pages (Firecrawl) → DB + Sheet + outreach",
    )
    p_firecrawl.add_argument("--query", default="", help="Filter jobs by title keyword")
    p_firecrawl.add_argument("--send", action="store_true",
                             help="Actually send outreach emails (default: dry run)")
    p_firecrawl.add_argument("--max-companies", type=int, default=0,
                             help="Limit number of companies scanned (0 = all ~100)")
    p_firecrawl.add_argument("--max-contacts", type=int, default=2,
                             help="Max contacts to find per company (default: 2)")

    p_process_async = subparsers.add_parser("process-async", 
                                             help="Process jobs using async pipeline")
    p_process_async.add_argument("query", nargs="?", default="software engineer",
                                 help='Search query (default: "software engineer")')
    p_process_async.add_argument("--resume", default="data/resume.txt",
                                 help="Path to resume file (default: data/resume.txt)")
    p_process_async.add_argument("--workers", type=int,
                                 help="Number of concurrent workers (default: 5)")
    p_process_async.add_argument("--queue-size", type=int,
                                 help="Queue size for backpressure (default: 100)")
    p_process_async.add_argument("--max-concurrent", type=int,
                                 help="Max concurrent API calls (default: 3)")
    p_process_async.add_argument("--llm-rate", type=float,
                                 help="LLM API rate limit (default: 10)")
    p_process_async.add_argument("--email-rate", type=float,
                                 help="Email API rate limit (default: 2)")
    p_process_async.add_argument("--scraper-rate", type=float,
                                 help="Scraper rate limit (default: 30)")
    p_process_async.add_argument("--min-score", type=int,
                                 help="Minimum match score (default: 50)")
    p_process_async.add_argument("--log-level", 
                                 choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                                 help="Log level (default: INFO)")

    args = parser.parse_args()

    if not args.command:
        cmd_help(args)
        return

    fn = COMMANDS.get(args.command)
    if not fn:
        print(f"Unknown command: {args.command}")
        cmd_help(args)
        sys.exit(1)

    fn(args)


if __name__ == "__main__":
    main()
