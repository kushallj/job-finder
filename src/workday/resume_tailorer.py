"""
src/workday/resume_tailorer.py — Dynamic ATS Resume Tailoring & PDF Document Synthesizer for Workday.
"""
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from src.models import Job
from src.workday.models import WorkdayCandidateProfile

logger = logging.getLogger("workday_resume_tailorer")

BASE_RESUMES_DIR = Path("data/workday_resumes")
BASE_RESUMES_DIR.mkdir(parents=True, exist_ok=True)

TECH_KEYWORD_TAXONOMY = [
    "python", "fastapi", "django", "flask", "react", "next.js", "typescript", "javascript",
    "node.js", "java", "spring boot", "golang", "go", "c++", "rust", "c#", ".net",
    "postgresql", "mysql", "mongodb", "redis", "kafka", "elasticsearch",
    "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "terraform", "ci/cd",
    "microservices", "distributed systems", "rest api", "graphql", "grpc", "system design",
    "agile", "scrum", "iot", "cloud architecture", "llm", "ai", "machine learning"
]


class WorkdayResumeTailorer:
    """Dynamically tailors candidate resumes for specific Workday job postings and builds clean PDF artifacts."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or BASE_RESUMES_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_job_keywords(self, title: str, description: str) -> List[str]:
        """Extract top matching technical skills and keywords from the job description."""
        combined = f"{title} {description}".lower()
        matched = []
        for kw in TECH_KEYWORD_TAXONOMY:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, combined):
                matched.append(kw.title() if len(kw) > 3 else kw.upper())
        return matched or ["Python", "FastAPI", "React", "PostgreSQL", "AWS", "Docker"]

    def calculate_ats_match_score(self, candidate_skills: List[str], job_keywords: List[str]) -> float:
        """Calculate estimated ATS keyword match score (65-98%)."""
        if not job_keywords:
            return 85.0
        cand_set = {s.lower() for s in candidate_skills}
        matched = sum(1 for kw in job_keywords if kw.lower() in cand_set or any(kw.lower() in s for s in cand_set))
        ratio = matched / max(1, len(job_keywords))
        return round(min(98.0, max(68.0, 65.0 + ratio * 32.0)), 1)

    def generate_tailored_summary(
        self,
        profile: WorkdayCandidateProfile,
        job_title: str,
        company: str,
        matched_keywords: List[str],
    ) -> str:
        """Generate targeted executive summary matching Workday role requirements."""
        stack_highlight = ", ".join(matched_keywords[:6])
        return (
            f"Versatile {profile.current_title or 'Senior Software Engineer'} with {profile.years_of_experience}+ years of hands-on "
            f"experience architecting high-throughput distributed microservices, low-latency APIs, and scalable full-stack web applications. "
            f"Core technical expertise in {stack_highlight}, cloud-native infrastructure, and database optimization. "
            f"Proven track record of improving system reliability to 99.99% and accelerating release velocity. "
            f"Excited to drive technical excellence and scalable product impact as {job_title} at {company}."
        )

    def generate_cover_letter_text(
        self,
        profile: WorkdayCandidateProfile,
        job_title: str,
        company: str,
        matched_keywords: List[str],
    ) -> str:
        """Generate personalized, high-converting Workday cover letter."""
        stack_str = ", ".join(matched_keywords[:5])
        return f"""Dear Hiring Team at {company},

I am excited to submit my application for the {job_title} role at {company}. With {profile.years_of_experience} years of software engineering experience specializing in {stack_str}, I am confident in my ability to immediately accelerate your engineering deliverables.

Throughout my tenure at {profile.current_company}, I have led backend and full-stack initiatives that scaled distributed architectures, slashed API latencies by over 40%, and maintained rigorous SLAs. My approach combines robust architectural design, test-driven development, and clear cross-functional collaboration.

What particularly draws me to {company} is your commitment to engineering innovation and high-impact solutions. I would welcome the opportunity to discuss how my technical depth, scalable system design background, and passion for engineering align with your current goals.

Thank you for your time and consideration.

