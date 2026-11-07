"""Experimental features (agents 16-26 and their services). NOT part of the Jobify product.

Nothing here is wired into orchestrator stages or ``/api/agents/*``. Some of it is reachable
through legacy ``main.py`` routes and the Telegram bot, and ``tests/test_sprint{1..6}_*.py``
covers it. Audit each module against CLAUDE.md section 1 (no fabrication, no auto-send)
before promoting it into ``src/agents`` or ``src/services``. Agent 17 (proof-of-work
"fabricator"), agent 25 (exec outreach drip) and agent 16's interviewer profiling carry the
highest risk.
"""
