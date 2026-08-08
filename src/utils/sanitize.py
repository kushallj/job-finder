"""
src/utils/sanitize.py — Input validation and sanitization for external data.

All data from external sources (scraped pages, API responses, user input)
should pass through these functions before being stored or used in emails.
"""

import re
import html
from typing import Optional


# Max lengths for each field type
MAX_TITLE_LENGTH = 500
MAX_COMPANY_LENGTH = 300
MAX_DESCRIPTION_LENGTH = 50_000
MAX_NAME_LENGTH = 200
MAX_EMAIL_LENGTH = 320
MAX_URL_LENGTH = 2048

# Regex for basic email validation
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

# Characters that could enable email header injection
_HEADER_INJECTION_RE = re.compile(r"[\r\n]")

# Basic HTML tag stripping
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_text(text: Optional[str], max_length: int = 10_000) -> str:
    """Strip HTML tags, normalize whitespace, truncate to max length."""
    if not text:
        return ""
    # Remove HTML tags
    clean = _HTML_TAG_RE.sub(" ", text)
    # Decode HTML entities
    clean = html.unescape(clean)
    # Normalize whitespace (collapse multiple spaces/newlines)
    clean = re.sub(r"\s+", " ", clean).strip()
    # Truncate
    if len(clean) > max_length:
        clean = clean[:max_length] + "…"
    return clean


def sanitize_job_title(title: Optional[str]) -> str:
    """Sanitize a job title from external source."""
    return sanitize_text(title, MAX_TITLE_LENGTH)


def sanitize_company_name(company: Optional[str]) -> str:
    """Sanitize a company name from external source."""
    return sanitize_text(company, MAX_COMPANY_LENGTH)


def sanitize_description(description: Optional[str]) -> str:
    """Sanitize a job description — allows longer text but strips HTML."""
    return sanitize_text(description, MAX_DESCRIPTION_LENGTH)


def sanitize_name(name: Optional[str]) -> str:
    """Sanitize a person's name — prevent header injection."""
    if not name:
        return ""
    clean = _HEADER_INJECTION_RE.sub(" ", name)
    clean = _HTML_TAG_RE.sub("", clean)
    clean = html.unescape(clean).strip()
    if len(clean) > MAX_NAME_LENGTH:
        clean = clean[:MAX_NAME_LENGTH]
    return clean


def validate_email(email: Optional[str]) -> Optional[str]:
    """
    Validate and normalize an email address.
    Returns the cleaned email or None if invalid.
    """
    if not email:
        return None
    email = email.strip().lower()
    # Prevent header injection
    if _HEADER_INJECTION_RE.search(email):
        return None
    # Length check
    if len(email) > MAX_EMAIL_LENGTH:
        return None
    # Format check
    if not _EMAIL_RE.match(email):
        return None
    return email


def sanitize_url(url: Optional[str]) -> str:
    """Sanitize a URL — validate scheme and length."""
    if not url:
        return ""
    url = url.strip()
    # Only allow http/https schemes
    if not url.startswith(("http://", "https://")):
        if url.startswith("//"):
            url = "https:" + url
        elif "." in url and not url.startswith("/"):
            url = "https://" + url
        else:
            return ""
    # Prevent injection via URL
    if _HEADER_INJECTION_RE.search(url):
        return ""
    if len(url) > MAX_URL_LENGTH:
        return ""
    return url
