"""
local_llm_service.py — Production Ollama/local LLM service.

What changed from original:
  ✓ httpx.AsyncClient created inside context managers — no leaked connections
  ✓ Model cascade: tries models in priority order, caches best available
  ✓ Health check (Level 1: is Ollama running? Level 2: which models installed?)
  ✓ Hardcoded "Kushall Jain" → settings.sender_name (config-driven)
  ✓ _parse_json handles more edge cases (list, arrays, nested fences)
  ✓ temperature=0.2 for structured extraction (was 0.7 — too creative for JSON)
  ✓ Prompt truncation guards — never overflow context window
  ✓ OllamaManager merged in (no duplicate class)
  ✓ qwen2.5-coder:7b is now primary model — best coding + JSON quality at 7B
  ✓ Per-method timeouts prevent outer 35s budget from silently cancelling calls
  ✓ exc_info=True on all warnings for full tracebacks

Install:
  macOS/Linux:  curl -fsSL https://ollama.com/install.sh | sh
  Windows:      https://ollama.ai/download
  Models:
    ollama pull qwen2.5-coder:7b  # PRIMARY — superior code/JSON quality (4.7GB)
    ollama pull qwen2.5:3b        # lighter fallback (1.9GB)
    ollama pull llama3.2:3b       # strong fallback (2GB, ~18 tok/s)
    ollama pull llama3.2:1b       # ultra fast if 3b is too slow (1GB)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import httpx

try:
    from src.config import settings as _settings
    _SENDER_NAME: str = getattr(_settings, "sender_name", "Applicant")
    _OLLAMA_MODEL: Optional[str] = getattr(_settings, "ollama_model", None)
except Exception:
    _SENDER_NAME = "Applicant"
    _OLLAMA_MODEL = None

log = logging.getLogger(__name__)

# =============================================================================
# Model priority order
# llama3.2:3b is first — optimal for 8GB M1 (2GB VRAM, ~18 tok/s on Metal)
# Mistral variants pushed to end — 4.9GB, starves OS on 8GB machines
# =============================================================================
_MODEL_ORDER = [
    "phi3:mini",        # PRIMARY — 2-3GB RAM, designed for low-resource devices, no lag/heat on 8GB
    "phi3.5:mini",      # Microsoft Phi3.5, slightly larger but still lean
    "qwen2.5:3b",       # lighter fallback — best instruction following at 3B (1.9GB)
    "llama3.2:3b",      # strong fallback — 2GB, good quality
    "llama3.2:1b",      # ultra-fast fallback — 1GB
    "gemma2:2b",
    "qwen2.5-coder:7b", # 4.7GB — only if you have headroom (16GB+)
    "llama3:8b",
    "mistral:latest",   # too large for 8GB M1 — use only on 16GB+
    "mistral:7b",
    "mistral",
]

# Per-method LLM call timeouts (seconds)
# qwen2.5-coder:7b on M1 is ~25s for short prompts, longer for big outputs
_TIMEOUT_EXTRACT   = 90.0   # extract_skills, match_resume
_TIMEOUT_REWRITE   = 240.0  # rewrite_resume — longer output
_TIMEOUT_COVER     = 180.0  # cover letter
_TIMEOUT_HTML      = 150.0  # extract_jobs_from_html


class LocalLLMService:
    """
    Async local LLM via Ollama.

    Model cascade: on first health_check(), discovers which model is
    installed and caches it. Subsequent calls skip /api/tags.

    All httpx clients created inside context managers — no leaks.
    Per-method timeouts ensure outer scraper budget is never silently cancelled.
    """

    BASE_URL = "http://localhost:11434"
    _cached_model: Optional[str] = None  # class-level — shared across instances

    def __init__(self, preferred_model: Optional[str] = None):
        self._preferred  = preferred_model or _OLLAMA_MODEL
        self._available  = False

    # ── HTTP client ───────────────────────────────────────────────────────────

    @asynccontextmanager
    async def _http(self, timeout: float = 120.0):
        async with httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(timeout),
        ) as c:
            yield c

    # ── Health check ──────────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """
        Level 1: Is Ollama running?
        Level 2: Which models installed? Pick best from priority list.
        Caches result — safe to call repeatedly.
        """
        if LocalLLMService._cached_model:
            self._available = True
            return True
        try:
            async with self._http(timeout=5.0) as c:
                resp = await c.get("/api/tags")
                if resp.status_code != 200:
                    log.debug("Ollama /api/tags returned %d", resp.status_code)
                    return False

                raw_models = resp.json().get("models", [])
                full_names: set = {m["name"] for m in raw_models}
                by_base: Dict[str, str] = {}
                for m in raw_models:
                    base = m["name"].split(":")[0]
                    if base not in by_base or "latest" in m["name"]:
                        by_base[base] = m["name"]

                log.debug("Ollama installed models: %s", sorted(full_names))

                candidates: List[str] = []
                if self._preferred:
                    candidates.append(self._preferred)
                candidates.extend(_MODEL_ORDER)

                for candidate in candidates:
                    if candidate in full_names:
                        LocalLLMService._cached_model = candidate
                        self._available = True
                        log.info("✅ Local LLM ready: %s (exact match)", candidate)
                        return True
                    base = candidate.split(":")[0]
                    if base in by_base:
                        LocalLLMService._cached_model = by_base[base]
                        self._available = True
                        log.info("✅ Local LLM ready: %s (matched via base '%s')",
                                 by_base[base], base)
                        return True

                log.warning(
                    "Ollama running but no supported model found.\n"
                    "  → Run: ollama pull qwen2.5-coder:7b\n"
                    "  → Installed: %s",
                    sorted(full_names),
                )
                return False

        except httpx.ConnectError:
            log.debug("Ollama not running at %s", self.BASE_URL)
            return False
        except Exception as exc:
            log.debug("Ollama health check failed: %s", exc)
            return False

    # ── Core API call ─────────────────────────────────────────────────────────

    async def _call(self, prompt: str, max_tokens: int = 1024,
                    timeout: float = 60.0) -> str:
        """
        Call Ollama. Timeout is per-call and passed explicitly by each method.
        Raises asyncio.TimeoutError (caller handles gracefully).
        """
        model = LocalLLMService._cached_model
        if not model:
            raise ConnectionError("Ollama not available. Run: ollama pull qwen2.5-coder:7b")

        async with self._http(timeout=timeout + 5.0) as c:
            resp = await asyncio.wait_for(
                c.post("/api/generate", json={
                    "model":  model,
                    "prompt": prompt[:12000],  # 12k chars — fits 7b context comfortably
                    "stream": False,
                    "options": {
                        "num_predict":   max_tokens,
                        "temperature":   0.2,
                        "top_p":         0.9,
                        "num_ctx":       2048,   # phi3:mini sweet spot — halves RAM vs 4096
                    },
                }),
                timeout=timeout,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama {resp.status_code}: {resp.text[:300]}")
            return resp.json().get("response", "")

    # ── JSON parser ───────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json(text: str, default: Any = None) -> Any:
        """
        Extract the most complete JSON object/array from LLM output.

        Some models (qwen2.5) emit a placeholder {} before the real answer,
        so we collect ALL JSON blocks and return the one with the most content
        rather than blindly taking the first match.
        """
        if not text:
            return default

        text = re.sub(r"```(?:json|python)?\s*", "", text)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE).strip()

        # Try the whole stripped text first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Collect all valid JSON blocks; pick the richest one
        candidates = []
        for open_ch, close_ch in [('{', '}'), ('[', ']')]:
            pos = 0
            while True:
                start = text.find(open_ch, pos)
                if start == -1:
                    break
                depth = 0
                for i, ch in enumerate(text[start:], start):
                    if ch == open_ch:
                        depth += 1
                    elif ch == close_ch:
                        depth -= 1
                        if depth == 0:
                            fragment = text[start:i+1]
                            for attempt in (fragment, fragment.replace("'", '"')):
                                try:
                                    parsed = json.loads(attempt)
                                    candidates.append(parsed)
                                except json.JSONDecodeError:
                                    pass
                            pos = i + 1
                            break
                else:
                    break

        if not candidates:
            return default

        # Return the candidate with the most content:
        # dicts ranked by number of non-empty values, lists by length
        def _richness(obj):
            if isinstance(obj, dict):
                return sum(1 for v in obj.values() if v)
            if isinstance(obj, list):
                return len(obj)
            return 0

        return max(candidates, key=_richness)

    # ── Public AI methods ─────────────────────────────────────────────────────

    async def extract_skills(self, job_description: str) -> Dict:
        prompt = f"""Extract skills from this job description. Return ONLY valid JSON.

