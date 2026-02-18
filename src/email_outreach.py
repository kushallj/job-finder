import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from src.contact_finder import Contact
from src.ai.claude_service import ClaudeService
from src.config import settings

@dataclass
class EmailTemplate:
    subject: str
    body: str
    template_type: str  # 'hr_outreach', 'engineering_manager', 'follow_up'

@dataclass
class OutreachRecord:
    contact_email: str
    contact_name: str
    company: str
    job_title: str
    sent_date: datetime
    template_used: str
    status: str  # 'sent', 'bounced', 'replied', 'no_response'

class EmailOutreach:
    """Handle cold email outreach to HR and Engineering Managers"""
    
    def __init__(self):
        self.ai = ClaudeService()
        self.sent_emails: List[OutreachRecord] = []
        
        # Email configuration
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = settings.gmail_address
        self.sender_password = getattr(settings, 'gmail_password', None)
        self.sender_name = "Kushall Jain"  # Your name
        
        # Resume file path
        self.resume_pdf_path = "data/resume.pdf"  # We'll create this
        
    async def create_personalized_email(self, 
                                      contact: Contact, 
                                      job_title: str, 
                                      job_description: str,
                                      resume_text: str) -> Optional[EmailTemplate]:
        """Create a personalized cold email - only if we have contact's name"""
        
        # Don't send emails to "Unknown" contacts
        if not contact.name or contact.name.lower() in ['unknown', 'n/a', '']:
            print(f"⏭️  Skipping contact with unknown name: {contact.email}")
            return None
        
        # Determine email type based on contact title
        if any(word in contact.title.lower() for word in ['hr', 'human resources', 'people', 'talent', 'recruiter']):
            template_type = 'hr_outreach'
        else:
            template_type = 'engineering_manager'
        
        subject, body = await self._generate_email_content(
            contact, job_title, job_description, resume_text, template_type
        )
        
        return EmailTemplate(
            subject=subject,
            body=body,
            template_type=template_type
        )
    
    async def _generate_email_content(self, 
                                    contact: Contact, 
                                    job_title: str, 
                                    job_description: str,
                                    resume_text: str,
                                    template_type: str) -> tuple[str, str]:
        """Generate personalized email content using AI"""
        
        if template_type == 'hr_outreach':
            prompt = f"""Write a professional cold email to an HR manager about a job opportunity.

CONTEXT:
- Contact: {contact.name} ({contact.title}) at {contact.company}
- Job: {job_title}
- My name: Kushall Jain
- My background: {resume_text[:1000]}

REQUIREMENTS:
- Address them by name: "Dear {contact.name},"
- Professional but warm tone
- Show genuine interest in the company and role
- Highlight 2-3 most relevant skills/experiences from my background
- Mention that my resume is attached
- Ask for a brief conversation or consideration
- Keep it concise (150-200 words)
- End with "Best regards,\nKushall Jain"
- Include a clear subject line

FORMAT:
Subject: [Your subject line]

Body:
[Your email body ending with "Best regards,\nKushall Jain"]

Write the email now:"""

        else:  # engineering_manager
            prompt = f"""Write a professional cold email to an engineering manager about a job opportunity.

CONTEXT:
- Contact: {contact.name} ({contact.title}) at {contact.company}
- Job: {job_title}
- Job Description: {job_description[:800]}
- My name: Kushall Jain
- My background: {resume_text[:1000]}

REQUIREMENTS:
- Address them by name: "Dear {contact.name},"
- Technical but approachable tone
- Show understanding of their tech challenges
- Highlight relevant technical experience from my background
- Mention specific technologies from the job description
- Mention that my resume is attached
- Ask for a technical conversation
- Keep it concise (150-200 words)
- End with "Best regards,\nKushall Jain"
- Include a clear subject line

FORMAT:
Subject: [Your subject line]

Body:
[Your email body ending with "Best regards,\nKushall Jain"]

Write the email now:"""
        
        try:
            response = await self.ai._call_claude(prompt, max_tokens=1024)
            
            # Parse subject and body
            lines = response.strip().split('\n')
            subject_line = ""
            body_lines = []
            
            for i, line in enumerate(lines):
                if line.startswith('Subject:'):
                    subject_line = line.replace('Subject:', '').strip()
                elif line.startswith('Body:'):
                    body_lines = lines[i+1:]
                    break
                elif subject_line and not line.startswith('Body:'):
                    body_lines.append(line)
            
            subject = subject_line or f"Interest in {job_title} role at {contact.company}"
            body = '\n'.join(body_lines).strip()
            
            return subject, body
            
        except Exception as e:
            print(f"❌ Error generating email content: {e}")
            # Fallback template
            subject = f"Interest in {job_title} role at {contact.company}"
            body = f"""Dear {contact.name},

I hope this email finds you well. I came across the {job_title} position at {contact.company} and I'm very interested in the opportunity.

With my background in software development, I believe I could contribute meaningfully to your team. I've attached my resume for your review and would love to discuss how my experience aligns with your needs.

Would you be available for a brief conversation this week?

Best regards,
Kushall Jain"""
            
            return subject, body
    
    async def send_email(self, 
                        contact: Contact, 
                        email_template: EmailTemplate,
                        job_title: str) -> bool:
        """Send email to a contact with resume attachment"""
        
        if not self.sender_password:
            print("❌ Gmail password not configured. Please add GMAIL_PASSWORD to your .env file")
            return False
        
        # Check if resume PDF exists
        if not os.path.exists(self.resume_pdf_path):
            print(f"❌ Resume PDF not found at {self.resume_pdf_path}")
            print("Please create a PDF version of your resume or update the path")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = contact.email
            msg['Subject'] = email_template.subject
            
            # Add body
            msg.attach(MIMEText(email_template.body, 'plain'))
            
            # Attach resume PDF
            with open(self.resume_pdf_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= "Kushall_Jain_Resume.pdf"'
            )
            msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, contact.email, text)
            server.quit()
            
            # Record the outreach
            record = OutreachRecord(
                contact_email=contact.email,
                contact_name=contact.name,
                company=contact.company,
                job_title=job_title,
                sent_date=datetime.now(),
                template_used=email_template.template_type,
                status='sent'
            )
            self.sent_emails.append(record)
            
            print(f"✅ Email sent to {contact.name} at {contact.company} (with resume attached)")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email to {contact.email}: {e}")
            return False
    
    async def send_bulk_outreach(self, 
                               contacts: List[Contact], 
                               job_title: str,
                               job_description: str,
                               resume_text: str,
                               delay_seconds: int = 60) -> Dict[str, int]:
        """Send outreach emails to multiple contacts with delays"""
        
        results = {'sent': 0, 'failed': 0}
        
        for i, contact in enumerate(contacts):
            try:
                # Create personalized email
                email_template = await self.create_personalized_email(
                    contact, job_title, job_description, resume_text
                )
                
                # Send email
                success = await self.send_email(contact, email_template, job_title)
                
                if success:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
                
                # Add delay between emails to avoid being flagged as spam
                if i < len(contacts) - 1:  # Don't delay after the last email
                    print(f"⏳ Waiting {delay_seconds} seconds before next email...")
                    await asyncio.sleep(delay_seconds)
                    
            except Exception as e:
                print(f"❌ Error processing contact {contact.email}: {e}")
                results['failed'] += 1
                continue
        
        return results
    
    def get_outreach_stats(self) -> Dict:
        """Get statistics about sent emails"""
        total_sent = len(self.sent_emails)
        
        if total_sent == 0:
            return {'total_sent': 0}
        
        # Group by status
        status_counts = {}
        for record in self.sent_emails:
            status_counts[record.status] = status_counts.get(record.status, 0) + 1
        
        # Group by company
        company_counts = {}
        for record in self.sent_emails:
            company_counts[record.company] = company_counts.get(record.company, 0) + 1
        
        return {
            'total_sent': total_sent,
            'status_breakdown': status_counts,
            'companies_contacted': len(company_counts),
            'top_companies': sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def save_outreach_log(self, filename: str = "outreach_log.json"):
        """Save outreach records to file"""
        records_dict = []
        for record in self.sent_emails:
            records_dict.append({
                'contact_email': record.contact_email,
                'contact_name': record.contact_name,
                'company': record.company,
                'job_title': record.job_title,
                'sent_date': record.sent_date.isoformat(),
                'template_used': record.template_used,
                'status': record.status
            })
        
        with open(filename, 'w') as f:
            json.dump(records_dict, f, indent=2)
        
        print(f"📄 Outreach log saved to {filename}")
    
    def load_outreach_log(self, filename: str = "outreach_log.json"):
        """Load outreach records from file"""
        try:
            with open(filename, 'r') as f:
                records_dict = json.load(f)
            
            self.sent_emails = []
            for record_dict in records_dict:
                record = OutreachRecord(
                    contact_email=record_dict['contact_email'],
                    contact_name=record_dict['contact_name'],
                    company=record_dict['company'],
                    job_title=record_dict['job_title'],
                    sent_date=datetime.fromisoformat(record_dict['sent_date']),
                    template_used=record_dict['template_used'],
                    status=record_dict['status']
                )
                self.sent_emails.append(record)
            
            print(f"📄 Loaded {len(self.sent_emails)} outreach records from {filename}")
            
        except FileNotFoundError:
            print(f"📄 No existing outreach log found at {filename}")
        except Exception as e:
            print(f"❌ Error loading outreach log: {e}")