from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func

from src.models import Job, Application, Contact, OutreachRecord
from .models import ReferralProfile, ReferralContext
from .linkedin_client import linkedin_client, LinkedInClient
from .message_generator import message_generator, ReferralMessageGenerator
from .rate_limiter import default_rate_limiter

log = logging.getLogger(__name__)


class ReferralService:
    """Orchestrates referral search, message generation, and CRM database synchronization."""

    def __init__(
        self,
        client: Optional[LinkedInClient] = None,
        generator: Optional[ReferralMessageGenerator] = None,
    ):
        self.client = client or linkedin_client
        self.generator = generator or message_generator

    def get_active_targets(self, db: Session, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Retrieves active target companies and roles currently in the pipeline.
        Prioritizes applications in 'ready', 'saved', or 'applied' stages.
        """
        query = (
            db.query(Job)
            .filter(Job.company.isnot(None), Job.company != "")
            .order_by(Job.fetched_at.desc())
            .limit(limit)
        )
        jobs = query.all()

        seen_companies = set()
        targets = []
        for j in jobs:
            c_clean = j.company.strip()
            if c_clean.lower() not in seen_companies:
                seen_companies.add(c_clean.lower())
                targets.append({
                    "job_id": j.id,
                    "company": c_clean,
                    "role_title": j.title,
                    "location": j.location or "Remote",
                    "job_url": j.url,
                    "source": j.source or "pipeline",
                })
        return targets

    def search_company_referrals(self, company: str, limit: int = 10) -> Dict[str, Any]:
        """Searches LinkedIn referral contacts for a target company with rate limiting."""
        default_rate_limiter.acquire(f"company:{company.lower()}", tokens=1.0)
        profiles = self.client.search_by_company(company, limit=limit)
        return {
            "company": company,
            "source": self.client.mode,
            "count": len(profiles),
            "profiles": [p.model_dump() for p in profiles],
        }

    def sync_profiles_to_contacts(self, db: Session, profiles_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Ingests and upserts discovered LinkedIn referral profiles into the SQLite Contacts CRM.
        Deduplicates by linkedin_url or name + company.
        """
        synced_count = 0
        new_contacts_count = 0

        for p_dict in profiles_data:
            name = (p_dict.get("full_name") or p_dict.get("name") or "").strip()
            company = (p_dict.get("company") or "").strip()
            if not name or not company:
                continue

            linkedin_url = p_dict.get("linkedin_url")
            existing = None
            if linkedin_url:
                existing = db.query(Contact).filter(Contact.linkedin_url == linkedin_url).first()
            if not existing:
                existing = db.query(Contact).filter(
                    func.lower(Contact.name) == name.lower(),
                    func.lower(Contact.company) == company.lower(),
                ).first()

            if existing:
                # Update existing contact
                if p_dict.get("title") and not existing.title:
                    existing.title = p_dict.get("title")
                if linkedin_url and not existing.linkedin_url:
                    existing.linkedin_url = linkedin_url
                synced_count += 1
            else:
                contact = Contact(
                    name=name,
                    company=company,
                    title=p_dict.get("title") or p_dict.get("headline"),
                    linkedin_url=linkedin_url,
                    source="linkedin_referral",
                    confidence_score=85 if linkedin_url else 70,
                    found_at=datetime.utcnow(),
                )
                db.add(contact)
                new_contacts_count += 1
                synced_count += 1

        db.commit()
        return {"synced_count": synced_count, "new_contacts_count": new_contacts_count}

    def generate_referral_note(
        self,
        profile_data: Dict[str, Any],
        context_data: Dict[str, Any],
        max_length: Optional[int] = 200,
    ) -> Dict[str, Any]:
        """Generates a personalized connection note and full referral letter."""
        profile = ReferralProfile(**profile_data)
        ctx = ReferralContext(**context_data)

        full_letter = self.generator.generate_letter(profile, ctx)
        connection_note = self.generator.generate_connection_note(profile, ctx, max_length=max_length or 200)

        return {
            "connection_note": connection_note,
            "full_letter": full_letter,
            "char_count": len(connection_note),
            "is_under_limit": len(connection_note) <= (max_length or 200),
        }

    def log_referral_action(
        self,
        db: Session,
        contact_name: str,
        company: str,
        action_type: str,
        linkedin_url: Optional[str] = None,
        contact_email: Optional[str] = None,
        message_body: Optional[str] = None,
        job_id: Optional[int] = None,
    ) -> OutreachRecord:
        """
        Logs a referral action (connection invite sent, message sent, replied)
        into the OutreachRecord table and updates CRM analytics.
        """
        contact = None
        if linkedin_url:
            contact = db.query(Contact).filter(Contact.linkedin_url == linkedin_url).first()
        if not contact:
            contact = db.query(Contact).filter(
                func.lower(Contact.name) == contact_name.lower(),
                func.lower(Contact.company) == company.lower(),
            ).first()

        if not contact:
            contact = Contact(
                name=contact_name,
                company=company,
                email=contact_email,
                linkedin_url=linkedin_url,
                source="linkedin_referral",
                confidence_score=80,
                found_at=datetime.utcnow(),
            )
            db.add(contact)
            db.commit()
            db.refresh(contact)

        # Map action_type to OutreachRecord status
        status_map = {
            "connection_sent": "sent",
            "message_sent": "sent",
            "replied": "replied",
        }
        rec_status = status_map.get(action_type, "sent")

        record = OutreachRecord(
            contact_id=contact.id,
            job_id=job_id,
            subject=f"LinkedIn Referral Outreach — {contact_name}",
            body=message_body or f"Referral action: {action_type}",
            template_type="linkedin_referral",
            status=rec_status,
            sent_at=datetime.utcnow(),
            replied_at=datetime.utcnow() if action_type == "replied" else None,
            email_sent=False,
            contact_email=contact_email or contact.email or f"{contact_name.lower().replace(' ', '.')}@linkedin",
            contact_name=contact_name,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record


referral_service = ReferralService()
