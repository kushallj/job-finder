"""
sp500_miner.py — Autonomous Job Sourcing & Tech Leadership Outreach Engine
for S&P 500 Enterprise Giants (US Market Leaders).

Features:
1. Sourcing live software and tech engineering openings across S&P 500 corporations.
2. Mining CTOs, VPs of Engineering, Engineering Directors, and Principal Architects.
3. Strict MAX 2 Decision Makers per Company limit.
4. Global Scale Cold Outreach Composer & SMTP Delivery.
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

from src.database import SessionLocal
from src.models import Contact, Job, OutreachRecord
from src.sp500_registry import SP500_REGISTRY, SP500Company

logger = logging.getLogger("sp500_miner")
logger.setLevel(logging.INFO)

MAX_OUTREACH_PER_COMPANY = 2

ROLE_PATTERNS = [
    (re.compile(r"\b(cto|chief\s+technology\s+officer|cio|chief\s+architect)\b", re.I), 1),
    (re.compile(r"\b(vp\s+of\s+engineering|vp\s+engineering|senior\s+vp|head\s+of\s+engineering)\b", re.I), 2),
    (re.compile(r"\b(director\s+of\s+engineering|engineering\s+director|senior\s+director)\b", re.I), 3),
    (re.compile(r"\b(principal\s+engineer|distinguished\s+engineer|staff\s+engineer|tech\s+lead)\b", re.I), 4),
    (re.compile(r"\b(head\s+of\s+talent|talent\s+acquisition|technical\s+recruiter)\b", re.I), 5),
]


def get_role_priority(title: str) -> int:
    """Rank tech leadership roles by architectural impact (1 = highest priority)."""
    t = title or ""
    for pattern, priority in ROLE_PATTERNS:
        if pattern.search(t):
            return priority
    return 6


class SP500Miner:
    """Autonomous miner for S&P 500 corporations, tech leadership, and engineering openings."""

    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_API_KEY") or os.getenv("SERP_API_KEY")
        self.gmail_user = os.getenv("GMAIL_ADDRESS")
        self.gmail_pass = os.getenv("GMAIL_PASSWORD")
        self.sender_name = os.getenv("SENDER_NAME", "Job Applicant")
        self.sender_linkedin = os.getenv("LINKEDIN_URL")

        self.total_mined = 0
        self.total_emailed = 0

    def synthesize_email(self, full_name: str, domain: str) -> str:
        """Derive standard corporate email format for S&P 500 leader."""
        parts = [p.lower() for p in re.sub(r"[^a-zA-Z\s]", "", full_name).split() if p]
        if not parts or not domain:
            return f"careers@{domain}" if domain else "careers@sp500.com"
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""
        if last:
            return f"{first}.{last}@{domain}"
        return f"{first}@{domain}"

    async def mine_sp500_decision_makers(
        self, company: SP500Company, max_results: int = 6
    ) -> List[Dict[str, Any]]:
        """Search and extract CTOs, VPs of Engineering, and Tech Directors for S&P 500 company."""
        if not self.serpapi_key:
            return []

        clean_name = company.name.split("(")[0].strip()
        query = f'site:linkedin.com/in/ {clean_name} (CTO OR "Chief Technology Officer" OR "VP Engineering" OR "Head of Engineering" OR "Director of Engineering")'
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
                    role = "Engineering Leader"

                name = re.sub(r"\(.*?\)", "", name).strip()
                if not name or len(name.split()) > 4:
                    continue

                email_addr = self.synthesize_email(name, company.domain)
                contacts.append({
                    "name": name,
                    "title": role,
                    "company": company.name,
                    "domain": company.domain,
                    "email": email_addr,
                    "linkedin_url": link,
                    "symbol": company.symbol,
                    "sector": company.sector,
                    "sub_industry": company.sub_industry,
                })

        except Exception as exc:
            logger.warning(f"Error mining leaders for S&P 500 company {company.name}: {exc}")

        return contacts

    def compose_sp500_outreach(self, contact: Dict[str, Any]) -> Tuple[str, str, str]:
        """Compose high-converting cold email tailored specifically to S&P 500 global platform scale."""
        first_name = contact["name"].split()[0] if contact.get("name") else "there"
        company = contact.get("company", "your enterprise")
        sector = contact.get("sector", "Technology")
        title = contact.get("title", "Engineering Leader")

        subject = f"Engineering & Platform Scalability at {company} (S&P 500) — Kushall Jain"

        body_text = f"""Hi {first_name},

