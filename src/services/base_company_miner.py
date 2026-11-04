"""
src/services/base_company_miner.py
Shared base class and utilities for autonomous catalog miners (S&P 500, Nifty 500,
Shark Tank, Accelerators, Fintech Festival).
Implements the DRY principle by unifying role priority ranking, corporate email synthesis,
MIME composition, and rate-limited decision-maker outreach.
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
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import func
from src.database import SessionLocal
from src.models import Contact, OutreachRecord

logger = logging.getLogger("base_company_miner")

MAX_OUTREACH_PER_COMPANY = 2

ROLE_PATTERNS = [
    (re.compile(r"\b(founder|co-founder|cto|chief\s+technology\s+officer|cio|chief\s+architect|ceo|head\s+of\s+technology)\b", re.I), 1),
    (re.compile(r"\b(founding\s+engineer|vp\s+of\s+engineering|vp\s+engineering|senior\s+vp|head\s+of\s+engineering)\b", re.I), 2),
    (re.compile(r"\b(director\s+of\s+engineering|engineering\s+director|senior\s+director)\b", re.I), 3),
    (re.compile(r"\b(principal\s+engineer|distinguished\s+engineer|staff\s+engineer|lead\s+.*engineer|tech\s+lead|engineering\s+manager)\b", re.I), 4),
    (re.compile(r"\b(head\s+of\s+talent|talent\s+acquisition|technical\s+recruiter)\b", re.I), 5),
]


def get_role_priority(title: str) -> int:
    """Rank tech leadership roles by architectural impact (1 = highest priority)."""
    t = title or ""
    for pattern, priority in ROLE_PATTERNS:
        if pattern.search(t):
            return priority
    return 6


class BaseCompanyMiner:
    """Reusable engine for extracting tech leaders and executing executive outreach."""

    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_API_KEY") or os.getenv("SERP_API_KEY")
        self.gmail_user = os.getenv("GMAIL_ADDRESS")
        self.gmail_pass = os.getenv("GMAIL_PASSWORD")
        self.sender_name = os.getenv("SENDER_NAME", "Job Applicant")
        self.sender_linkedin = os.getenv("LINKEDIN_URL") or "https://linkedin.com/in/kushal-jain"

        self.total_mined = 0
        self.total_emailed = 0

    @staticmethod
    def synthesize_email(full_name: str, domain: str, default_domain: str = "company.com") -> str:
        """Derive standard corporate email format for an executive."""
        parts = [p.lower() for p in re.sub(r"[^a-zA-Z\s]", "", full_name).split() if p]
        d = domain or default_domain
        if not parts:
            return f"careers@{d}"
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""
        if last:
            return f"{first}.{last}@{d}"
        return f"{first}@{d}"

    async def search_linkedin_decision_makers(
        self,
        company_name: str,
        domain: str,
        max_results: int = 6,
    ) -> List[Dict[str, Any]]:
        """Search Google via SerpApi for engineering decision makers on LinkedIn."""
        if not self.serpapi_key:
            return []

        clean_name = company_name.split("(")[0].strip()
        query = (
            f'site:linkedin.com/in/ "{clean_name}" '
            '(CTO OR "Chief Technology Officer" OR "VP Engineering" OR "Head of Engineering" OR "Director of Engineering")'
        )
        url = (
            f"https://serpapi.com/search.json?engine=google&q={urllib.parse.quote(query)}"
            f"&api_key={self.serpapi_key}&num={max_results}"
        )

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

                email_addr = self.synthesize_email(name, domain)
                contacts.append({
                    "name": name,
                    "title": role,
                    "company": company_name,
                    "email": email_addr,
                    "linkedin_url": link,
                })
        except Exception as exc:
            logger.warning("Error mining decision makers for %s: %s", company_name, exc)

        return contacts

    def compose_outreach_email(
        self,
        contact: Dict[str, Any],
        context_label: str = "Enterprise",
    ) -> Tuple[str, str, str]:
        """Generate high-impact cold outreach template."""
        first_name = contact["name"].split()[0] if contact.get("name") else "there"
        company = contact.get("company", "your enterprise")
        sector = contact.get("sector") or contact.get("industry") or "Technology"
        title = contact.get("title", "Engineering Leader")

        subject = f"Engineering & Platform Scalability at {company} ({context_label}) — {self.sender_name}"

        body_text = f"""Hi {first_name},