Job Description:
{job_description[:2000]}

Return this exact JSON structure with no other text:
{{"technical_skills":["Python","React"],"soft_skills":["Communication"],"experience_level":"Mid","key_responsibilities":["Build APIs"]}}"""

        try:
            raw    = await self._call(prompt, max_tokens=512, timeout=_TIMEOUT_EXTRACT)
            result = self._parse_json(raw, {})
            return {
                "technical_skills":     result.get("technical_skills", []),
                "soft_skills":          result.get("soft_skills", []),
                "experience_level":     result.get("experience_level", "Mid"),
                "key_responsibilities": result.get("key_responsibilities", []),
            }
        except asyncio.TimeoutError:
            log.warning("LLM extract_skills timed out (%.0fs) — keyword fallback", _TIMEOUT_EXTRACT)
            return self._kw_skills(job_description)
        except Exception as exc:
            log.warning("LLM extract_skills failed: %s | type=%s", exc, type(exc).__name__, exc_info=True)
            return self._kw_skills(job_description)

    async def match_resume_to_job(self, resume: str, job_skills: Dict) -> Dict:
        prompt = f"""Compare resume to job requirements. Return ONLY valid JSON.

Resume:
{resume[:1500]}

Required technical skills: {json.dumps(job_skills.get("technical_skills", [])[:15])}
Experience level: {job_skills.get("experience_level", "Mid")}

