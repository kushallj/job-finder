"""
firecrawl_startup_pipeline.py — end-to-end pipeline for the top Indian startups.

    scrape career pages (Firecrawl) → store in DB → log to Google Sheet
        → find contacts per company (EmailDiscoveryService)
        → send outreach (EmailOutreach)

This reuses the exact same building blocks as the rest of the repo — the same
Job/Contact/OutreachRecord models, the same GoogleSheetsClient, the same
EmailDiscoveryService and EmailOutreach classes job_processor.py uses — it
just swaps in FirecrawlCareerScraper as the job source, and skips the AI
resume-matching gate (this is for building a company/contact list from a
target set of startups, not filtering by resume fit).

Usage:
    python firecrawl_startup_pipeline.py                     # dry run, no emails sent
    python firecrawl_startup_pipeline.py --send               # actually send outreach
    python firecrawl_startup_pipeline.py --query "backend"    # filter by job title
    python firecrawl_startup_pipeline.py --max-companies 20   # scan fewer companies (testing)
    python firecrawl_startup_pipeline.py --max-contacts 1     # contacts per company (default 2)

Requires FIRECRAWL_API_KEY in .env. Contact discovery and email sending reuse
whatever providers/credentials are already configured (see API_KEYS_CHECKLIST.md) —
this script doesn't need any new keys of its own beyond Firecrawl's.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from sqlalchemy.exc import IntegrityError

from src.config import settings
from src.contact_finder import Contact
from src.database import SessionLocal, init_db
from src.email_discovery import EmailDiscoveryService
from src.email_outreach import EmailOutreach
from src.models import Contact as ContactModel, Job, OutreachRecord
from src.scrapers.firecrawl_scraper import TOP_INDIAN_STARTUPS, FirecrawlCareerScraper
from src.utils.sheets import GoogleSheetsClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("firecrawl_pipeline")


class _JobStub:
    """Duck-typed Job object for EmailOutreach.send_outreach_email(), which
    expects attribute access (job.title, job.company, ...) not a dict."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


async def store_jobs(jobs: List[Dict]) -> int:
    """Persist newly scraped jobs to the Job table. Skips duplicates by job_id,
    same dedup approach as JobProcessor.fetch_and_store_jobs()."""
    stored = 0
    db = SessionLocal()
    try:
        seen = set()
        for job_data in jobs:
            jid = job_data.get("job_id")
            if not jid or jid in seen:
                continue
            seen.add(jid)

            if db.query(Job).filter_by(job_id=jid).first():
                continue

            db.add(Job(
                job_id=jid,
                title=job_data["title"],
                company=job_data["company"],
                location=job_data.get("location", ""),
                description=job_data.get("description", ""),
                url=job_data.get("url", ""),
                source=job_data.get("source", "firecrawl_careers"),
                posted_date=datetime.utcnow(),
            ))
            try:
                db.commit()
                stored += 1
            except IntegrityError:
                db.rollback()
    finally:
        db.close()
    return stored


def log_jobs_to_sheet(sheets: GoogleSheetsClient, jobs: List[Dict]) -> int:
    logged = 0
    sheets.ensure_jobs_worksheet()
    for job in jobs:
        try:
            sheets.append_job_row(
                title=job["title"],
                company=job["company"],
                location=job.get("location", ""),
                url=job.get("url", ""),
                source=job.get("source", "firecrawl_careers"),
                posted_date=job.get("posted_date", ""),
            )
            logged += 1
        except Exception as exc:
            log.warning("Sheet write failed for %s @ %s: %s", job.get("title"), job.get("company"), exc)
    return logged


async def find_and_store_contacts(
    discovery: EmailDiscoveryService,
    sheets: GoogleSheetsClient,
    company: str,
    max_contacts: int,
) -> List[Dict]:
    """Find contacts for a company, persist to DB + Contacts sheet, return them."""
    contacts = await discovery.find_contacts(company_name=company, limit=max_contacts)
    if not contacts:
        return []

    db = SessionLocal()
    try:
        for c in contacts:
            email = c.get("email")
            if not email:
                continue
            existing = db.query(ContactModel).filter_by(email=email, company=company).first()
            if existing:
                continue
            db.add(ContactModel(
                name=c.get("name", "Unknown"),
                title=c.get("title", ""),
                email=email,
                company=company,
                confidence_score=int(c.get("confidence", 0)),
                source=c.get("source", "firecrawl_pipeline"),
            ))
        db.commit()
    except IntegrityError:
        db.rollback()
    finally:
        db.close()

    if sheets:
        try:
            sheets.ensure_contacts_worksheet()
            for c in contacts:
                sheets.append_contact_row(
                    company=company,
                    job_title="",
                    contact_name=c.get("name", "Unknown"),
                    contact_email=c.get("email", ""),
                    contact_title=c.get("title", ""),
                    confidence=int(c.get("confidence", 0)),
                    source=c.get("source", "firecrawl_pipeline"),
                )
        except Exception as exc:
            log.warning("Contacts sheet write failed for %s: %s", company, exc)

    return contacts


