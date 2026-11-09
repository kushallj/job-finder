from __future__ import annotations

import html
from datetime import datetime, timezone

from src.attention import attention_service
from .models import ResumeGenerateRequest, CoverLetterGenerateRequest, ResumeDocumentResponse


class ATSResumeGenerator:
    """Generate resume and cover-letter drafts using only supplied candidate facts."""

    @staticmethod
    def _contact_link(label: str, value: str | None) -> str:
        if not value:
            return ""
        url = value.strip()
        if not url.lower().startswith(("https://", "http://")):
            url = f"https://{url}"
        return f'<a href="{html.escape(url, quote=True)}">{html.escape(value)}</a>'

    def generate_ats_resume(self, req: ResumeGenerateRequest) -> ResumeDocumentResponse:
        jd_text = req.job_description or f"{req.role_title} at {req.company}"
        attention_result = attention_service.match_job(
            jd_text,
            custom_bullets=req.custom_bullets or [],
        )
        bullets = (
            [bullet.tailored_text for bullet in attention_result.tailored_bullets]
            if attention_result.tailored_bullets
            else req.custom_bullets or []
        )
        keywords = [
            token.text
            for token in attention_result.matrix.query_tokens[:8]
        ] if attention_result.matrix else []

        contact_parts = [
            html.escape(value.strip())
            for value in (req.candidate_location, req.candidate_email, req.candidate_phone)
            if value and value.strip()
        ]
        contact_parts.extend(
            link for link in (
                self._contact_link("LinkedIn", req.candidate_linkedin),
                self._contact_link("GitHub", req.candidate_github),
            ) if link
        )
        contact_html = " | ".join(contact_parts)
        contact_text = " | ".join(
            value.strip()
            for value in (
                req.candidate_location,
                req.candidate_email,
                req.candidate_phone,
                req.candidate_linkedin,
                req.candidate_github,
            )
            if value and value.strip()
        )
        name_html = f"<h1>{html.escape(req.candidate_name)}</h1>" if req.candidate_name else ""
        name_text = req.candidate_name or ""
        bullet_section = ""
        if bullets:
            bullet_items = "".join(f"<li>{html.escape(bullet)}</li>" for bullet in bullets)
            bullet_section = f"<h2>Experience highlights</h2><ul>{bullet_items}</ul>"

        keyword_section = ""
        if keywords:
            keyword_section = (
                "<h2>Job-description keywords</h2>"
                f"<p>{html.escape(', '.join(keywords))}</p>"
            )

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{html.escape(req.role_title)} at {html.escape(req.company)}</title>
<style>
  @page {{ margin: 0.5in; size: letter; }}
  body {{ font-family: Arial, sans-serif; color: #111827; line-height: 1.45; font-size: 10.5pt; max-width: 800px; margin: 0 auto; padding: 20px; }}
  h1 {{ font-size: 18pt; margin: 0 0 4px; text-align: center; }}
  h2 {{ font-size: 11pt; border-bottom: 1px solid #0F172A; text-transform: uppercase; margin: 12px 0 6px; }}
  .contact-line {{ text-align: center; font-size: 9pt; color: #4B5563; margin-bottom: 14px; }}
  a {{ color: #2563EB; text-decoration: none; }}
  li {{ margin-bottom: 3px; }}
  @media print {{ body {{ padding: 0; }} }}
</style>
</head>
<body>
  {name_html}
  <div class="contact-line">{contact_html}</div>
  <h2>Target role</h2>
  <p><strong>{html.escape(req.role_title)}</strong> at <strong>{html.escape(req.company)}</strong></p>
  {keyword_section}
  {bullet_section}
</body>
</html>"""

        plain_sections = [
            name_text,
            contact_text,
            f"TARGET ROLE: {req.role_title} @ {req.company}",
        ]
        if keywords:
            plain_sections.append(f"JOB-DESCRIPTION KEYWORDS: {', '.join(keywords)}")
        if bullets:
            plain_sections.append(
                "EXPERIENCE HIGHLIGHTS:\n" + "\n".join(f"- {bullet}" for bullet in bullets)
            )

        return ResumeDocumentResponse(
            status="success",
            document_type="ats_resume",
            company=req.company,
            role_title=req.role_title,
            ats_match_score=attention_result.overall_score,
            html_content=html_doc,
            plain_text="\n\n".join(section for section in plain_sections if section),
            suggested_keywords=keywords,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def generate_cover_letter(self, req: CoverLetterGenerateRequest) -> ResumeDocumentResponse:
        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
        manager = req.hiring_manager_name or "Hiring Team"
        name = req.candidate_name or ""
        email = req.candidate_email or ""
        greeting = (
            f"Dear {html.escape(manager)},"
        )
        signature = html.escape(name)
        if email:
            signature += f"<br>{html.escape(email)}"
        signature_html = f"<p>Sincerely,<br>{signature}</p>" if name or email else ""
        name_html = f"<h1>{html.escape(name)}</h1>" if name else ""

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cover letter for {html.escape(req.role_title)} at {html.escape(req.company)}</title>
<style>
  body {{ font-family: Arial, sans-serif; color: #1F2937; line-height: 1.6; font-size: 11pt; max-width: 750px; margin: 0 auto; padding: 30px; }}
  h1 {{ font-size: 16pt; margin-bottom: 2px; color: #0F172A; }}
  .date {{ color: #6B7280; font-size: 10pt; margin-bottom: 20px; }}
  p {{ margin-bottom: 14px; }}
  @media print {{ body {{ padding: 0; }} }}
</style>
</head>
<body>
  {name_html}
  <div class="date">{date_str}</div>
  <p>{greeting}</p>
  <p>I am writing to express my interest in the <strong>{html.escape(req.role_title)}</strong> role at <strong>{html.escape(req.company)}</strong>.</p>
  <p>I would welcome the opportunity to discuss the position and how I could contribute to your team.</p>
  {signature_html}
</body>
</html>"""

        plain_text = (
            f"Dear {manager},\n\n"
            f"I am writing to express my interest in the {req.role_title} role at {req.company}.\n\n"
            "I would welcome the opportunity to discuss the position and how I could contribute to your team."
        )
        if name or email:
            plain_text += f"\n\nSincerely,\n{name}"
            if email:
                plain_text += f"\n{email}"

        return ResumeDocumentResponse(
            status="success",
            document_type="cover_letter",
            company=req.company,
            role_title=req.role_title,
            ats_match_score=0.0,
            html_content=html_doc,
            plain_text=plain_text,
            suggested_keywords=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


ats_resume_generator = ATSResumeGenerator()
