"""
Test script: Run email discovery against jobs in the database,
store discovered contacts in the Google Sheet "Contacts" worksheet.
"""

import asyncio
import sys
from datetime import datetime
from src.config import settings
from src.database import SessionLocal
from src.models import Job
from src.email_discovery import EmailDiscoveryService
from src.utils.sheets import GoogleSheetsClient, CONTACTS_WORKSHEET, CONTACTS_HEADERS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_COMPANIES = 15          # How many unique companies to process
CONTACTS_PER_COMPANY = 3    # Max contacts to find per company
MIN_CONFIDENCE = 20         # Skip contacts below this confidence


async def main():
    print("=" * 60)
    print("📧 Email Discovery Test — DB → Sheet")
    print("=" * 60)

    # --- 1. Connect to DB and get unique companies from jobs ---
    db = SessionLocal()
    from sqlalchemy import func
    rows = (
        db.query(Job.company, func.min(Job.title).label("title"), func.min(Job.id).label("jid"))
        .filter(Job.company.isnot(None), Job.company != "", Job.company != "N/A")
        .group_by(Job.company)
        .limit(MAX_COMPANIES)
        .all()
    )
    if not rows:
        print("❌ No jobs in database. Run a search first.")
        db.close()
        return

    companies = [(r[0], r[1], r[2]) for r in rows]
    print(f"🏢 Found {len(companies)} unique companies to process\n")

    # --- 2. Init Google Sheet (Contacts worksheet) ---
    sheets = None
    try:
        sheets = GoogleSheetsClient()
        if getattr(settings, "google_sheet_id", None):
            sheets.get_spreadsheet_by_id(settings.google_sheet_id)
        else:
            sheets.get_or_create_spreadsheet(getattr(settings, "google_sheet_title", None))
        sheets.ensure_contacts_worksheet()
        print(f"📄 Google Sheet: {sheets.get_spreadsheet_url()}")
        print(f"   Worksheet : {CONTACTS_WORKSHEET}\n")
    except Exception as e:
        print(f"⚠️  Google Sheets init failed: {e}")
        print("   Contacts will be printed to console only.\n")
        sheets = None

    # --- 3. Init Email Discovery ---
    discovery = EmailDiscoveryService(settings=settings)

    # --- 4. Process each company ---
    total_found = 0
    total_stored = 0

    for idx, (company, job_title, job_id) in enumerate(companies, 1):
        print(f"[{idx}/{len(companies)}] 🔍 {company} — {job_title}")

        try:
            contacts = await discovery.find_contacts(
                company_name=company,
                job_title=job_title,
                limit=CONTACTS_PER_COMPANY,
            )
        except Exception as e:
            print(f"   ❌ Discovery error: {e}")
            continue

        if not contacts:
            print(f"   ⚠️  No contacts found")
            continue

        total_found += len(contacts)

        for c in contacts:
            conf = c.get("confidence", 0)
            if conf < MIN_CONFIDENCE:
                continue

            email = c.get("email", "")
            name = c.get("name", "")
            title = c.get("title", "")
            source = c.get("source", "")
            verified = c.get("verified", False)
            linkedin = c.get("linkedin_url", "")
            phone = c.get("phone", "")

            print(f"   ✅ {name} <{email}> ({title}) — conf={conf} src={source}")

            if sheets:
                try:
                    sheets.append_contact_row(
                        company=company,
                        job_title=job_title,
                        contact_name=name,
                        contact_email=email,
                        contact_title=title,
                        confidence=conf,
                        source=source,
                        verified=verified,
                        linkedin_url=linkedin,
                        phone=phone,
                    )
                    total_stored += 1
                except Exception as e:
                    print(f"   ⚠️  Sheet write error: {e}")

        # Small delay between companies to avoid rate limits
        await asyncio.sleep(1)

    # --- 5. Cleanup ---
    await discovery.close()
    db.close()

    print("\n" + "=" * 60)
    print(f"📊 Done! Found {total_found} contacts, stored {total_stored} in sheet.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
