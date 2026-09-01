"""
accelerator_miner.py — Autonomous Job Sourcing & Decision Maker Outreach Engine
for Y Combinator, Surge by Peak XV, Accel Atoms, Antler, and Techstars Startups.

Capabilities:
1. Live Career Portal & ATS Sourcing (Greenhouse, Lever, Ashby, Workday).
2. Leadership Mining: Founders, Co-Founders, CTOs, and Founding Engineers.
3. Strict MAX 2 Decision Makers per Company constraint.
4. Accelerator-Tailored Cold Outreach Composer & SMTP Delivery.
"""
from __future__ import annotations

import asyncio
import email.utils
import json
import logging
import os
import re
import smtplib
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

load_dotenv()

from src.accelerators_registry import ACCELERATORS_REGISTRY, AcceleratorStartup
from src.database import SessionLocal
from src.models import Contact, Job, OutreachRecord

logger = logging.getLogger("accelerator_miner")
logger.setLevel(logging.INFO)

MAX_OUTREACH_PER_COMPANY = 2

ROLE_PATTERNS = [
    (re.compile(r"\b(founder|co-founder|cto|chief\s+technology\s+officer|ceo)\b", re.I), 1),
    (re.compile(r"\b(founding\s+engineer|vp\s+of\s+engineering|vp\s+engineering|head\s+of\s+engineering)\b", re.I), 2),
    (re.compile(r"\b(director\s+of\s+engineering|engineering\s+director)\b", re.I), 3),
    (re.compile(r"\b(engineering\s+manager|lead\s+.*engineer|tech\s+lead|staff\s+engineer|principal\s+engineer)\b", re.I), 4),
    (re.compile(r"\b(head\s+of\s+talent|talent\s+acquisition|technical\s+recruiter|recruiter)\b", re.I), 5),
]



def get_role_priority(title: str) -> int:
    """Rank leadership roles by startup executive impact (1 = highest priority)."""
    t = title or ""
    for pattern, priority in ROLE_PATTERNS:
        if pattern.search(t):
            return priority
    return 6