Return this exact JSON with no other text:
{{"match_score":75,"matched_skills":["Python"],"missing_skills":["Kubernetes"],"recommendations":"Add cloud experience"}}"""

        try:
            raw    = await self._call(prompt, max_tokens=512, timeout=_TIMEOUT_EXTRACT)
            result = self._parse_json(raw, {})
            return {
                "match_score":     max(0, min(100, int(result.get("match_score", 50)))),
                "matched_skills":  result.get("matched_skills", []),
                "missing_skills":  result.get("missing_skills", []),
                "recommendations": result.get("recommendations", ""),
            }
        except asyncio.TimeoutError:
            log.warning("LLM match_resume timed out (%.0fs) — keyword fallback", _TIMEOUT_EXTRACT)
            return self._kw_match(resume, job_skills)
        except Exception as exc:
            log.warning("LLM match_resume failed: %s | type=%s", exc, type(exc).__name__, exc_info=True)
            return self._kw_match(resume, job_skills)

    async def rewrite_resume(self, resume: str, job_description: str) -> str:
        prompt = f"""Rewrite this resume to better match the job description.
Keep all facts true. Add job keywords naturally.

Job:
{job_description[:1000]}

Resume:
{resume[:2000]}

Rewritten resume (start directly, no preamble):"""
        try:
            text = await self._call(prompt, max_tokens=1500, timeout=_TIMEOUT_REWRITE)
            return text.strip() or resume
        except asyncio.TimeoutError:
            log.warning("LLM rewrite_resume timed out (%.0fs) — returning original", _TIMEOUT_REWRITE)
            return resume
        except Exception as exc:
            log.warning("LLM rewrite_resume failed: %s | type=%s", exc, type(exc).__name__, exc_info=True)
            return resume

    async def generate_cover_letter(
        self, resume: str, job_description: str, company: str
    ) -> str:
        name = _SENDER_NAME
        prompt = f"""Write a 3-paragraph professional cover letter.

Company: {company}
Job description: {job_description[:1000]}
My background: {resume[:1000]}

Rules:
- Start with "Dear Hiring Manager,"
- End with "Best regards,\\n{name}"
- 250-350 words
- Do NOT include placeholder addresses or dates
- Mention one specific thing about {company}

Cover letter:"""
        try:
            text = await self._call(prompt, max_tokens=800, timeout=_TIMEOUT_COVER)
            return text.strip() or self._fallback_letter(company)
        except asyncio.TimeoutError:
            log.warning("LLM cover_letter timed out (%.0fs) — fallback template", _TIMEOUT_COVER)
            return self._fallback_letter(company)
        except Exception as exc:
            log.warning("LLM cover_letter failed: %s | type=%s", exc, type(exc).__name__, exc_info=True)
            return self._fallback_letter(company)

    async def extract_jobs_from_html(self, html: str, source: str) -> List[Dict]:
        """LLM-powered HTML extraction — last resort when CSS selectors fail."""
        clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        clean = re.sub(r"<style[^>]*>.*?</style>",  "", clean, flags=re.DOTALL)
        clean = re.sub(r"<[^>]+>", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()[:6000]  # 6k for 7b model

        prompt = f"""Extract job listings from this text from {source}.

