"""
Core Application & Domain Exceptions
Hierarchy of clean, typed domain exceptions for error isolation.
"""
from typing import Any


class AppBaseException(Exception):
    """Base class for all internal application exceptions."""

    def __init__(self, message: str = "", code: str = "INTERNAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class EntityNotFoundException(AppBaseException):
    """Raised when requested entity is missing in repository."""

    def __init__(self, entity_name: str, entity_id: Any = None):
        super().__init__(
            f"{entity_name} with id '{entity_id}' not found.",
            code="ENTITY_NOT_FOUND",
        )


class ValidationException(AppBaseException):
    """Raised when invariant or business rule fails."""

    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_FAILED")


class ScraperFailureException(AppBaseException):
    """Raised when external ATS or scraper fails."""

    def __init__(self, source: str, detail: str):
        super().__init__(f"Scraper '{source}' failed: {detail}", code="SCRAPER_ERROR")


class RateLimitExceededException(AppBaseException):
    """Raised when API rate limits are encountered."""

    def __init__(self, service_name: str, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded for {service_name}. Retry after {retry_after}s.",
            code="RATE_LIMIT_EXCEEDED",
        )
        self.retry_after = retry_after
