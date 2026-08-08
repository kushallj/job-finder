"""
FastAPI error handlers for comprehensive error responses.

This module provides custom exception handlers with proper HTTP status codes,
structured error responses, and request tracing support.

Requirements: 23.2 (Comprehensive error responses), 23.4 (Request timeout handling)
"""

import asyncio
import logging
from typing import Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api_models import (
    ErrorResponse,
    ErrorDetail,
    TimeoutErrorResponse,
    RateLimitErrorResponse,
)

log = logging.getLogger("api_error_handlers")


# ═══════════════════════════════════════════════════════════════════════════
# Custom Exceptions
# ═══════════════════════════════════════════════════════════════════════════

class APIError(Exception):
    """Base exception for API errors"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type: str = "APIError",
        details: list = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.details = details or []
        super().__init__(self.message)


class ValidationError(APIError):
    """Request validation error"""
    
    def __init__(self, message: str, details: list = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_type="ValidationError",
            details=details,
        )


class ResourceNotFoundError(APIError):
    """Resource not found error"""
    
    def __init__(self, resource_type: str, resource_id: Union[int, str]):
        super().__init__(
            message=f"{resource_type} with ID {resource_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_type="ResourceNotFoundError",
        )


class ServiceUnavailableError(APIError):
    """Service unavailable error"""
    
    def __init__(self, service_name: str, reason: str = None):
        message = f"Service '{service_name}' is currently unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type="ServiceUnavailableError",
        )


class TimeoutError(APIError):
    """Request timeout error"""
    
    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            message=f"Operation '{operation}' timed out after {timeout_seconds} seconds",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_type="TimeoutError",
        )
        self.timeout_seconds = timeout_seconds


class RateLimitError(APIError):
    """Rate limit exceeded error"""
    
    def __init__(self, message: str, retry_after_seconds: int = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_type="RateLimitError",
        )
        self.retry_after_seconds = retry_after_seconds


class DatabaseError(APIError):
    """Database operation error"""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Database error: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="DatabaseError",
        )


class ExternalAPIError(APIError):
    """External API call error"""
    
    def __init__(self, api_name: str, message: str):
        super().__init__(
            message=f"External API '{api_name}' error: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_type="ExternalAPIError",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Error Response Builders
# ═══════════════════════════════════════════════════════════════════════════

def build_error_response(
    error_type: str,
    message: str,
    status_code: int,
    trace_id: str = None,
    details: list = None,
) -> JSONResponse:
    """
    Build a standardized error response.
    
    Requirements: 23.2 (Comprehensive error responses with proper HTTP status codes)
    """
    error_response = ErrorResponse(
        error=error_type,
        message=message,
        trace_id=trace_id,
        details=details,
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(mode="json", exclude_none=True),
    )


def build_validation_error_response(
    errors: list,
    trace_id: str = None,
) -> JSONResponse:
    """
    Build a validation error response from Pydantic validation errors.
    
    Requirements: 23.2 (Comprehensive error responses)
    """
    details = []
    for error in errors:
        # Extract field path
        field_path = " -> ".join(str(loc) for loc in error.get("loc", []))
        
        details.append(
            ErrorDetail(
                field=field_path,
                message=error.get("msg", "Validation error"),
                type=error.get("type", "value_error"),
            )
        )
    
    error_response = ErrorResponse(
        error="ValidationError",
        message="Request validation failed. Please check the request parameters.",
        trace_id=trace_id,
        details=details,
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json", exclude_none=True),
    )


def build_timeout_error_response(
    message: str,
    timeout_seconds: int,
    trace_id: str = None,
) -> JSONResponse:
    """
    Build a timeout error response.
    
    Requirements: 23.4 (Implement request timeout handling)
    """
    timeout_response = TimeoutErrorResponse(
        message=message,
        timeout_seconds=timeout_seconds,
        trace_id=trace_id,
    )
    
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content=timeout_response.model_dump(mode="json", exclude_none=True),
    )


def build_rate_limit_error_response(
    message: str,
    retry_after_seconds: int = None,
    trace_id: str = None,
) -> JSONResponse:
    """
    Build a rate limit error response.
    
    Requirements: 23.2 (Comprehensive error responses)
    """
    rate_limit_response = RateLimitErrorResponse(
        message=message,
        retry_after_seconds=retry_after_seconds,
        trace_id=trace_id,
    )
    
    headers = {}
    if retry_after_seconds:
        headers["Retry-After"] = str(retry_after_seconds)
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=rate_limit_response.model_dump(mode="json", exclude_none=True),
        headers=headers,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Exception Handlers
# ═══════════════════════════════════════════════════════════════════════════

async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Handler for custom APIError exceptions.
    
    Requirements: 23.2 (Comprehensive error responses), 23.5 (Request tracing)
    """
    trace_id = getattr(request.state, "trace_id", None)
    
    log.warning(
        "[%s] API Error: %s - %s",
        trace_id or "no-trace",
        exc.error_type,
        exc.message,
    )
    
    # Special handling for timeout errors
    if isinstance(exc, TimeoutError):
        return build_timeout_error_response(
            message=exc.message,
            timeout_seconds=exc.timeout_seconds,
            trace_id=trace_id,
        )
    
    # Special handling for rate limit errors
    if isinstance(exc, RateLimitError):
        return build_rate_limit_error_response(
            message=exc.message,
            retry_after_seconds=getattr(exc, "retry_after_seconds", None),
            trace_id=trace_id,
        )
    
    # General API error response
    return build_error_response(
        error_type=exc.error_type,
        message=exc.message,
        status_code=exc.status_code,
        trace_id=trace_id,
        details=exc.details,
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handler for Pydantic validation errors.
    
    Requirements: 23.2 (Validate request parameters, comprehensive error responses)
    """
    trace_id = getattr(request.state, "trace_id", None)
    
    log.warning(
        "[%s] Validation Error: %s",
        trace_id or "no-trace",
        exc.errors(),
    )
    
    return build_validation_error_response(
        errors=exc.errors(),
        trace_id=trace_id,
    )


async def pydantic_validation_error_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    """
    Handler for Pydantic ValidationError (from response models).
    
    Requirements: 23.2 (Comprehensive error responses)
    """
    trace_id = getattr(request.state, "trace_id", None)
    
    log.warning(
        "[%s] Pydantic Validation Error: %s",
        trace_id or "no-trace",
        exc.errors(),
    )
    
    return build_validation_error_response(
        errors=exc.errors(),
        trace_id=trace_id,
    )


async def asyncio_timeout_error_handler(
    request: Request,
    exc: asyncio.TimeoutError,
) -> JSONResponse:
    """
    Handler for asyncio.TimeoutError exceptions.
    
    Requirements: 23.4 (Implement request timeout handling)
    """
    trace_id = getattr(request.state, "trace_id", None)
    
    log.error(
        "[%s] Asyncio Timeout Error on %s %s",
        trace_id or "no-trace",
        request.method,
        request.url.path,
    )
    
    return build_timeout_error_response(
        message="Request timed out while processing",
        timeout_seconds=300,  # Default timeout
        trace_id=trace_id,
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handler for uncaught exceptions.
    
    Requirements: 23.2 (Comprehensive error responses), 23.5 (Request tracing)
    """
    trace_id = getattr(request.state, "trace_id", None)
    
    log.error(
        "[%s] Unhandled Exception: %s %s - %s",
        trace_id or "no-trace",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True,
    )
    
    return build_error_response(
        error_type="InternalServerError",
        message="An internal server error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        trace_id=trace_id,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Handler Registration
# ═══════════════════════════════════════════════════════════════════════════

def register_error_handlers(app):
    """
    Register all error handlers with the FastAPI application.
    
    Call this during application startup to enable comprehensive error handling.
    
    Requirements: 23.2 (Comprehensive error responses with proper HTTP status codes)
    """
    # Custom API errors
    app.add_exception_handler(APIError, api_error_handler)
    
    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_error_handler)
    
    # Timeout errors
    app.add_exception_handler(asyncio.TimeoutError, asyncio_timeout_error_handler)
    
    # Generic exception handler (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    log.info("Registered comprehensive error handlers")
