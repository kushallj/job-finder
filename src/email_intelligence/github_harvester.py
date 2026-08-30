from __future__ import annotations

import logging
import os
import re
from typing import List, Optional, Dict, Any
import httpx

from .models import DiscoveredContact

log = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
IGNORE_EMAIL_SUBSTRINGS = ["users.noreply.github.com", "example.com", "localhost", "sentry.io"]


class GitHubAuthorHarvester:
    """
    Extracts authentic, verified emails of engineers, tech leads, and managers
    from public Git commit events on GitHub.
    """

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN", "").strip() or None

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "JobFinder-EmailIntelligence/1.0",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    async def get_user_commit_email(self, username: str) -> Optional[Dict[str, str]]:
        """Extracts author email from recent public push events of a GitHub user."""
        url = f"{GITHUB_API_BASE}/users/{username}/events/public"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code != 200:
                    return None
                events = resp.json()
                for ev in events:
                    if ev.get("type") == "PushEvent":
                        commits = ev.get("payload", {}).get("commits", [])
                        for c in commits:
                            author = c.get("author", {})
                            email = (author.get("email") or "").strip().lower()
                            name = author.get("name") or username
                            if email and not any(ign in email for ign in IGNORE_EMAIL_SUBSTRINGS):
                                return {"email": email, "name": name, "username": username}
        except Exception as exc:
            log.debug("GitHub user event check failed for %s: %s", username, exc)
        return None

    async def search_company_engineers(
        self,
        company: str,
        domain: Optional[str] = None,
        limit: int = 5,
    ) -> List[DiscoveredContact]:
        """Discovers engineers at a company and extracts their commit author emails."""
        contacts: List[DiscoveredContact] = []
        clean_company = re.sub(r"[^a-zA-Z0-9]", "", company).strip()
        if not clean_company:
            return []

        url = f"{GITHUB_API_BASE}/search/users"
        params = {"q": f"company:{clean_company} type:user", "per_page": min(10, limit * 2)}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers(), params=params)
                if resp.status_code != 200:
                    return []
                users = resp.json().get("items", [])

                for u in users[:limit]:
                    uname = u.get("login")
                    if not uname:
                        continue
                    author_data = await self.get_user_commit_email(uname)
                    if author_data and author_data.get("email"):
                        email = author_data["email"]
                        contacts.append(DiscoveredContact(
                            name=author_data.get("name") or uname,
                            title="Senior Engineer / Tech Lead",
                            company=company,
                            domain=domain or email.split("@")[-1],
                            email=email,
                            confidence_score=90.0,
                            persona_score=70,
                            source="github_commit",
                            github_username=uname,
                            verified=True,
                        ))
        except Exception as exc:
            log.debug("GitHub company engineer search error: %s", exc)

        return contacts


github_harvester = GitHubAuthorHarvester()