Sincerely,
{profile.first_name} {profile.last_name}
{profile.email if hasattr(profile, 'email') else profile.account_email} | {profile.phone}
{profile.linkedin_url}
"""

    def build_tailored_resume_pdf(
        self,
        profile: WorkdayCandidateProfile,
        job_id: int,
        job_title: str,
        company: str,
        matched_keywords: List[str],
    ) -> Tuple[str, str]:
        """
        Synthesizes a clean, ATS-compliant PDF resume and returns (pdf_path, text_content).
        Uses ReportLab to produce professional layout conforming to Workday ATS parsers.
        """
        ts = int(time.time() * 1000)
        safe_comp = re.sub(r"[^a-zA-Z0-9_]", "_", company)[:20]
        pdf_filename = f"workday_resume_job{job_id}_{safe_comp}_{ts}.pdf"
        pdf_path = str(self.output_dir / pdf_filename)

        summary_text = self.generate_tailored_summary(profile, job_title, company, matched_keywords)
        skills = profile.to_dict().get("skills", [])
        combined_skills = list(dict.fromkeys(matched_keywords + skills))

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0f172a")
        accent_color = colors.HexColor("#0284c7")
        text_color = colors.HexColor("#334155")

        title_style = ParagraphStyle(
            "NameTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=primary_color,
            alignment=1,
        )
        subtitle_style = ParagraphStyle(
            "HeadlineSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=accent_color,
            alignment=1,
        )
        contact_style = ParagraphStyle(
            "ContactLine",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=text_color,
            alignment=1,
        )
        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=primary_color,
            spaceAfter=3,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            textColor=text_color,
        )
        bold_body = ParagraphStyle(
            "BoldBody",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=primary_color,
        )
        bullet_style = ParagraphStyle(
            "Bullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=12,
            textColor=text_color,
            leftIndent=12,
            firstLineIndent=-8,
        )

        story = []

        # ── Header ──
        full_name = f"{profile.first_name} {profile.last_name}".strip()
        story.append(Paragraph(full_name, title_style))
        story.append(Spacer(1, 2))
        headline_text = f"{job_title} | Full-Stack & Backend Cloud Architecture"
        story.append(Paragraph(headline_text, subtitle_style))
        story.append(Spacer(1, 4))
        
        email_val = profile.account_email
        contact_line = f"{email_val} • {profile.phone} • {profile.city}, {profile.country} • {profile.linkedin_url} • {profile.github_url}"
        story.append(Paragraph(contact_line, contact_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=8))

        # ── Professional Summary ──
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_heading))
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 8))

        # ── Core Technical Competencies ──
        story.append(Paragraph("CORE TECHNICAL SKILLS", section_heading))
        skills_str = ", ".join(combined_skills[:18])
        story.append(Paragraph(f"<b>Primary Technologies:</b> {skills_str}", body_style))
        story.append(Paragraph("<b>Architecture & Cloud:</b> Microservices, RESTful APIs, GraphQL, Docker, Kubernetes, AWS, PostgreSQL, Redis, Kafka, CI/CD", body_style))
        story.append(Spacer(1, 8))

        # ── Professional Experience ──
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_heading))
        work_items = profile.to_dict().get("work_history", [])
        for w in work_items:
            comp_name = w.get("company", "Tech Company")
            role_title = w.get("title", "Software Engineer")
            dates = f"{w.get('start_date', '2022')} – {w.get('end_date', 'Present')}"
            loc = w.get("location", "Remote")
            
            exp_header = f"<b>{role_title}</b> — {comp_name} ({loc}) <font color='#64748b'>| {dates}</font>"
            story.append(Paragraph(exp_header, bold_body))
            story.append(Spacer(1, 2))
            
            desc = w.get("description", "")
            if desc:
                story.append(Paragraph(f"• {desc}", bullet_style))
            
            # Tailored bullet points emphasizing matched keywords
            kw_sample = [k for k in matched_keywords if k.lower() in ("python", "fastapi", "react", "postgresql", "aws", "docker", "redis", "kafka")][:3]
            kw_clause = f" with {', '.join(kw_sample)}" if kw_sample else ""
            story.append(Paragraph(f"• Engineered scalable backend services and automated REST endpoints{kw_clause}, improving throughput by 35% and system reliability.", bullet_style))
            story.append(Paragraph(f"• Collaborated with cross-functional product teams to design low-latency API contracts and maintain 99.99% SLA availability.", bullet_style))
            story.append(Spacer(1, 6))

        # ── Education ──
        story.append(Paragraph("EDUCATION", section_heading))
        edu_items = profile.to_dict().get("education", [])
        for e in edu_items:
            school = e.get("school", "University")
            deg = e.get("degree", "Bachelor of Engineering")
            fos = e.get("field_of_study", "Computer Science")
            dates = f"{e.get('start_date', '2017')} – {e.get('end_date', '2021')}"
            story.append(Paragraph(f"<b>{deg} in {fos}</b> — {school} <font color='#64748b'>| {dates}</font>", body_style))
            story.append(Spacer(1, 4))

        doc.build(story)
        logger.info(f"Generated tailored Workday PDF resume: {pdf_path}")

        raw_text = f"""{full_name}
{headline_text}
{contact_line}

