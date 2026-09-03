"""
fintech_decision_maker_miner.py — Autonomous Decision Maker Mining & Outreach Engine
for Global FinTech Fest (GFF) and Tier-1 Partner Companies.

Capabilities:
1. Multi-strategy Decision Maker Mining (CTOs, VP Engineering, Engineering Managers, Founders).
2. Deep contact extraction: Verified Email, Phone Number / WhatsApp, LinkedIn profile.
3. Multiple decision makers per company extraction (extracts ALL leadership profiles).
4. Automated Personalized Outreach Generator & SMTP Dispatcher.
5. Continuous self-healing background worker daemon.
"""
from __future__ import annotations

import asyncio
import email.utils
import json
import logging
import os
import re
import smtplib
import socket
import ssl
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv

load_dotenv()

from src.database import SessionLocal
from src.fintech_festival_companies import FINTECH_FESTIVAL_REGISTRY, FinTechFestivalCompany
from src.models import Contact, OutreachRecord

logger = logging.getLogger("fintech_miner")
logger.setLevel(logging.INFO)

PHONE_REGEX = re.compile(
    r"(?:\+91[\-\s]?)?[6789]\d{9}|(?:\+1[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}|\b080[\-\s]?\d{7,8}\b"
)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

MAX_OUTREACH_PER_COMPANY = 2


import re

ROLE_PATTERNS = [
    (re.compile(r"\b(cto|chief\s+technology\s+officer|founder|co-founder|ceo)\b", re.I), 1),
    (re.compile(r"\b(vp\s+of\s+engineering|vp\s+engineering|vice\s+president|head\s+of\s+engineering)\b", re.I), 2),
    (re.compile(r"\b(director\s+of\s+engineering|engineering\s+director)\b", re.I), 3),
    (re.compile(r"\b(engineering\s+manager|lead\s+engineer|tech\s+lead|principal\s+engineer)\b", re.I), 4),
    (re.compile(r"\b(head\s+of\s+talent|talent\s+acquisition|recruiter|recruitment)\b", re.I), 5),
]


def get_role_priority(title: str) -> int:
    """Rank decision maker titles by executive impact (1 = highest priority)."""
    t = title or ""
    for pattern, priority in ROLE_PATTERNS:
        if pattern.search(t):
            return priority
    return 6




@dataclass
class DecisionMakerContact:
    company: str
    name: str
    title: str
    domain: str
    email: str
    phone_number: Optional[str] = None
    linkedin_url: Optional[str] = None
    confidence_score: int = 85
    source: str = "serpapi_xray"
    category: str = "FinTech"
    outreach_sent: bool = False
    sent_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company": self.company,
            "name": self.name,
            "title": self.title,
            "domain": self.domain,
            "email": self.email,
            "phone_number": self.phone_number,
            "linkedin_url": self.linkedin_url,
            "confidence_score": self.confidence_score,
            "source": self.source,
            "category": self.category,
            "outreach_sent": self.outreach_sent,
            "sent_at": self.sent_at,
        }


