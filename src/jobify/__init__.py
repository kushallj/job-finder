"""Jobify product API: the backend for the ``jobify/`` React frontend (CLAUDE.md sections 6-9).

- ``routers/``: FastAPI routers mounted under ``/api`` in ``main.py``. Thin: auth, request
  parsing, response shape (``src.api.contract``). One module per Jobify screen.
- ``services/``: business logic. Every per-user query goes through ``scoped()``.

Shared infrastructure stays outside this package: ``src.models``, ``src.auth``,
``src.api.contract``, ``src.services.credit_service``, ``src.services.inbound_email_classifier``.
"""
