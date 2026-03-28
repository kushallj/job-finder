"""
github_miner.py — GitHub organization commit email mining.

Why GitHub?
  Every public git commit contains author.email — a real, deliverable
  email address that the person uses professionally. This is the highest-
  quality free source of verified emails in existence.

  Companies that use GitHub for open source (Stripe, Cloudflare, Meta,
  Shopify, Airbnb, etc.) have hundreds of engineer commit emails available
  in their public repositories.

Algorithm:
  1. Resolve company → GitHub org name
     - Try: clean_slug(company_name) → HEAD https://github.com/{slug}
     - Fallback: GitHub search API (GET /search/users?q={company}+type:org)
  2. List repos in org (GET /orgs/{org}/repos?per_page=30&sort=pushed)
  3. For each repo, fetch recent commits (GET /repos/{org}/{repo}/commits?per_page=50)
  4. Extract: commit.commit.author.email + commit.commit.author.name
  5. Filter: skip noreply@github.com, skip bots, skip role emails
  6. Return: list of (name, email, company) with source="github_commits"

Rate limits:
  Unauthenticated: 60 req/hour (IP-based)
  With GITHUB_TOKEN: 5000 req/hour
  → Use GITHUB_TOKEN if set in env, gracefully degrade without it

Concurrency:
  AsyncIO + httpx (all I/O bound, no CPU work)
  Semaphore(5): max 5 concurrent repo fetches
  Rate limit: respect X-RateLimit-Remaining header → sleep if < 10

Filtering:
  - Skip emails with "noreply" in domain
  - Skip emails ending in @users.noreply.github.com
  - Skip bot accounts (login contains [bot] or -bot)
  - Skip emails that are the same as login@github.com (generated)
  - Only keep emails where domain != "github.com" (we want real company emails)
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import httpx

log = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"
_NOREPLY_RE = re.compile(r"noreply|no-reply|@users\.noreply\.github\.com", re.IGNORECASE)
_BOT_RE     = re.compile(r"\[bot\]|-bot$|_bot$|\.bot$", re.IGNORECASE)


@dataclass
class GitHubContact:
    name:         str
    email:        str
    github_login: str
    company:      str
    repo:         str       # which repo this was found in
    confidence:   int = 75  # GitHub commits are high-quality source


class GitHubMiner:
    """
    Mines GitHub organization repos for engineer emails.

    Usage:
        miner = GitHubMiner()
        contacts = await miner.mine_org("stripe", "Stripe")
        for c in contacts:
            print(c.name, c.email)
        await miner.close()
    """

    MAX_REPOS    = 20     # max repos to search per org
    MAX_COMMITS  = 50     # commits to fetch per repo
    CONCURRENCY  = 5      # max parallel repo fetches

    def __init__(self, github_token: Optional[str] = None):
        token = github_token or os.environ.get("GITHUB_TOKEN", "")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
            log.debug("GitHub miner: authenticated (5000 req/hr)")
        else:
            log.debug("GitHub miner: unauthenticated (60 req/hr) — set GITHUB_TOKEN for best results")

        self._http    = httpx.AsyncClient(headers=headers, timeout=15.0)
        self._sem     = asyncio.Semaphore(self.CONCURRENCY)
        self._rl_lock = asyncio.Lock()
        self._remaining_requests = 60

    # ── Public API ────────────────────────────────────────────────────────────

    async def mine_org(
        self,
        company_name: str,
        domain: Optional[str] = None,
    ) -> List[GitHubContact]:
        """
        Find GitHub org for company → mine commits → return contacts.

        Args:
            company_name: Company name (e.g. "Stripe")
            domain:       Optional domain for email filtering (e.g. "stripe.com")

        Returns:
            Deduplicated list of GitHubContact objects
        """
        org = await self._resolve_org(company_name)
        if not org:
            log.debug("No GitHub org found for %s", company_name)
            return []

        log.info("GitHub: mining org=%s (company=%s)", org, company_name)
        repos = await self._list_repos(org)
        if not repos:
            return []

        # Mine repos concurrently (bounded by semaphore)
        tasks = [
            asyncio.create_task(self._mine_repo(org, repo, company_name, domain))
            for repo in repos[:self.MAX_REPOS]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten + dedup by email
        seen: Set[str] = set()
        contacts: List[GitHubContact] = []
        for batch in results:
            if isinstance(batch, list):
                for c in batch:
                    if c.email not in seen:
                        seen.add(c.email)
                        contacts.append(c)

        log.info(
            "GitHub: found %d unique contacts at %s across %d repos",
            len(contacts), org, len(repos),
        )
        return contacts

    async def resolve_person(
        self,
        github_login: str,
    ) -> Optional[GitHubContact]:
        """
        Enrich a specific GitHub login → get their public email.
        GET /users/{login} → .email field (if public).
        """
        await self._throttle()
        try:
            resp = await self._http.get(f"{_GITHUB_API}/users/{github_login}")
            self._update_rate_limit(resp)
            if resp.status_code != 200:
                return None
            data  = resp.json()
            email = data.get("email") or ""
            name  = data.get("name")  or data.get("login", "")
            if email and not _NOREPLY_RE.search(email):
                return GitHubContact(
                    name=name,
                    email=email.lower(),
                    github_login=github_login,
                    company=data.get("company", "").lstrip("@"),
                    repo="profile",
                    confidence=80,
                )
        except Exception as e:
            log.debug("GitHub user lookup failed for %s: %s", github_login, e)
        return None

    async def close(self) -> None:
        await self._http.aclose()

    # ── Org resolution ────────────────────────────────────────────────────────

    async def _resolve_org(self, company_name: str) -> Optional[str]:
        """
        Try to find the GitHub org for a company.

        Strategy:
          1. Direct slug guess: "Stripe Inc" → "stripe"
          2. GitHub org search API: /search/users?q={name}+type:org
        """
        slug = _slugify(company_name)

        # Try direct
        await self._throttle()
        try:
            resp = await self._http.get(f"{_GITHUB_API}/orgs/{slug}")
            self._update_rate_limit(resp)
            if resp.status_code == 200:
                return resp.json().get("login", slug)
        except Exception:
            pass

        # Try search
        await self._throttle()
        try:
            resp = await self._http.get(
                f"{_GITHUB_API}/search/users",
                params={"q": f"{company_name} type:org", "per_page": 3},
            )
            self._update_rate_limit(resp)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                # Pick the org whose login most closely matches the company slug
                for item in items:
                    if item.get("type") == "Organization":
                        login = item.get("login", "")
                        # Basic fuzzy match: slug contained in login or vice versa
                        if slug in login.lower() or login.lower() in slug:
                            return login
                # Fallback: return first org result
                for item in items:
                    if item.get("type") == "Organization":
                        return item.get("login")
        except Exception as e:
            log.debug("GitHub org search failed: %s", e)

        return None

    # ── Repo listing ──────────────────────────────────────────────────────────

    async def _list_repos(self, org: str) -> List[str]:
        """List org repos sorted by most recently pushed (highest activity first)."""
        await self._throttle()
        try:
            resp = await self._http.get(
                f"{_GITHUB_API}/orgs/{org}/repos",
                params={"per_page": self.MAX_REPOS, "sort": "pushed", "type": "public"},
            )
            self._update_rate_limit(resp)
            if resp.status_code != 200:
                return []
            return [r["name"] for r in resp.json() if not r.get("fork")]
        except Exception as e:
            log.debug("GitHub list repos failed for %s: %s", org, e)
            return []

    # ── Commit mining ─────────────────────────────────────────────────────────

    async def _mine_repo(
        self,
        org: str,
        repo: str,
        company_name: str,
        domain: Optional[str],
    ) -> List[GitHubContact]:
        """Fetch commits from one repo and extract personal author emails."""
        async with self._sem:
            await self._throttle()
            try:
                resp = await self._http.get(
                    f"{_GITHUB_API}/repos/{org}/{repo}/commits",
                    params={"per_page": self.MAX_COMMITS},
                )
                self._update_rate_limit(resp)
                if resp.status_code != 200:
                    return []

                contacts: Dict[str, GitHubContact] = {}
                for commit in resp.json():
                    if not isinstance(commit, dict):
                        continue

                    # Skip bots
                    author_obj = commit.get("author") or {}
                    if author_obj and _BOT_RE.search(author_obj.get("login", "")):
                        continue

                    git_author = commit.get("commit", {}).get("author", {})
                    name  = git_author.get("name",  "")
                    email = git_author.get("email", "").lower()

                    if not email or not name:
                        continue
                    if _NOREPLY_RE.search(email):
                        continue
                    if email.endswith("@github.com"):
                        continue
                    # Optionally filter by domain
                    if domain and "@" in email:
                        email_domain = email.split("@")[1]
                        if not email_domain.endswith(domain.lstrip(".")):
                            continue

                    if email not in contacts:
                        contacts[email] = GitHubContact(
                            name=name,
                            email=email,
                            github_login=author_obj.get("login", ""),
                            company=company_name,
                            repo=repo,
                            confidence=80,
                        )

                return list(contacts.values())

            except Exception as e:
                log.debug("GitHub mine_repo error (%s/%s): %s", org, repo, e)
                return []

    # ── Rate limiting ─────────────────────────────────────────────────────────

    async def _throttle(self) -> None:
        """Sleep if we're close to the rate limit."""
        async with self._rl_lock:
            if self._remaining_requests < 5:
                log.warning("GitHub rate limit nearly exhausted — sleeping 60s")
                await asyncio.sleep(60)
            elif self._remaining_requests < 15:
                await asyncio.sleep(2.0)

    def _update_rate_limit(self, resp: httpx.Response) -> None:
        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining is not None:
            try:
                self._remaining_requests = int(remaining)
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Convert company name to likely GitHub org slug."""
    slug = name.lower().strip()
    # Remove common suffixes
    for suffix in (" inc", " ltd", " llc", " co", " corp", " technologies",
                   " technology", " solutions", " systems", " software"):
        slug = slug.replace(suffix, "")
    # Remove non-alphanumeric (GitHub orgs allow hyphens)
    slug = re.sub(r"[^a-z0-9\-]", "", slug.replace(" ", "-"))
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug
