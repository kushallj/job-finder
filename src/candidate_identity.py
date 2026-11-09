"""The candidate's own contact identity for ATS integrations (Workday, NextRaise, Tsenta).

Read from the environment only. There is deliberately no fallback: these integrations
submit applications to employers, and a hardcoded or placeholder email/phone would be
sent as if it were the candidate's (CLAUDE.md section 1: never hardcode candidate data).
"""

from __future__ import annotations

import os


def candidate_account_email() -> str:
    email = (os.getenv("NEXTRAISE_EMAIL") or os.getenv("GMAIL_ADDRESS") or "").strip()
    if not email:
        raise ValueError("Set NEXTRAISE_EMAIL (or GMAIL_ADDRESS) to the candidate's email for ATS accounts")
    return email
