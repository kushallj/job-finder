#!/usr/bin/env python3
"""
Export Database to Google Sheets
Copies all jobs, contacts, and outreach data to Google Sheets
"""

import asyncio
from datetime import datetime
from src.database import SessionLocal
from src.models import Job, Contact, OutreachRecord, Application
from src.utils.sheets import GoogleSheetsClient
from src.config import settings

def export_jobs_to_sheet(sheet_client: GoogleSheetsClient, worksheet_name: str = "Jobs"):
    """Export all jobs to a Google Sheet"""
    
    print(f"\n📋 Exporting Jobs to '{worksheet_name}'...")
    
    db = SessionLocal()
    jobs = db.query(Job).order_by(Job.fetched_at.desc()).all()
    
    if not jobs:
        print("   No jobs found in database")
        db.close()
        return
    
    # Prepare data
    headers = [
        "ID", "Job ID", "Title", "Company", "Location", 
        "Source", "URL", "Posted Date", "Fetched At", "Description"
    ]
    
    rows = [headers]
    
    for job in jobs:
        rows.append([
            str(job.id),
            job.job_id or "",
            job.title or "",
            job.company or "",
            job.location or "",
            job.source or "",
            job.url or "",
            job.posted_date.strftime("%Y-%m-%d") if job.posted_date else "",
            job.fetched_at.strftime("%Y-%m-%d %H:%M") if job.fetched_at else "",
            (job.description or "")[:500]  # Truncate long descriptions
        ])
    
    # Create or get worksheet
    try:
        worksheet = sheet_client.spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
    except:
        worksheet = sheet_client.spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=len(rows) + 100,
            cols=len(headers)
        )
    
    # Write data
    worksheet.update('A1', rows)
    
    # Format header
    worksheet.format('A1:J1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9}
    })
    
    print(f"   ✅ Exported {len(jobs)} jobs")
    db.close()

def export_contacts_to_sheet(sheet_client: GoogleSheetsClient, worksheet_name: str = "Contacts"):
    """Export all contacts to a Google Sheet"""
    
    print(f"\n👥 Exporting Contacts to '{worksheet_name}'...")
    
    db = SessionLocal()
    contacts = db.query(Contact).order_by(Contact.found_at.desc()).all()
    
    if not contacts:
        print("   No contacts found in database")
        db.close()
        return
    
    # Prepare data
    headers = [
        "ID", "Name", "Title", "Email", "Company", 
        "Department", "LinkedIn", "Confidence Score", "Source", "Found At"
    ]
    
    rows = [headers]
    
    for contact in contacts:
        rows.append([
            str(contact.id),
            contact.name or "",
            contact.title or "",
            contact.email or "",
            contact.company or "",
            contact.department or "",
            contact.linkedin_url or "",
            str(contact.confidence_score) if contact.confidence_score else "0",
            contact.source or "",
            contact.found_at.strftime("%Y-%m-%d %H:%M") if contact.found_at else ""
        ])
    
    # Create or get worksheet
    try:
        worksheet = sheet_client.spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
    except:
        worksheet = sheet_client.spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=len(rows) + 100,
            cols=len(headers)
        )
    
    # Write data
    worksheet.update('A1', rows)
    
    # Format header
    worksheet.format('A1:J1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.6, 'blue': 0.2}
    })
    
    print(f"   ✅ Exported {len(contacts)} contacts")
    db.close()

def export_outreach_to_sheet(sheet_client: GoogleSheetsClient, worksheet_name: str = "Outreach"):
    """Export all outreach records to a Google Sheet"""
    
    print(f"\n📧 Exporting Outreach to '{worksheet_name}'...")
    
    db = SessionLocal()
    records = db.query(OutreachRecord).order_by(OutreachRecord.sent_at.desc()).all()
    
    if not records:
        print("   No outreach records found in database")
        db.close()
        return
    
    # Prepare data
    headers = [
        "ID", "Contact Name", "Contact Email", "Company", "Job Title",
        "Subject", "Status", "Sent At", "Replied At", 
        "Follow-up Sent", "Template Type"
    ]
    
    rows = [headers]
    
    for record in records:
        # Get related contact and job
        contact = db.query(Contact).filter_by(id=record.contact_id).first()
        job = db.query(Job).filter_by(id=record.job_id).first()
        
        rows.append([
            str(record.id),
            contact.name if contact else "",
            contact.email if contact else "",
            job.company if job else "",
            job.title if job else "",
            record.subject or "",
            record.status or "",
            record.sent_at.strftime("%Y-%m-%d %H:%M") if record.sent_at else "",
            record.replied_at.strftime("%Y-%m-%d %H:%M") if record.replied_at else "",
            "Yes" if record.follow_up_sent else "No",
            record.template_type or ""
        ])
    
    # Create or get worksheet
    try:
        worksheet = sheet_client.spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
    except:
        worksheet = sheet_client.spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=len(rows) + 100,
            cols=len(headers)
        )
    
    # Write data
    worksheet.update('A1', rows)
    
    # Format header
    worksheet.format('A1:K1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.2, 'green': 0.9, 'blue': 0.6}
    })
    
    print(f"   ✅ Exported {len(records)} outreach records")
    db.close()

