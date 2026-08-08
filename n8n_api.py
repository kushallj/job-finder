"""
n8n Integration API
FastAPI server that exposes endpoints for n8n workflow integration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
import asyncio
from datetime import datetime, timedelta
import json

from src.job_processor import JobProcessor
from src.outreach_processor import OutreachProcessor
from src.contact_finder import Contact
from src.email_discovery import EmailDiscoveryService
from src.email_outreach import EmailOutreach
from src.database import SessionLocal, init_db
from src.models import Job, Contact as ContactModel, OutreachRecord

# Initialize FastAPI app
app = FastAPI(
    title="Job Outreach n8n API",
    description="API for n8n workflow integration - job search, contact finding, and email outreach",
    version="1.0.0"
)

# Add CORS middleware for n8n
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your n8n instance URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# ============================================================================
# Request/Response Models
# ============================================================================

class JobSearchRequest(BaseModel):
    keywords: List[str]
    locations: Optional[List[str]] = ["Remote", "Bangalore", "Delhi"]
    min_match_score: Optional[int] = 60

class JobSearchResponse(BaseModel):
    total_jobs: int
    new_jobs: int
    jobs: List[Dict]

class ContactSearchRequest(BaseModel):
    company_name: str
    job_title: Optional[str] = ""

class ContactSearchResponse(BaseModel):
    total_contacts: int
    contacts: List[Dict]

class EmailOutreachRequest(BaseModel):
    job_id: int
    contact_email: EmailStr
    contact_name: str
    send_immediately: Optional[bool] = False

class EmailOutreachResponse(BaseModel):
    success: bool
    message: str
    outreach_id: Optional[int] = None

class FollowUpRequest(BaseModel):
    outreach_id: int
    days_since_sent: Optional[int] = 7

class FollowUpResponse(BaseModel):
    follow_ups_sent: int
    details: List[Dict]

class JobListResponse(BaseModel):
    total: int
    jobs: List[Dict]

class OutreachStatsResponse(BaseModel):
    total_outreach: int
    sent: int
    replied: int
    no_response: int
    pending_follow_ups: int

# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Job Outreach n8n API",
        "version": "1.0.0",
        "endpoints": {
            "jobs": "/api/jobs",
            "search": "/api/jobs/search",
            "contacts": "/api/contacts/search",
            "outreach": "/api/outreach/send",
            "follow_up": "/api/outreach/follow-up",
            "stats": "/api/stats"
        }
    }

@app.post("/api/jobs/search", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest, background_tasks: BackgroundTasks):
    """
    Search for jobs across multiple platforms
    
    This endpoint triggers a comprehensive job search and returns results.
    Perfect for n8n workflow trigger.
    """
    try:
        job_processor = JobProcessor()
        
        total_new_jobs = 0
        all_jobs = []
        
        # Search for each keyword
        for keyword in request.keywords:
            for location in request.locations:
                jobs_count = await job_processor.fetch_and_store_jobs(
                    query=keyword
                )
                total_new_jobs += jobs_count
        
        # Get recent jobs from database
        db = SessionLocal()
        recent_jobs = db.query(Job).order_by(Job.fetched_at.desc()).limit(50).all()
        
        jobs_data = []
        for job in recent_jobs:
            jobs_data.append({
                "id": job.id,
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "url": job.url,
                "source": job.source,
                "description": job.description[:200] + "..." if job.description else "",
                "posted_date": job.posted_date.isoformat() if job.posted_date else None,
                "fetched_at": job.fetched_at.isoformat()
            })
        
        db.close()
        job_processor.close()
        await job_processor.scraper.close()
        
        return JobSearchResponse(
            total_jobs=len(jobs_data),
            new_jobs=total_new_jobs,
            jobs=jobs_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs", response_model=JobListResponse)
async def get_jobs(
    limit: int = 20,
    min_match_score: Optional[int] = None,
    company: Optional[str] = None
):
    """
    Get list of jobs from database
    
    Use this in n8n to retrieve jobs for processing.
    """
    try:
        db = SessionLocal()
        query = db.query(Job)
        
        # Filter by company if specified
        if company:
            query = query.filter(Job.company.ilike(f"%{company}%"))
        
        jobs = query.order_by(Job.fetched_at.desc()).limit(limit).all()
        
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                "id": job.id,
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "url": job.url,
                "source": job.source,
                "description": job.description,
                "posted_date": job.posted_date.isoformat() if job.posted_date else None
            })
        
        db.close()
        
        return JobListResponse(
            total=len(jobs_data),
            jobs=jobs_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/contacts/search", response_model=ContactSearchResponse)
async def search_contacts(request: ContactSearchRequest):
    """
    Search for contacts at a company
    
    Use this in n8n to find HR/Engineering contacts for outreach.
    """
    try:
        from src.config import settings as app_settings
        discovery = EmailDiscoveryService(settings=app_settings)

        contacts_data = await discovery.find_contacts(
            company_name=request.company_name,
            job_title=request.job_title,
            limit=10,
        )

        await discovery.close()

        contacts_list = [
            {
                "name":             c.get("name", ""),
                "title":            c.get("title", ""),
                "email":            c.get("email", ""),
                "linkedin_url":     c.get("linkedin_url", ""),
                "company":          c.get("company", request.company_name),
                "department":       "",
                "confidence_score": float(c.get("confidence", 0)),
            }
            for c in contacts_data
            if c.get("email")
        ]

        return ContactSearchResponse(
            total_contacts=len(contacts_list),
            contacts=contacts_list,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/outreach/send", response_model=EmailOutreachResponse)
async def send_outreach_email(request: EmailOutreachRequest):
    """
    Send outreach email to a contact
    
    Use this in n8n to send personalized cold emails.
    """
    try:
        db = SessionLocal()
        
        # Get job details
        job = db.query(Job).filter_by(id=request.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Load resume
        with open("data/resume.txt", "r") as f:
            resume_text = f.read()
        
        # Create email outreach
        email_outreach = EmailOutreach()
        
        # Create contact object
        from src.contact_finder import Contact as ContactData
        contact = ContactData(
            name=request.contact_name,
            title="",
            email=request.contact_email,
            company=job.company
        )
        
        # Generate personalized email
        email_template = await email_outreach.create_personalized_email(
            contact,
            job.title,
            job.description or "",
            resume_text
        )
        
        if not email_template:
            raise HTTPException(status_code=400, detail="Could not generate email - contact name may be invalid")
        
        # Send email if requested
        success = False
        if request.send_immediately:
            success = await email_outreach.send_email(
                contact,
                email_template,
                job.title
            )
        
        # Store in database
        contact_model = ContactModel(
            name=request.contact_name,
            email=request.contact_email,
            company=job.company,
            source="n8n_workflow"
        )
        db.add(contact_model)
        db.commit()
        
        outreach_record = OutreachRecord(
            contact_id=contact_model.id,
            job_id=job.id,
            subject=email_template.subject,
            body=email_template.body,
            template_type=email_template.template_type,
            status="sent" if success else "pending"
        )
        db.add(outreach_record)
        db.commit()
        
        outreach_id = outreach_record.id
        
        db.close()
        
        return EmailOutreachResponse(
            success=success or not request.send_immediately,
            message="Email sent successfully" if success else "Email queued for sending",
            outreach_id=outreach_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/outreach/follow-up", response_model=FollowUpResponse)
async def send_follow_ups(request: FollowUpRequest):
    """
    Send follow-up emails for non-responders
    
    Use this in n8n scheduled workflow to automate follow-ups.
    """
    try:
        db = SessionLocal()
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=request.days_since_sent)
        
        # Find outreach records needing follow-up
        records = db.query(OutreachRecord).filter(
            OutreachRecord.status == "sent",
            OutreachRecord.sent_at < cutoff_date,
            OutreachRecord.follow_up_sent == False
        ).all()
        
        follow_ups_sent = 0
        details = []
        
        email_outreach = EmailOutreach()
        
        for record in records[:10]:  # Limit to 10 follow-ups per call
            try:
                # Get contact and job info
                contact_model = db.query(ContactModel).filter_by(id=record.contact_id).first()
                job = db.query(Job).filter_by(id=record.job_id).first()
                
                if not contact_model or not job:
                    continue
                
                # Create follow-up email
                from src.contact_finder import Contact as ContactData
                contact = ContactData(
                    name=contact_model.name,
                    title=contact_model.title or "",
                    email=contact_model.email,
                    company=contact_model.company
                )
                
                # Simple follow-up template
                follow_up_subject = f"Following up: {job.title} at {job.company}"
                follow_up_body = f"""Dear {contact.name},