class AcceleratorMiner:
    """
    Autonomous engine for sourcing jobs and decision makers across top global accelerators.
    """

    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_API_KEY") or os.getenv("SERP_API_KEY")
        self.gmail_user = os.getenv("GMAIL_ADDRESS", "canaby007@gmail.com")
        self.gmail_pass = os.getenv("GMAIL_PASSWORD", "ujjk wwig znwp lise")
        self.sender_name = os.getenv("SENDER_NAME", "Kushall Jain")
        self.sender_linkedin = os.getenv("LINKEDIN_URL", "https://linkedin.com/in/kushall-jain-263009261")
        self.total_jobs_sourced = 0
        self.total_leaders_mined = 0
        self.total_emails_dispatched = 0

    def synthesize_email(self, full_name: str, domain: str) -> str:
        """Derive standard corporate email format for startup leader."""
        parts = [p.lower() for p in re.sub(r"[^a-zA-Z\s]", "", full_name).split() if p]
        if not parts or not domain:
            return f"founders@{domain}" if domain else "founders@startup.com"
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""
        if last:
            return f"{first}.{last}@{domain}"
        return f"{first}@{domain}"

    async def scrape_startup_jobs(self, startup: AcceleratorStartup, max_jobs: int = 15) -> List[Dict[str, Any]]:
        """Scrape live open engineering positions from company ATS portal."""
        jobs: List[Dict[str, Any]] = []
        if not startup.ats_slug:
            return []

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                if startup.ats_platform == "greenhouse":
                    url = f"https://boards-api.greenhouse.io/v1/boards/{startup.ats_slug}/jobs"
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("jobs", [])[:max_jobs]:
                            title = item.get("title", "")
                            jobs.append({
                                "title": title,
                                "company": startup.name,
                                "location": item.get("location", {}).get("name", "Remote / India"),
                                "url": item.get("absolute_url", startup.careers_url or ""),
                                "source": f"accelerator_{startup.accelerator.lower().replace(' ', '_')}",
                                "tags": ["Startup", startup.accelerator, startup.stage, "Engineering"],
                            })

                elif startup.ats_platform == "lever":
                    url = f"https://api.lever.co/v0/postings/{startup.ats_slug}?mode=json"
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data[:max_jobs]:
                            jobs.append({
                                "title": item.get("text", ""),
                                "company": startup.name,
                                "location": item.get("categories", {}).get("location", "Remote / India"),
                                "url": item.get("hostedUrl", startup.careers_url or ""),
                                "source": f"accelerator_{startup.accelerator.lower().replace(' ', '_')}",
                                "tags": ["Startup", startup.accelerator, startup.stage, "Engineering"],
                            })

            # Upsert into DB
            if jobs:
                with SessionLocal() as db:
                    for j in jobs:
                        job_id = f"acc_{startup.id}_{hash(j['title']) % 1000000}"
                        existing = db.query(Job).filter(Job.job_id == job_id).first()
                        if not existing:
                            new_job = Job(
                                job_id=job_id,
                                title=j["title"],
                                company=j["company"],
                                location=j["location"],
                                url=j["url"],
                                source=j["source"],
                                tags=json.dumps(j["tags"]),
                                description=f"Live opening at {startup.name} ({startup.accelerator} - {startup.batch}). Stage: {startup.stage}.",
                                fetched_at=datetime.utcnow(),
                            )
                            db.add(new_job)
                            self.total_jobs_sourced += 1
                    db.commit()

        except Exception as exc:
            logger.warning(f"Error sourcing jobs for {startup.name}: {exc}")

        return jobs

    async def mine_startup_decision_makers(
        self, startup: AcceleratorStartup, max_results: int = 6
    ) -> List[Dict[str, Any]]:
        """Search and extract founders, CTOs, and technical leaders for startup."""
        if not self.serpapi_key:
            return []

        clean_name = startup.name.split("(")[0].strip()
        domain = startup.domain or f"{clean_name.lower().replace(' ', '')}.com"
        query = f'site:linkedin.com/in/ {clean_name} (Founder OR Co-Founder OR CTO OR "Founding Engineer" OR "VP Engineering" OR "Head of Engineering")'
        url = f"https://serpapi.com/search.json?engine=google&q={urllib.parse.quote(query)}&api_key={self.serpapi_key}&num={max_results}"

        contacts: List[Dict[str, Any]] = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JobFinder/2.0"})
            loop = asyncio.get_event_loop()
            resp_bytes = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=18).read())
            data = json.loads(resp_bytes.decode())
            results = data.get("organic_results", [])

            for r in results:
                raw_title = r.get("title", "")
                link = r.get("link", "")

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
                    role = "Founder / Tech Leader"

                name = re.sub(r"\(.*?\)", "", name).strip()
                if not name or len(name.split()) > 4:
                    continue

                email_addr = self.synthesize_email(name, domain)
                contacts.append({
                    "name": name,
                    "title": role,
                    "company": startup.name,
                    "domain": domain,
                    "email": email_addr,
                    "linkedin_url": link,
                    "accelerator": startup.accelerator,
                    "batch": startup.batch,
                })

        except Exception as exc:
            logger.warning(f"Error mining leaders for {startup.name}: {exc}")

        return contacts

    def compose_accelerator_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose high-converting cold email tailored specifically to accelerator & startup culture."""
        first_name = contact["name"].split()[0] if contact.get("name") else "there"
        company = contact.get("company", "your startup")
        accelerator = contact.get("accelerator", "top accelerator")
        batch = contact.get("batch", "")
        title = contact.get("title", "Founder")

        subject = f"Building & Scaling Engineering at {company} ({accelerator}) — Kushall Jain"

        body_text = f"""Hi {first_name},

I've been closely following {company}'s rapid scaling trajectory since your {accelerator} ({batch}) journey.

I'm a Software Engineer specializing in Python, FastAPI, React, and building robust, high-performance distributed backends from 0-to-1 and 1-to-10. I thrive in fast-paced startup environments where engineering speed, clean system design, and high autonomy matter.

Given your leadership as {title}, I wanted to reach out directly to see if you're looking for a versatile engineer who can take full ownership of core product features and scale your backend architecture.

Key Highlights:
• End-to-end full-stack development with FastAPI, Python, React & Next.js
• Built low-latency APIs and event-driven data pipelines (PostgreSQL, Redis, Kafka)
• Startup mindset: high velocity, rapid prototyping, and production-grade reliability

