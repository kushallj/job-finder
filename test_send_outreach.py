"""Send a limited batch of outreach emails using existing job + discovery stack."""

import asyncio
from pathlib import Path
from typing import List

from src.config import settings
from src.database import SessionLocal
from src.models import Job
from src.email_discovery import EmailDiscoveryService
from src.email_outreach import EmailOutreach
from src.contact_finder import Contact

MAX_JOBS = 2
CONTACTS_PER_JOB = 1
MIN_CONFIDENCE = 40
RESUME_TEXT_PATH = Path("data/resume.txt")


def load_resume_text() -> str:
    if RESUME_TEXT_PATH.exists():
        return RESUME_TEXT_PATH.read_text(encoding="utf-8")
    return "Experienced software engineer with full-stack background."


def dict_to_contact(data: dict, fallback_company: str) -> Contact:
    return Contact(
        name=data.get("name") or "Hiring Manager",
        title=data.get("title") or data.get("source", ""),
        email=data.get("email"),
        company=data.get("company") or fallback_company,
        department="",
        confidence_score=int(data.get("confidence") or 0),
    )


async def main():
    db = SessionLocal()
    jobs: List[Job] = (
        db.query(Job)
        .order_by(Job.posted_date.desc())
        .limit(MAX_JOBS)
        .all()
    )
    if not jobs:
        print("❌ No jobs stored in the database. Run scraping first.")
        return

    resume_text = load_resume_text()
    discovery = EmailDiscoveryService(settings=settings)
    outreach = EmailOutreach()

    sent = 0
    for job in jobs:
        print(f"\n=== {job.company} — {job.title} ===")
        contacts = await discovery.find_contacts(
            company_name=job.company,
            job_title=job.title,
            limit=CONTACTS_PER_JOB,
        )
        if not contacts:
            print("⚠️  No contacts discovered. Skipping job.")
            continue

        for raw in contacts:
            if raw.get("confidence", 0) < MIN_CONFIDENCE:
                print(f"⏭️  Skipping {raw.get('email')} — low confidence {raw.get('confidence')}")
                continue
            if not raw.get("email"):
                print("⏭️  Discovery result missing email.")
                continue

            contact = dict_to_contact(raw, fallback_company=job.company)
            email_template = await outreach.create_personalized_email(
                contact,
                job_title=job.title,
                job_description=job.description or "",
                resume_text=resume_text,
            )
            if not email_template:
                print(f"⏭️  Could not craft template for {contact.email}")
                continue

            success = await outreach.send_email(contact, email_template, job.title)
            if success:
                sent += 1
                break  # only send one email per job for safety
        await asyncio.sleep(2)

    await discovery.close()
    db.close()
    print(f"\n📤 Completed test send. Emails sent: {sent}")


if __name__ == "__main__":
    asyncio.run(main())
