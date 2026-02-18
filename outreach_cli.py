#!/usr/bin/env python3
"""
Job Outreach CLI Tool

This tool helps you manage your job outreach campaign with various commands.
"""

import asyncio
import argparse
import os
from src.database import init_db, SessionLocal
from src.models import Job, Contact, OutreachRecord
from src.outreach_processor import OutreachProcessor
from src.job_processor import JobProcessor

def setup_database():
    """Initialize database"""
    init_db()
    print("✅ Database initialized")

def list_jobs(limit=10, min_score=None):
    """List jobs in database"""
    db = SessionLocal()
    
    query = db.query(Job)
    if min_score:
        from src.models import Application
        query = query.join(Application).filter(Application.match_score >= min_score)
    
    jobs = query.limit(limit).all()
    
    print(f"\n📋 Found {len(jobs)} jobs:")
    print("-" * 80)
    
    for job in jobs:
        print(f"ID: {job.id}")
        print(f"Title: {job.title}")
        print(f"Company: {job.company}")
        print(f"Location: {job.location}")
        print(f"Source: {job.source}")
        print(f"Posted: {job.posted_date}")
        print("-" * 80)
    
    db.close()

def list_contacts(company=None, limit=10):
    """List contacts in database"""
    db = SessionLocal()
    
    query = db.query(Contact)
    if company:
        query = query.filter(Contact.company.ilike(f"%{company}%"))
    
    contacts = query.limit(limit).all()
    
    print(f"\n👥 Found {len(contacts)} contacts:")
    print("-" * 80)
    
    for contact in contacts:
        print(f"ID: {contact.id}")
        print(f"Name: {contact.name}")
        print(f"Title: {contact.title}")
        print(f"Email: {contact.email}")
        print(f"Company: {contact.company}")
        print(f"Confidence: {contact.confidence_score}")
        print("-" * 80)
    
    db.close()

def show_outreach_stats():
    """Show outreach statistics"""
    db = SessionLocal()
    
    total_jobs = db.query(Job).count()
    total_contacts = db.query(Contact).count()
    total_outreach = db.query(OutreachRecord).count()
    
    print(f"\n📊 Outreach Statistics:")
    print(f"   Total jobs: {total_jobs}")
    print(f"   Total contacts: {total_contacts}")
    print(f"   Total outreach attempts: {total_outreach}")
    
    # Status breakdown
    records = db.query(OutreachRecord).all()
    status_counts = {}
    for record in records:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1
    
    if status_counts:
        print(f"\n   Status breakdown:")
        for status, count in status_counts.items():
            print(f"     {status}: {count}")
    
    # Recent outreach
    recent = db.query(OutreachRecord).order_by(OutreachRecord.sent_at.desc()).limit(5).all()
    if recent:
        print(f"\n   Recent outreach:")
        for record in recent:
            contact = db.query(Contact).filter_by(id=record.contact_id).first()
            job = db.query(Job).filter_by(id=record.job_id).first()
            print(f"     {contact.name} at {contact.company} for {job.title} ({record.sent_at.strftime('%Y-%m-%d')})")
    
    db.close()

async def run_outreach(job_ids=None, dry_run=False, max_contacts=2):
    """Run outreach campaign"""
    
    # Load resume
    resume_path = "data/resume.txt"
    if not os.path.exists(resume_path):
        print("❌ Resume file not found at data/resume.txt")
        return
    
    with open(resume_path, "r") as f:
        resume_text = f.read()
    
    outreach_processor = OutreachProcessor()
    
    try:
        if job_ids:
            print(f"🎯 Running outreach for specific jobs: {job_ids}")
            stats = await outreach_processor.process_multiple_jobs(
                job_ids=job_ids,
                resume_text=resume_text,
                max_contacts_per_job=max_contacts,
                send_emails=not dry_run
            )
        else:
            print("🎯 Running outreach for all eligible jobs")
            stats = await outreach_processor.process_multiple_jobs(
                resume_text=resume_text,
                max_contacts_per_job=max_contacts,
                send_emails=not dry_run
            )
        
        print(f"\n✅ Outreach completed:")
        print(f"   Jobs processed: {stats['jobs_processed']}")
        print(f"   Contacts found: {stats['total_contacts_found']}")
        print(f"   Emails sent: {stats['total_emails_sent']}")
        
    finally:
        await outreach_processor.close()

