import asyncio
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.contact_finder import ContactFinder, Contact as ContactData
from src.email_outreach import EmailOutreach
from src.database import SessionLocal
from src.models import Job, Contact, OutreachRecord
from datetime import datetime
import json

class OutreachProcessor:
    """Main orchestrator for job outreach pipeline"""
    
    def __init__(self):
        self.contact_finder = ContactFinder()
        self.email_outreach = EmailOutreach()
        self.db = SessionLocal()
    
    async def process_job_outreach(self, 
                                 job: Job, 
                                 resume_text: str,
                                 max_contacts: int = 3,
                                 send_emails: bool = True) -> Dict:
        """Process outreach for a single job"""
        
        print(f"🎯 Processing outreach for: {job.title} at {job.company}")
        
        # Step 1: Find contacts for the company
        contacts_data = await self.contact_finder.find_company_contacts(
            job.company, job.title
        )
        
        if not contacts_data:
            print(f"❌ No contacts found for {job.company}")
            return {'contacts_found': 0, 'emails_sent': 0}
        
        print(f"👥 Found {len(contacts_data)} potential contacts")
        
        # Step 2: Store contacts in database and filter existing outreach
        stored_contacts = []
        for contact_data in contacts_data[:max_contacts]:
            contact = self._store_contact(contact_data)
            if contact and not self._already_contacted(contact, job):
                stored_contacts.append(contact)
        
        if not stored_contacts:
            print(f"⏭️  All contacts already contacted for this job")
            return {'contacts_found': len(contacts_data), 'emails_sent': 0}
        
        print(f"📧 Will contact {len(stored_contacts)} new contacts")
        
        # Step 3: Send outreach emails
        emails_sent = 0
        if send_emails:
            for contact in stored_contacts:
                try:
                    # Create personalized email
                    email_template = await self.email_outreach.create_personalized_email(
                        self._contact_to_data(contact), 
                        job.title, 
                        job.description or "", 
                        resume_text
                    )
                    
                    # Skip if no email template (e.g., unknown contact name)
                    if not email_template:
                        print(f"⏭️  Skipping contact {contact.email} - no valid name")
                        continue
                    
                    # Send email
                    success = await self.email_outreach.send_email(
                        self._contact_to_data(contact), 
                        email_template, 
                        job.title
                    )
                    
                    if success:
                        # Record outreach in database
                        self._record_outreach(contact, job, email_template)
                        emails_sent += 1
                        
                        # Add delay between emails
                        await asyncio.sleep(30)  # 30 second delay
                    
                except Exception as e:
                    print(f"❌ Error sending email to {contact.name}: {e}")
                    continue
        
        return {
            'contacts_found': len(contacts_data),
            'contacts_stored': len(stored_contacts),
            'emails_sent': emails_sent
        }
    
    async def process_multiple_jobs(self, 
                                  job_ids: List[int] = None,
                                  resume_text: str = "",
                                  max_contacts_per_job: int = 2,
                                  send_emails: bool = True) -> Dict:
        """Process outreach for multiple jobs"""
        
        # Get jobs to process
        if job_ids:
            jobs = self.db.query(Job).filter(Job.id.in_(job_ids)).all()
        else:
            # Get jobs without outreach in the last 30 days
            jobs = self._get_jobs_needing_outreach()
        
        print(f"🚀 Processing outreach for {len(jobs)} jobs")
        
        total_stats = {
            'jobs_processed': 0,
            'total_contacts_found': 0,
            'total_emails_sent': 0,
            'jobs_with_contacts': 0
        }
        
        for job in jobs:
            try:
                result = await self.process_job_outreach(
                    job, resume_text, max_contacts_per_job, send_emails
                )
                
                total_stats['jobs_processed'] += 1
                total_stats['total_contacts_found'] += result['contacts_found']
                total_stats['total_emails_sent'] += result['emails_sent']
                
                if result['contacts_found'] > 0:
                    total_stats['jobs_with_contacts'] += 1
                
                # Delay between jobs to be respectful
                await asyncio.sleep(60)  # 1 minute delay between jobs
                
            except Exception as e:
                print(f"❌ Error processing job {job.title}: {e}")
                continue
        
        return total_stats
    
    def _store_contact(self, contact_data: ContactData) -> Optional[Contact]:
        """Store contact in database"""
        try:
            # Check if contact already exists
            existing = self.db.query(Contact).filter_by(
                email=contact_data.email,
                company=contact_data.company
            ).first()
            
            if existing:
                return existing
            
            # Create new contact
            contact = Contact(
                name=contact_data.name,
                title=contact_data.title,
                email=contact_data.email,
                linkedin_url=contact_data.linkedin_url,
                company=contact_data.company,
                department=contact_data.department,
                confidence_score=contact_data.confidence_score,
                source="automated_search"
            )
            
            self.db.add(contact)
            self.db.commit()
            return contact
            
        except IntegrityError:
            self.db.rollback()
            return None
        except Exception as e:
            print(f"❌ Error storing contact: {e}")
            self.db.rollback()
            return None
    
    def _already_contacted(self, contact: Contact, job: Job) -> bool:
        """Check if we've already contacted this person about this job"""
        existing = self.db.query(OutreachRecord).filter_by(
            contact_id=contact.id,
            job_id=job.id
        ).first()
        return existing is not None
    
    def _contact_to_data(self, contact: Contact) -> ContactData:
        """Convert database Contact to ContactData"""
        return ContactData(
            name=contact.name,
            title=contact.title or "",
            email=contact.email,
            linkedin_url=contact.linkedin_url,
            company=contact.company,
            department=contact.department or "",
            confidence_score=contact.confidence_score
        )
    
    def _record_outreach(self, contact: Contact, job: Job, email_template) -> OutreachRecord:
        """Record outreach attempt in database"""
        try:
            record = OutreachRecord(
                contact_id=contact.id,
                job_id=job.id,
                subject=email_template.subject,
                body=email_template.body,
                template_type=email_template.template_type,
                status="sent"
            )
            
            self.db.add(record)
            self.db.commit()
            return record
            
        except Exception as e:
            print(f"❌ Error recording outreach: {e}")
            self.db.rollback()
            return None
    
    def _get_jobs_needing_outreach(self, limit: int = 20) -> List[Job]:
        """Get jobs that need outreach (no recent outreach attempts)"""
        # Get jobs that either have no outreach records or 
        # haven't been contacted in the last 30 days
        from datetime import datetime, timedelta
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # This is a simplified query - you might want to make it more sophisticated
        jobs = self.db.query(Job).outerjoin(OutreachRecord).filter(
            (OutreachRecord.id == None) |  # No outreach records
            (OutreachRecord.sent_at < thirty_days_ago)  # Old outreach
        ).limit(limit).all()
        
        return jobs
    
    def get_outreach_stats(self) -> Dict:
        """Get outreach statistics"""
        total_contacts = self.db.query(Contact).count()
        total_outreach = self.db.query(OutreachRecord).count()
        
        # Get status breakdown
        status_counts = {}
        records = self.db.query(OutreachRecord).all()
        for record in records:
            status_counts[record.status] = status_counts.get(record.status, 0) + 1
        
        # Get top companies contacted
        company_counts = {}
        contacts = self.db.query(Contact).all()
        for contact in contacts:
            company_counts[contact.company] = company_counts.get(contact.company, 0) + 1
        
        return {
            'total_contacts': total_contacts,
            'total_outreach_attempts': total_outreach,
            'status_breakdown': status_counts,
            'companies_contacted': len(company_counts),
            'top_companies': sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    async def close(self):
        """Clean up resources"""
        await self.contact_finder.close()
        self.db.close()