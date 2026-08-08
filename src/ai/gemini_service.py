"""
gemini_service.py — Gemini AI client with async HTTP support.

REFACTORED for async pipeline:
  • Uses aiohttp.ClientSession for true async HTTP calls (no thread executor blocking)
  • Connection pooling with configurable limits (max connections, timeouts)
  • Proper session cleanup on shutdown via async context manager
  • Direct REST API calls to Gemini API endpoints for non-blocking I/O
  • Maintains same public interface (extract_skills, match_resume_to_job, etc.)

Migration from SDK to REST API:
  OLD: client.models.generate_content() (blocking, requires run_in_executor)
  NEW: aiohttp POST to https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
       (true async, no thread executor needed)

API Reference: https://ai.google.dev/api/rest/v1beta/models/generateContent
Install: aiohttp already in requirements.txt
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import aiohttp

from src.config import settings

log = logging.getLogger(__name__)


class GeminiService:
    """
    Async Gemini AI service using aiohttp for true non-blocking HTTP calls.

    Features:
    - Shared ClientSession with connection pooling (reuse across requests)
    - Configurable connection limits and timeouts
    - Direct REST API calls (no blocking SDK)
    - Proper cleanup via async context manager
    - Same public interface as before

    Usage:
        async with GeminiService() as ai:
            skills = await ai.extract_skills(description)
            match = await ai.match_resume_to_job(resume, skills)

    Or initialize once and reuse:
        ai = GeminiService()
        await ai.initialize()
        # ... use ai ...
        await ai.close()
    """

    # API endpoint and model configuration
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    MODEL = getattr(settings, "gemini_model", "gemini-2.0-flash-exp")

    def __init__(
        self,
        max_connections: int = 100,
        max_connections_per_host: int = 10,
        connection_timeout: float = 30.0,
        request_timeout: float = 60.0,
    ):
        """
        Initialize GeminiService with connection pooling configuration.

        Args:
            max_connections: Total connection pool size
            max_connections_per_host: Max connections per host (rate limiting)
            connection_timeout: Timeout for establishing connection
            request_timeout: Timeout for complete request/response
        """
        api_key = getattr(settings, "gemini_api_key", None) or getattr(settings, "google_api_key", None)
        if not api_key:
            raise ValueError(
                "Gemini API key not found.\n"
                "Add GEMINI_API_KEY=your_key to your .env file.\n"
                "Get a key at: https://aistudio.google.com/apikey"
            )

        self._api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Connection pool configuration
        self._connector_config = {
            "limit": max_connections,
            "limit_per_host": max_connections_per_host,
            "ttl_dns_cache": 300,  # DNS cache TTL in seconds
            "enable_cleanup_closed": True,
        }
        
        # Timeout configuration
        self._timeout = aiohttp.ClientTimeout(
            total=request_timeout,
            connect=connection_timeout,
            sock_read=request_timeout,
        )
        
        log.info(
            "GeminiService initialized (model=%s, max_conn=%d, conn_per_host=%d)",
            self.MODEL,
            max_connections,
            max_connections_per_host,
        )

    async def initialize(self) -> None:
        """
        Initialize the HTTP session. Must be called before making requests
        if not using the async context manager.
        """
        if self._session is None:
            connector = aiohttp.TCPConnector(**self._connector_config)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self._timeout,
                raise_for_status=False,  # Handle errors manually
            )
            log.debug("HTTP session created with connection pooling")

    async def close(self) -> None:
        """Close the HTTP session and cleanup resources."""
        if self._session is not None:
            await self._session.close()
            self._session = None
            log.debug("HTTP session closed")

    async def __aenter__(self) -> "GeminiService":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session is initialized."""
        if self._session is None:
            raise RuntimeError(
                "GeminiService not initialized. Call await service.initialize() "
                "or use async with GeminiService() as service:"
            )
        return self._session

    async def _ensure_initialized(self) -> None:
        """Auto-initialize session if not already done (for backward compatibility)."""
        if self._session is None:
            log.debug("Auto-initializing GeminiService session")
            await self.initialize()

    # ── Core HTTP call — everything else goes through here ───────────────────

    async def _call_gemini(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        Send a prompt to Gemini via REST API and return the text response.
        Uses aiohttp for true async HTTP (no thread executor needed).

        Args:
            prompt: The prompt to send to Gemini
            max_tokens: Maximum tokens in response

        Returns:
            Generated text from Gemini

        Raises:
            aiohttp.ClientError: On HTTP errors
            asyncio.TimeoutError: On timeout
            ValueError: On invalid API response
        """
        # Auto-initialize if needed (for backward compatibility)
        await self._ensure_initialized()
        session = self._ensure_session()
        
        # Build REST API URL
        url = f"{self.BASE_URL}/{self.MODEL}:generateContent"
        
        # Build request payload (Gemini REST API format)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7,
            },
        }
        
        # Add API key as query parameter
        params = {"key": self._api_key}
        
        try:
            async with session.post(url, json=payload, params=params) as response:
                # Check for HTTP errors
                if response.status != 200:
                    error_text = await response.text()
                    log.error(
                        "Gemini API error (status=%d): %s",
                        response.status,
                        error_text[:500],
                    )
                    raise aiohttp.ClientError(
                        f"Gemini API returned status {response.status}: {error_text[:200]}"
                    )
                
                # Parse response
                data = await response.json()
                
                # Extract text from response structure
                # Response format: {candidates: [{content: {parts: [{text: "..."}]}}]}
                try:
                    candidates = data.get("candidates", [])
                    if not candidates:
                        log.warning("No candidates in Gemini response")
                        return ""
                    
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        log.warning("No parts in Gemini response")
                        return ""
                    
                    text = parts[0].get("text", "")
                    return text
                    
                except (KeyError, IndexError, TypeError) as exc:
                    log.error("Failed to parse Gemini response: %s", exc)
                    raise ValueError(f"Invalid Gemini API response structure: {exc}")
                    
        except asyncio.TimeoutError:
            log.error("Gemini API request timed out")
            raise
        except aiohttp.ClientError as exc:
            log.error("Gemini API HTTP error: %s", exc)
            raise

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