async def fetch_jobs(queries=None, comprehensive=False):
    """Fetch new jobs"""
    if not queries:
        if comprehensive:
            queries = [
                "Python Developer", "Backend Developer", "Full Stack Developer",
                "Software Engineer", "Django Developer", "FastAPI Developer",
                "GenAI Engineer", "Machine Learning Engineer"
            ]
        else:
            queries = ["python developer", "software engineer", "backend developer"]
    
    job_processor = JobProcessor()
    
    try:
        total_jobs = 0
        for query in queries:
            print(f"🔍 Fetching jobs for: {query}")
            if comprehensive:
                print("   Using comprehensive multi-platform search...")
            count = await job_processor.fetch_and_store_jobs(query=query)
            total_jobs += count
            print(f"✅ Stored {count} new jobs")
            await asyncio.sleep(2)
        
        print(f"\n🎯 Total jobs fetched: {total_jobs}")
        
    finally:
        job_processor.close()
        await job_processor.scraper.close()

async def run_comprehensive_search(dry_run=False, max_contacts=2):
    """Run comprehensive search and outreach"""
    print("🚀 Running comprehensive multi-platform job search and outreach...")
    
    # Import here to avoid circular imports
    import subprocess
    import sys
    
    try:
        # Run the comprehensive script
        cmd = [sys.executable, "comprehensive_job_search.py"]
        if dry_run:
            print("📋 Note: This will run the full comprehensive search.")
            print("   Use 'outreach --dry-run' for email-only dry runs.")
        
        result = subprocess.run(cmd, check=True)
        print("✅ Comprehensive search completed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Comprehensive search failed: {e}")
    except Exception as e:
        print(f"❌ Error running comprehensive search: {e}")

def main():
    parser = argparse.ArgumentParser(description="Job Outreach CLI Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Initialize database')
    
    # List jobs command
    jobs_parser = subparsers.add_parser('jobs', help='List jobs')
    jobs_parser.add_argument('--limit', type=int, default=10, help='Number of jobs to show')
    jobs_parser.add_argument('--min-score', type=int, help='Minimum match score')
    
    # List contacts command
    contacts_parser = subparsers.add_parser('contacts', help='List contacts')
    contacts_parser.add_argument('--company', help='Filter by company name')
    contacts_parser.add_argument('--limit', type=int, default=10, help='Number of contacts to show')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show outreach statistics')
    
    # Outreach command
    outreach_parser = subparsers.add_parser('outreach', help='Run outreach campaign')
    outreach_parser.add_argument('--job-ids', nargs='+', type=int, help='Specific job IDs to target')
    outreach_parser.add_argument('--dry-run', action='store_true', help='Don\'t send emails, just show what would be sent')
    outreach_parser.add_argument('--max-contacts', type=int, default=2, help='Max contacts per job')
    
    # Comprehensive search command
    comprehensive_parser = subparsers.add_parser('comprehensive', help='Run comprehensive multi-platform search and outreach')
    comprehensive_parser.add_argument('--dry-run', action='store_true', help='Don\'t send emails, just show what would be sent')
    comprehensive_parser.add_argument('--max-contacts', type=int, default=2, help='Max contacts per job')
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch new jobs')
    fetch_parser.add_argument('--queries', nargs='+', help='Search queries')
    fetch_parser.add_argument('--comprehensive', action='store_true', help='Use comprehensive multi-platform search')
    
    args = parser.parse_args()
    
    if args.command == 'setup':
        setup_database()
    elif args.command == 'jobs':
        list_jobs(args.limit, args.min_score)
    elif args.command == 'contacts':
        list_contacts(args.company, args.limit)
    elif args.command == 'stats':
        show_outreach_stats()
    elif args.command == 'outreach':
        asyncio.run(run_outreach(args.job_ids, args.dry_run, args.max_contacts))
    elif args.command == 'comprehensive':
        asyncio.run(run_comprehensive_search(args.dry_run, args.max_contacts))
    elif args.command == 'fetch':
        asyncio.run(fetch_jobs(args.queries, getattr(args, 'comprehensive', False)))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()