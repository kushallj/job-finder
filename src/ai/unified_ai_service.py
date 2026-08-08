"""
Unified AI Service with Enhanced Cascade Fallback Chain.

Automatically selects the best available AI backend with:
1. Local LLM (Ollama) - Free, unlimited, private (PRIMARY)
2. Gemini API - Free tier with quotas (FALLBACK 1)
3. Keyword matching - Zero-dependency fallback (FALLBACK 2)

Enhanced features (Task 10.1):
  ✓ Verified fallback chain: Ollama → Gemini → Keyword matching
  ✓ Health checks for each LLM provider before use
  ✓ Automatic provider failover on errors
  ✓ Provider availability tracking and metrics
  ✓ Per-provider error counts and success rates
  ✓ Last health check timestamps

Validates: Requirements 11.2, 11.3, 11.4, 32.1
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)

# Sender name from config — falls back to "Applicant" if not set
try:
    from src.config import settings as _settings
    _SENDER_NAME: str = getattr(_settings, "sender_name", "Applicant")
except Exception:
    _SENDER_NAME = "Applicant"


class ProviderStatus(Enum):
    """Status of an LLM provider."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNAVAILABLE = "unavailable"  # Not configured or missing API key


@dataclass
class ProviderMetrics:
    """Metrics for tracking provider usage and availability."""
    name: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_count: int = 0
    last_health_check: Optional[float] = None
    last_successful_call: Optional[float] = None
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None
    consecutive_failures: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100.0
    
    @property
    def is_healthy(self) -> bool:
        """Check if provider is considered healthy."""
        return self.status == ProviderStatus.HEALTHY
    
    def record_success(self) -> None:
        """Record a successful call."""
        self.total_calls += 1
        self.successful_calls += 1
        self.last_successful_call = time.time()
        self.consecutive_failures = 0
    
    def record_failure(self, error: str, is_timeout: bool = False) -> None:
        """Record a failed call."""
        self.total_calls += 1
        self.failed_calls += 1
        self.last_error = error
        self.last_error_time = time.time()
        self.consecutive_failures += 1
        if is_timeout:
            self.timeout_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "timeout_count": self.timeout_count,
            "success_rate": round(self.success_rate, 2),
            "last_health_check": self.last_health_check,
            "last_successful_call": self.last_successful_call,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time,
            "consecutive_failures": self.consecutive_failures,
        }


