"""
src/workday/resume_tailorer.py — Dynamic ATS Resume Tailoring & PDF Document Synthesizer for Workday.
"""
from __future__ import annotations

import logging
import html
import json
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
        return matched

    def calculate_ats_match_score(self, candidate_skills: List[str], job_keywords: List[str]) -> float:
        """Calculate keyword overlap from candidate-provided skills."""
        if not job_keywords:
            return 0.0
        cand_set = {s.lower() for s in candidate_skills}
        if not cand_set:
            return 0.0
        matched = sum(1 for kw in job_keywords if kw.lower() in cand_set or any(kw.lower() in s for s in cand_set))
        ratio = matched / max(1, len(job_keywords))
        return round(ratio * 100.0, 1)

    def generate_tailored_summary(
        self,
        profile: WorkdayCandidateProfile,
        job_title: str,
        company: str,
        matched_keywords: List[str],
    ) -> str:
        """Generate targeted executive summary matching Workday role requirements."""
        try:
            skills = json.loads(profile.skills_json or "[]")
        except (TypeError, json.JSONDecodeError):
            skills = []
        details = []
        if profile.current_title:
            details.append(profile.current_title)
        if profile.years_of_experience is not None:
            details.append(f"{profile.years_of_experience:g} years of experience")
        if skills:
            details.append(f"Skills: {', '.join(skills)}")
        if not details:
            return "Candidate profile details are required to generate a grounded summary."
        return f"{'. '.join(details)}. Relevant role: {job_title} at {company}."

    def generate_cover_letter_text(
        self,
        profile: WorkdayCandidateProfile,
        job_title: str,
        company: str,
        matched_keywords: List[str],
    ) -> str:
        """Generate personalized, high-converting Workday cover letter."""
        candidate_name = " ".join(
            part for part in (profile.first_name, profile.last_name) if part
        )
        try:
            skills = json.loads(profile.skills_json or "[]")
        except (TypeError, json.JSONDecodeError):
            skills = []
        lines = [
            f"Dear Hiring Team at {company},",
            "",
            f"I am interested in the {job_title} role at {company}.",
        ]
        if profile.years_of_experience is not None:
            lines.append(f"I have {profile.years_of_experience:g} years of experience.")
        if profile.current_company:
            lines.append(f"My current company is {profile.current_company}.")
        if skills:
            lines.append(f"My listed skills include {', '.join(skills)}.")
        lines.extend(["", "Thank you for your time and consideration."])
        if candidate_name:
            lines.extend(["", "Sincerely,", candidate_name])
        contact = [profile.account_email, profile.phone, profile.linkedin_url]
        contact = [value for value in contact if value]
        if contact:
            lines.extend(["", " | ".join(contact)])
        return "\n".join(lines)

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
        matched_skill_names = {keyword.casefold() for keyword in matched_keywords}
        combined_skills = sorted(
            dict.fromkeys(skills),
            key=lambda skill: skill.casefold() not in matched_skill_names,
        )

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
        headline_text = profile.current_title or ""
        if full_name:
            story.append(Paragraph(html.escape(full_name), title_style))
            story.append(Spacer(1, 2))
        if profile.current_title:
            story.append(Paragraph(html.escape(profile.current_title), subtitle_style))
            story.append(Spacer(1, 4))

        contact_values = [
            profile.account_email,
            profile.phone,
            ", ".join(value for value in (profile.city, profile.country) if value),
            profile.linkedin_url,
            profile.github_url,
        ]
        contact_line = " • ".join(html.escape(value) for value in contact_values if value)
        if contact_line:
            story.append(Paragraph(contact_line, contact_style))
            story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=8))

        # ── Professional Summary ──
        if summary_text:
            story.append(Paragraph("PROFESSIONAL SUMMARY", section_heading))
            story.append(Paragraph(html.escape(summary_text), body_style))
            story.append(Spacer(1, 8))

        # ── Core Technical Competencies ──
        skills_str = ", ".join(combined_skills[:18])
        if skills_str:
            story.append(Paragraph("CORE TECHNICAL SKILLS", section_heading))
            story.append(Paragraph(f"<b>Skills:</b> {html.escape(skills_str)}", body_style))
            story.append(Spacer(1, 8))

        # ── Professional Experience ──
        work_items = profile.to_dict().get("work_history", [])
        if work_items:
            story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_heading))
        for w in work_items:
            role_title = w.get("title", "")
            comp_name = w.get("company", "")
            loc = w.get("location", "")
            dates = " – ".join(value for value in (w.get("start_date", ""), w.get("end_date", "")) if value)
            exp_header = " — ".join(value for value in (role_title, comp_name) if value)
            details = " | ".join(value for value in (loc, dates) if value)
            if exp_header:
                exp_header = f"<b>{html.escape(exp_header)}</b>"
                if details:
                    exp_header += f" <font color='#64748b'>| {html.escape(details)}</font>"
                story.append(Paragraph(exp_header, bold_body))
                story.append(Spacer(1, 2))

            desc = w.get("description", "")
            if desc:
                story.append(Paragraph(f"• {html.escape(desc)}", bullet_style))
            if exp_header or desc:
                story.append(Spacer(1, 6))

        # ── Education ──
        edu_items = profile.to_dict().get("education", [])
        if edu_items:
            story.append(Paragraph("EDUCATION", section_heading))
        for e in edu_items:
            school = e.get("school", "")
            degree = e.get("degree", "")
            field_of_study = e.get("field_of_study", "")
            dates = " – ".join(value for value in (e.get("start_date", ""), e.get("end_date", "")) if value)
            qualification = " in ".join(value for value in (degree, field_of_study) if value)
            education_line = " — ".join(value for value in (qualification, school) if value)
            if education_line:
                details = f" <font color='#64748b'>| {html.escape(dates)}</font>" if dates else ""
                story.append(Paragraph(f"<b>{html.escape(education_line)}</b>{details}", body_style))
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
{chr(10).join(f"{w.get('title', '')} at {w.get('company', '')} ({w.get('start_date', '')} - {w.get('end_date', '')}): {w.get('description', '')}" for w in work_items)}

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
                account_email=candidate_profile.get("email") or candidate_profile.get("account_email", ""),
                first_name=candidate_profile.get("first_name", ""),
                last_name=candidate_profile.get("last_name", "Jain"),
                phone=candidate_profile.get("phone", ""),  # never a placeholder phone on a real application
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
