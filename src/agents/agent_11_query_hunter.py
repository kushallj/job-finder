"""
agent_11_query_hunter.py — Boolean Query Hunter Agent.

STRATEGY
--------
This is the "Hunter" archetype extended past ATS APIs: executes the
X-ray/boolean query bank in config/boolean_queries.yml (ATS platforms, YC
directories, funding press, Medium/Substack, GitHub, YouTube, and
search-indexed X/LinkedIn posts) and writes every result into a
`boolean_leads` table in data/agent_state.db — which is the seed of the
"full CRM tool": company, source query, URL, title, discovered_at, and a
`status` column (new -> reviewed -> converted-to-application) you can move
through as you triage.

IMPORTANT — how this stays ToS-compliant:
  This agent NEVER scrapes Google, LinkedIn, or X search-results pages
  directly (all three explicitly forbid that, and IPs/accounts get
  blocked). It only calls:
    - Google Custom Search JSON API   (official, key + cx required)
    - Serper.dev                       (official, key required)
  Both are exactly what "X-ray sourcing" tools like SeekOut/hireEZ run on
  under the hood. If neither is configured, this agent still runs — it
  just renders the templated queries for you to paste into Google/Bing
  manually, rather than failing or silently doing something it shouldn't.

DAG node contract:
    Input:  AgentContext, categories: List[str] = None (filter query bank),
            max_results_per_query: int = 10
    Output: AgentResult.data = {
        "executed": bool, "leads": [...], "rendered_queries": [...]
    }
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import AgentContext, AgentResult, BaseAgent, get_state_conn, CONFIG_DIR

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    import httpx
    _HTTPX = True
except ImportError:  # pragma: no cover
    _HTTPX = False

try:
    from src.config import settings
except Exception:  # noqa: BLE001
    settings = None

QUERY_BANK_PATH = CONFIG_DIR / "boolean_queries.yml"
GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
SERPER_URL = "https://google.serper.dev/search"


def _load_query_bank() -> List[Dict[str, Any]]:
    if yaml is None or not QUERY_BANK_PATH.exists():
        return []
    with open(QUERY_BANK_PATH, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("queries", [])


def _ensure_leads_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS boolean_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT,
            category TEXT,
            title TEXT,
            url TEXT UNIQUE,
            snippet TEXT,
            status TEXT DEFAULT 'new',
            discovered_at REAL NOT NULL
        )
    """)
    conn.commit()


class QueryHunterAgent(BaseAgent):
    name = "query_hunter"

    def run(self, categories: Optional[List[str]] = None,
            max_results_per_query: int = 10) -> AgentResult:
        return self._timed(self._run, categories, max_results_per_query)

    def _run(self, categories: Optional[List[str]], max_results_per_query: int) -> AgentResult:
        bank = _load_query_bank()
        if categories:
            bank = [q for q in bank if q.get("category") in categories]

        if not bank:
            return AgentResult(
                agent=self.name, ok=False,
                summary="config/boolean_queries.yml not found or empty.",
            )

        rendered = [{"id": q["id"], "category": q["category"], "query": q["query"].strip(),
                     "purpose": q.get("purpose", "")} for q in bank]

        backend = self._select_backend()
        if backend is None:
            return AgentResult(
                agent=self.name, ok=True,
                summary=f"No search backend configured ({len(rendered)} queries rendered for manual use). "
                        f"Set google_cse_api_key + google_cse_id, or serper_api_key, in .env to auto-execute.",
                data={"executed": False, "leads": [], "rendered_queries": rendered},
            )

        if not _HTTPX:
            return AgentResult(
                agent=self.name, ok=False,
                summary="httpx not installed — cannot execute queries against the search backend.",
                data={"executed": False, "leads": [], "rendered_queries": rendered},
            )

        conn = get_state_conn()
        _ensure_leads_table(conn)
        all_leads: List[Dict[str, Any]] = []

        with httpx.Client(timeout=10.0) as client:
            for q in bank:
                results = self._execute(client, backend, q["query"].strip(), max_results_per_query)
                for r in results:
                    lead = {
                        "query_id": q["id"], "category": q["category"],
                        "title": r.get("title", ""), "url": r.get("url", ""),
                        "snippet": r.get("snippet", ""),
                    }
                    all_leads.append(lead)
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO boolean_leads "
                            "(query_id, category, title, url, snippet, discovered_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (lead["query_id"], lead["category"], lead["title"], lead["url"],
                             lead["snippet"], time.time()),
                        )
                    except Exception:  # noqa: BLE001
                        continue
        conn.commit()
        conn.close()

        return AgentResult(
            agent=self.name, ok=True,
            summary=f"Executed {len(bank)} queries via {backend}, found {len(all_leads)} candidate leads.",
            data={"executed": True, "leads": all_leads, "rendered_queries": rendered},
        )

    @staticmethod
    def _select_backend() -> Optional[str]:
        if settings is None:
            return None
        if getattr(settings, "google_cse_api_key", None) and getattr(settings, "google_cse_id", None):
            return "google_cse"
        if getattr(settings, "serper_api_key", None):
            return "serper"
        return None

    def _execute(self, client, backend: str, query: str, max_results: int) -> List[Dict[str, str]]:
        try:
            if backend == "google_cse":
                resp = client.get(GOOGLE_CSE_URL, params={
                    "key": settings.google_cse_api_key, "cx": settings.google_cse_id,
                    "q": query, "num": min(max_results, 10),
                })
                resp.raise_for_status()
                items = resp.json().get("items", [])
                return [{"title": i.get("title", ""), "url": i.get("link", ""),
                          "snippet": i.get("snippet", "")} for i in items]
            if backend == "serper":
                resp = client.post(SERPER_URL, json={"q": query, "num": max_results},
                                    headers={"X-API-KEY": settings.serper_api_key})
                resp.raise_for_status()
                items = resp.json().get("organic", [])
                return [{"title": i.get("title", ""), "url": i.get("link", ""),
                          "snippet": i.get("snippet", "")} for i in items]
        except Exception:  # noqa: BLE001
            self.log.warning("Query execution failed for %r via %s", query[:60], backend, exc_info=True)
        return []


if __name__ == "__main__":
    ctx = AgentContext.load()
    result = QueryHunterAgent(ctx).run(categories=["funding"])
    print(result.to_json())