My LinkedIn: {self.sender_linkedin}

Would you be open to a brief 10-minute chat this week to see if my skill set could add immediate leverage to {company}?

Best regards,
{self.sender_name}
Software Engineer
{self.sender_linkedin}
"""

        body_html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; line-height: 1.6;">
  <p>Hi {first_name},</p>
  <p>I've been closely following <strong>{company}</strong>'s rapid scaling trajectory since your <strong>{accelerator}</strong> ({batch}) journey.</p>
  <p>I'm a Software Engineer specializing in <strong>Python, FastAPI, React</strong>, and building robust, high-performance distributed backends from 0-to-1 and 1-to-10. I thrive in fast-paced startup environments where engineering speed, clean system design, and high autonomy matter.</p>
  <p>Given your leadership as <em>{title}</em>, I wanted to reach out directly to see if you're looking for a versatile engineer who can take full ownership of core product features and scale your backend architecture.</p>
  <p><strong>Key Highlights:</strong></p>
  <ul>
    <li>End-to-end full-stack development with FastAPI, Python, React & Next.js</li>
    <li>Built low-latency APIs and event-driven data pipelines (PostgreSQL, Redis, Kafka)</li>
    <li>Startup mindset: high velocity, rapid prototyping, and production-grade reliability</li>
  </ul>
  <p>Would you be open to a brief 10-minute chat this week to see if my skill set could add immediate leverage to {company}?</p>
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

    async def mine_and_outreach_startup(
        self, startup: AcceleratorStartup, auto_send: bool = True
    ) -> List[Dict[str, Any]]:
        """Mine decision makers for single accelerator startup and dispatch outreach with strict <= 2 cap."""
        from sqlalchemy import func

        contacts = await self.mine_startup_decision_makers(startup, max_results=6)
        if not contacts:
            return []

        contacts.sort(key=lambda x: get_role_priority(x.get("title", "")))

        saved: List[Dict[str, Any]] = []
        with SessionLocal() as db:
            company_sent_count = (
                db.query(OutreachRecord)
                .join(Contact, OutreachRecord.contact_id == Contact.id)
                .filter(func.lower(Contact.company) == func.lower(startup.name))
                .count()
            )
            slots_remaining = max(0, MAX_OUTREACH_PER_COMPANY - company_sent_count)

            for dm in contacts:
                existing = db.query(Contact).filter(Contact.email == dm["email"]).first()
                if not existing:
                    new_c = Contact(
                        name=dm["name"],
                        title=dm["title"],
                        company=dm["company"],
                        email=dm["email"],
                        linkedin_url=dm["linkedin_url"],
                        confidence_score=90,
                        source=f"accelerator_{startup.accelerator.lower().replace(' ', '_')}",
                        department=startup.category,
                    )
                    db.add(new_c)
                    db.commit()
                    db.refresh(new_c)
                    contact_id = new_c.id
                    self.total_leaders_mined += 1
                else:
                    contact_id = existing.id

                # Send outreach if within quota
                if auto_send and slots_remaining > 0:
                    already_sent = db.query(OutreachRecord).filter(
                        (OutreachRecord.contact_id == contact_id) | (OutreachRecord.contact_email == dm["email"])
                    ).first()

                    if not already_sent and dm["email"]:
                        subj, text, html = self.compose_accelerator_outreach(dm)
                        loop = asyncio.get_event_loop()
                        sent_ok = await loop.run_in_executor(
                            None, lambda: self.send_smtp_email(dm["email"], subj, text, html)
                        )
                        if sent_ok:
                            slots_remaining -= 1
                            self.total_emails_dispatched += 1
                            rec = OutreachRecord(
                                contact_id=contact_id,
                                contact_name=dm["name"],
                                contact_email=dm["email"],
                                subject=subj,
                                body=text,
                                template_type="accelerator_founder_outreach",
                                status="sent",
                                email_sent=True,
                                sent_at=datetime.now(timezone.utc),
                            )
                            db.add(rec)
                            db.commit()
                            logger.info(f"Sent outreach to {dm['name']} ({dm['title']} at {dm['company']}) -> {dm['email']}")
                            await asyncio.sleep(2.5)

                saved.append(dm)

        return saved


accelerator_miner = AcceleratorMiner()