def export_applications_to_sheet(sheet_client: GoogleSheetsClient, worksheet_name: str = "Applications"):
    """Export all applications to a Google Sheet"""
    
    print(f"\n📝 Exporting Applications to '{worksheet_name}'...")
    
    db = SessionLocal()
    applications = db.query(Application).order_by(Application.created_at.desc()).all()
    
    if not applications:
        print("   No applications found in database")
        db.close()
        return
    
    # Prepare data
    headers = [
        "ID", "Job Title", "Company", "Match Score", 
        "Matched Skills", "Missing Skills", "Status", 
        "Applied At", "Created At"
    ]
    
    rows = [headers]
    
    for app in applications:
        # Get related job
        job = db.query(Job).filter_by(id=app.job_id).first()
        
        rows.append([
            str(app.id),
            job.title if job else "",
            job.company if job else "",
            str(app.match_score) if app.match_score else "0",
            app.skills_matched or "",
            app.skills_missing or "",
            app.status or "",
            app.applied_at.strftime("%Y-%m-%d") if app.applied_at else "",
            app.created_at.strftime("%Y-%m-%d %H:%M") if app.created_at else ""
        ])
    
    # Create or get worksheet
    try:
        worksheet = sheet_client.spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
    except:
        worksheet = sheet_client.spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=len(rows) + 100,
            cols=len(headers)
        )
    
    # Write data
    worksheet.update('A1', rows)
    
    # Format header
    worksheet.format('A1:I1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.6, 'green': 0.2, 'blue': 0.9}
    })
    
    print(f"   ✅ Exported {len(applications)} applications")
    db.close()

def export_summary_to_sheet(sheet_client: GoogleSheetsClient, worksheet_name: str = "Summary"):
    """Export summary statistics to a Google Sheet"""
    
    print(f"\n📊 Exporting Summary to '{worksheet_name}'...")
    
    db = SessionLocal()
    
    # Gather statistics
    total_jobs = db.query(Job).count()
    total_contacts = db.query(Contact).count()
    total_outreach = db.query(OutreachRecord).count()
    total_applications = db.query(Application).count()
    
    # Outreach by status
    sent = db.query(OutreachRecord).filter_by(status="sent").count()
    replied = db.query(OutreachRecord).filter_by(status="replied").count()
    
    # Top companies
    from sqlalchemy import func
    top_companies = db.query(
        Job.company, 
        func.count(Job.id).label('count')
    ).group_by(Job.company).order_by(func.count(Job.id).desc()).limit(10).all()
    
    # Prepare data
    rows = [
        ["Job Search Campaign Summary", ""],
        ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["", ""],
        ["Overall Statistics", ""],
        ["Total Jobs Found", str(total_jobs)],
        ["Total Contacts", str(total_contacts)],
        ["Total Outreach Attempts", str(total_outreach)],
        ["Total Applications", str(total_applications)],
        ["", ""],
        ["Outreach Statistics", ""],
        ["Emails Sent", str(sent)],
        ["Replies Received", str(replied)],
        ["Response Rate", f"{(replied/sent*100):.1f}%" if sent > 0 else "0%"],
        ["", ""],
        ["Top 10 Companies", "Job Count"],
    ]
    
    for company, count in top_companies:
        rows.append([company or "Unknown", str(count)])
    
    # Create or get worksheet
    try:
        worksheet = sheet_client.spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
    except:
        worksheet = sheet_client.spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=len(rows) + 50,
            cols=2
        )
    
    # Write data
    worksheet.update('A1', rows)
    
    # Format title
    worksheet.format('A1:B1', {
        'textFormat': {'bold': True, 'fontSize': 14},
        'backgroundColor': {'red': 0.2, 'green': 0.7, 'blue': 0.9}
    })
    
    # Format section headers
    worksheet.format('A4:B4', {'textFormat': {'bold': True}})
    worksheet.format('A10:B10', {'textFormat': {'bold': True}})
    worksheet.format('A15:B15', {'textFormat': {'bold': True}})
    
    print(f"   ✅ Exported summary statistics")
    db.close()

def main():
    """Main export function"""
    
    print("📊 Database to Google Sheets Export Tool")
    print("=" * 50)
    
    try:
        # Initialize Google Sheets client
        print("\n🔗 Connecting to Google Sheets...")
        sheets_client = GoogleSheetsClient()
        
        # Get or create spreadsheet
        sheet_id = getattr(settings, "google_sheet_id", None)
        if sheet_id:
            sheets_client.get_spreadsheet_by_id(sheet_id)
            print(f"   ✅ Using existing sheet: {sheet_id}")
        else:
            sheet_title = f"Job Search Data - {datetime.now().strftime('%Y-%m-%d')}"
            sheets_client.get_or_create_spreadsheet(sheet_title)
            print(f"   ✅ Created new sheet: {sheet_title}")
        
        print(f"\n📄 Sheet URL: {sheets_client.get_spreadsheet_url()}")
        
        # Export all data
        export_summary_to_sheet(sheets_client, "Summary")
        export_jobs_to_sheet(sheets_client, "Jobs")
        export_contacts_to_sheet(sheets_client, "Contacts")
        export_outreach_to_sheet(sheets_client, "Outreach")
        export_applications_to_sheet(sheets_client, "Applications")
        
        print("\n" + "=" * 50)
        print("🎉 Export Complete!")
        print("=" * 50)
        print(f"\n📊 View your data:")
        print(f"   {sheets_client.get_spreadsheet_url()}")
        print("\n💡 Tip: You can now:")
        print("   • Analyze data with pivot tables")
        print("   • Create charts and visualizations")
        print("   • Share with others")
        print("   • Export to Excel/CSV")
        
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check GOOGLE_SHEET_ID in .env")
        print("   2. Verify service account has access")
        print("   3. Check GOOGLE_CREDENTIALS_PATH is correct")

if __name__ == "__main__":
    main()
