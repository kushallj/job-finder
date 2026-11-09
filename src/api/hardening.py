"""HTTP hardening middleware: security headers, request body cap, safe trace ids.

Pure ASGI (no BaseHTTPMiddleware) so streaming responses (chat SSE) are untouched.
"""

from __future__ import annotations

import re
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Client-supplied trace ids end up in logs and response headers. Accept only a short,
# boring token; anything else (newlines, quotes, 10 KB strings) gets a fresh UUID.
_TRACE_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def safe_trace_id(candidate: str | None) -> str:
    return candidate if candidate and _TRACE_ID.match(candidate) else str(uuid.uuid4())


# The API serves JSON only; docs pages (when enabled) need the Swagger CDN.
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
_DOCS_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
             "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
             "frame-ancestors 'none'")


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        csp = _DOCS_CSP if path in ("/docs", "/redoc") else _API_CSP

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {k.lower() for k, _ in headers}
                extra = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"no-referrer",
                    b"permissions-policy": b"camera=(), microphone=(), geolocation=(), payment=()",
                    b"cross-origin-opener-policy": b"same-origin",
                    b"content-security-policy": csp.encode(),
                }
                if self.hsts:
                    extra[b"strict-transport-security"] = b"max-age=31536000; includeSubDomains"
                headers += [(k, v) for k, v in extra.items() if k not in present]
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodySizeLimitMiddleware:
    """Reject bodies over `max_bytes` (413) before the app reads them.

    Checks Content-Length up front and counts streamed chunks, so chunked uploads
    without a length are capped too. Some paths (inbound email with attachments)
    get a larger allowance.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int, overrides: dict[str, int] | None = None) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.overrides = overrides or {}

    def _limit(self, path: str) -> int:
        return next((n for prefix, n in self.overrides.items() if path.startswith(prefix)), self.max_bytes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return
        limit = self._limit(scope.get("path", ""))
        declared = dict(scope.get("headers", [])).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await _reject(send, limit)
            return

        received = 0
        rejected = False

        async def counting_receive() -> Message:
            # Over the cap mid-stream: answer 413 ourselves, then tell the app the client
            # left. (Raising here would be swallowed by FastAPI's body parser as a 400.)
            nonlocal received, rejected
            if rejected:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    rejected = True
                    await _reject(send, limit)
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            if not rejected:  # the 413 already went out; drop whatever the app sends after
                await send(message)

        await self.app(scope, counting_receive, guarded_send)


async def _reject(send: Send, limit: int) -> None:
    body = (b'{"error":{"code":"PAYLOAD_TOO_LARGE","message":"Request body exceeds %d bytes"},'
            b'"detail":"Request body too large"}' % limit)
    await send({"type": "http.response.start", "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})