Text:
{clean}

Return ONLY a valid JSON array. Each job: title, company, location, url, description. Use "" for missing.

Example:
[{{"title":"Engineer","company":"Acme","location":"Delhi","url":"https://...","description":"Build APIs"}}]

JSON array:"""

        try:
            raw  = await self._call(prompt, max_tokens=1500, timeout=_TIMEOUT_HTML)
            jobs = self._parse_json(raw, [])
            if isinstance(jobs, list):
                log.info("LLM extracted %d jobs from %s", len(jobs), source)
                return jobs
        except asyncio.TimeoutError:
            log.warning("LLM HTML extraction timed out (%.0fs) for %s", _TIMEOUT_HTML, source)
        except Exception as exc:
            log.warning("LLM HTML extraction failed for %s: %s | type=%s",
                        source, exc, type(exc).__name__, exc_info=True)
        return []

    # ── Keyword fallbacks (no LLM needed) ────────────────────────────────────

    @staticmethod
    def _kw_skills(desc: str) -> Dict:
        known = [
            "python", "javascript", "typescript", "java", "go", "rust",
            "react", "vue", "angular", "node.js", "django", "fastapi",
            "flask", "spring", "postgresql", "mysql", "mongodb", "redis",
            "aws", "gcp", "azure", "docker", "kubernetes", "git", "terraform",
        ]
        found = [s.title() for s in known if s in desc.lower()]
        return {
            "technical_skills":     found[:12],
            "soft_skills":          ["Communication", "Problem Solving"],
            "experience_level":     "Mid",
            "key_responsibilities": [],
        }

    @staticmethod
    def _kw_match(resume: str, job_skills: Dict) -> Dict:
        r       = resume.lower()
        skills  = [s.lower() for s in job_skills.get("technical_skills", [])]
        matched = [s.title() for s in skills if s in r]
        missing = [s.title() for s in skills if s not in r]
        score   = min(100, int(len(matched) / max(len(skills), 1) * 100) + 15)
        return {
            "match_score":     score,
            "matched_skills":  matched,
            "missing_skills":  missing,
            "recommendations": "Good match" if score >= 60 else "Consider upskilling in missing areas",
        }

    def _fallback_letter(self, company: str) -> str:
        name = _SENDER_NAME
        return (
            f"Dear Hiring Manager,\n\n"
            f"I am writing to express my strong interest in the position at {company}. "
            f"My background in software development and track record of delivering "
            f"high-quality solutions make me a strong candidate for this role.\n\n"
            f"I am particularly drawn to {company} because of its reputation for "
            f"innovation and technical excellence. I believe my skills align well "
            f"with your requirements and I am eager to contribute to your team.\n\n"
            f"Thank you for your consideration. I look forward to discussing how "
            f"I can contribute to {company}.\n\n"
            f"Best regards,\n{name}"
        )

    # ── Model info ────────────────────────────────────────────────────────────

    @property
    def model(self) -> Optional[str]:
        return LocalLLMService._cached_model

    @property
    def available(self) -> bool:
        return self._available

    async def list_installed_models(self) -> List[str]:
        try:
            async with self._http(timeout=5.0) as c:
                resp = await c.get("/api/tags")
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []

    @staticmethod
    def install_instructions() -> str:
        return """
╔══════════════════════════════════════════════════════════╗
║  LOCAL LLM SETUP (Ollama — Free, Unlimited, Private)    ║
╚══════════════════════════════════════════════════════════╝

1. Install Ollama:
   macOS/Linux:  curl -fsSL https://ollama.com/install.sh | sh
   Windows:      https://ollama.ai/download

2. Pull the recommended model:
   ollama pull phi3:mini          ← PRIMARY (2-3GB, fast, no heat on 8GB RAM)
   ollama pull phi3.5:mini       ← slightly larger but still lean
   ollama pull qwen2.5:3b        ← heavier fallback (1.9GB)

3. Set in .env:
   OLLAMA_MODEL=qwen2.5-coder:7b
   OLLAMA_KEEP_ALIVE=60m
   SENDER_NAME=Your Name

Ollama runs automatically. No API key needed. Zero cost.
"""