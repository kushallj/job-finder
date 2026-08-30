from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models import Job, Contact, OutreachRecord, XOAuthToken
from .models import XProfile, XTweet, XContext, XEngagementAction
from .auth import x_oauth, XOAuthHandler
from .client import x_client, XClient
from .message_generator import x_message_generator, XMessageGenerator
from .rate_limiter import default_x_limiter, XRateLimiter

log = logging.getLogger(__name__)


class XReferralService:
    """Orchestrates X (Twitter) referral workflows, hiring tweet discovery, and CRM engagement."""

    def __init__(
        self,
        client: Optional[XClient] = None,
        generator: Optional[XMessageGenerator] = None,
        oauth_handler: Optional[XOAuthHandler] = None,
        rate_limiter: Optional[XRateLimiter] = None,
    ):
        self.client = client or x_client
        self.generator = generator or x_message_generator
        self.oauth_handler = oauth_handler or x_oauth
        self.rate_limiter = rate_limiter or default_x_limiter

    def get_active_targets(self, db: Session, limit: int = 30) -> List[Dict[str, Any]]:
        """Extracts active target companies and roles currently in the pipeline."""
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
                    "source": j.source or "pipeline",
                })
        return targets

    def search_company_referrals(self, company: str, role: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Searches X tech leaders, engineering managers, and recruiters for a company."""
        self.rate_limiter.acquire(1.0)
        profiles = self.client.search_users_by_company(company, role=role, limit=limit)
        return {
            "company": company,
            "role": role,
            "source": self.client.mode,
            "count": len(profiles),
            "profiles": [p.model_dump() for p in profiles],
        }

    def search_hiring_tweets(self, company: str, role: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Searches active hiring announcements and referral tweets for a company."""
        self.rate_limiter.acquire(1.0)
        tweets = self.client.search_hiring_tweets(company, role=role, limit=limit)
        return {
            "company": company,
            "role": role,
            "count": len(tweets),
            "tweets": [t.model_dump() for t in tweets],
        }

    def generate_message(
        self,
        action_type: str,
        profile_data: Dict[str, Any],
        context_data: Dict[str, Any],
        tweet_data: Optional[Dict[str, Any]] = None,
        max_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generates AI-crafted contextual tweet replies, quote tweets, or DMs."""
        profile = XProfile(**profile_data)
        ctx = XContext(**context_data)
        tweet = XTweet(**tweet_data) if tweet_data else None

        if action_type == "reply":
            msg = self.generator.generate_tweet_reply(profile, tweet, ctx, max_length=max_length or 280)
            limit = max_length or 280
        elif action_type == "quote":
            msg = self.generator.generate_quote_tweet(profile, tweet, ctx, max_length=max_length or 280)
            limit = max_length or 280
        else:  # dm
            msg = self.generator.generate_dm(profile, ctx, max_length=max_length or 1000)
            limit = max_length or 1000

        intent_url = self.client.get_intent_url(
            action_type=action_type,
            username=profile.username,
            tweet_id=tweet.tweet_id if tweet else None,
            text=msg,
        )

        return {
            "action_type": action_type,
            "message": msg,
            "char_count": len(msg),
            "is_under_limit": len(msg) <= limit,
            "intent_url": intent_url,
        }

    def sync_profiles_to_contacts(self, db: Session, profiles_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Ingests and upserts discovered X profiles into the Contacts CRM table."""
        synced_count = 0
        new_contacts_count = 0

        for p_dict in profiles_data:
            name = (p_dict.get("name") or p_dict.get("username") or "").strip()
            company = (p_dict.get("company") or "Tech Company").strip()
            username = (p_dict.get("username") or "").lstrip("@").strip()
            if not username:
                continue

            x_url = f"https://x.com/{username}"
            existing = db.query(Contact).filter(Contact.linkedin_url == x_url).first()
            if not existing:
                existing = db.query(Contact).filter(
                    func.lower(Contact.name) == name.lower(),
                    func.lower(Contact.company) == company.lower(),
                ).first()

            if existing:
                if not existing.linkedin_url:
                    existing.linkedin_url = x_url
                if p_dict.get("title") and not existing.title:
                    existing.title = p_dict.get("title")
                synced_count += 1
            else:
                contact = Contact(
                    name=name,
                    company=company,
                    title=p_dict.get("title") or "Tech Engineer / Leader",
                    linkedin_url=x_url,
                    source="x_referral",
                    confidence_score=85,
                    found_at=datetime.utcnow(),
                )
                db.add(contact)
                new_contacts_count += 1
                synced_count += 1

        db.commit()
        return {"synced_count": synced_count, "new_contacts_count": new_contacts_count}

    async def engage_user(
        self,
        db: Session,
        action_type: str,
        target_username: str,
        company: str,
        target_user_id: Optional[str] = None,
        tweet_id: Optional[str] = None,
        message_text: Optional[str] = None,
        job_id: Optional[int] = None,
        user_identifier: str = "default_user",
    ) -> Dict[str, Any]:
        """
        Executes engagement action (follow, like, repost, reply, DM),
        enforces rate limits, and records into OutreachRecord.
        """
        if not self.rate_limiter.check_daily_limit(action_type):
            raise ValueError(f"Daily limit reached for action '{action_type}' ({self.rate_limiter.get_daily_usage()[action_type]['limit']} per day).")

        token_rec = self.oauth_handler.get_token(db, user_identifier=user_identifier)
        access_token = token_rec.access_token if token_rec else None
        source_user_id = token_rec.x_user_id if token_rec else None

        result = await self.client.execute_action(
            action_type=action_type,
            target_username=target_username,
            target_user_id=target_user_id,
            tweet_id=tweet_id,
            message_text=message_text,
            access_token=access_token,
            source_user_id=source_user_id,
        )

        self.rate_limiter.record_daily_action(action_type)

        # Log into OutreachRecord
        contact = db.query(Contact).filter(
            Contact.linkedin_url == f"https://x.com/{target_username.lstrip('@')}"
        ).first()

        if not contact:
            contact = Contact(
                name=target_username,
                company=company or "Tech Company",
                linkedin_url=f"https://x.com/{target_username.lstrip('@')}",
                source="x_referral",
                confidence_score=80,
                found_at=datetime.utcnow(),
            )
            db.add(contact)
            db.commit()
            db.refresh(contact)

        rec = OutreachRecord(
            contact_id=contact.id,
            job_id=job_id,
            subject=f"X (Twitter) Engagement — @{target_username.lstrip('@')} ({action_type})",
            body=message_text or f"X action: {action_type}",
            template_type="x_referral",
            status="sent",
            sent_at=datetime.utcnow(),
            email_sent=False,
            contact_name=target_username,
            contact_email=f"{target_username.lstrip('@')}@x.com",
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

        return {
            "status": "success",
            "outreach_id": rec.id,
            "action_type": action_type,
            "target": target_username,
            "intent_url": result.get("intent_url"),
            "mode": result.get("mode", "api"),
            "daily_usage": self.rate_limiter.get_daily_usage(),
        }


x_referral_service = XReferralService()