@dataclass
class CascadeMetrics:
    """Aggregate metrics for the entire cascade chain."""
    providers: Dict[str, ProviderMetrics] = field(default_factory=dict)
    total_cascade_calls: int = 0
    cascade_fallback_count: int = 0
    full_cascade_failures: int = 0  # All providers failed
    
    def get_provider(self, name: str) -> ProviderMetrics:
        """Get or create metrics for a provider."""
        if name not in self.providers:
            self.providers[name] = ProviderMetrics(name=name)
        return self.providers[name]
    
    def record_fallback(self, from_provider: str, to_provider: str) -> None:
        """Record a fallback from one provider to another."""
        self.cascade_fallback_count += 1
        log.info(
            "LLM cascade fallback: %s → %s (total fallbacks: %d)",
            from_provider, to_provider, self.cascade_fallback_count
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all metrics to dictionary."""
        return {
            "total_cascade_calls": self.total_cascade_calls,
            "cascade_fallback_count": self.cascade_fallback_count,
            "full_cascade_failures": self.full_cascade_failures,
            "providers": {
                name: metrics.to_dict()
                for name, metrics in self.providers.items()
            },
        }


# Global metrics instance
_cascade_metrics = CascadeMetrics()


def get_cascade_metrics() -> CascadeMetrics:
    """Get the global cascade metrics instance."""
    return _cascade_metrics


class UnifiedAIService:
    """
    Unified AI service with enhanced cascade fallback chain.
    
    Features:
    - Cascade order: Ollama → Gemini → Keyword matching
    - Health checks for each provider
    - Automatic failover on errors
    - Provider availability tracking and metrics
    - Consecutive failure tracking for circuit breaking
    
    Validates: Requirements 11.2, 11.3, 11.4, 32.1
    """
    
    # Maximum consecutive failures before marking provider unhealthy
    MAX_CONSECUTIVE_FAILURES = 3
    # Health check interval in seconds (5 minutes)
    HEALTH_CHECK_INTERVAL = 300.0

    def __init__(self):
        self.backend = None
        self.backend_name = "unknown"
        
        # Store all available backends for cascade
        self._ollama_backend = None
        self._gemini_backend = None
        self._fallback_backend = None
        
        # Cascade order (Requirement 11.2, 11.3)
        self._cascade_order = ["ollama", "gemini", "fallback"]
        
        # Initialize all backends
        self._initialize_all_backends()
    
    def _initialize_all_backends(self):
        """Initialize all available backends for the cascade chain."""
        # Initialize Ollama (primary)
        self._init_ollama()
        
        # Initialize Gemini (fallback 1)
        self._init_gemini()
        
        # Initialize keyword fallback (always available)
        self._init_fallback()
        
        # Select the best available backend as primary
        self._select_primary_backend()


    def _init_ollama(self) -> None:
        """Initialize Ollama backend."""
        metrics = _cascade_metrics.get_provider("ollama")
        try:
            from src.ai.local_llm_service import LocalLLMService
            llm = LocalLLMService()
            
            # Try health check if not in async context
            try:
                asyncio.get_running_loop()
                # Loop is running, defer health check
                self._ollama_backend = llm
                metrics.status = ProviderStatus.UNKNOWN
                log.info("Ollama backend initialized (health check deferred)")
            except RuntimeError:
                # No loop running, can do sync health check
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                try:
                    is_healthy = loop.run_until_complete(llm.health_check())
                    metrics.last_health_check = time.time()
                    if is_healthy:
                        self._ollama_backend = llm
                        metrics.status = ProviderStatus.HEALTHY
                        model = LocalLLMService._cached_model or "unknown"
                        log.info("✅ Ollama backend ready: %s", model)
                        print(f"✅ Using Local LLM (Ollama: {model}) — Free, Unlimited & Private!")
                    else:
                        metrics.status = ProviderStatus.UNHEALTHY
                        log.info("Ollama not responding")
                except Exception as exc:
                    metrics.status = ProviderStatus.UNHEALTHY
                    metrics.last_error = str(exc)
                    log.debug("Ollama health check failed: %s", exc)
                    
        except ImportError:
            metrics.status = ProviderStatus.UNAVAILABLE
            log.debug("Ollama service not available (import failed)")
        except Exception as exc:
            metrics.status = ProviderStatus.UNHEALTHY
            metrics.last_error = str(exc)
            log.debug("Could not initialize Ollama: %s", exc)


    def _init_gemini(self) -> None:
        """Initialize Gemini backend."""
        metrics = _cascade_metrics.get_provider("gemini")
        try:
            from src.config import settings
            api_key = getattr(settings, "gemini_api_key", None) or getattr(settings, "google_api_key", None)
            if not api_key:
                metrics.status = ProviderStatus.UNAVAILABLE
                log.debug("Gemini API key not configured")
                return
            
            from src.ai.gemini_service import GeminiService as RealGeminiService
            self._gemini_backend = RealGeminiService()
            metrics.status = ProviderStatus.HEALTHY  # Assume healthy if API key exists
            metrics.last_health_check = time.time()
            log.info("✅ Gemini backend initialized")
            
        except ImportError:
            metrics.status = ProviderStatus.UNAVAILABLE
            log.debug("Gemini service not available (import failed)")
        except ValueError as exc:
            # API key validation failed
            metrics.status = ProviderStatus.UNAVAILABLE
            metrics.last_error = str(exc)
            log.debug("Gemini API key invalid: %s", exc)
        except Exception as exc:
            metrics.status = ProviderStatus.UNHEALTHY
            metrics.last_error = str(exc)
            log.debug("Could not initialize Gemini: %s", exc)

    def _init_fallback(self) -> None:
        """Initialize keyword fallback backend (always available)."""
        metrics = _cascade_metrics.get_provider("fallback")
        try:
            from src.ai.fallback_service import FallbackAIService
            self._fallback_backend = FallbackAIService()
            metrics.status = ProviderStatus.HEALTHY
            metrics.last_health_check = time.time()
            log.info("✅ Keyword fallback backend ready")
        except Exception as exc:
            metrics.status = ProviderStatus.UNHEALTHY
            metrics.last_error = str(exc)
            log.error("Failed to initialize fallback service: %s", exc)


    def _select_primary_backend(self) -> None:
        """Select the best available backend as primary."""
        for provider_name in self._cascade_order:
            backend = self._get_backend_by_name(provider_name)
            metrics = _cascade_metrics.get_provider(provider_name)
            if backend is not None and metrics.status in (ProviderStatus.HEALTHY, ProviderStatus.UNKNOWN):
                self.backend = backend
                self.backend_name = provider_name
                log.info("Primary backend selected: %s", provider_name)
                return
        
        # If nothing else available, use fallback
        if self._fallback_backend:
            self.backend = self._fallback_backend
            self.backend_name = "fallback"
            print("⚠️  Using Fallback AI (keyword-based matching)")
            print("   For better results: ollama pull qwen2.5-coder:7b")
        else:
            log.error("No AI backends available!")
            self.backend = None
            self.backend_name = "none"

    def _get_backend_by_name(self, name: str) -> Optional[Any]:
        """Get backend instance by name."""
        backends = {
            "ollama": self._ollama_backend,
            "gemini": self._gemini_backend,
            "fallback": self._fallback_backend,
        }
        return backends.get(name)

    def _get_next_provider(self, current: str) -> Optional[str]:
        """Get the next provider in the cascade chain."""
        try:
            idx = self._cascade_order.index(current)
            if idx + 1 < len(self._cascade_order):
                return self._cascade_order[idx + 1]
        except ValueError:
            pass
        return None


    # ── Health Check Methods ──────────────────────────────────────────────────

    async def health_check_provider(self, provider_name: str) -> bool:
        """
        Perform a health check on a specific provider.
        
        Returns True if provider is healthy, False otherwise.
        Updates provider metrics with result.
        """
        metrics = _cascade_metrics.get_provider(provider_name)
        backend = self._get_backend_by_name(provider_name)
        
        if backend is None:
            metrics.status = ProviderStatus.UNAVAILABLE
            return False
        
        try:
            if provider_name == "ollama":
                is_healthy = await backend.health_check()
                metrics.last_health_check = time.time()
                metrics.status = ProviderStatus.HEALTHY if is_healthy else ProviderStatus.UNHEALTHY
                return is_healthy
            
            elif provider_name == "gemini":
                # For Gemini, try a simple test call
                await backend._ensure_initialized()
                metrics.last_health_check = time.time()
                metrics.status = ProviderStatus.HEALTHY
                return True
            
            elif provider_name == "fallback":
                # Fallback is always healthy if initialized
                metrics.last_health_check = time.time()
                metrics.status = ProviderStatus.HEALTHY
                return True
                
        except Exception as exc:
            metrics.status = ProviderStatus.UNHEALTHY
            metrics.last_error = str(exc)
            metrics.last_error_time = time.time()
            log.warning("Health check failed for %s: %s", provider_name, exc)
            return False
        
        return False


    async def health_check_all(self) -> Dict[str, bool]:
        """
        Perform health checks on all providers.
        
        Returns dict mapping provider name to health status.
        """
        results = {}
        for provider_name in self._cascade_order:
            results[provider_name] = await self.health_check_provider(provider_name)
        return results

    async def _should_health_check(self, provider_name: str) -> bool:
        """Check if a provider needs a health check based on interval."""
        metrics = _cascade_metrics.get_provider(provider_name)
        if metrics.last_health_check is None:
            return True
        elapsed = time.time() - metrics.last_health_check
        return elapsed >= self.HEALTH_CHECK_INTERVAL

    async def _ensure_provider_healthy(self, provider_name: str) -> bool:
        """
        Ensure a provider is healthy before use.
        
        Performs health check if:
        - Status is UNKNOWN (never checked)
        - Last health check was more than HEALTH_CHECK_INTERVAL ago
        - Provider has consecutive failures >= MAX_CONSECUTIVE_FAILURES
        """
        metrics = _cascade_metrics.get_provider(provider_name)
        
        # Skip check if recently verified healthy
        if metrics.status == ProviderStatus.HEALTHY:
            if metrics.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                log.info("Provider %s has %d consecutive failures, re-checking health",
                        provider_name, metrics.consecutive_failures)
            elif not await self._should_health_check(provider_name):
                return True
        
        # Provider is unknown or unhealthy or needs re-check
        return await self.health_check_provider(provider_name)


    # ── Cascade Execution ─────────────────────────────────────────────────────

    async def _execute_with_cascade(
        self,
        method_name: str,
        method_args: tuple,
        method_kwargs: dict,
        fallback_result: Any,
    ) -> Any:
        """
        Execute a method with automatic cascade fallback.
        
        Tries providers in cascade order: Ollama → Gemini → Fallback
        
        Validates: Requirements 11.2, 11.3, 11.4
        """
        _cascade_metrics.total_cascade_calls += 1
        
        for provider_name in self._cascade_order:
            backend = self._get_backend_by_name(provider_name)
            metrics = _cascade_metrics.get_provider(provider_name)
            
            if backend is None:
                continue
            
            # Check if provider is healthy
            if not await self._ensure_provider_healthy(provider_name):
                log.debug("Provider %s not healthy, trying next", provider_name)
                next_provider = self._get_next_provider(provider_name)
                if next_provider:
                    _cascade_metrics.record_fallback(provider_name, next_provider)
                continue
            
            try:
                # Get the method from backend
                method = getattr(backend, method_name, None)
                if method is None:
                    log.debug("Provider %s doesn't have method %s", provider_name, method_name)
                    continue
                
                # Execute the method
                result = await method(*method_args, **method_kwargs)
                
                # Record success
                metrics.record_success()
                log.debug("Method %s succeeded on %s", method_name, provider_name)
                return result
                
            except asyncio.TimeoutError as exc:
                metrics.record_failure(str(exc), is_timeout=True)
                log.warning("%s timed out on %s", method_name, provider_name)
                
            except Exception as exc:
                metrics.record_failure(str(exc))
                log.warning("%s failed on %s: %s", method_name, provider_name, exc)
            
            # Try next provider in cascade
            next_provider = self._get_next_provider(provider_name)
            if next_provider:
                _cascade_metrics.record_fallback(provider_name, next_provider)
        
        # All providers failed
        _cascade_metrics.full_cascade_failures += 1
        log.error("All providers failed for %s, using fallback result", method_name)
        return fallback_result


    # ── Public Interface ──────────────────────────────────────────────────────

    async def extract_skills(self, job_description: str) -> Dict:
        """
        Extract skills from job description using cascade chain.
        
        Validates: Requirements 11.2, 11.3, 11.4, 11.6
        """
        fallback_result = {
            "technical_skills": [],
            "soft_skills": [],
            "experience_level": "Mid",
            "key_responsibilities": [],
        }
        return await self._execute_with_cascade(
            "extract_skills",
            (job_description,),
            {},
            fallback_result,
        )

    async def match_resume_to_job(self, resume: str, job_skills: Dict) -> Dict:
        """
        Match resume to job skills using cascade chain.
        
        Validates: Requirements 11.2, 11.3, 11.4, 11.7
        """
        fallback_result = {
            "match_score": 50,
            "matched_skills": [],
            "missing_skills": job_skills.get("technical_skills", []),
            "recommendations": "Could not analyze resume.",
        }
        return await self._execute_with_cascade(
            "match_resume_to_job",
            (resume, job_skills),
            {},
            fallback_result,
        )

    async def rewrite_resume(self, original_resume: str, job_description: str) -> str:
        """
        Rewrite resume tailored to job description using cascade chain.
        """
        # Fallback: return original resume
        return await self._execute_with_cascade(
            "rewrite_resume",
            (original_resume, job_description),
            {},
            original_resume,
        )


    async def generate_cover_letter(
        self, resume: str, job_description: str, company: str
    ) -> str:
        """
        Generate cover letter using cascade chain.
        """
        fallback_letter = self._fallback_letter(company)
        return await self._execute_with_cascade(
            "generate_cover_letter",
            (resume, job_description, company),
            {},
            fallback_letter,
        )

    async def generate_text(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Generic text generation using cascade chain.
        
        Tries providers that support _call method.
        """
        for provider_name in self._cascade_order:
            backend = self._get_backend_by_name(provider_name)
            if backend is None:
                continue
            
            # Only try backends with _call method (Ollama)
            if not hasattr(backend, "_call"):
                continue
            
            metrics = _cascade_metrics.get_provider(provider_name)
            
            if not await self._ensure_provider_healthy(provider_name):
                continue
            
            try:
                result = await backend._call(prompt, max_tokens=max_tokens)
                metrics.record_success()
                return result
            except asyncio.TimeoutError as exc:
                metrics.record_failure(str(exc), is_timeout=True)
                log.warning("generate_text timed out on %s", provider_name)
            except Exception as exc:
                metrics.record_failure(str(exc))
                log.warning("generate_text failed on %s: %s", provider_name, exc)
        
        return ""


    # ── Metrics and Status ────────────────────────────────────────────────────

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics for all providers.
        
        Returns:
            Dict with provider metrics, cascade stats, and current status
        """
        return {
            "current_primary": self.backend_name,
            "cascade_order": self._cascade_order,
            **_cascade_metrics.to_dict(),
        }

    def get_provider_status(self, provider_name: str) -> Dict[str, Any]:
        """Get status and metrics for a specific provider."""
        metrics = _cascade_metrics.get_provider(provider_name)
        backend = self._get_backend_by_name(provider_name)
        
        return {
            "name": provider_name,
            "available": backend is not None,
            "status": metrics.status.value,
            "metrics": metrics.to_dict(),
        }

    def get_all_provider_statuses(self) -> List[Dict[str, Any]]:
        """Get status for all providers in cascade order."""
        return [
            self.get_provider_status(name)
            for name in self._cascade_order
        ]

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _fallback_letter(self, company: str) -> str:
        """Generate a basic cover letter template."""
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
ClaudeService = UnifiedAIService
GeminiService = UnifiedAIService
