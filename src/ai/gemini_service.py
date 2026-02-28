"""
gemini_service.py — Gemini AI client.

FIXED:
  • Migrated from deprecated `google.generativeai` → `google.genai`
    (google.generativeai is end-of-life, receives no more updates/bug fixes)
  • New SDK uses google.genai.Client with a different call signature
  • All public methods (_call_gemini, extract_skills, match_resume_to_job,
    rewrite_resume, generate_cover_letter) preserve the same interface
    so nothing else in the codebase needs to change

Migration reference:
  OLD: import google.generativeai as genai
       genai.configure(api_key=...)
       model = genai.GenerativeModel("gemini-pro")
       response = model.generate_content(prompt)

  NEW: from google import genai
       client = genai.Client(api_key=...)
       response = client.models.generate_content(
           model="gemini-2.0-flash",
           contents=prompt,
       )

Install: pip install google-genai
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

# ── New SDK ───────────────────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    genai = None  # type: ignore

from src.config import settings

log = logging.getLogger(__name__)


class GeminiService:
    """
    Async wrapper around the new google-genai SDK.

    All methods are async — they run the blocking SDK call in a thread
    executor so the FastAPI event loop is never blocked.

    Public interface (unchanged from old version):
        await ai.extract_skills(description)          → List[str]
        await ai.match_resume_to_job(resume, skills)  → Dict
        await ai.rewrite_resume(resume, description)  → str
        await ai.generate_cover_letter(resume, desc, company) → str
        await ai._call_gemini(prompt, max_tokens)     → str
    """

    # Model to use — gemini-2.0-flash is the current fast default
    MODEL = getattr(settings, "gemini_model", "gemini-2.0-flash")

    def __init__(self):
        if not _GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package not installed.\n"
                "Run: pip install google-genai\n"
                "Do NOT install google-generativeai — that package is deprecated."
            )

        api_key = getattr(settings, "gemini_api_key", None) or getattr(settings, "google_api_key", None)
        if not api_key:
            raise ValueError(
                "Gemini API key not found.\n"
                "Add GEMINI_API_KEY=your_key to your .env file.\n"
                "Get a key at: https://aistudio.google.com/apikey"
            )

        # Client is created once and reused — thread-safe for concurrent calls
        self._client = genai.Client(api_key=api_key)
        log.info("GeminiService ready (model=%s)", self.MODEL)

    # ── Core call — everything else goes through here ─────────────────────────

    async def _call_gemini(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        Send a prompt to Gemini and return the text response.
        Runs the blocking SDK call in a thread executor (keeps event loop free).

        Raises on API errors — callers should wrap in try/except or use
        the with_retry() helper from job_processor.py.
        """
        loop = asyncio.get_event_loop()

        def _blocking_call() -> str:
            response = self._client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                ),
            )
            # Extract text from the response
            if response.text:
                return response.text
            # Fallback: manually join parts if .text is None
            parts = []
            for candidate in (response.candidates or []):
                for part in (candidate.content.parts or []):
                    if hasattr(part, "text") and part.text:
                        parts.append(part.text)
            return "".join(parts)

        return await loop.run_in_executor(None, _blocking_call)

    # ── Public methods ────────────────────────────────────────────────────────

    async def extract_skills(self, job_description: str) -> List[str]:
        """Extract required skills from a job description. Returns a list of strings."""
        prompt = f"""Extract the key technical skills and requirements from this job description.
Return ONLY a JSON array of strings, no explanation, no markdown.
Example output: ["Python", "FastAPI", "PostgreSQL", "Docker"]

Job description:
{job_description[:3000]}

JSON array:"""
        try:
            raw = await self._call_gemini(prompt, max_tokens=512)
            return self._parse_json_list(raw)
        except Exception as exc:
            log.error("extract_skills failed: %s", exc)
            return []

    async def match_resume_to_job(
        self, resume_text: str, job_skills: List[str]
    ) -> Dict[str, Any]:
        """
        Compare resume against job skills.
        Returns: {match_score, matched_skills, missing_skills, recommendations}
        """
        prompt = f"""You are a technical recruiter. Compare this resume to the required job skills.

REQUIRED SKILLS:
{json.dumps(job_skills, indent=2)}

RESUME:
{resume_text[:3000]}

Return ONLY a JSON object with this exact structure (no markdown, no explanation):
{{
  "match_score": <integer 0-100>,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3", "skill4"],
  "recommendations": "One sentence of advice"
}}

JSON:"""
        try:
            raw = await self._call_gemini(prompt, max_tokens=1024)
            return self._parse_json_dict(raw, default={
                "match_score": 0,
                "matched_skills": [],
                "missing_skills": job_skills,
                "recommendations": "Could not analyse resume.",
            })
        except Exception as exc:
            log.error("match_resume_to_job failed: %s", exc)
            return {
                "match_score": 0,
                "matched_skills": [],
                "missing_skills": job_skills,
                "recommendations": f"Analysis failed: {exc}",
            }

    async def rewrite_resume(self, resume_text: str, job_description: str) -> str:
        """Tailor the resume to highlight skills relevant to this job."""
        prompt = f"""Rewrite this resume to better match the job description.
Keep all facts accurate — do not invent experience.
Emphasise skills and achievements most relevant to the role.
Use clean plain text format (no markdown).

JOB DESCRIPTION:
{job_description[:1500]}

ORIGINAL RESUME:
{resume_text[:2000]}

TAILORED RESUME:"""
        try:
            return await self._call_gemini(prompt, max_tokens=2048)
        except Exception as exc:
            log.error("rewrite_resume failed: %s — returning original", exc)
            return resume_text  # safe fallback: return original unchanged

    async def generate_cover_letter(
        self, resume_text: str, job_description: str, company: str
    ) -> str:
        """Generate a concise, personalised cover letter."""
        prompt = f"""Write a professional cover letter for this job application.

COMPANY: {company}
JOB DESCRIPTION: {job_description[:1500]}
MY BACKGROUND: {resume_text[:1500]}

REQUIREMENTS:
- 3 short paragraphs max
- Specific and concrete — mention actual skills from the job description
- No generic filler like "I am passionate about..."
- End with a clear call to action
- Plain text only

COVER LETTER:"""
        try:
            return await self._call_gemini(prompt, max_tokens=1024)
        except Exception as exc:
            log.error("generate_cover_letter failed: %s", exc)
            return (
                f"Dear Hiring Manager,\n\n"
                f"I am writing to express my interest in this position at {company}. "
                f"Please find my resume attached for your review.\n\n"
                f"I would welcome the opportunity to discuss how my experience aligns "
                f"with your team's needs.\n\nBest regards"
            )

    # ── JSON parsing helpers ──────────────────────────────────────────────────

    @staticmethod
    def _parse_json_list(raw: str) -> List[str]:
        """Extract a JSON array from a potentially noisy LLM response."""
        raw = raw.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        # Find the first [...] block
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return []

    @staticmethod
    def _parse_json_dict(raw: str, default: Dict) -> Dict:
        """Extract a JSON object from a potentially noisy LLM response."""
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return default