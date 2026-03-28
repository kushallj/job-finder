"""
pdf_builder.py — Dynamic ResumeData → PDF generator.

Builds a clean, ATS-readable, single-column PDF from a ResumeData object.
Uses the same ReportLab setup as create_resume_pdf.py but driven by data
instead of hardcoded strings.

ATS readability rules applied:
  - Single column layout (no tables, no frames)
  - Standard fonts (Helvetica family — always available in ReportLab)
  - No headers/footers (ATS parsers often skip them)
  - Text is selectable (vector PDF, not image)
  - Standard section titles in plain text (not styled dividers)
  - No special characters in section headers

Output:
  data/resume_v{job_id}.pdf  — tailored variant
  data/resume.pdf            — base resume (untouched)

Modified bullets are visually identical to originals — no indication
of rewriting is visible in the PDF (professional appearance).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from .resume_model import ResumeData, ResumeSection

log = logging.getLogger(__name__)

# ── Color palette (same as create_resume_pdf.py) ─────────────────────────────
_NAVY  = colors.HexColor("#1a1a2e")
_GRAY  = colors.HexColor("#444444")
_LGRAY = colors.HexColor("#333333")

# ── Font sizes ────────────────────────────────────────────────────────────────
_SZ = {
    "name":    15, "tagline": 8.5, "contact": 8.5,
    "section": 9.5, "job_title": 9, "company": 8.5,
    "bullet":  8.2, "body":     8.2, "skill":   8.0,
}


def _make_styles() -> dict:
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "name": s("name",
            fontName="Helvetica-Bold", fontSize=_SZ["name"],
            leading=_SZ["name"] + 2, alignment=TA_CENTER,
            spaceAfter=1, textColor=_NAVY),

        "tagline": s("tagline",
            fontName="Helvetica", fontSize=_SZ["tagline"],
            leading=_SZ["tagline"] + 2, alignment=TA_CENTER,
            spaceAfter=1, textColor=_GRAY),

        "contact": s("contact",
            fontName="Helvetica", fontSize=_SZ["contact"],
            leading=_SZ["contact"] + 2, alignment=TA_CENTER,
            spaceAfter=4, textColor=_LGRAY),

        "section": s("section",
            fontName="Helvetica-Bold", fontSize=_SZ["section"],
            leading=_SZ["section"] + 1, spaceBefore=5, spaceAfter=1,
            textColor=_NAVY, alignment=TA_LEFT),

        "job_title": s("job_title",
            fontName="Helvetica-Bold", fontSize=_SZ["job_title"],
            leading=_SZ["job_title"] + 1, spaceBefore=4, spaceAfter=0),

        "company": s("company",
            fontName="Helvetica-Oblique", fontSize=_SZ["company"],
            leading=_SZ["company"] + 1, spaceBefore=0, spaceAfter=1,
            textColor=_GRAY),

        "bullet": s("bullet",
            fontName="Helvetica", fontSize=_SZ["bullet"],
            leading=_SZ["bullet"] + 2.2,
            leftIndent=10, firstLineIndent=-10,
            spaceBefore=0, spaceAfter=0.5),

        "skill_line": s("skill_line",
            fontName="Helvetica", fontSize=_SZ["skill"],
            leading=_SZ["skill"] + 2.5, spaceBefore=0, spaceAfter=0),

        "body": s("body",
            fontName="Helvetica", fontSize=_SZ["body"],
            leading=_SZ["body"] + 2.5, spaceBefore=0, spaceAfter=0),

        "project_title": s("project_title",
            fontName="Helvetica-Bold", fontSize=_SZ["body"],
            leading=_SZ["body"] + 2, spaceBefore=3, spaceAfter=0),

        "project_body": s("project_body",
            fontName="Helvetica", fontSize=_SZ["body"] - 0.2,
            leading=_SZ["body"] + 1.8, spaceBefore=0, spaceAfter=0),
    }


class ResumePDFBuilder:
    """
    Builds a PDF from a ResumeData object.

    Usage:
        builder = ResumePDFBuilder()
        path = builder.build(resume_data, job_id=42)
        # → "data/resume_v42.pdf"
    """

    OUTPUT_DIR = Path("data")

    def build(self, resume: ResumeData, job_id: Optional[int] = None) -> str:
        """
        Build PDF and return the output path.

        Args:
            resume: Populated ResumeData (possibly tailored)
            job_id: If provided, outputs resume_v{job_id}.pdf; else resume.pdf
        """
        self.OUTPUT_DIR.mkdir(exist_ok=True)
        filename = f"resume_v{job_id}.pdf" if job_id else "resume.pdf"
        pdf_path = str(self.OUTPUT_DIR / filename)

        st    = _make_styles()
        story = self._build_story(resume, st)

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            leftMargin=0.45 * inch,
            rightMargin=0.45 * inch,
            topMargin=0.4 * inch,
            bottomMargin=0.35 * inch,
        )
        doc.build(story)
        log.info("PDF built: %s (%d bytes)", pdf_path, Path(pdf_path).stat().st_size)
        return pdf_path

    # ── Story builder ─────────────────────────────────────────────────────────

    def _build_story(self, resume: ResumeData, st: dict) -> list:
        story = []

        # Header
        story.append(Paragraph(resume.name, st["name"]))
        if resume.tagline:
            story.append(Paragraph(
                self._escape(resume.tagline).replace("·", "&nbsp;·&nbsp;"),
                st["tagline"]
            ))

        # Contact line
        contact_parts = []
        if resume.email:    contact_parts.append(resume.email)
        if resume.linkedin: contact_parts.append(resume.linkedin)
        if resume.github:   contact_parts.append(resume.github)
        if resume.website:  contact_parts.append(resume.website)
        if resume.phone:    contact_parts.append(resume.phone)
        if contact_parts:
            story.append(Paragraph(
                " &nbsp;|&nbsp; ".join(self._escape(p) for p in contact_parts),
                st["contact"]
            ))

        # Sections in order
        section_order = ["summary", "skills", "experience", "projects", "education", "certs"]
        rendered_types = set()

        for sec_type in section_order:
            sections = [s for s in resume.sections if s.type == sec_type]
            if not sections:
                continue

            # Section header (once per type)
            if sec_type not in rendered_types:
                story.append(Paragraph(sections[0].title.upper(), st["section"]))
                story.append(HRFlowable(
                    width="100%", thickness=0.6,
                    color=_NAVY, spaceAfter=2, spaceBefore=0,
                ))
                rendered_types.add(sec_type)

            for sec in sections:
                self._render_section(story, sec, st, sec_type)

        return story

    def _render_section(
        self, story: list, sec: ResumeSection, st: dict, sec_type: str
    ) -> None:
        if sec_type == "summary":
            for b in sec.bullets:
                story.append(Paragraph(self._escape(b.text), st["body"]))

        elif sec_type == "skills":
            for b in sec.bullets:
                # Skills bullets contain "Label: value" format
                text = self._escape(b.text)
                # Bold the label part (up to first colon)
                if ":" in text:
                    label, _, rest = text.partition(":")
                    text = f"<b>{label}:</b>{rest}"
                story.append(Paragraph(text, st["skill_line"]))

        elif sec_type == "experience":
            if sec.header:
                # Split "Job Title\nCompany · Dates · Location"
                lines = sec.header.split("\n")
                job_title = lines[0].strip()
                company   = lines[1].strip() if len(lines) > 1 else ""
                story.append(Paragraph(self._escape(job_title), st["job_title"]))
                if company:
                    story.append(Paragraph(
                        self._escape(company).replace("·", "&nbsp;·&nbsp;"),
                        st["company"]
                    ))
            for b in sec.bullets:
                story.append(Paragraph(
                    f"• {self._escape(b.text)}", st["bullet"]
                ))
            story.append(Spacer(1, 3))

        elif sec_type == "projects":
            for b in sec.bullets:
                # Projects: first bullet is title+tech, rest is description
                text = self._escape(b.text)
                if sec.header and b == sec.bullets[0]:
                    story.append(Paragraph(f"<b>{text}</b>", st["project_title"]))
                else:
                    story.append(Paragraph(text, st["project_body"]))

        elif sec_type == "education":
            for b in sec.bullets:
                story.append(Paragraph(self._escape(b.text), st["body"]))

        elif sec_type == "certs":
            for b in sec.bullets:
                text = self._escape(b.text)
                story.append(Paragraph(text, st["skill_line"]))

    @staticmethod
    def _escape(text: str) -> str:
        """Escape XML special chars for ReportLab Paragraph."""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            # Restore bold/italic tags we intentionally add
            .replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
            .replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
        )
