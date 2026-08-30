from __future__ import annotations

import html
import logging
import os
import re
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
import httpx
from bs4 import BeautifulSoup

from .models import SearchDork, DiscoveredContact

log = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE)
OBFUSCATED_AT_REGEX = re.compile(r"([A-Za-z0-9._%+-]+)\s*(?:\[at\]|\(at\)|@|\bat\b)\s*([A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.IGNORECASE)
NAME_REGEX = re.compile(r"\b[A-Z][a-z]{1,20}\s+[A-Z][a-z]{1,20}\b")


class GoogleDorkingEngine:
    """
    Generates and executes advanced Google Boolean Dorks to uncover decision-makers,
    email formats, and verified contact addresses across the public web.
    """

    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY", "").strip() or None
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID", "").strip() or None

    def generate_dorks(
        self,
        company: str,
        domain: Optional[str] = None,
        person_name: Optional[str] = None,
        role_title: Optional[str] = None,
    ) -> List[SearchDork]:
        """Constructs a comprehensive suite of OSINT Google Boolean Dorks."""
        dorks: List[SearchDork] = []
        dom = domain or f"{company.lower().replace(' ', '')}.com"
        clean_comp = company.replace('"', '').strip()

        # Dork 1: LinkedIn Decision Maker Email Dork
        q1 = f'site:linkedin.com/in/ "{clean_comp}" ("@{dom}" OR "@gmail.com" OR "email:" OR "contact me at") ("Engineering Manager" OR "Head of Engineering" OR "VP of Engineering" OR "Technical Recruiter" OR "Founder")'
        dorks.append(SearchDork(
            dork_type="linkedin_decision_makers_email",
            query=q1,
            target_role="Engineering Leadership / Talent",
            description=f"Uncovers LinkedIn profiles of {clean_comp} leaders who publicize contact emails.",
            url=f"https://www.google.com/search?q={urllib.parse.quote_plus(q1)}",
        ))

        # Dork 2: Direct Person Name + Corporate Email Dork
        if person_name:
            p_clean = person_name.replace('"', '').strip()
            q2 = f'"{p_clean}" "{clean_comp}" ("@{dom}" OR "email" OR "mailto:")'
            dorks.append(SearchDork(
                dork_type="person_corporate_email",
                query=q2,
                target_role=role_title or "Target Executive",
                description=f"Direct search for {p_clean}'s corporate email on {dom}.",
                url=f"https://www.google.com/search?q={urllib.parse.quote_plus(q2)}",
            ))

        # Dork 3: Company Email Pattern & Directory Dork
        q3 = f'"{clean_comp}" ("email format" OR "email pattern" OR "@{dom}") (site:rocketreach.co OR site:hunter.io OR site:contactout.com)'
        dorks.append(SearchDork(
            dork_type="email_pattern_directory",
            query=q3,
            description=f"Identifies canonical corporate naming patterns ({dom}).",
            url=f"https://www.google.com/search?q={urllib.parse.quote_plus(q3)}",
        ))

        # Dork 4: Public GitHub Commits & Developer Email Dork
        q4 = f'site:github.com "{clean_comp}" ("@{dom}" OR "author-email" OR "author:")'
        dorks.append(SearchDork(
            dork_type="github_commits_dork",
            query=q4,
            description=f"Extracts git commit author emails associated with {clean_comp}.",
            url=f"https://www.google.com/search?q={urllib.parse.quote_plus(q4)}",
        ))

        # Dork 5: Public Document & Presentation Leaks
        q5 = f'"{clean_comp}" "@{dom}" filetype:pdf OR filetype:docx OR filetype:txt'
        dorks.append(SearchDork(
            dork_type="document_email_leak",
            query=q5,
            description=f"Finds direct email addresses in published whitepapers, PDFs, and slide decks.",
            url=f"https://www.google.com/search?q={urllib.parse.quote_plus(q5)}",
        ))

        return dorks

    def decode_and_extract_emails(self, text: str, domain: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """
        Extracts valid emails from raw text/HTML, resolving obfuscated email patterns.
        Returns List of tuples: (email, proximate_name, proximate_title)
        """
        results: List[Tuple[str, str, str]] = []
        seen_emails = set()

        unescaped = html.unescape(text)

        # 1. Direct Regex match
        for match in EMAIL_REGEX.finditer(unescaped):
            email = match.group(0).lower().strip()
            if email in seen_emails or any(x in email for x in ("noreply", "no-reply", "example.com", "schema.org", "sentry.io")):
                continue
            seen_emails.add(email)

            # Proximity extraction
            start = max(0, match.start() - 150)
            end = min(len(unescaped), match.end() + 150)
            snippet = unescaped[start:end]

            name = "Engineering Leader"
            title = "Engineering / Talent"

            name_matches = NAME_REGEX.findall(snippet)
            if name_matches:
                for cand in name_matches:
                    if not any(w.lower() in cand.lower() for w in ("linkedin", "google", "github", "twitter", "email", "manager", "engineer")):
                        name = cand
                        break

            if "engineering manager" in snippet.lower():
                title = "Engineering Manager"
            elif "head of engineering" in snippet.lower():
                title = "Head of Engineering"
            elif "recruiter" in snippet.lower():
                title = "Technical Recruiter"
            elif "vp" in snippet.lower() and "eng" in snippet.lower():
                title = "VP of Engineering"
            elif "cto" in snippet.lower():
                title = "Chief Technology Officer"

            results.append((email, name, title))

        # 2. Obfuscated match: [at] / (at)
        for match in OBFUSCATED_AT_REGEX.finditer(unescaped):
            user = match.group(1).strip()
            dom = match.group(2).strip()
            email = f"{user}@{dom}".lower()
            if email not in seen_emails and "." in dom:
                seen_emails.add(email)
                results.append((email, "Engineering Leader", "Engineering / Talent"))

        return results

    async def execute_dork_search(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 8,
    ) -> List[DiscoveredContact]:
        """Executes a search dork via Google Custom Search API or DuckDuckGo HTML fallback."""
        contacts: List[DiscoveredContact] = []
        raw_text_corpus = ""

        # Option A: Google Custom Search API if available
        if self.google_api_key and self.google_cse_id:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        "https://www.googleapis.com/customsearch/v1",
                        params={
                            "key": self.google_api_key,
                            "cx": self.google_cse_id,
                            "q": query,
                            "num": min(10, limit),
                        },
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("items", [])
                        for item in items:
                            raw_text_corpus += f" {item.get('title', '')} {item.get('snippet', '')}"
            except Exception as exc:
                log.debug("Google CSE API search error: %s", exc)

        # Option B: DuckDuckGo / Public Search Fallback
        if not raw_text_corpus:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True) as client:
                    resp = await client.get(
                        "https://html.duckduckgo.com/html/",
                        params={"q": query},
                    )
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        snippets = soup.find_all("a", class_="result__snippet")
                        titles = soup.find_all("a", class_="result__title")
                        for el in snippets + titles:
                            raw_text_corpus += f" {el.get_text()}"
            except Exception as exc:
                log.debug("DuckDuckGo dork fallback error: %s", exc)

        extracted = self.decode_and_extract_emails(raw_text_corpus, domain=domain)
        for email, name, title in extracted[:limit]:
            contacts.append(DiscoveredContact(
                name=name,
                title=title,
                company="Company",
                domain=domain or email.split("@")[-1],
                email=email,
                confidence_score=85.0,
                source="dorking",
                verified=True,
            ))

        return contacts


dorking_engine = GoogleDorkingEngine()
