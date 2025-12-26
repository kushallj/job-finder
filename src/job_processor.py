import asyncio
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.scrapers.api_scraper import APIJobScraper
from src.ai.claude_service import ClaudeService
from src.database import SessionLocal
from src.models import Job, Application, Resume
from datetime import datetime
import json
from src.utils.sheets import GoogleSheetsClient, DEFAULT_SHEET_TITLE, DEFAULT_WORKSHEET
from src.config import settings

class JobProcessor:
    """Main orchestrator for job processing pipeline"""
    
    def __init__(self):
        self.scraper = APIJobScraper()
        self.ai = ClaudeService()
        self.db = SessionLocal()
        # Initialize Google Sheets (Option B)
        try:
            self.sheets = GoogleSheetsClient()
            # Prefer opening an existing sheet by ID if provided
            if getattr(settings, "google_sheet_id", None):
                self.sheets.get_spreadsheet_by_id(settings.google_sheet_id)
            else:
                self.sheets.get_or_create_spreadsheet(getattr(settings, "google_sheet_title", None))
            self.sheets.ensure_worksheet()
            print(f"📄 Google Sheet: {self.sheets.get_spreadsheet_url()}")
        except Exception as e:
            # Provide helpful guidance for common permission errors
            self.sheets = None
            hint = ""
            msg = str(e)
            if "PERMISSION_DENIED" in msg or "does not have permission" in msg:
                hint = " — share the sheet with your service account email and try again"
            elif "storage quota" in msg.lower():
                hint = " — free up Drive storage or provide GOOGLE_SHEET_ID of an existing sheet"
            print(f"⚠️ Google Sheets disabled: {e}{hint}")
    
    async def fetch_and_store_jobs(self, query: str = "software engineer") -> int:
        """Fetch jobs and store in database"""
        print(f"🔍 Fetching jobs for: {query}")
        
        jobs = await self.scraper.fetch_all(query)
        print(f"✅ Found {len(jobs)} jobs")
        
        stored_count = 0
        seen_ids = set()
        for job_data in jobs:
            # Skip duplicates within the same batch (across multiple sources)
            jid = job_data.get('job_id')
            if not jid:
                continue
            if jid in seen_ids:
                continue
            seen_ids.add(jid)
            
            # Check if job already exists
            existing = self.db.query(Job).filter_by(job_id=jid).first()
            if existing:
                continue
            
            # Create new job
            job = Job(
                job_id=jid,
                title=job_data['title'],
                company=job_data['company'],
                location=job_data['location'],
                description=job_data['description'],
                url=job_data['url'],
                source=job_data['source'],
                posted_date=datetime.now()
            )
            try:
                self.db.add(job)
                self.db.commit()
                stored_count += 1
            except IntegrityError:
                # Handle race/duplicate safely
                self.db.rollback()
                continue
        print(f"💾 Stored {stored_count} new jobs")
        return stored_count
    
    async def process_job(self, job: Job, resume_text: str, min_score: int = 50) -> Application:
        """Process a single job through the AI pipeline"""
        print(f"🤖 Processing: {job.title} at {job.company}")
        
        # Extract skills from job description
        job_skills = await self.ai.extract_skills(job.description)
        
        # Match resume to job
        match_result = await self.ai.match_resume_to_job(resume_text, job_skills)
        
        # Only proceed if match score is good enough
        if match_result['match_score'] < min_score:
            print(f"⏭️  Skipping (low match: {match_result['match_score']})")
            # Still log the evaluation to Google Sheet
            try:
                if self.sheets:
                    self.sheets.append_application_row(
                        title=job.title,
                        company=job.company or "",
                        location=job.location or "",
                        match_score=match_result['match_score'],
                        matched_skills=match_result.get('matched_skills', []),
                        missing_skills=match_result.get('missing_skills', []),
                        recommendations="Low match - skipped",
                        url=job.url or "",
                        source=job.source or "",
                    )
            except Exception as e:
                print(f"⚠️ Could not write skipped job to Google Sheet: {e}")
            return None
        
        print(f"✅ Match score: {match_result['match_score']}")
        
        # Generate tailored content
        rewritten_resume = await self.ai.rewrite_resume(resume_text, job.description)
        cover_letter = await self.ai.generate_cover_letter(resume_text, job.description, job.company)
        
        # Create application record
        application = Application(
            job_id=job.id,
            match_score=match_result['match_score'],
            skills_matched=json.dumps(match_result['matched_skills']),
            skills_missing=json.dumps(match_result['missing_skills']),
            resume_version=rewritten_resume,
            cover_letter=cover_letter,
            status="ready"
        )
        
        self.db.add(application)
        self.db.commit()
        
        # Append to Google Sheet
        try:
            if self.sheets:
                self.sheets.append_application_row(
                    title=job.title,
                    company=job.company or "",
                    location=job.location or "",
                    match_score=match_result['match_score'],
                    matched_skills=match_result.get('matched_skills', []),
                    missing_skills=match_result.get('missing_skills', []),
                    recommendations=match_result.get('recommendations', ''),
                    url=job.url or "",
                    source=job.source or "",
                )
        except Exception as e:
            print(f"⚠️ Could not write to Google Sheet: {e}")
        
        print(f"✅ Application created for {job.title}")
        return application
    
    async def process_all_jobs(self, resume_text: str, min_score: int = 50):
        """Process all unprocessed jobs"""
        # Get jobs without applications
        jobs = self.db.query(Job).outerjoin(Application).filter(Application.id == None).all()
        
        print(f"📊 Processing {len(jobs)} jobs...")
        
        for job in jobs:
            try:
                await self.process_job(job, resume_text, min_score=min_score)
                await asyncio.sleep(2)  # Rate limiting
            except Exception as e:
                print(f"❌ Error processing {job.title}: {e}")
                continue
    
    def close(self):
        self.db.close()