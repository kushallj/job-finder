"""
contact_researcher.py — Async contact intelligence gatherer.

Data sources:
  1. GitHub user API    — profile bio, languages, pinned repos, recent activity
  2. GitHub repos API   — most-starred personal repos, topics
  3. Personal blog/site — if URL found in GitHub profile or email domain
  4. GitHub starred     — infers technical interests from what they star

GitHub is the richest public source for engineers.
We derive github_username from:
  a) linkedin_url pattern  (github.com/username in LinkedIn contact section)
  b) email prefix          (john.doe@company.com → try "johndoe", "john-doe")
  c) name-based slug       ("John Doe" → "johndoe", "john-doe")

Privacy note:
  Only uses public GitHub API (no auth for basic calls, 60 req/hr unauthenticated).
  Never scrapes LinkedIn (ToS violation). No private data.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    import aiohttp
    _AIOHTTP = True
except ImportError:
    _AIOHTTP = False

from .models import ContactProfile

log = logging.getLogger(__name__)

_CACHE_DB  = Path("data/personalization_cache.db")
_CACHE_TTL = 3 * 24 * 3600   # 3 days (contacts change more often)

_TECH_RE = re.compile(
    r"\b(Python|FastAPI|Django|Node\.?js|React|TypeScript|Go|Rust|Java"
    r"|Kubernetes|Docker|AWS|GCP|PostgreSQL|Redis|Kafka|ML|AI|LLM"
    r"|GraphQL|gRPC|distributed|systems|compiler|parser|infra|platform"
    r"|open.source|performance|security|backend|frontend|fullstack)\b",
    re.IGNORECASE,
)


class ContactResearcher:
    """
    Researches a contact from public signals.

    Usage:
        researcher = ContactResearcher()
        profile = await researcher.research("John Doe", email="john@company.com")
    """

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session      = session
        self._owns_session = session is None
        self._init_cache()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def research(
        self,
        name:          str,
        email:         str = "",
        linkedin_url:  str = "",
        github_hint:   str = "",   # explicit username if known
    ) -> ContactProfile:
        """
        Research a contact.  Returns cached result if fresh.

        Args:
            name:         Full name ("John Doe")
            email:        Contact email (used for username derivation)
            linkedin_url: LinkedIn profile URL (not scraped, mined for username hint)
            github_hint:  Explicit GitHub username if already known
        """
        cache_key = _cache_key(name, email)
        cached    = self._load_cache(cache_key)
        if cached:
            log.debug("ContactResearcher: cache hit for %s", name)
            return cached

        username = (
            github_hint
            or _extract_github_from_linkedin(linkedin_url)
            or await self._find_github_username(name, email)
        )

        if username:
            profile = await self._research_github_user(name, username)
        else:
            profile = ContactProfile(name=name)
            log.debug("ContactResearcher: no GitHub found for %s", name)

        self._save_cache(cache_key, profile)
        return profile

    # ── GitHub user research ───────────────────────────────────────────────────

    async def _research_github_user(self, name: str, username: str) -> ContactProfile:
        session  = await self._get_session()
        sources  = []
        profile  = ContactProfile(name=name, github_username=username)

        # Fetch user profile
        user_url = f"https://api.github.com/users/{username}"
        try:
            async with session.get(user_url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status == 200:
                    data        = await r.json()
                    profile.bio = data.get("bio") or ""
                    sources.append(user_url)
                    # Personal blog from profile
                    blog_url    = data.get("blog", "")
                    if blog_url and not blog_url.startswith("http"):
                        blog_url = "https://" + blog_url
                    if blog_url:
                        posts = await self._fetch_blog_titles(blog_url, session)
                        profile.blog_posts = posts
                        if posts:
                            sources.append(blog_url)
                elif r.status == 404:
                    return profile
        except Exception as exc:
            log.debug("GitHub user %s: %s", username, exc)
            return profile

        # Fetch repos (most recent, non-fork)
        repos_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=20"
        try:
            async with session.get(repos_url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status == 200:
                    repos = await r.json()
                    sources.append(repos_url)

                    personal = [rp for rp in repos if not rp.get("fork")]
                    # Sort by stars for "best work" signal
                    personal.sort(key=lambda x: x.get("stargazers_count", 0), reverse=True)

                    profile.recent_repos = [
                        f"{rp['name']}: {rp.get('description', '') or ''}"
                        for rp in personal[:6]
                    ]

                    # Language distribution
                    lang_counts: Dict[str, int] = {}
                    for rp in personal:
                        lang = rp.get("language")
                        if lang:
                            lang_counts[lang] = lang_counts.get(lang, 0) + 1
                    profile.languages = sorted(lang_counts, key=lang_counts.get, reverse=True)[:5]

                    # Topics from repos
                    all_topics = []
                    for rp in personal[:10]:
                        all_topics.extend(rp.get("topics", []))
                    profile.recent_topics = list(dict.fromkeys(all_topics))[:10]

                    # Distill technical keywords from bio + repo descriptions + topics
                    all_text = " ".join([
                        profile.bio,
                        " ".join(profile.recent_topics),
                        " ".join(r.split(":", 1)[1] if ":" in r else r for r in profile.recent_repos),
                    ])
                    profile.technical_keywords = list(dict.fromkeys(
                        m.group(0) for m in _TECH_RE.finditer(all_text)
                    ))[:12]
        except Exception as exc:
            log.debug("GitHub repos for %s: %s", username, exc)

        profile.research_sources = sources
        return profile

    # ── GitHub username discovery ──────────────────────────────────────────────

    async def _find_github_username(self, name: str, email: str) -> str:
        """
        Try common username patterns and verify against GitHub API.
        Returns first valid username or empty string.
        """
        candidates = _derive_username_candidates(name, email)
        session    = await self._get_session()

        # Check candidates concurrently (max 3 at a time)
        sem = asyncio.Semaphore(3)

        async def check(username: str) -> str:
            async with sem:
                try:
                    url = f"https://api.github.com/users/{username}"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as r:
                        if r.status == 200:
                            data = await r.json()
                            # Verify it's likely the same person (name similarity)
                            gh_name = (data.get("name") or "").lower()
                            if _name_similarity(name.lower(), gh_name) > 0.5:
                                return username
                except Exception:
                    pass
                return ""

        results = await asyncio.gather(*[check(c) for c in candidates[:8]])
        return next((r for r in results if r), "")

    # ── Blog scraper ───────────────────────────────────────────────────────────

    async def _fetch_blog_titles(
        self, url: str, session: aiohttp.ClientSession
    ) -> List[str]:
        """Fetch h1/h2 titles from personal blog homepage."""
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=5),
                headers={"User-Agent": "Mozilla/5.0"},
                allow_redirects=True, max_redirects=3,
            ) as r:
                if r.status == 200:
                    html  = await r.text(errors="ignore")
                    heads = re.findall(r"<h[12][^>]*>\s*([^<]{10,100})\s*</h[12]>", html, re.IGNORECASE)
                    return [re.sub(r"\s+", " ", h).strip() for h in heads[:5]]
        except Exception:
            pass
        return []

    # ── Session management ─────────────────────────────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session      = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    # ── SQLite cache ───────────────────────────────────────────────────────────

    def _init_cache(self) -> None:
        _CACHE_DB.parent.mkdir(exist_ok=True)
        with sqlite3.connect(_CACHE_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contact_research (
                    cache_key   TEXT PRIMARY KEY,
                    data_json   TEXT NOT NULL,
                    cached_at   INTEGER NOT NULL
                )
            """)

    def _load_cache(self, key: str) -> Optional[ContactProfile]:
        try:
            with sqlite3.connect(_CACHE_DB) as conn:
                row = conn.execute(
                    "SELECT data_json, cached_at FROM contact_research WHERE cache_key=?",
                    (key,)
                ).fetchone()
                if row and (time.time() - row[1]) < _CACHE_TTL:
                    return ContactProfile(**json.loads(row[0]))
        except Exception:
            pass
        return None

    def _save_cache(self, key: str, profile: ContactProfile) -> None:
        try:
            import dataclasses
            with sqlite3.connect(_CACHE_DB) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO contact_research (cache_key, data_json, cached_at)
                       VALUES (?, ?, ?)""",
                    (key, json.dumps(dataclasses.asdict(profile)), int(time.time()))
                )
        except Exception as exc:
            log.debug("Contact cache save: %s", exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cache_key(name: str, email: str) -> str:
    base = email.split("@")[0] if email else re.sub(r"\s+", "_", name.lower())
    return base[:40]


def _extract_github_from_linkedin(linkedin_url: str) -> str:
    """If someone put their GitHub in their LinkedIn contact section URL."""
    m = re.search(r"github\.com/([A-Za-z0-9_-]+)", linkedin_url or "")
    return m.group(1) if m else ""


def _derive_username_candidates(name: str, email: str) -> List[str]:
    """
    Generate likely GitHub username candidates.
    Examples for "John Doe" / "john.doe@stripe.com":
      johndoe, john-doe, john_doe, jdoe, doe-john, john.doe (email prefix)
    """
    parts  = re.findall(r"[a-zA-Z]+", name.lower())
    prefix = email.split("@")[0].lower() if email else ""

    candidates = []
    if len(parts) >= 2:
        first, last = parts[0], parts[-1]
        candidates += [
            first + last,          # johndoe
            first + "-" + last,    # john-doe
            first + "_" + last,    # john_doe
            first[0] + last,       # jdoe
            first,                 # john
        ]
    if prefix and prefix not in candidates:
        candidates.append(prefix)
        candidates.append(prefix.replace(".", ""))
        candidates.append(prefix.replace(".", "-"))

    return list(dict.fromkeys(candidates))[:8]


def _name_similarity(a: str, b: str) -> float:
    """Simple token overlap similarity (0-1)."""
    if not a or not b:
        return 0.0
    ta = set(re.findall(r"[a-z]+", a))
    tb = set(re.findall(r"[a-z]+", b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))