I wanted to follow up on my previous email regarding the {job.title} position at {job.company}.

I remain very interested in this opportunity and would love to discuss how my experience aligns with your needs.

Would you have 15 minutes this week for a brief conversation?

Best regards,
Kushall Jain"""
                
                from src.email_outreach import EmailTemplate
                follow_up_template = EmailTemplate(
                    subject=follow_up_subject,
                    body=follow_up_body,
                    template_type="follow_up"
                )
                
                # Send follow-up
                success = await email_outreach.send_email(
                    contact,
                    follow_up_template,
                    job.title
                )
                
                if success:
                    # Update record
                    record.follow_up_sent = True
                    record.follow_up_scheduled = datetime.now()
                    db.commit()
                    
                    follow_ups_sent += 1
                    details.append({
                        "contact": contact.name,
                        "company": job.company,
                        "job_title": job.title,
                        "sent_at": datetime.now().isoformat()
                    })
                
                # Rate limiting
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"Error sending follow-up: {e}")
                continue
        
        db.close()
        
        return FollowUpResponse(
            follow_ups_sent=follow_ups_sent,
            details=details
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats", response_model=OutreachStatsResponse)
async def get_outreach_stats():
    """
    Get outreach campaign statistics
    
    Use this in n8n to monitor campaign performance.
    """
    try:
        db = SessionLocal()
        
        total_outreach = db.query(OutreachRecord).count()
        sent = db.query(OutreachRecord).filter_by(status="sent").count()
        replied = db.query(OutreachRecord).filter_by(status="replied").count()
        no_response = db.query(OutreachRecord).filter(
            OutreachRecord.status == "sent",
            OutreachRecord.replied_at == None
        ).count()
        
        # Count pending follow-ups (sent > 7 days ago, no follow-up sent)
        cutoff_date = datetime.now() - timedelta(days=7)
        pending_follow_ups = db.query(OutreachRecord).filter(
            OutreachRecord.status == "sent",
            OutreachRecord.sent_at < cutoff_date,
            OutreachRecord.follow_up_sent == False
        ).count()
        
        db.close()
        
        return OutreachStatsResponse(
            total_outreach=total_outreach,
            sent=sent,
            replied=replied,
            no_response=no_response,
            pending_follow_ups=pending_follow_ups
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
async def get_job_details(job_id: int):
    """Get detailed information about a specific job"""
    try:
        db = SessionLocal()
        job = db.query(Job).filter_by(id=job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = {
            "id": job.id,
            "job_id": job.job_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "source": job.source,
            "description": job.description,
            "posted_date": job.posted_date.isoformat() if job.posted_date else None,
            "fetched_at": job.fetched_at.isoformat()
        }
        
        db.close()
        return job_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/outreach/{outreach_id}/status")
async def update_outreach_status(outreach_id: int, status: str):
    """
    Update outreach status (e.g., when you get a reply)
    
    Use this in n8n when monitoring email replies.
    """
    try:
        db = SessionLocal()
        record = db.query(OutreachRecord).filter_by(id=outreach_id).first()
        
        if not record:
            raise HTTPException(status_code=404, detail="Outreach record not found")
        
        record.status = status
        if status == "replied":
            record.replied_at = datetime.now()
        
        db.commit()
        db.close()
        
        return {"success": True, "message": f"Status updated to {status}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Run the server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)