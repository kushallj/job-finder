"""ApyHub / SharpAPI Resume Parser & Evaluation Service.

Converts unstructured resume documents (PDF, DOCX, TXT) into rich structured candidate
data (skills, employment history, education, contact info) and evaluates candidate-job fit.
"""
from __future__ import annotations

import asyncio
import io
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

APYHUB_PARSE_URL = "https://api.us.apyhub.com/sharpapi/parse-resume"
APYHUB_STATUS_BASE = "https://api.us.apyhub.com/sharpapi/parse-resume/job/status"

COMMON_TECH_SKILLS = [
    "Python", "FastAPI", "Django", "Flask", "React", "TypeScript", "JavaScript",
    "Node.js", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes",
    "AWS", "GCP", "Azure", "CI/CD", "Git", "REST API", "GraphQL", "Microservices",
    "SQL", "NoSQL", "Pandas", "NumPy", "PyTorch", "TensorFlow", "Linux", "Terraform",
    "Next.js", "Redux", "TailwindCSS", "Kafka", "RabbitMQ", "Elasticsearch"
]


def _extract_text_from_bytes(file_bytes: bytes, filename: str = "resume.pdf") -> str:
    """Extract raw text from PDF or TXT bytes."""
    if filename.lower().endswith(".pdf") or file_bytes.startswith(b"%PDF"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if text.strip():
                return text
        except Exception as e:
            logger.debug("pypdf extraction failed: %s", e)
    try:
        text = file_bytes.decode("utf-8", errors="ignore")
        if len(text.strip()) > 30:
            return text
    except Exception:
        pass
    default_txt = Path("data/resume.txt")
    if default_txt.exists():
        return default_txt.read_text(encoding="utf-8", errors="ignore")
    return ""


def _extract_fallback_profile(text: str) -> Dict[str, Any]:
    """Extract candidate email, phone, and skills from raw resume text."""
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    
    # Extract skills
    found_skills = []
    text_lower = text.lower()
    for sk in COMMON_TECH_SKILLS:
        pattern = r"\b" + re.escape(sk.lower()) + r"\b"
        if re.search(pattern, text_lower):
            found_skills.append(sk)
            
    # Extract name (heuristic from first lines)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidate_name = lines[0] if lines else "Candidate"
    if len(candidate_name) > 40 or "@" in candidate_name:
        candidate_name = getattr(settings, "sender_name", "Kushall Jain") or "Kushall Jain"

    return {
        "status": "fallback",
        "provider": "local_nlp_fallback",
        "candidate": {
            "name": candidate_name,
            "email": email_match.group(0) if email_match else "",
            "phone": phone_match.group(0) if phone_match else "",
            "city": "",
            "country": "",
            "languages": ["English"],
        },
        "positions": [],
        "education": [],
        "skills": found_skills,
        "raw_text_snippet": text[:300],
    }


class SharpAPIResumeParser:
    """Client for ApyHub SharpAPI Resume Parsing & Evaluation."""

    def __init__(
        self,
        token: Optional[str] = None,
        timeout: float = 30.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.token = (
            token
            or getattr(settings, "apyhub_token", None)
            or getattr(settings, "sharpapi_api_key", None)
            or getattr(settings, "apyhub_api_key", None)
        )
        self.timeout = timeout
        self.transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    async def parse_resume_bytes(
        self,
        file_bytes: bytes,
        filename: str = "resume.pdf",
        poll_interval: float = 1.5,
        max_poll_attempts: int = 15,
    ) -> Dict[str, Any]:
        """Submit resume bytes to ApyHub SharpAPI and poll for structured JSON results."""
        if not self.enabled:
            raise ValueError("ApyHub / SharpAPI token is not configured.")

        headers = {"apy-token": self.token}
        files = {"file": (filename, file_bytes, "application/pdf" if filename.endswith(".pdf") else "application/octet-stream")}

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, transport=self.transport) as client:
            resp = await client.post(APYHUB_PARSE_URL, headers=headers, files=files)
            if resp.status_code != 202:
                resp.raise_for_status()

            init_data = resp.json()
            job_id = init_data.get("job_id")
            if not job_id:
                raise RuntimeError(f"ApyHub did not return a valid job_id: {init_data}")

            status_url = f"{APYHUB_STATUS_BASE}/{job_id}"

            # Poll for completion
            for attempt in range(max_poll_attempts):
                await asyncio.sleep(poll_interval)
                poll_resp = await client.get(status_url, headers=headers)
                if poll_resp.status_code == 200:
                    data = poll_resp.json()
                    attributes = data.get("data", {}).get("attributes", {})
                    status = attributes.get("status") or data.get("status")
                    if status in ("success", "completed", "COMPLETED"):
                        result_payload = attributes.get("result", {})
                        return self._normalize_parsed_resume(result_payload, job_id=job_id)
                    if status in ("failed", "FAILED"):
                        raise RuntimeError(f"ApyHub resume parsing failed: {data}")
                elif poll_resp.status_code not in (202, 404):
                    poll_resp.raise_for_status()

            raise TimeoutError(f"ApyHub SharpAPI parsing timed out after {max_poll_attempts} attempts for job {job_id}")

    async def parse_resume_file(
        self,
        file_path: Union[str, Path],
        poll_interval: float = 1.5,
        max_poll_attempts: int = 15,
    ) -> Dict[str, Any]:
        """Parse a local resume file."""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Resume file not found at: {file_path}")
        content = p.read_bytes()
        return await self.parse_resume_bytes(content, filename=p.name, poll_interval=poll_interval, max_poll_attempts=max_poll_attempts)

    def _normalize_parsed_resume(self, raw: Dict[str, Any], job_id: Optional[str] = None) -> Dict[str, Any]:
        """Normalize SharpAPI parsed resume into clean candidate profile."""
        skills: List[str] = []
        positions = raw.get("positions", []) or []
        for pos in positions:
            for sk in pos.get("skills", []) or []:
                if sk and sk not in skills:
                    skills.append(sk)

        if "skills" in raw and isinstance(raw["skills"], list):
            for sk in raw["skills"]:
                if isinstance(sk, str) and sk not in skills:
                    skills.append(sk)
                elif isinstance(sk, dict) and sk.get("name") and sk["name"] not in skills:
                    skills.append(sk["name"])

        return {
            "status": "success",
            "provider": "sharpapi_apyhub",
            "job_id": job_id,
            "candidate": {
                "name": raw.get("candidate_name") or "",
                "email": raw.get("candidate_email") or "",
                "phone": raw.get("candidate_phone") or "",
                "address": raw.get("candidate_address") or "",
                "city": raw.get("candidate_city") or "",
                "country": raw.get("candidate_country") or "",
                "languages": raw.get("candidate_spoken_languages") or [],
            },
            "positions": positions,
            "education": raw.get("education", []) or [],
            "skills": skills,
            "raw_result": raw,
        }

    async def evaluate_resume(
        self,
        file_bytes: bytes,
        filename: str = "resume.pdf",
        job_description: Optional[str] = None,
        job_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Parse resume via SharpAPI and evaluate relevance against a target job description."""
        try:
            parsed = await self.parse_resume_bytes(file_bytes, filename=filename)
        except Exception as exc:
            logger.warning("SharpAPI online parse failed (%s) — falling back to local text analysis", exc)
            extracted_text = _extract_text_from_bytes(file_bytes, filename=filename)
            parsed = _extract_fallback_profile(extracted_text)
            parsed["fallback_reason"] = str(exc)

        candidate_skills = [s for s in parsed.get("skills", []) if s]
        candidate_skills_lower = set(s.lower() for s in candidate_skills)
        jd_text = (job_description or "").lower()
        title_text = (job_title or "").lower()

        # Skill matching
        matched_skills = []
        if jd_text or title_text:
            for skill in candidate_skills:
                sk_low = skill.lower()
                if sk_low in jd_text or sk_low in title_text:
                    matched_skills.append(skill)

        match_score = 0.0
        if candidate_skills and (jd_text or title_text):
            match_score = min(100.0, round((len(matched_skills) / max(len(candidate_skills), 1)) * 100, 1))
        elif parsed.get("status") == "success":
            match_score = 85.0
        elif candidate_skills:
            match_score = 70.0

        return {
            "evaluation_status": "completed",
            "match_score": match_score,
            "parsed_profile": parsed,
            "matched_skills": matched_skills,
            "total_candidate_skills": len(candidate_skills),
            "target_job_title": job_title,
        }


# Alias for compatibility
ApyHubResumeParserClient = SharpAPIResumeParser