I've been following {company}'s industry-defining milestones and scalable software infrastructure in {sector}.

I'm a Software Engineer specializing in Python, FastAPI, React, and building fault-tolerant, high-throughput distributed microservices. Engineering at S&P 500 scale requires rigorous system reliability, low-latency API design, and clean architectural separation of concerns.

Given your leadership as {title}, I wanted to reach out directly to see if your engineering organization is looking for a versatile software engineer who can contribute immediately across full-stack and backend systems.

Key Technical Highlights:
• Full-stack architecture with FastAPI, Python, React & Next.js
• Distributed caching, messaging pipelines, and database optimization (PostgreSQL, Redis, Kafka)
• Cloud infrastructure, microservices design, and automated CI/CD pipelines

My LinkedIn: {self.sender_linkedin}

Would you be open to a brief 10-minute chat this week to explore how my technical background aligns with {company}'s current engineering roadmaps?

Best regards,
{self.sender_name}
Software Engineer
{self.sender_linkedin}
"""

        body_html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; line-height: 1.6;">
  <p>Hi {first_name},</p>
  <p>I've been following <strong>{company}</strong>'s industry-defining milestones and scalable software infrastructure in <em>{sector}</em>.</p>
  <p>I'm a Software Engineer specializing in <strong>Python, FastAPI, React</strong>, and building fault-tolerant, high-throughput distributed microservices. Engineering at S&P 500 scale requires rigorous system reliability, low-latency API design, and clean architectural separation of concerns.</p>
  <p>Given your leadership as <em>{title}</em>, I wanted to reach out directly to see if your engineering organization is looking for a versatile software engineer who can contribute immediately across full-stack and backend systems.</p>
  <p><strong>Key Technical Highlights:</strong></p>
  <ul>
    <li>Full-stack architecture with FastAPI, Python, React & Next.js</li>
    <li>Distributed caching, messaging pipelines, and database optimization (PostgreSQL, Redis, Kafka)</li>
    <li>Cloud infrastructure, microservices design, and automated CI/CD pipelines</li>
  </ul>
  <p>Would you be open to a brief 10-minute chat this week to explore how my technical background aligns with {company}'s current engineering roadmaps?</p>
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

    async def mine_and_outreach_company(
        self, company: SP500Company, auto_send: bool = False
    ) -> List[Dict[str, Any]]:

        """Mine decision makers for single S&P 500 company and dispatch outreach with strict <= 2 cap."""
        from sqlalchemy import func

        contacts = await self.mine_sp500_decision_makers(company, max_results=6)
        if not contacts:
            return []

        contacts.sort(key=lambda x: get_role_priority(x.get("title", "")))

        saved: List[Dict[str, Any]] = []
        with SessionLocal() as db:
            company_sent_count = (
                db.query(OutreachRecord)
                .join(Contact, OutreachRecord.contact_id == Contact.id)
                .filter(func.lower(Contact.company) == func.lower(company.name))
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
                        source=f"sp500_{company.symbol.lower()}",
                        department=company.sector,
                    )
                    db.add(new_c)
                    db.commit()
                    db.refresh(new_c)
                    contact_id = new_c.id
                    self.total_mined += 1
                else:
                    contact_id = existing.id

                # Send outreach if within quota
                if auto_send and slots_remaining > 0:
                    already_sent = db.query(OutreachRecord).filter(
                        (OutreachRecord.contact_id == contact_id) | (OutreachRecord.contact_email == dm["email"])
                    ).first()

                    if not already_sent and dm["email"]:
                        subj, text, html = self.compose_sp500_outreach(dm)
                        loop = asyncio.get_event_loop()
                        sent_ok = await loop.run_in_executor(
                            None, lambda: self.send_smtp_email(dm["email"], subj, text, html)
                        )
                        if sent_ok:
                            slots_remaining -= 1
                            self.total_emailed += 1
                            rec = OutreachRecord(
                                contact_id=contact_id,
                                contact_name=dm["name"],
                                contact_email=dm["email"],
                                subject=subj,
                                body=text,
                                template_type="sp500_enterprise_outreach",
                                status="sent",
                                email_sent=True,
                                sent_at=datetime.now(timezone.utc),
                            )
                            db.add(rec)
                            db.commit()
                            logger.info(f"Sent S&P 500 outreach to {dm['name']} ({dm['title']} at {dm['company']}) -> {dm['email']}")
                            await asyncio.sleep(2.5)

                saved.append(dm)

        return saved


sp500_miner = SP500Miner()