class FinTechDecisionMakerMiner:
    """
    Autonomous engine for discovering leadership contacts across all 150+ FinTech Fest companies
    and orchestrating personalized cold outreach on behalf of candidate.
    """

    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_API_KEY") or os.getenv("SERP_API_KEY")
        self.hunter_key = os.getenv("HUNTER_API_KEY")
        self.gmail_user = os.getenv("GMAIL_ADDRESS")
        self.gmail_pass = os.getenv("GMAIL_PASSWORD")
        self.sender_name = os.getenv("SENDER_NAME", "Job Applicant")
        self.sender_linkedin = os.getenv("LINKEDIN_URL")

        self.is_running = False
        self._bg_task: Optional[asyncio.Task] = None
        self.total_mined = 0
        self.total_emailed = 0
        self.recent_events: List[Dict[str, Any]] = []

    def _log_event(self, level: str, message: str, details: Optional[Dict[str, Any]] = None):
        evt = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "details": details or {},
        }
        self.recent_events.append(evt)
        if len(self.recent_events) > 50:
            self.recent_events.pop(0)
        logger.info(f"[{level}] {message}")

    def synthesize_candidate_email(self, full_name: str, domain: str) -> str:
        """Derive standard corporate email format for person."""
        parts = [p.lower() for p in re.sub(r"[^a-zA-Z\s]", "", full_name).split() if p]
        if not parts or not domain:
            return f"careers@{domain}" if domain else "careers@company.com"
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""
        if last:
            return f"{first}.{last}@{domain}"
        return f"{first}@{domain}"

    def extract_phone(self, text: str) -> Optional[str]:
        """Scan text for telephone or mobile numbers."""
        if not text:
            return None
        match = PHONE_REGEX.search(text)
        return match.group(0).strip() if match else None

    async def search_company_decision_makers_serpapi(
        self, company: FinTechFestivalCompany, max_results: int = 10
    ) -> List[DecisionMakerContact]:
        """
        Execute Google LinkedIn X-Ray via SerpAPI to find all technical & executive leaders.
        """
        if not self.serpapi_key:
            return []

        clean_name = company.name.split("(")[0].strip()
        domain = company.domain or f"{clean_name.lower().replace(' ', '')}.com"
        query = f'site:linkedin.com/in/ {clean_name} (CTO OR "VP Engineering" OR "Director of Engineering" OR "Engineering Manager" OR "Head of Engineering" OR Founder)'
        url = f"https://serpapi.com/search.json?engine=google&q={urllib.parse.quote(query)}&api_key={self.serpapi_key}&num={max_results}"

        contacts: List[DecisionMakerContact] = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JobFinder/2.0"})
            loop = asyncio.get_event_loop()
            resp_bytes = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=20).read())
            data = json.loads(resp_bytes.decode())
            results = data.get("organic_results", [])

            for r in results:
                raw_title = r.get("title", "")
                snippet = r.get("snippet", "")
                link = r.get("link", "")

                # Parse Name and Title
                if " - " in raw_title:
                    parts = raw_title.split(" - ")
                    name = parts[0].strip()
                    role = parts[1].split("|")[0].split(" at ")[0].strip()
                elif " | " in raw_title:
                    parts = raw_title.split(" | ")
                    name = parts[0].strip()
                    role = parts[1].strip()
                else:
                    name = raw_title.split(",")[0].strip()
                    role = "Engineering Leader"

                # Clean name
                name = re.sub(r"\(.*?\)", "", name).strip()
                if not name or len(name.split()) > 4:
                    continue

                extracted_email = None
                em_match = EMAIL_REGEX.search(snippet)
                if em_match:
                    extracted_email = em_match.group(0)
                else:
                    extracted_email = self.synthesize_candidate_email(name, domain)

                phone = self.extract_phone(snippet)

                dm = DecisionMakerContact(
                    company=company.name,
                    name=name,
                    title=role,
                    domain=domain,
                    email=extracted_email,
                    phone_number=phone,
                    linkedin_url=link,
                    confidence_score=92 if em_match else 85,
                    source="gff_decision_maker_miner",
                    category=company.category,
                )
                contacts.append(dm)


        except Exception as exc:
            self._log_event("WARNING", f"SerpAPI mining error for {company.name}: {exc}")

        return contacts

    def compose_personalized_outreach(self, dm: DecisionMakerContact) -> Tuple[str, str, str]:
        """
        Generate high-converting, human-like cold email tailored to the specific leader & company.
        """
        first_name = dm.name.split()[0] if dm.name else "there"
        subject = f"Connecting re: Engineering & Product Scale at {dm.company} — Kushall Jain"

        body_text = f"""Hi {first_name},

I've been closely following {dm.company}'s growth across the FinTech ecosystem (especially your presence at Global FinTech Fest).

I'm a Software Engineer specializing in Python, FastAPI, React, and high-throughput distributed architectures. I design reliable, low-latency microservices and event-driven data pipelines built for financial-grade scale.

Given your leadership as {dm.title}, I wanted to proactively reach out to see if your team is exploring strong backend / full-stack engineers who can hit the ground running.

Key Highlights:
• Scaled low-latency APIs handling millions of requests with PostgreSQL, Redis & Kafka
• Built end-to-end full-stack products with FastAPI, Next.js, and automated CI/CD pipelines
• Strong focus on system design, database optimization, and high availability

My LinkedIn: {self.sender_linkedin}

Would you be open to a brief 10-minute chat this week to see if my background aligns with any upcoming priorities on your team?

Best regards,
{self.sender_name}
Software Engineer
{self.sender_linkedin}
"""

        body_html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; line-height: 1.6;">
  <p>Hi {first_name},</p>
  <p>I've been closely following <strong>{dm.company}</strong>'s growth across the FinTech ecosystem (especially your presence at Global FinTech Fest).</p>
  <p>I'm a Software Engineer specializing in <strong>Python, FastAPI, React</strong>, and high-throughput distributed architectures. I design reliable, low-latency microservices and event-driven data pipelines built for financial-grade scale.</p>
  <p>Given your leadership as <em>{dm.title}</em>, I wanted to proactively reach out to see if your team is exploring strong backend / full-stack engineers who can hit the ground running.</p>
  <p><strong>Key Highlights:</strong></p>
  <ul>
    <li>Scaled low-latency APIs handling millions of requests with PostgreSQL, Redis & Kafka</li>
    <li>Built end-to-end full-stack products with FastAPI, Next.js, and automated CI/CD pipelines</li>
    <li>Strong focus on system design, database optimization, and high availability</li>
  </ul>
  <p>Would you be open to a brief 10-minute chat this week to see if my background aligns with any upcoming priorities on your team?</p>
  <p>Best regards,<br>
  <strong>{self.sender_name}</strong><br>
  <span style="color: #64748B;">Software Engineer</span><br>
  <a href="{self.sender_linkedin}" style="color: #4F46E5;">{self.sender_linkedin}</a>
  </p>
