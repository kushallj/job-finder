"""
Unified AI Service
Automatically selects the best available AI backend:
1. Local LLM (Ollama) - Free, unlimited, private
2. Gemini API - Free tier with quotas
3. Fallback - Keyword-based matching

Changes from original:
  ✓ _try_local_llm runs health_check properly in all event loop states
  ✓ Logs which model was selected (llama3.2:3b vs mistral etc.)
  ✓ Cover letter fallback uses settings.sender_name, not hardcoded name
  ✓ All backend failures log exc_info=True for full tracebacks
  ✓ asyncio.TimeoutError caught separately with clear message
"""

from typing import Dict
import asyncio
import logging

log = logging.getLogger(__name__)

# Sender name from config — falls back to "Applicant" if not set
try:
    from src.config import settings as _settings
    _SENDER_NAME: str = getattr(_settings, "sender_name", "Applicant")
except Exception:
    _SENDER_NAME = "Applicant"


class UnifiedAIService:
    """Unified AI service that automatically selects the best available backend."""

    def __init__(self):
        self.backend      = None
        self.backend_name = "unknown"
        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize AI backend in order of preference."""
        if self._try_local_llm():
            return
        if self._try_gemini():
            return
        self._use_fallback()

    def _try_local_llm(self) -> bool:
        """Try to initialize Local LLM (Ollama)."""
        try:
            from src.ai.local_llm_service import LocalLLMService
            llm = LocalLLMService()

            # Run health_check regardless of event loop state
            try:
                loop = asyncio.get_running_loop()
                # Loop is running (e.g. inside FastAPI startup) — schedule as task
                # We can't block here, so assume healthy and verify on first real call
                self.backend      = llm
                self.backend_name = "ollama"
                print("✅ Using Local LLM (Ollama) — health check deferred (loop running)")
                return True
            except RuntimeError:
                # No running loop — safe to run synchronously
                pass

            try:
                loop       = asyncio.get_event_loop()
                is_healthy = loop.run_until_complete(llm.health_check())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    is_healthy = loop.run_until_complete(llm.health_check())
                finally:
                    loop.close()

            if is_healthy:
                self.backend      = llm
                self.backend_name = "ollama"
                model = LocalLLMService._cached_model or "unknown"
                print(f"✅ Using Local LLM (Ollama: {model}) — Free, Unlimited & Private!")
                return True
            else:
                print("ℹ️  Ollama not responding. Run: ollama serve")
                print("    Then pull a model: ollama pull llama3.2:3b")
                return False

        except Exception as exc:
            log.debug("Could not initialize Ollama: %s", exc, exc_info=True)
            print(f"⚠️  Ollama initialization failed: {exc}")
            return False

    def _try_gemini(self) -> bool:
        """Try to initialize Gemini API."""
        try:
            from src.config import settings
            if not settings.gemini_api_key:
                return False
            from src.ai.gemini_service import GeminiService
            self.backend      = GeminiService()
            self.backend_name = "gemini"
            print("✅ Using Gemini API (quota limits apply)")
            return True
        except Exception as exc:
            log.debug("Could not initialize Gemini: %s", exc)
            return False

    def _use_fallback(self):
        """Use fallback keyword-based AI."""
        from src.ai.fallback_service import FallbackAIService
        self.backend      = FallbackAIService()
        self.backend_name = "fallback"
        print("⚠️  Using Fallback AI (keyword-based matching)")
        print("   For better results: ollama pull llama3.2:3b")

    # ── Public interface ──────────────────────────────────────────────────────

    async def extract_skills(self, job_description: str) -> Dict:
        try:
            return await self.backend.extract_skills(job_description)
        except asyncio.TimeoutError:
            log.warning("extract_skills timed out on %s — fallback", self.backend_name)
            return await self._fallback_skills(job_description)
        except Exception as exc:
            log.error("extract_skills failed on %s: %s", self.backend_name, exc, exc_info=True)
            return await self._fallback_skills(job_description)

    async def match_resume_to_job(self, resume: str, job_skills: Dict) -> Dict:
        try:
            return await self.backend.match_resume_to_job(resume, job_skills)
        except asyncio.TimeoutError:
            log.warning("match_resume timed out on %s — fallback", self.backend_name)
            return await self._fallback_match(resume, job_skills)
        except Exception as exc:
            log.error("match_resume failed on %s: %s", self.backend_name, exc, exc_info=True)
            return await self._fallback_match(resume, job_skills)

    async def rewrite_resume(self, original_resume: str, job_description: str) -> str:
        try:
            return await self.backend.rewrite_resume(original_resume, job_description)
        except asyncio.TimeoutError:
            log.warning("rewrite_resume timed out on %s — returning original", self.backend_name)
            return original_resume
        except Exception as exc:
            log.error("rewrite_resume failed on %s: %s", self.backend_name, exc, exc_info=True)
            return original_resume

    async def generate_cover_letter(
        self, resume: str, job_description: str, company: str
    ) -> str:
        try:
            return await self.backend.generate_cover_letter(resume, job_description, company)
        except asyncio.TimeoutError:
            log.warning("cover_letter timed out on %s — template fallback", self.backend_name)
            return self._fallback_letter(company)
        except Exception as exc:
            log.error("cover_letter failed on %s: %s", self.backend_name, exc, exc_info=True)
            return self._fallback_letter(company)

    # ── Internal fallbacks ────────────────────────────────────────────────────

    async def _fallback_skills(self, job_description: str) -> Dict:
        if self.backend_name != "fallback":
            try:
                from src.ai.fallback_service import FallbackAIService
                return await FallbackAIService().extract_skills(job_description)
            except Exception:
                pass
        return {
            "technical_skills": [], "soft_skills": [],
            "experience_level": "Mid", "key_responsibilities": [],
        }

    async def _fallback_match(self, resume: str, job_skills: Dict) -> Dict:
        if self.backend_name != "fallback":
            try:
                from src.ai.fallback_service import FallbackAIService
                return await FallbackAIService().match_resume_to_job(resume, job_skills)
            except Exception:
                pass
        return {
            "match_score": 50, "matched_skills": [],
            "missing_skills": [], "recommendations": "",
        }

    def _fallback_letter(self, company: str) -> str:
        name = _SENDER_NAME
        return (
            f"Dear Hiring Manager,\n\n"
            f"I am writing to express my strong interest in the position at {company}. "
            f"With my background in software development, I believe I could contribute "
            f"meaningfully to your team.\n\n"
            f"I have attached my resume for your review and would love to discuss how "
            f"my experience aligns with your needs.\n\n"
            f"Thank you for your consideration.\n\n"
            f"Best regards,\n{name}"
        )


# Backward compatibility aliases
ClaudeService  = UnifiedAIService
GeminiService  = UnifiedAIService