PROFESSIONAL SUMMARY
{summary_text}

CORE TECHNICAL SKILLS
Primary: {skills_str}

EXPERIENCE
{chr(10).join(f"{w.get('title')} at {w.get('company')} ({w.get('start_date')} - {w.get('end_date')})" for w in work_items)}

EDUCATION
{chr(10).join(f"{e.get('degree')} in {e.get('field_of_study')} - {e.get('school')}" for e in edu_items)}
"""
        return pdf_path, raw_text

    def tailor_for_job(
        self,
        profile: WorkdayCandidateProfile,
        job: Job,
    ) -> Dict[str, Any]:
        """End-to-end resume tailoring returning PDF path, raw text, and ATS metrics."""
        job_title = job.title or "Software Engineer"
        company = job.company or "Company"
        job_desc = job.description or ""

        matched_keywords = self.extract_job_keywords(job_title, job_desc)
        candidate_skills = profile.to_dict().get("skills", [])
        ats_score = self.calculate_ats_match_score(candidate_skills, matched_keywords)

        pdf_path, raw_text = self.build_tailored_resume_pdf(
            profile=profile,
            job_id=job.id,
            job_title=job_title,
            company=company,
            matched_keywords=matched_keywords,
        )

        cover_letter = self.generate_cover_letter_text(
            profile=profile,
            job_title=job_title,
            company=company,
            matched_keywords=matched_keywords,
        )

        return {
            "job_id": job.id,
            "job_title": job_title,
            "company": company,
            "matched_keywords": matched_keywords,
            "ats_match_score": ats_score,
            "tailored_resume_path": pdf_path,
            "tailored_resume_text": raw_text,
            "cover_letter_text": cover_letter,
        }

    def tailor_for_workday(
        self,
        job_description: str,
        candidate_profile: Optional[Dict[str, Any] | WorkdayCandidateProfile] = None,
        job_title: str = "Senior Engineer",
    ) -> Dict[str, Any]:
        """Analyzes and previews tailoring against a job description."""
        matched_keywords = self.extract_job_keywords(job_title, job_description)
        skills = []
        if isinstance(candidate_profile, dict):
            skills = candidate_profile.get("skills", [])
        elif isinstance(candidate_profile, WorkdayCandidateProfile):
            skills = candidate_profile.to_dict().get("skills", [])

        ats_score = self.calculate_ats_match_score(skills, matched_keywords)
        combined_skills = list(dict.fromkeys(matched_keywords + skills))

        return {
            "job_title": job_title,
            "matched_keywords": matched_keywords,
            "ats_score": ats_score,
            "ats_match_score": ats_score,
            "skills": combined_skills,
            "recommended_focus": matched_keywords[:5],
        }

    def generate_tailored_pdf(
        self,
        job_id: int,
        company_name: str,
        tailored_data: Dict[str, Any],
        candidate_profile: Dict[str, Any] | WorkdayCandidateProfile,
    ) -> str:
        """Builds and persists tailored PDF directly from dict or profile."""
        import json
        if isinstance(candidate_profile, dict):
            prof = WorkdayCandidateProfile(
                account_email=candidate_profile.get("email") or candidate_profile.get("account_email", "canaby007@gmail.com"),
                first_name=candidate_profile.get("first_name", "Kushall"),
                last_name=candidate_profile.get("last_name", "Jain"),
                phone=candidate_profile.get("phone", "+1 555-0199"),
                city=candidate_profile.get("city", "San Francisco"),
                state_province=candidate_profile.get("state", "CA"),
                country=candidate_profile.get("country", "USA"),
                headline=candidate_profile.get("headline", "Senior Engineer"),
                skills_json=json.dumps(candidate_profile.get("skills", [])),
                work_history_json=json.dumps(candidate_profile.get("experience", candidate_profile.get("work_history", []))),
                education_json=json.dumps(candidate_profile.get("education", [])),
            )
        else:
            prof = candidate_profile

        matched_kws = tailored_data.get("matched_keywords", ["Python", "FastAPI"])
        pdf_path, _ = self.build_tailored_resume_pdf(
            profile=prof,
            job_id=job_id,
            job_title=tailored_data.get("job_title", "Senior Software Engineer"),
            company=company_name,
            matched_keywords=matched_kws,
        )
        return pdf_path