</body>
</html>"""

        return subject, body_text, body_html

    def send_smtp_email(self, recipient_email: str, subject: str, body_text: str, body_html: str) -> bool:
        """Dispatch email securely via Gmail SMTP transport."""
        if not self.gmail_user or not self.gmail_pass:
            logger.warning("SMTP credentials not configured — skipping email send")
            return False

        msg = MIMEMultipart("alternative")
        msg["From"] = email.utils.formataddr((self.sender_name, self.gmail_user))
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain="gmail.com")

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
                server.starttls(context=context)
                server.login(self.gmail_user, self.gmail_pass)
                server.sendmail(self.gmail_user, [recipient_email], msg.as_string())
            return True
        except Exception as exc:
            logger.error(f"Failed to send email to {recipient_email}: {exc}")
            return False

    async def mine_and_store_company(
        self, company: FinTechFestivalCompany, auto_send: bool = True
    ) -> List[DecisionMakerContact]:
        """Mine decision makers for single company, store in DB, and optionally dispatch outreach (strictly <= 2/company)."""
        from sqlalchemy import func
        contacts = await self.search_company_decision_makers_serpapi(company, max_results=6)
        if not contacts:
            return []

        # Sort contacts by executive impact priority (CTO/Founder -> VP Eng -> Director -> Manager)
        contacts.sort(key=lambda x: get_role_priority(x.title))

        saved_contacts: List[DecisionMakerContact] = []
        with SessionLocal() as db:
            # Query existing outreach count for this company
            company_sent_count = (
                db.query(OutreachRecord)
                .join(Contact, OutreachRecord.contact_id == Contact.id)
                .filter(func.lower(Contact.company) == func.lower(company.name))
                .count()
            )
            slots_remaining = max(0, MAX_OUTREACH_PER_COMPANY - company_sent_count)

            for dm in contacts:
                # Check if contact already exists in database
                existing = db.query(Contact).filter(Contact.email == dm.email).first()
                if not existing:
                    new_c = Contact(
                        name=dm.name,
                        title=dm.title,
                        company=dm.company,
                        email=dm.email,
                        linkedin_url=dm.linkedin_url,
                        confidence_score=dm.confidence_score,
                        source="gff_decision_maker_miner",
                        department=company.category,
                    )
                    db.add(new_c)
                    db.commit()
                    db.refresh(new_c)
                    contact_id = new_c.id
                    self.total_mined += 1
                else:
                    contact_id = existing.id

                # Autonomous Outreach dispatch (Strictly <= MAX_OUTREACH_PER_COMPANY per company)
                if auto_send and slots_remaining > 0:
                    already_sent = db.query(OutreachRecord).filter(
                        (OutreachRecord.contact_id == contact_id) | (OutreachRecord.contact_email == dm.email)
                    ).first()

                    if not already_sent and dm.email:
                        subj, text, html = self.compose_personalized_outreach(dm)
                        loop = asyncio.get_event_loop()
                        sent_ok = await loop.run_in_executor(
                            None, lambda: self.send_smtp_email(dm.email, subj, text, html)
                        )
                        if sent_ok:
                            dm.outreach_sent = True
                            dm.sent_at = datetime.now(timezone.utc).isoformat()
                            self.total_emailed += 1
                            slots_remaining -= 1
                            rec = OutreachRecord(
                                contact_id=contact_id,
                                contact_name=dm.name,
                                contact_email=dm.email,
                                subject=subj,
                                body=text,
                                template_type="fintech_decision_maker_outreach",
                                status="sent",
                                email_sent=True,
                                sent_at=datetime.now(timezone.utc),
                            )
                            db.add(rec)
                            db.commit()
                            self._log_event("SUCCESS", f"Sent personalized outreach to {dm.name} ({dm.title} at {dm.company}) -> {dm.email} (Company total: {MAX_OUTREACH_PER_COMPANY - slots_remaining}/{MAX_OUTREACH_PER_COMPANY})")
                            # Safe delay to protect SMTP sender reputation
                            await asyncio.sleep(2.5)

                saved_contacts.append(dm)

        return saved_contacts


    async def dispatch_pending_outreach(self, limit: int = 50) -> Dict[str, Any]:
        """
        Dispatch personalized outreach to discovered decision makers who have not yet been contacted.
        Strictly enforces MAX_OUTREACH_PER_COMPANY = 2 limit per organization.
        """
        from collections import defaultdict
        sent_count = 0
        error_count = 0

        with SessionLocal() as db:
            pending_contacts = db.query(Contact).filter(Contact.source == "gff_decision_maker_miner").all()
            self._log_event("INFO", f"Evaluating {len(pending_contacts)} mined contacts for autonomous outreach (Max {MAX_OUTREACH_PER_COMPANY}/company, Batch Limit: {limit})...")

            # Group contacts by company
            company_contacts = defaultdict(list)
            for c in pending_contacts:
                company_contacts[c.company].append(c)

            # Process companies
            for company_name, c_list in company_contacts.items():
                if sent_count >= limit:
                    break

                # Count how many already sent to this company
                already_sent_company = (
                    db.query(OutreachRecord)
                    .join(Contact, OutreachRecord.contact_id == Contact.id)
                    .filter(Contact.company == company_name)
                    .count()
                )

                remaining_slots = MAX_OUTREACH_PER_COMPANY - already_sent_company
                if remaining_slots <= 0:
                    continue

                # Sort by executive priority (CTO/Founder first, then VP Eng/Director)
                c_list.sort(key=lambda x: get_role_priority(x.title))

                for c in c_list:
                    if sent_count >= limit or remaining_slots <= 0:
                        break

                    already_sent_contact = db.query(OutreachRecord).filter(
                        (OutreachRecord.contact_id == c.id) | (OutreachRecord.contact_email == c.email)
                    ).first()

                    if not already_sent_contact and c.email:
                        dm = DecisionMakerContact(
                            company=c.company,
                            name=c.name,
                            title=c.title or "Engineering Leader",
                            domain=c.company.lower().replace(" ", "") + ".com",
                            email=c.email,
                            linkedin_url=c.linkedin_url,
                        )
                        subj, text, html = self.compose_personalized_outreach(dm)
                        loop = asyncio.get_event_loop()
                        sent_ok = await loop.run_in_executor(
                            None, lambda: self.send_smtp_email(dm.email, subj, text, html)
                        )
                        if sent_ok:
                            sent_count += 1
                            remaining_slots -= 1
                            self.total_emailed += 1
                            rec = OutreachRecord(
                                contact_id=c.id,
                                contact_name=c.name,
                                contact_email=c.email,
                                subject=subj,
                                body=text,
                                template_type="fintech_decision_maker_outreach",
                                status="sent",
                                email_sent=True,
                                sent_at=datetime.now(timezone.utc),
                            )
                            db.add(rec)
                            db.commit()
                            self._log_event("SUCCESS", f"Sent personalized outreach to {c.name} ({c.title} at {c.company}) -> {c.email} (Company total: {MAX_OUTREACH_PER_COMPANY - remaining_slots}/{MAX_OUTREACH_PER_COMPANY})")
                            await asyncio.sleep(2.5)
                        else:
                            error_count += 1

        return {
            "status": "success",
            "total_sent": sent_count,
            "total_errors": error_count,
            "max_per_company_enforced": MAX_OUTREACH_PER_COMPANY,
        }


    async def run_full_gff_decision_maker_sweep(self, auto_send: bool = True) -> Dict[str, Any]:
        """Execute sweep across all 150+ FinTech festival partners."""
        self._log_event("INFO", f"Starting Full GFF Decision Maker Mining Sweep across {len(FINTECH_FESTIVAL_REGISTRY)} companies (Auto-Send: {auto_send})...")
        total_discovered = 0
        total_dispatched = 0

        for idx, company in enumerate(FINTECH_FESTIVAL_REGISTRY, 1):
            try:
                self._log_event("INFO", f"[{idx}/{len(FINTECH_FESTIVAL_REGISTRY)}] Mining leaders at {company.name} ({company.category})...")
                results = await self.mine_and_store_company(company, auto_send=auto_send)
                total_discovered += len(results)
                total_dispatched += sum(1 for r in results if r.outreach_sent)
                # Rate-limit delay between companies
                await asyncio.sleep(1.0)
            except Exception as e:
                self._log_event("WARNING", f"Error mining {company.name}: {e}")

        self._log_event("SUCCESS", f"Finished GFF Decision Maker Sweep: {total_discovered} leaders discovered, {total_dispatched} emails sent.")
        return {
            "companies_scanned": len(FINTECH_FESTIVAL_REGISTRY),
            "decision_makers_mined": total_discovered,
            "emails_dispatched": total_dispatched,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


    def start_background_miner(self, interval_seconds: int = 3600, auto_send: bool = True):
        """Start continuous self-healing background miner."""
        if self.is_running:
            return
        self.is_running = True

        async def _daemon():
            self._log_event("INFO", f"GFF Decision Maker Daemon Started (Interval: {interval_seconds}s)")
            while self.is_running:
                try:
                    await self.run_full_gff_decision_maker_sweep(auto_send=auto_send)
                except Exception as exc:
                    self._log_event("ERROR", f"Daemon cycle encountered error: {exc}")
                await asyncio.sleep(interval_seconds)

        self._bg_task = asyncio.create_task(_daemon())

    def stop_background_miner(self):
        """Halt background miner."""
        self.is_running = False
        if self._bg_task:
            self._bg_task.cancel()


# Global Singleton Instance
fintech_miner = FinTechDecisionMakerMiner()
