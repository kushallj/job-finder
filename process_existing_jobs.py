#!/usr/bin/env python3
"""
Process Existing Jobs in Database

This script processes jobs that are already in the database without scraping new ones.
It will analyze them with AI and find contacts for outreach.
"""

import asyncio
import os
from src.job_processor import JobProcessor
from src.database import SessionLocal, init_db
from src.models import Job, Contact, OutreachRecord

async def main():
    """Process existing jobs in the database."""
    print("🚀 Processing Existing Jobs")
    print("=" * 60)
    
    # Initialize database
    init_db()
    job_processor = JobProcessor()
    
    # Load resume
    resume_path = "data/resume.txt"
    if not os.path.exists(resume_path):
        print("❌ Resume file not found at data/resume.txt")
        return
    
    with open(resume_path, "r") as f:
        resume_text = f.read()
    
    print("📄 Resume loaded successfully")
    
    # Get all jobs from database
    db = SessionLocal()
    try:
        jobs = db.query(Job).all()
        print(f"\n📊 Found {len(jobs)} jobs in database")
        
        if len(jobs) == 0:
            print("❌ No jobs to process")
            return
        
        # Process jobs with AI analysis
        print("\n🤖 Step 1: AI-Powered Job Analysis & Matching")
        print("-" * 50)
        print(f"Processing {len(jobs)} jobs with AI matching...")
        print("This may take 10-30 minutes depending on number of jobs")
        
        try:
            # Process all jobs with default min_score of 50
            result = await job_processor.process_all_jobs(
                resume_text=resume_text,
                min_score=50
            )
            
            high_match_count = result.get("high_match_count", 0)
            print(f"\n✅ Job Analysis Complete!")
            print(f"   High-match jobs (score ≥50): {high_match_count}")
            
        except Exception as e:
            print(f"\n❌ Error processing jobs: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Get statistics
        print("\n📊 Final Statistics")
        print("-" * 50)
        
        jobs_count = db.query(Job).count()
        contacts_count = db.query(Contact).count()
        outreach_count = db.query(OutreachRecord).count()
        
        print(f"Total Jobs: {jobs_count}")
        print(f"Contacts Found: {contacts_count}")
        print(f"Outreach Records: {outreach_count}")
        
        if contacts_count > 0:
            print(f"\n✅ Contact discovery successful!")
            print(f"   Found {contacts_count} potential contacts")
        else:
            print(f"\n⚠️  No contacts found. This could mean:")
            print(f"   - API keys for contact discovery services not configured")
            print(f"   - All jobs processed didn't meet the threshold")
        
        if outreach_count > 0:
            print(f"\n✅ Email outreach initiated!")
            print(f"   {outreach_count} outreach attempts")
        
    finally:
        db.close()
    
    print("\n🎉 Processing Complete!")
    print("\nNext steps:")
    print("1. Check logs/main.log for detailed processing logs")
    print("2. Run 'python export_to_sheets.py' to export results")
    print("3. Monitor your email for responses")

if __name__ == "__main__":
    asyncio.run(main())
