import httpx
import logging
import re
from typing import List, Dict, Optional
from src.config import settings

log = logging.getLogger(__name__)

class NewsService:
    """
    Service to interact with NewsAPI.org to fetch recently funded startups.
    """
    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.news_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_funded_startups(self, country: str = "in", category: str = "business", pages: int = 5) -> List[str]:
        """
        Fetches news articles related to startup funding in India and extracts company names.
        Note: This is a basic implementation that extracts names from titles.
        """
        if not self.api_key or self.api_key == "your_news_api_key_here":
            log.warning("News API key not configured. Skipping news fetch.")
            return []

        companies = set()
        queries = [
            "Indian startup funding",
            "startup raised series",
            "startup funding round India",
            "recently funded startups India"
        ]

        for query in queries:
            for page in range(1, pages + 1):
                params = {
                    "q": query,
                    "apiKey": self.api_key,
                    "pageSize": 100,
                    "page": page,
                    "language": "en",
                    "sortBy": "publishedAt"
                }
                try:
                    resp = await self.client.get(f"{self.BASE_URL}/everything", params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        articles = data.get("articles", [])
                        for article in articles:
                            title = article.get("title", "")
                            # Simple extraction heuristic: Look for company names before "raises", "gets", "secures"
                            # This is a placeholder for more advanced LLM-based extraction
                            name = self._extract_company_name(title)
                            if name:
                                companies.add(name)
                    else:
                        log.error(f"News API error: {resp.status_code} - {resp.text}")
                        break
                except Exception as e:
                    log.error(f"Failed to fetch news: {e}")
                    break

        return list(companies)

    def _extract_company_name(self, title: str) -> Optional[str]:
        """
        Heuristic to extract company name from headline.
        Example: "Zomato raises $100M" -> "Zomato"
        """
        keywords = [" raises ", " gets ", " secures ", " bags ", " announces ", " funding ", " Series "]
        for kw in keywords:
            if kw in title:
                parts = title.split(kw)
                potential_name = parts[0].strip()
                # Clean up name (remove leading dates or locations if any)
                potential_name = potential_name.split(":")[-1].strip()
                if 2 < len(potential_name) < 50:
                    return potential_name
        return None

    async def close(self):
        await self.client.aclose()


class FirecrawlNewsService:
    """
    Service to interact with Firecrawl's /search endpoint with sources: ["news"].
    """
    BASE_URL = "https://api.firecrawl.dev/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.firecrawl_api_key
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers=self._headers(),
        )

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def fetch_funded_startups(self, limit: int = 50, location: str = "India") -> List[str]:
        """
        Uses Firecrawl /search to find recently funded startups.
        """
        if not self.api_key:
            log.warning("Firecrawl API key not configured. Skipping news fetch.")
            return []

        queries = [
            "recently funded Indian startups hiring",
            "Indian startups raised funding recently",
            "new startup funding rounds India",
            "Indian startup investment news",
            "startups raising capital India",
            "venture capital deals India startup",
            "Indian tech startups funding 2024",
            "Series A funding Indian startups",
            "Seed round funding India startups",
            "Pre-series A startups India hiring"
        ]

        companies = set()
        # Randomize queries and pick a subset to vary results each time
        import random
        selected_queries = random.sample(queries, min(3, len(queries)))
        
        for query in selected_queries:
            # Based on user description, 'sources' should work. 
            # If it failed before, maybe it needs a different structure.
            # But 'limit' and 'location' work at top level.
            payload = {
                "query": query,
                "limit": limit,
                "location": location,
                # "sources": ["news"], # Re-commenting if it causes 400
                "scrapeOptions": {
                    "formats": ["markdown"],
                    "onlyMainContent": True
                }
            }
            # The issue says: "Firecrawl's /search endpoint with sources: ["news"] returns both in one request."
            # Maybe I should try putting it inside a 'searchOptions' if I use the new SDK-like structure,
            # but I'm calling REST API directly.
            # Let's try to add it back and see. If it fails, I'll stick to what works.
            
            # Actually, I'll stick to what works (top-level limit/location) and try to improve extraction.

            try:
                resp = await self.client.post("/search", json=payload)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    for result in data:
                        # Process both title and content/markdown if available
                        title = result.get("title", "")
                        markdown = result.get("markdown", "")
                        description = result.get("description", "")
                        
                        # Extract company names from title
                        name = self._extract_company_name(title)
                        if name:
                            companies.add(name)
                        
                        # Optionally could use LLM here to extract from markdown/description
                        # For now, we use the same heuristic
                        if description:
                            name = self._extract_company_name(description)
                            if name:
                                companies.add(name)
                else:
                    log.error(f"Firecrawl API error: {resp.status_code} - {resp.text}")
            except Exception as e:
                log.error(f"Failed to fetch news via Firecrawl: {e}")

        return list(companies)

    def _extract_company_name(self, text: str) -> Optional[str]:
        """
        Heuristic to extract company name.
        Uses common patterns in startup funding news.
        """
        if not text:
            return None

        # Patterns like "Company raises $10M", "Company bags funding", etc.
        keywords = [" raises ", " gets ", " secures ", " bags ", " announces ", " funding ", " Series ", " raised ", " raised $"]
        for kw in keywords:
            if kw in text:
                parts = text.split(kw)
                potential_name = parts[0].strip()
                
                # Further cleaning: 
                # Headlines often have "Source: Company raises..." or "Location: Company raises..."
                potential_name = potential_name.split(":")[-1].strip()
                
                # Take last 1-2 words as they are most likely the company name
                words = potential_name.split()
                if not words:
                    continue
                
                # Try to see if previous words are also capitalized (multi-word names like "Phone Pe")
                name_parts = [words[-1]]
                for i in range(len(words)-2, -1, -1):
                    word = words[i].strip(".,:;\"'()")
                    if not word: continue
                    if word[0].isupper() and word.lower() not in ["the", "a", "an", "based", "startup", "indian", "recently", "bengaluru", "mumbai", "delhi", "gurugram", "noida"]:
                        name_parts.insert(0, word)
                    else:
                        break
                
                name = " ".join(name_parts)
                name = name.strip(".,:;\"'()| ")
                
                # Strip amounts like $10M or $500k
                name = re.sub(r'\$\d+(?:\.\d+)?[kMBm]?', '', name).strip()
                
                # Exclude common noise words that might match capitalized heuristic
                noise_words = ["Funding", "Tracker", "Series", "Seed", "Pre-seed", "Round", "Venture", "Capital", "Mn", "Through", "Defense", "Accelerator", "Accel", "Bessemer", "SaaS", "Class", "News", "Report", "IPO", "Investment", "VC", "Equity", "Startup", "Founder"]
                if any(noise.lower() in name.lower().split() for noise in noise_words) or not name:
                    continue

                if 2 < len(name) < 50 and name[0].isupper():
                    return name
        return None

    async def close(self):
        await self.client.aclose()