async def send_outreach_for_company(
    outreach: EmailOutreach,
    company: str,
    contacts: List[Dict],
    jobs_for_company: List[Dict],
    dry_run: bool,
) -> Dict[str, int]:
    """Send outreach for the best job at this company to each discovered contact."""
    stats = {"sent": 0, "failed": 0, "skipped": 0}
    if not contacts or not jobs_for_company:
        return stats

    job_stub = _JobStub(**jobs_for_company[0])
    db = SessionLocal()
    try:
        for c in contacts:
            email = c.get("email")
            if not email:
                stats["skipped"] += 1
                continue

            existing = (
                db.query(OutreachRecord)
                .filter_by(contact_email=email, job_id=None)
                .first()
            )
            if existing:
                stats["skipped"] += 1
                continue

            if dry_run:
                log.info("[DRY RUN] Would email %s <%s> re: %s", c.get("name"), email, job_stub.title)
                stats["skipped"] += 1
                continue

            contact_obj = Contact(
                name=c.get("name", "Hiring Manager"),
                email=email,
                title=c.get("title", "Recruiter"),
                company=company,
                confidence_score=c.get("confidence", 50),
            )
            try:
                success = await outreach.send_outreach_email(contact_obj, job_stub)
            except Exception as exc:
                log.error("Outreach failed for %s: %s", email, exc)
                success = False

            db.add(OutreachRecord(
                contact_email=email,
                contact_name=c.get("name", "Unknown"),
                subject=f"Re: {job_stub.title} at {company}",
                template_type="firecrawl_pipeline",
                email_sent=success,
                sent_at=datetime.utcnow() if success else None,
                status="sent" if success else "failed",
            ))
            db.commit()

            stats["sent" if success else "failed"] += 1
    finally:
        db.close()

    return stats


async def run(args: argparse.Namespace) -> None:
    init_db()

    registry = TOP_INDIAN_STARTUPS[: args.max_companies] if args.max_companies else TOP_INDIAN_STARTUPS
    log.info("🚀 Firecrawl startup pipeline — %d companies, dry_run=%s", len(registry), not args.send)

    scraper = FirecrawlCareerScraper(api_key=settings.firecrawl_api_key)
    sheets = None
    try:
        sheets_client = GoogleSheetsClient()
        sheet_id = getattr(settings, "google_sheet_id", None)
        if sheet_id:
            sheets_client.get_spreadsheet_by_id(sheet_id)
        else:
            sheets_client.get_or_create_spreadsheet(getattr(settings, "google_sheet_title", None))
        sheets = sheets_client
        log.info("📄 Google Sheet ready: %s", sheets_client.get_spreadsheet_url())
    except Exception as exc:
        log.warning("⚠️  Google Sheets disabled: %s", exc)

    try:
        log.info("🔍 Scraping career pages for %d companies…", len(registry))
        jobs = await scraper.search(query=args.query, companies=registry)
        log.info("✅ Found %d job listings", len(jobs))

        if not jobs:
            log.warning("No jobs found — nothing to store, log, or contact. Check FIRECRAWL_API_KEY.")
            return

        stored = await store_jobs(jobs)
        log.info("💾 Stored %d new jobs in DB", stored)

        if sheets:
            logged = log_jobs_to_sheet(sheets, jobs)
            log.info("📝 Logged %d jobs to the Jobs sheet", logged)

        # Group jobs by company so outreach targets one job per company contact.
        jobs_by_company: Dict[str, List[Dict]] = {}
        for j in jobs:
            jobs_by_company.setdefault(j["company"], []).append(j)

        discovery = EmailDiscoveryService(settings=settings)
        outreach = EmailOutreach()

        total_contacts = 0
        total_outreach = {"sent": 0, "failed": 0, "skipped": 0}

        for company, company_jobs in jobs_by_company.items():
            log.info("📧 Finding contacts for %s (%d jobs found)…", company, len(company_jobs))
            contacts = await find_and_store_contacts(discovery, sheets, company, args.max_contacts)
            total_contacts += len(contacts)

            outcome = await send_outreach_for_company(
                outreach, company, contacts, company_jobs, dry_run=not args.send
            )
            for k in total_outreach:
                total_outreach[k] += outcome[k]

        await discovery.close()

        log.info(
            "🎯 Done — %d jobs, %d contacts found, outreach: sent=%d failed=%d skipped=%d",
            len(jobs), total_contacts,
            total_outreach["sent"], total_outreach["failed"], total_outreach["skipped"],
        )
        if not args.send:
            log.info("This was a dry run — pass --send to actually send outreach emails.")

    finally:
        await scraper.close()


def main():
    parser = argparse.ArgumentParser(description="Firecrawl top-Indian-startups pipeline")
    parser.add_argument("--query", default="", help="Filter jobs by title keyword (default: all)")
    parser.add_argument("--send", action="store_true", help="Actually send outreach emails (default: dry run)")
    parser.add_argument("--max-companies", type=int, default=0, help="Limit number of companies scanned (0 = all)")
    parser.add_argument("--max-contacts", type=int, default=2, help="Max contacts to find per company")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
