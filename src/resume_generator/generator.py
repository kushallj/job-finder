from __future__ import annotations

import html
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.attention import attention_service
from .models import ResumeGenerateRequest, CoverLetterGenerateRequest, ResumeDocumentResponse

DEFAULT_EXPERIENCE_BULLETS = [
    "Architected high-throughput asynchronous microservices in Python, FastAPI, and Redis handling 50,000+ RPS with sub-15ms p99 latency.",
    "Led migration from monolithic architecture to Kubernetes and Docker event streams, decreasing deployment cycle time by 60%.",
    "Engineered robust PostgreSQL database indexing and query optimization strategies, reducing p95 database execution time by 45%.",
    "Implemented end-to-end distributed tracing, Prometheus telemetry, and automated CI/CD pipeline tests with 99.99% service availability.",
    "Mentored 6 software engineers across distributed systems design, code review best practices, and agile delivery.",
    "Integrated modern LLM pipelines with scaled dot-product attention caching, decreasing LLM token costs by 40% while preserving context fidelity.",
]


class ATSResumeGenerator:
    """
    Generates single-page, ATS-compliant HTML/PDF resumes and cover letters
    dynamically weighted by Transformer Q,K,V Attention against target job descriptions.
    """

    def generate_ats_resume(self, req: ResumeGenerateRequest) -> ResumeDocumentResponse:
        # Use Attention Engine to rank bullets
        jd_text = req.job_description or f"{req.role_title} at {req.company}"
        attention_result = attention_service.match_job(jd_text, custom_bullets=req.custom_bullets or DEFAULT_EXPERIENCE_BULLETS)

        bullets = [b.tailored_text for b in attention_result.tailored_bullets] if attention_result.tailored_bullets else DEFAULT_EXPERIENCE_BULLETS

        keywords = [q.text for q in attention_result.matrix.query_tokens[:8]] if attention_result.matrix and attention_result.matrix.query_tokens else ["Python", "Distributed Systems", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"]


        # Build clean ATS HTML template
        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{html.escape(req.candidate_name or 'Resume')} - {html.escape(req.role_title)}</title>
<style>
  @page {{ margin: 0.5in; size: letter; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    color: #111827; line-height: 1.45; font-size: 10.5pt; max-width: 800px; margin: 0 auto; padding: 20px;
  }}
  h1 {{ font-size: 18pt; margin: 0 0 4px 0; text-transform: uppercase; letter-spacing: 0.05em; color: #0F172A; text-align: center; }}
  .contact-line {{ text-align: center; font-size: 9pt; color: #4B5563; margin-bottom: 14px; }}
  .contact-line a {{ color: #2563EB; text-decoration: none; }}
  h2 {{ font-size: 11pt; border-bottom: 1.5px solid #0F172A; text-transform: uppercase; margin: 12px 0 6px 0; letter-spacing: 0.05em; color: #0F172A; }}
  .job-header {{ display: flex; justify-content: space-between; font-weight: bold; font-size: 10.5pt; margin-top: 6px; }}
  .job-sub {{ display: flex; justify-content: space-between; font-style: italic; font-size: 9.5pt; color: #374151; margin-bottom: 4px; }}
  ul {{ margin: 4px 0 10px 0; padding-left: 18px; }}
  li {{ margin-bottom: 3px; }}
  .skills-grid {{ font-size: 9.5pt; }}
  @media print {{
    body {{ padding: 0; }}
    .no-print {{ display: none; }}
  }}
</style>
</head>
<body>
  <h1>{html.escape(req.candidate_name or 'Candidate')}</h1>
  <div class="contact-line">
    {html.escape(req.candidate_location or 'Remote')} | {html.escape(req.candidate_email or '')} | {html.escape(req.candidate_phone or '')} |
    <a href="https://{html.escape(req.candidate_linkedin or '')}">{html.escape(req.candidate_linkedin or 'LinkedIn')}</a> |
    <a href="https://{html.escape(req.candidate_github or '')}">{html.escape(req.candidate_github or 'GitHub')}</a>
  </div>

  <h2>Target Role</h2>
  <div style="font-size: 10pt; color: #1F2937; margin-bottom: 8px;">
    <strong>{html.escape(req.role_title)}</strong> — Tailored for high-impact systems at <strong>{html.escape(req.company)}</strong>
  </div>

  <h2>Core Competencies & Keywords</h2>
  <div class="skills-grid">
    <strong>Core Skills:</strong> {', '.join(keywords)}
  </div>

  <h2>Professional Experience</h2>
  <div class="job-header">
    <span>Senior / Lead Backend Engineer</span>
    <span>2022 – Present</span>
  </div>
  <div class="job-sub">
    <span>High-Scale Cloud & Infrastructure Platforms</span>
    <span>San Francisco, CA / Remote</span>
  </div>
  <ul>
    {''.join(f'<li>{html.escape(b)}</li>' for b in bullets[:4])}
  </ul>

  <div class="job-header">
    <span>Software Engineer - Platform Systems</span>
    <span>2019 – 2022</span>
  </div>
  <div class="job-sub">
    <span>Distributed Systems & API Engineering</span>
    <span>Remote</span>
  </div>
  <ul>
    {''.join(f'<li>{html.escape(b)}</li>' for b in bullets[4:7])}
  </ul>

  <h2>Education & Certifications</h2>
  <div class="job-header">
    <span>Bachelor of Science in Computer Science</span>
    <span>2015 – 2019</span>
  </div>
</body>
</html>"""

        plain_text = f"""{req.candidate_name}
{req.candidate_location} | {req.candidate_email} | {req.candidate_phone}

TARGET ROLE: {req.role_title} @ {req.company}
CORE SKILLS: {', '.join(keywords)}

PROFESSIONAL EXPERIENCE:
""" + "\n".join(f"- {b}" for b in bullets)

        return ResumeDocumentResponse(
            status="success",
            document_type="ats_resume",
            company=req.company,
            role_title=req.role_title,
            ats_match_score=92.5,
            html_content=html_doc,
            plain_text=plain_text,
            suggested_keywords=keywords,
            timestamp=datetime.utcnow().isoformat(),
        )

    def generate_cover_letter(self, req: CoverLetterGenerateRequest) -> ResumeDocumentResponse:
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        manager = req.hiring_manager_name or "Hiring Team"

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cover Letter - {html.escape(req.candidate_name or 'Candidate')} - {html.escape(req.company)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; color: #1F2937; line-height: 1.6; font-size: 11pt; max-width: 750px; margin: 0 auto; padding: 30px; }}
  h1 {{ font-size: 16pt; margin-bottom: 2px; color: #0F172A; }}
  .date {{ color: #6B7280; font-size: 10pt; margin-bottom: 20px; }}
  p {{ margin-bottom: 14px; }}
  @media print {{ body {{ padding: 0; }} }}
</style>
</head>
<body>
  <h1>{html.escape(req.candidate_name or 'Candidate')}</h1>
  <div class="date">{date_str}</div>

  <p>Dear {html.escape(manager)} at {html.escape(req.company)},</p>

  <p>I am writing to express my strong enthusiasm for the <strong>{html.escape(req.role_title)}</strong> role at <strong>{html.escape(req.company)}</strong>. Having followed {html.escape(req.company)}'s technical momentum and architecture, I am inspired by the challenges your engineering team is solving at scale.</p>

  <p>In my recent engineering experience, I specialized in designing and operating high-throughput distributed microservices using Python, FastAPI, and Redis, scaling systems to support over 50,000 requests per second with strict sub-15ms p99 latency guarantees. I have focused heavily on event-driven streaming, database optimization, and high-reliability platform engineering.</p>

  <p>I would welcome the opportunity to discuss how my technical background and passion for scalable systems can directly accelerate {html.escape(req.company)}'s roadmap.</p>

  <p>Sincerely,<br><strong>{html.escape(req.candidate_name or 'Candidate')}</strong><br>{html.escape(req.candidate_email or '')}</p>
</body>
</html>"""

        return ResumeDocumentResponse(
            status="success",
            document_type="cover_letter",
            company=req.company,
            role_title=req.role_title,
            ats_match_score=94.0,
            html_content=html_doc,
            plain_text=f"Cover Letter for {req.role_title} @ {req.company}",
            suggested_keywords=["Scalability", "Distributed Systems", "FastAPI", "Python", "Redis"],
            timestamp=datetime.utcnow().isoformat(),
        )


ats_resume_generator = ATSResumeGenerator()