I've been following {company}'s industry-defining milestones and scalable software infrastructure in {sector}.

I'm a Software Engineer specializing in Python, FastAPI, React, and building fault-tolerant, high-throughput distributed microservices. Engineering at {context_label} scale requires rigorous system reliability, low-latency API design, and clean architectural separation of concerns.

Given your leadership as {title}, I wanted to reach out directly to see if your engineering organization is looking for a versatile software engineer who can contribute immediately across full-stack and backend systems.

Key Technical Highlights:
• Full-stack architecture with FastAPI, Python, React & Next.js
• Distributed caching, messaging pipelines, and database optimization (PostgreSQL, Redis, Kafka)
• Cloud infrastructure, microservices design, and automated CI/CD pipelines

My LinkedIn: {self.sender_linkedin or ''}

Would you be open to a brief 10-minute chat this week to explore how my technical background aligns with {company}'s current engineering roadmaps?

Best regards,
{self.sender_name}
Software Engineer
{self.sender_linkedin or ''}
"""

        body_html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; line-height: 1.6;">
  <p>Hi {first_name},</p>
  <p>I've been following <strong>{company}</strong>'s industry-defining milestones and scalable software infrastructure in <em>{sector}</em>.</p>
  <p>I'm a Software Engineer specializing in <strong>Python, FastAPI, React</strong>, and building fault-tolerant, high-throughput distributed microservices. Engineering at {context_label} scale requires rigorous system reliability, low-latency API design, and clean architectural separation of concerns.</p>
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
  <a href="{self.sender_linkedin or '#'}" style="color: #4F46E5;">{self.sender_linkedin or ''}</a>
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
            logger.error("Failed to send email to %s: %s", recipient_email, exc)
            return False

    async def save_and_outreach(
        self,
        contacts: List[Dict[str, Any]],
        company_name: str,
        source_prefix: str,
        department: Optional[str] = None,
        auto_send: bool = False,
        composer: Any = None,
        template_type: str = "enterprise_outreach",
    ) -> List[Dict[str, Any]]:
        """Persists decision makers to database and executes rate-capped outreach."""
        if not contacts:
            return []

        contacts.sort(key=lambda x: get_role_priority(x.get("title", "")))

        saved: List[Dict[str, Any]] = []
        with SessionLocal() as db:
            company_sent_count = (
                db.query(OutreachRecord)
                .join(Contact, OutreachRecord.contact_id == Contact.id)
                .filter(func.lower(Contact.company) == func.lower(company_name))
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
                        source=source_prefix,
                        department=department,
                    )
                    db.add(new_c)
                    db.commit()
                    db.refresh(new_c)
                    contact_id = new_c.id
                    self.total_mined += 1
                else:
                    contact_id = existing.id

                if auto_send and slots_remaining > 0:
                    already_sent = db.query(OutreachRecord).filter(
                        (OutreachRecord.contact_id == contact_id) | (OutreachRecord.contact_email == dm["email"])
                    ).first()

                    if not already_sent and dm["email"]:
                        if composer:
                            subj, text, html = composer(dm)
                        else:
                            subj, text, html = self.compose_outreach_email(dm)

                        loop = asyncio.get_event_loop()
                        sent_ok = await loop.run_in_executor(
                            None, lambda: self.send_smtp_email(dm["email"], subj, text, html)
                        )
                        if sent_ok:
                            slots_remaining -= 1
                            self.total_emailed += 1
                            rec = OutreachRecord(
                                contact_id=contact_id,
                                contact_email=dm["email"],
                                contact_name=dm["name"],
                                subject=subj,
                                body=text,
                                template_type=template_type,
                                status="sent",
                                email_sent=True,
                                sent_at=datetime.utcnow(),
                            )
                            db.add(rec)
                            db.commit()
                            logger.info(
                                "Sent outreach to %s (%s at %s) -> %s",
                                dm["name"],
                                dm["title"],
                                dm["company"],
                                dm["email"],
                            )
                            await asyncio.sleep(2.5)

                saved.append(dm)

        return saved
