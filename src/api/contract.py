"""
contract.py — Response shapes the Jobify frontend expects (jobify/docs/INTEGRATION.md).

  Lists:  {"items": [...], "total": n, "page": p, "pageSize": s}
  Errors: {"error": {"code": "...", "message": "..."}, "detail": <legacy>}

The frontend is the spec: new routes return `paginate(...)` for lists and raise
HTTPException (or APIError) for errors; the handlers below shape the body. `detail`
is kept alongside `error` so existing FastAPI-style clients keep working.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Default machine-readable code per HTTP status. 402 is always CREDITS_REQUIRED:
# the frontend maps that code to its "Choose a plan" prompt.
STATUS_CODES: Dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    402: "CREDITS_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "BAD_GATEWAY",
    503: "UNAVAILABLE",
    504: "TIMEOUT",
}

MAX_PAGE_SIZE = 100


def error_payload(status_code: int, message: str, code: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    if status_code == 402:
        code = "CREDITS_REQUIRED"
    error: Dict[str, Any] = {"code": code or STATUS_CODES.get(status_code, "ERROR"), "message": message}
    error.update({k: v for k, v in extra.items() if v is not None})
    return {"error": error, "detail": message}


def error_response(
    status_code: int,
    message: str,
    code: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    **extra: Any,
) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_payload(status_code, message, code, **extra), headers=headers)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    code = None
    extra: Dict[str, Any] = {}
    if isinstance(detail, dict):
        # e.g. credit_service: {"error": "INSUFFICIENT_CREDITS", "message": ..., "balance": ...}
        message = str(detail.get("message") or detail.get("detail") or detail.get("error") or "Request failed")
        code = detail.get("code") or (detail.get("error") if isinstance(detail.get("error"), str) else None)
        extra = {k: v for k, v in detail.items() if k not in ("message", "detail", "error", "code")}
    else:
        message = str(detail) if detail else "Request failed"
    body = error_payload(exc.status_code, message, code, trace_id=getattr(request.state, "trace_id", None), **extra)
    body["detail"] = detail if detail is not None else message
    return JSONResponse(status_code=exc.status_code, content=body, headers=getattr(exc, "headers", None))


def paginate(
    query,
    page: int = 1,
    page_size: int = 20,
    mapper: Callable[[Any], Any] = lambda row: row,
) -> Dict[str, Any]:
    """Apply offset/limit to a SQLAlchemy query and return the frontend list shape.

    Apply filters and ordering to `query` before calling. Page is 1-based;
    page_size is clamped to [1, MAX_PAGE_SIZE].
    """
    page = max(1, int(page or 1))
    page_size = min(MAX_PAGE_SIZE, max(1, int(page_size or 20)))
    total = query.order_by(None).count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [mapper(r) for r in rows], "total": total, "page": page, "pageSize": page_size}


def scoped(query, model, user):
    """Restrict `query` to rows owned by `user`. Use on every per-user read/update/delete.

    Raises TypeError when the model has no user_id column, so a table that still
    needs tenant isolation fails loudly instead of leaking every user's rows.
    """
    if not hasattr(model, "user_id"):
        raise TypeError(f"{model.__name__} has no user_id column; add one before exposing it per-user")
    if user is None or getattr(user, "id", None) is None:
        raise TypeError("scoped() requires an authenticated user")
    return query.filter(model.user_id == user.id)
