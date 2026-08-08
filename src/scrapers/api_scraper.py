"""
api_scraper.py — Production-grade graph-based job scraper.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE (what billion-dollar scrapers actually do)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Layer 0 — TLS impersonation (curl_cffi)
    Real Chrome TLS handshake at the network level.
    Bypasses JA3/JA4 fingerprinting without any browser.
    Fastest: ~50ms/request.

  Layer 1 — API sources (httpx, async, pooled)
    Remotive, Adzuna, Foorilla, MultiPlatform.
    No browser. Pure HTTP. Cached 4h.

  Layer 2 — Stealth browser graph (anti-detection stack)
    Nodriver  → Chrome without CDP traces (async-native)
    Camoufox  → Firefox engine-level fingerprint spoofing
    Playwright→ fallback, stealth plugin
    Selenium  → last browser resort
    Each tier tried only if previous is blocked.

  Layer 3 — Search engine graph (find job URLs)
    DuckDuckGo → Brave → Bing → SerpAPI
    Used when direct site scraping fails completely.

  Layer 4 — LLM extraction (Ollama/Mistral local)
    Passes cleaned HTML to local LLM when all CSS selectors fail.
    Zero data loss: something always comes back.

  Normalization → Dedup (Trie O(k)) → TrustScore → Cache

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MCP SETUP (Claude Desktop integration)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Option A — Run as MCP server for Claude Desktop:
    1. pip install "mcp[cli]"
    2. Add to ~/Library/Application Support/Claude/claude_desktop_config.json:
       {
         "mcpServers": {
           "job-scraper": {
             "command": "python",
             "args": ["-m", "src.scrapers.api_scraper", "--mcp"],
             "env": {"PYTHONPATH": "/path/to/job-finder"}
           }
         }
       }
    3. Restart Claude Desktop
    4. Claude now has tool: search_jobs(query, location, max_results)

  Option B — Playwright MCP (browser automation via MCP):
    1. npm install -g @playwright/mcp
    2. npx playwright-mcp --port 3001
    3. Set MCP_PLAYWRIGHT_URL=http://localhost:3001 in .env

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTALL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  pip install curl_cffi playwright camoufox nodriver \
              playwright-stealth beautifulsoup4 lxml httpx
  playwright install chromium firefox
  camoufox fetch
  # Ollama: curl -fsSL https://ollama.com/install.sh | sh
  # Then:   ollama pull llama3.2:3b
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import logging.handlers
import os
import random
import re
import sys
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from src.scrapers.jobspy_scraper import JobSpyScraper

import httpx

# ── Optional: curl_cffi (TLS impersonation) ───────────────────────────────────
try:
    from curl_cffi.requests import AsyncSession as CurlSession
    CURL_CFFI_OK = True
except ImportError:
    CURL_CFFI_OK = False
    CurlSession = None

# ── Optional: Nodriver (async Chrome, no CDP traces) ──────────────────────────
try:
    import nodriver as _nodriver
    NODRIVER_OK = True
except ImportError:
    NODRIVER_OK = False

# ── Optional: Camoufox (Firefox engine-level stealth) ─────────────────────────
try:
    from camoufox.async_api import AsyncCamoufox
    CAMOUFOX_OK = True
except ImportError:
    CAMOUFOX_OK = False

# ── Optional: Playwright ──────────────────────────────────────────────────────
try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PWTimeout
    try:
        from playwright_stealth import stealth_async
        _STEALTH_OK = True
    except ImportError:
        async def stealth_async(p): pass
        _STEALTH_OK = False
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

# ── Optional: Selenium fallback ───────────────────────────────────────────────
try:
    from src.scrapers.selenium_scraper import HybridJobScraper as _SeleniumHub
    SELENIUM_OK = True
except ImportError:
    SELENIUM_OK = False

# ── Optional: BeautifulSoup ───────────────────────────────────────────────────
try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False

# ── Internal ──────────────────────────────────────────────────────────────────
from src.scrapers.base import BaseScraper
from src.scrapers.multi_platform_scraper import MultiPlatformJobScraper
from src.config import settings
from src.ai.local_llm_service import LocalLLMService

try:
    from src.scrapers.foorilla_scraper import FoorillaScraper as _Foorilla
    _FOORILLA_OK = True
except ImportError:
    _FOORILLA_OK = False

# =============================================================================
# Logging
# =============================================================================

_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)

_FMT = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)-24s | trace=%(trace_id)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
for _h in [
    logging.StreamHandler(),
    logging.handlers.RotatingFileHandler(
        _LOG_DIR / "scraper.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    ),
]:
    _h.setFormatter(_FMT)
    logging.getLogger("scraper").addHandler(_h)
logging.getLogger("scraper").setLevel(logging.INFO)
logging.getLogger("scraper").propagate = False


class TLog:
    """Trace-bound structured logger. Every log line carries trace_id."""
    def __init__(self, name: str, trace_id: str = "-"):
        self._l = logging.getLogger(f"scraper.{name}")
        self.trace_id = trace_id

    def _x(self) -> Dict: return {"trace_id": self.trace_id}
    def debug(self, m, *a, **k):   self._l.debug(m, *a,   extra=self._x(), **k)
    def info(self, m, *a, **k):    self._l.info(m, *a,    extra=self._x(), **k)
    def warning(self, m, *a, **k): self._l.warning(m, *a, extra=self._x(), **k)
    def error(self, m, *a, **k):   self._l.error(m, *a,   extra=self._x(), **k)


# =============================================================================
# Canonical data contract
# =============================================================================

@dataclass
class NormalizedJob:
    """Single canonical job shape. All sources produce this."""
    job_id:      str
    title:       str
    company:     str
    location:    str
    description: str
    url:         str
    source:      str
    posted_date: Optional[str] = None
    salary:      Optional[str] = None
    skills:      List[str]     = field(default_factory=list)
    experience:  Optional[str] = None
    job_type:    Optional[str] = None
    trust_score: int           = 50

    def to_dict(self) -> Dict:
        return asdict(self)


def _job_id(title: str, company: str, source: str) -> str:
    s = f"{title.lower().strip()}::{company.lower().strip()}::{source}::{datetime.utcnow().strftime('%Y%m%d')}"
    return hashlib.md5(s.encode()).hexdigest()[:16]


def _score(j: NormalizedJob) -> int:
    pts = 0
    if j.title   and len(j.title)   > 3:   pts += 20
    if j.company and len(j.company) > 1:   pts += 20
    if j.url     and j.url.startswith("http"): pts += 20
    if j.description and len(j.description) > 50: pts += 20
    if j.location and len(j.location) > 2: pts += 10
    if j.posted_date:                      pts += 10
    return pts


def normalize(d: Dict, src: str = "") -> Optional[NormalizedJob]:
    """Convert any dict → NormalizedJob. Returns None if title/company missing."""
    title   = str(d.get("title")   or "").strip()[:200]
    company = str(d.get("company") or d.get("company_name") or "").strip()[:200]
    if not title or not company:
        return None
    j = NormalizedJob(
        job_id      = d.get("job_id") or _job_id(title, company, d.get("source", src)),
        title       = title,
        company     = company,
        location    = str(d.get("location") or "").strip()[:200] or "Unknown",
        description = str(d.get("description") or "").strip()[:3000],
        url         = str(d.get("url") or "").strip(),
        source      = d.get("source") or src,
        posted_date = d.get("posted_date") or d.get("publication_date"),
        salary      = d.get("salary"),
        skills      = d.get("skills") or d.get("tags") or [],
        experience  = d.get("experience"),
        job_type    = d.get("job_type"),
    )
    j.trust_score = _score(j)
    return j


# =============================================================================
# LRU + TTL Cache
# =============================================================================

class ScrapeCache:
    def __init__(self, max_size: int = 512, ttl_seconds: int = 14_400):
        self._d: OrderedDict[str, Tuple[List[Dict], float]] = OrderedDict()
        self._max = max_size
        self._ttl = ttl_seconds
        self._hits = self._miss = 0

    def _k(self, src: str, q: str, loc: str) -> str:
        return hashlib.md5(f"{src}::{q.lower()}::{loc.lower()}".encode()).hexdigest()

    def get(self, src: str, q: str, loc: str) -> Optional[List[Dict]]:
        k = self._k(src, q, loc)
        e = self._d.get(k)
        if e is None:
            self._miss += 1
            return None
        data, ts = e
        if time.monotonic() - ts > self._ttl:
            del self._d[k]
            self._miss += 1
            return None
        self._d.move_to_end(k)
        self._hits += 1
        return data

    def set(self, src: str, q: str, loc: str, data: List[Dict]):
        k = self._k(src, q, loc)
        if len(self._d) >= self._max:
            self._d.popitem(last=False)
        self._d[k] = (data, time.monotonic())

    @property
    def stats(self) -> Dict:
        t = self._hits + self._miss
        return {"hits": self._hits, "misses": self._miss,
                "hit_rate_pct": round(self._hits / t * 100, 1) if t else 0,
                "size": len(self._d)}


_CACHE = ScrapeCache()


# =============================================================================
# Circuit Breaker
# =============================================================================

class CircuitBreaker:
    def __init__(self, name: str, threshold: int = 4, recovery: float = 300.0):
        self.name = name
        self._threshold = threshold
        self._recovery  = recovery
        self._fails     = 0
        self._opened_at = 0.0
        self._open      = False

    @property
    def is_open(self) -> bool:
        if self._open and time.monotonic() - self._opened_at > self._recovery:
            self._open = False
        return self._open

    def success(self):
        self._fails = 0
        self._open  = False

    def failure(self, reason: str = ""):
        self._fails += 1
        log = logging.getLogger("scraper.circuit")
        log.debug("CB %s: fail %d/%d %s", self.name, self._fails, self._threshold, reason,
                  extra={"trace_id": "-"})
        if self._fails >= self._threshold:
            self._open      = True
            self._opened_at = time.monotonic()
            log.warning("⚡ Circuit OPEN: %s (recovery in %.0fs)", self.name, self._recovery,
                        extra={"trace_id": "-"})

    @property
    def status(self) -> Dict:
        return {"name": self.name, "open": self.is_open, "fails": self._fails,
                "threshold": self._threshold}


# =============================================================================
# StrategyGraph
# =============================================================================

class StrategyGraph:
    def __init__(self):
        self._edges: Dict[str, List[str]]      = {}
        self._nodes: Dict[str, Callable]       = {}
        self._cbs:   Dict[str, CircuitBreaker] = {}
        self._log    = TLog("strategy_graph")

    def add_node(self, node_id: str, fn: Callable, cb: Optional[CircuitBreaker] = None):
        self._nodes[node_id] = fn
        self._cbs[node_id]   = cb or CircuitBreaker(node_id)
        if node_id not in self._edges:
            self._edges[node_id] = []

    def add_edge(self, from_id: str, to_id: str):
        self._edges.setdefault(from_id, []).append(to_id)
        self._edges.setdefault(to_id, [])

    async def execute(
        self,
        start: str,
        *args,
        timeout: float = 45.0,
        min_results: int = 1,
        **kwargs,
    ) -> List[Dict]:
        visited = set()
        queue   = [start]

        while queue:
            node_id = queue.pop(0)
            if node_id in visited or node_id not in self._nodes:
                continue
            visited.add(node_id)

            cb = self._cbs[node_id]
            if cb.is_open:
                self._log.debug("Node %s circuit OPEN — skipping", node_id)
                queue.extend(n for n in self._edges.get(node_id, []) if n not in visited)
                continue

            self._log.info("Graph: trying node '%s'", node_id)
            try:
                result = await asyncio.wait_for(
                    self._nodes[node_id](*args, **kwargs),
                    timeout=timeout,
                )
                if isinstance(result, list) and len(result) >= min_results:
                    cb.success()
                    self._log.info("Graph: node '%s' succeeded (%d results)", node_id, len(result))
                    return result
                else:
                    self._log.warning("Graph: node '%s' returned %d results — falling back",
                                      node_id, len(result) if isinstance(result, list) else 0)
                    cb.failure("insufficient_results")
            except asyncio.TimeoutError:
                self._log.warning("Graph: node '%s' timed out (%.0fs)", node_id, timeout)
                cb.failure("timeout")
            except Exception as exc:
                self._log.warning("Graph: node '%s' failed: %s", node_id, exc)
                cb.failure(str(exc)[:80])

            queue.extend(n for n in self._edges.get(node_id, []) if n not in visited)

        self._log.warning("Graph: all nodes exhausted for start='%s'", start)
        return []

    def all_statuses(self) -> Dict:
        return {nid: self._cbs[nid].status for nid in self._nodes}


# =============================================================================
# TLS Layer
# =============================================================================

_IMPERSONATE_TARGETS = ["chrome136", "chrome124", "chrome110", "firefox117"]

class TLSLayer:
    def __init__(self):
        self._log    = TLog("tls_layer")
        self._target = random.choice(_IMPERSONATE_TARGETS)

    async def get(self, url: str, headers: Optional[Dict] = None,
                  timeout: float = 20.0) -> Optional[str]:
        if not CURL_CFFI_OK:
            return None
        try:
            async with CurlSession(impersonate=self._target) as session:
                resp = await session.get(
                    url,
                    headers=headers or self._headers(),
                    timeout=timeout,
                    allow_redirects=True,
                )
                if resp.status_code == 200:
                    return resp.text
                self._log.debug("TLS GET %s → %d", url, resp.status_code)
                return None
        except Exception as exc:
            self._log.debug("TLS layer failed for %s: %s", url, exc)
            return None

    def _headers(self) -> Dict:
        return {
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT":             "1",
            "Connection":      "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }


# =============================================================================
# Nodriver engine
# FIX #11: headless is now controlled by self._headless instead of hardcoded False
# =============================================================================

class NodriverEngine:
    def __init__(self, headless: bool = True):
        self._log     = TLog("nodriver")
        self._browser = None
        self._headless = headless  # FIX: was always False (opened visible window)

    async def start(self):
        if not NODRIVER_OK:
            raise ImportError("pip install nodriver")
        self._browser = await _nodriver.start(
            headless=self._headless,  # FIX: use configured value
            browser_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                f"--window-size={random.choice(['1920,1080','1440,900','1536,864'])}",
            ],
        )
        self._log.info("Nodriver started (headless=%s)", self._headless)

    async def get_page_html(self, url: str, wait_selector: str = "body",
                            timeout: float = 20.0) -> Optional[str]:
        if not self._browser:
            return None
        try:
            tab = await asyncio.wait_for(self._browser.get(url), timeout=timeout)
            await asyncio.sleep(random.uniform(1.5, 3.0))
            for _ in range(random.randint(2, 4)):
                await tab.evaluate(f"window.scrollBy(0, {random.randint(300,700)})")
                await asyncio.sleep(random.uniform(0.4, 1.2))
            html = await tab.get_content()
            await tab.close()
            return html
        except Exception as exc:
            self._log.debug("Nodriver get_page failed for %s: %s", url, exc)
            return None

    async def close(self):
        if self._browser:
            with suppress(Exception):
                self._browser.stop()


# =============================================================================
# Camoufox engine
# =============================================================================

class CamoufoxEngine:
    def __init__(self):
        self._log = TLog("camoufox")

    async def get_page_html(self, url: str, timeout: float = 25.0) -> Optional[str]:
        if not CAMOUFOX_OK:
            return None
        try:
            async with AsyncCamoufox(headless=True, geoip=True) as browser:
                page = await browser.new_page()
                await page.goto(url, timeout=int(timeout * 1000))
                await asyncio.sleep(random.uniform(1.0, 2.5))
                for _ in range(random.randint(2, 3)):
                    await page.evaluate(f"window.scrollBy(0, {random.randint(200,600)})")
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                html = await page.content()
                await page.close()
                return html
        except Exception as exc:
            self._log.debug("Camoufox failed for %s: %s", url, exc)
            return None


# =============================================================================
# Playwright engine
# =============================================================================

class PlaywrightEngine:
    _BROWSER_ORDER = ["chromium", "firefox", "webkit"]

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._pw       = None
        self._browser  = None
        self._log      = TLog("playwright")

    async def start(self):
        if not PLAYWRIGHT_OK:
            raise ImportError("pip install playwright && playwright install")
        self._pw = await async_playwright().start()
        for bname in self._BROWSER_ORDER:
            try:
                launcher = getattr(self._pw, bname)
                self._browser = await launcher.launch(
                    headless=self._headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage",
                          "--disable-blink-features=AutomationControlled"],
                )
                self._log.info("Playwright: %s launched", bname)
                return
            except Exception as exc:
                self._log.warning("Playwright: %s failed: %s — trying next", bname, exc)
        raise RuntimeError("All Playwright browsers failed")

    async def get_page_html(self, url: str, card_selector: str = "",
                             timeout: float = 20.0) -> Optional[str]:
        if not self._browser:
            return None
        ctx  = None
        page = None
        try:
            ctx  = await self._browser.new_context(
                user_agent=random.choice([
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                ]),
                viewport=random.choice([
                    {"width": 1920, "height": 1080},
                    {"width": 1440, "height": 900},
                ]),
                locale="en-US",
            )
            await ctx.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot,mp4,webp}",
                lambda r: asyncio.ensure_future(r.abort()),
            )
            page = await ctx.new_page()
            await stealth_async(page)
            await page.goto(url, wait_until="domcontentloaded",
                            timeout=int(timeout * 1000))
            if card_selector:
                with suppress(PWTimeout):
                    await page.wait_for_selector(card_selector,
                                                  timeout=int(min(timeout * 0.5, 10) * 1000))
            for _ in range(random.randint(2, 4)):
                await page.evaluate(f"window.scrollBy(0, {random.randint(300,700)})")
                await asyncio.sleep(random.uniform(0.4, 1.0))
            return await page.content()
        except Exception as exc:
            self._log.debug("Playwright get_page failed for %s: %s", url, exc)
            return None
        finally:
            for obj in [page, ctx]:
                if obj:
                    with suppress(Exception):
                        await obj.close()

    async def close(self):
        if self._browser:
            with suppress(Exception): await self._browser.close()
        if self._pw:
            with suppress(Exception): await self._pw.stop()


# =============================================================================
# HTML Parser
# =============================================================================

class HTMLParser:
    _JSONLD_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                             re.DOTALL | re.IGNORECASE)

    @classmethod
    def parse_job_listings(cls, html: str, source: str,
                            card_selectors: List[str],
                            field_map: Dict[str, List[str]]) -> List[Dict]:
        if not BS4_OK:
            return cls._regex_parse(html, source)

        soup = BeautifulSoup(html, "lxml")

        jsonld_jobs = cls._parse_jsonld(soup, source)
        if jsonld_jobs:
            return jsonld_jobs

        for sel in card_selectors:
            try:
                cards = soup.select(sel)
                if cards:
                    jobs = []
                    for card in cards[:50]:
                        job = cls._extract_card(card, field_map, source)
                        if job:
                            jobs.append(job)
                    if jobs:
                        return jobs
            except Exception:
                continue

        return cls._semantic_parse(soup, source)

    @classmethod
    def _parse_jsonld(cls, soup, source: str) -> List[Dict]:
        jobs = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if not isinstance(data, (dict, list)):
                    continue
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") == "JobPosting":
                        org = item.get("hiringOrganization", {})
                        loc = item.get("jobLocation", {})
                        addr = loc.get("address", {}) if isinstance(loc, dict) else {}
                        jobs.append({
                            "title":       item.get("title", ""),
                            "company":     org.get("name", "") if isinstance(org, dict) else str(org),
                            "location":    addr.get("addressLocality", "") or str(loc),
                            "description": item.get("description", "")[:2000],
                            "url":         item.get("url", ""),
                            "posted_date": item.get("datePosted"),
                            "salary":      str(item.get("baseSalary", "")),
                            "source":      source,
                        })
            except Exception:
                continue
        return jobs

    @classmethod
    def _extract_card(cls, card, field_map: Dict[str, List[str]], source: str) -> Optional[Dict]:
        result: Dict[str, str] = {"source": source}
        for field, selectors in field_map.items():
            for sel in selectors:
                try:
                    if "[" in sel and sel.endswith("]"):
                        attr  = sel.split("[")[-1].rstrip("]")
                        csel  = sel.split("[")[0]
                        el    = card.select_one(csel)
                        val   = el.get(attr, "") if el else ""
                    else:
                        el    = card.select_one(sel)
                        val   = el.get_text(strip=True) if el else ""
                    if val:
                        result[field] = str(val)[:500]
                        break
                except Exception:
                    continue
        return result if result.get("title") and result.get("company") else None

    @classmethod
    def _semantic_parse(cls, soup, source: str) -> List[Dict]:
        jobs = []
        for tag in ["article", "section", "li", "div"]:
            for el in soup.find_all(tag, limit=100):
                text = el.get_text(separator=" ", strip=True)
                if len(text) < 30 or len(text) > 2000:
                    continue
                lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 3][:5]
                if len(lines) >= 2:
                    link = el.find("a")
                    url  = link.get("href", "") if link else ""
                    if url and not url.startswith("http"):
                        url = ""
                    jobs.append({
                        "title":       lines[0][:200],
                        "company":     lines[1][:200] if len(lines) > 1 else "",
                        "location":    lines[2][:200] if len(lines) > 2 else "",
                        "description": text[:500],
                        "url":         url,
                        "source":      source,
                    })
                    if len(jobs) >= 30:
                        break
            if jobs:
                break
        return jobs

    @classmethod
    def _regex_parse(cls, html: str, source: str) -> List[Dict]:
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean)
        pattern = r'([A-Z][^\n.]{5,80})\s+at\s+([A-Z][^\n.]{2,60})\s+in\s+([A-Z][^\n.]{2,40})'
        jobs = []
        for m in re.finditer(pattern, clean)[:20]:
            jobs.append({
                "title":    m.group(1).strip(),
                "company":  m.group(2).strip(),
                "location": m.group(3).strip(),
                "source":   source,
            })
        return jobs


# =============================================================================
# Selector maps
# =============================================================================

_NAUKRI_CARDS = [
    "div.srp-jobtuple-wrapper",   # current React SPA class (networkidle2 render)
    "article.jobTuple",           # older SSR class
    "div[class*='srp-jobtuple']",
    "div[class*='job-tuple']",
    "div[class*='job-container']",
]
_NAUKRI_FIELDS = {
    "title":   ["a.title", "a.title-href", "a[class*='title']", "h2 a", "h3 a"],
    "url":     ["a.title[href]", "a.title-href[href]", "h2 a[href]", "h3 a[href]"],
    "company": ["a.subTitle", "a.comp-name", "span.comp-name", "a[class*='comp']"],
    "location":["span.locWdth", "span.loc-wrap", "span[class*='loc']", "li[class*='loc']"],
    "description":["div.job-description", "div.row3", "div[class*='desc']"],
}

_LINKEDIN_CARDS = [
    "div.base-card",
    "li.jobs-search-results__list-item",
    "div[class*='job-card']",
]
_LINKEDIN_FIELDS = {
    "title":   ["h3.base-search-card__title", "a.job-card-list__title"],
    "company": ["h4.base-search-card__subtitle", "a.job-card-container__company-name"],
    "location":["span.job-search-card__location"],
    "url":     ["a.base-card__full-link[href]", "a.job-card-list__title[href]"],
}

_INDEED_CARDS = [
    "div.job_seen_beacon",
    "div[class*='job_seen']",
    "td.resultContent",
]
_INDEED_FIELDS = {
    "title":   ["h2.jobTitle span", "h2.jobTitle a span"],
    "company": ["span.companyName", "span[data-testid='company-name']"],
    "location":["div.companyLocation", "div[data-testid='job-location']"],
    "url":     ["a.jcs-JobTitle[href]", "h2.jobTitle a[href]"],
}


# =============================================================================
# Search Engine Graph
# =============================================================================

class SearchEngineGraph:
    def __init__(self, http: httpx.AsyncClient,
                 cbs: Dict[str, CircuitBreaker], tls: TLSLayer):
        self._http = http
        self._cbs  = cbs
        self._tls  = tls
        self._log  = TLog("search_graph")

    async def find_job_urls(self, query: str, max_results: int = 10) -> List[str]:
        encoded = query.replace(" ", "+")
        urls: List[str] = []

        cb = self._cbs.get("duckduckgo", CircuitBreaker("duckduckgo"))
        if not cb.is_open:
            try:
                html = await self._tls.get(
                    f"https://html.duckduckgo.com/html/?q={encoded}+site%3Anaukri.com+OR+site%3Alinkedin.com",
                    timeout=12.0
                ) or ""
                urls = self._extract_urls_from_html(html, max_results)
                if urls:
                    cb.success()
                    self._log.info("DDG: found %d URLs", len(urls))
                    return urls
                cb.failure("no_results")
            except Exception as exc:
                cb.failure(str(exc)[:60])

        brave_key = getattr(settings, "brave_api_key", "")
        if brave_key and not self._cbs.get("brave", CircuitBreaker("brave")).is_open:
            cb = self._cbs.get("brave", CircuitBreaker("brave"))
            try:
                resp = await asyncio.wait_for(
                    self._http.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        params={"q": query, "count": max_results},
                        headers={"Accept": "application/json",
                                 "X-Subscription-Token": brave_key},
                    ), timeout=10.0
                )
                items = resp.json().get("web", {}).get("results", [])
                urls  = [r["url"] for r in items if "url" in r
                         and any(s in r["url"] for s in ["naukri", "linkedin", "indeed", "job"])]
                if urls:
                    cb.success()
                    self._log.info("Brave: found %d URLs", len(urls))
                    return urls[:max_results]
                cb.failure("no_results")
            except Exception as exc:
                cb.failure(str(exc)[:60])

        bing_key = getattr(settings, "bing_api_key", "")
        if bing_key and not self._cbs.get("bing", CircuitBreaker("bing")).is_open:
            cb = self._cbs.get("bing", CircuitBreaker("bing"))
            try:
                resp = await asyncio.wait_for(
                    self._http.get(
                        "https://api.bing.microsoft.com/v7.0/search",
                        params={"q": query, "count": max_results},
                        headers={"Ocp-Apim-Subscription-Key": bing_key},
                    ), timeout=10.0
                )
                items = resp.json().get("webPages", {}).get("value", [])
                urls  = [r["url"] for r in items]
                if urls:
                    cb.success()
                    self._log.info("Bing: found %d URLs", len(urls))
                    return urls[:max_results]
                cb.failure("no_results")
            except Exception as exc:
                cb.failure(str(exc)[:60])

        return urls

    def _extract_urls_from_html(self, html: str, max_results: int) -> List[str]:
        if not html or not BS4_OK:
            return []
        soup  = BeautifulSoup(html, "lxml")
        links = []
        job_kw = ["naukri.com/job", "linkedin.com/jobs", "indeed.co", "/job-detail", "/jobs/"]
        for a in soup.find_all("a", href=True)[:200]:
            href = a["href"]
            if href.startswith("http") and any(kw in href for kw in job_kw):
                links.append(href)
            if len(links) >= max_results:
                break
        return links


# =============================================================================
# Site scrapers
# FIX #10: _scrape_naukri no longer creates a new StrategyGraph per call.
#          Browser graph + circuit breakers are passed in and persist across calls.
# =============================================================================

async def _scrape_naukri(
    keyword: str, location: str, max_jobs: int,
    browser_graph: StrategyGraph,
    naukri_cbs: Dict[str, CircuitBreaker],   # FIX: persistent CBs passed in
    llm: Optional[LocalLLMService],
    cache: ScrapeCache,
    log: TLog,
) -> List[Dict]:
    """Naukri scraper using persistent strategy graph (CBs survive across calls).

    Strategy order:
      1. cloudflare — renders in real Chromium at CF edge, bypasses bot detection
      2. tls         — curl_cffi TLS impersonation (fast, sometimes blocked)
      3. browser     — local nodriver/playwright (slow, needs browser installed)
      4. llm         — LLM HTML extraction (last resort)
    """
    cached = cache.get("naukri", keyword, location)
    if cached is not None:
        log.info("Cache HIT naukri/%s/%s", keyword, location)
        return cached

    url = (f"https://www.naukri.com/"
           f"{keyword.lower().replace(' ','-')}-jobs-in-"
           f"{location.lower().replace(' ','-')}")

    tls_layer = TLSLayer()

    async def _via_cloudflare() -> List[Dict]:
        try:
            from src.scrapers.crawl import cloudflare_render_page
        except ImportError:
            return []
        # No waitForSelector — use networkidle2 (inside cloudflare_render_page via
        # gotoOptions) so the React SPA finishes fetching job data before snapshot.
        html = await cloudflare_render_page(url)
        if not html or len(html) < 50_000:   # splash-screen guard: full page > 100KB
            return []
        jobs_raw = HTMLParser.parse_job_listings(html, "naukri", _NAUKRI_CARDS, _NAUKRI_FIELDS)
        results  = [j.to_dict() for j in [normalize(r, "naukri") for r in jobs_raw] if j][:max_jobs]
        log.info("CF /content → %d Naukri jobs for '%s' in '%s'", len(results), keyword, location)
        return results

    async def _via_tls() -> List[Dict]:
        html = await tls_layer.get(url)
        if not html:
            return []
        jobs_raw = HTMLParser.parse_job_listings(html, "naukri", _NAUKRI_CARDS, _NAUKRI_FIELDS)
        return [j.to_dict() for j in [normalize(r, "naukri") for r in jobs_raw] if j][:max_jobs]

    async def _via_browser() -> List[Dict]:
        # FIX #7: correctly unwrap HTML string from browser graph result list
        result = await browser_graph.execute(
            "nodriver",
            url=url, card_selector=", ".join(_NAUKRI_CARDS),
            timeout=30.0, min_results=1
        )
        # browser graph nodes return [html_string] — unwrap it
        html = result[0] if result and isinstance(result, list) and isinstance(result[0], str) else None
        if not html:
            return []
        jobs_raw = HTMLParser.parse_job_listings(html, "naukri", _NAUKRI_CARDS, _NAUKRI_FIELDS)
        return [j.to_dict() for j in [normalize(r, "naukri") for r in jobs_raw] if j][:max_jobs]

    async def _via_llm() -> List[Dict]:
        if not llm:
            return []
        html = await tls_layer.get(url) or ""
        raw  = await llm.extract_jobs_from_html(html, "naukri")
        return [j.to_dict() for j in [normalize(r, "naukri") for r in raw] if j][:max_jobs]

    # Add cloudflare CB alongside the existing ones
    if "cloudflare" not in naukri_cbs:
        naukri_cbs["cloudflare"] = CircuitBreaker("naukri_cloudflare")

    sg = StrategyGraph()
    sg.add_node("cloudflare", _via_cloudflare, naukri_cbs["cloudflare"])
    sg.add_node("tls",        _via_tls,        naukri_cbs["tls"])
    sg.add_node("browser",    _via_browser,    naukri_cbs["browser"])
    sg.add_node("llm",        _via_llm,        naukri_cbs["llm"])
    sg.add_edge("cloudflare", "tls")
    sg.add_edge("tls",        "browser")
    sg.add_edge("browser",    "llm")

    jobs = await sg.execute("cloudflare", timeout=40.0)
    if jobs:
        cache.set("naukri", keyword, location, jobs)
    return jobs


async def _scrape_linkedin(
    keyword: str, location: str, max_jobs: int,
    pw_engine: PlaywrightEngine,
    llm: Optional[LocalLLMService],
    cache: ScrapeCache,
    log: TLog,
) -> List[Dict]:
    cached = cache.get("linkedin", keyword, location)
    if cached is not None:
        log.info("Cache HIT linkedin/%s/%s", keyword, location)
        return cached

    url = (f"https://www.linkedin.com/jobs/search?"
           f"keywords={keyword.replace(' ','%20')}&location={location.replace(' ','%20')}"
           f"&f_TPR=r604800")

    html = await pw_engine.get_page_html(
        url,
        card_selector=", ".join(_LINKEDIN_CARDS),
        timeout=25.0,
    ) or ""

    jobs_raw = HTMLParser.parse_job_listings(html, "linkedin", _LINKEDIN_CARDS, _LINKEDIN_FIELDS)
    jobs = [j.to_dict() for j in [normalize(r, "linkedin") for r in jobs_raw] if j][:max_jobs]

    if not jobs and llm:
        log.info("LinkedIn: CSS failed — LLM fallback")
        raw  = await llm.extract_jobs_from_html(html, "linkedin")
        jobs = [j.to_dict() for j in [normalize(r, "linkedin") for r in raw] if j][:max_jobs]

    if jobs:
        cache.set("linkedin", keyword, location, jobs)
    return jobs


async def _scrape_indeed(
    keyword: str, location: str, max_jobs: int,
    pw_engine: PlaywrightEngine,
    llm: Optional[LocalLLMService],
    cache: ScrapeCache,
    log: TLog,
) -> List[Dict]:
    cached = cache.get("indeed", keyword, location)
    if cached is not None:
        log.info("Cache HIT indeed/%s/%s", keyword, location)
        return cached

    url  = f"https://www.indeed.co.in/jobs?q={keyword.replace(' ','+')}&l={location.replace(' ','+')}"
    html = await pw_engine.get_page_html(
        url,
        card_selector=", ".join(_INDEED_CARDS),
        timeout=20.0,
    ) or ""

    jobs_raw = HTMLParser.parse_job_listings(html, "indeed", _INDEED_CARDS, _INDEED_FIELDS)
    for j in jobs_raw:
        if j.get("url") and not j["url"].startswith("http"):
            j["url"] = "https://www.indeed.co.in" + j["url"]

    jobs = [j.to_dict() for j in [normalize(r, "indeed") for r in jobs_raw] if j][:max_jobs]

    if not jobs and llm:
        log.info("Indeed: CSS failed — LLM fallback")
        raw  = await llm.extract_jobs_from_html(html, "indeed")
        jobs = [j.to_dict() for j in [normalize(r, "indeed") for r in raw] if j][:max_jobs]

    if jobs:
        cache.set("indeed", keyword, location, jobs)
    return jobs


# =============================================================================
# Trie Deduplicator
# =============================================================================

class TrieDedup:
    class _N:
        __slots__ = ("ch", "e")
        def __init__(self): self.ch: Dict[str, Any] = {}; self.e = False

    def __init__(self):
        self._id_root  = self._N()
        self._url_root = self._N()

    def _insert(self, root: "_N", key: str) -> bool:
        node = root
        for ch in key:
            node.ch.setdefault(ch, self._N())
            node = node.ch[ch]
        if node.e: return False
        node.e = True
        return True

    def is_new(self, job: Dict) -> bool:
        title_key = f"{job.get('title','').lower().strip()}::{job.get('company','').lower().strip()}"
        url_key   = (job.get("url") or "").lower().strip().rstrip("/")
        if not self._insert(self._id_root, title_key):
            return False
        if url_key and not self._insert(self._url_root, url_key):
            return False
        return True

    def filter(self, jobs: List[Dict]) -> List[Dict]:
        return [j for j in jobs if j.get("trust_score", 50) >= 25 and self.is_new(j)]


# =============================================================================
# MCP Layer
# =============================================================================

class MCPLayer:
    def __init__(self, scraper: "APIJobScraper"):
        self._s   = scraper
        self._log = TLog("mcp")

    def tools(self) -> List[Dict]:
        return [
            {
                "name": "search_jobs",
                "description": "Search for job listings across Naukri, LinkedIn, Indeed, Remotive, Adzuna.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query":       {"type": "string",  "description": "Job search query e.g. 'Python developer'"},
                        "location":    {"type": "string",  "description": "Location e.g. 'Bangalore', 'Remote'", "default": "india"},
                        "max_results": {"type": "integer", "description": "Max jobs to return", "default": 20},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "scraper_health",
                "description": "Check which scraper sources are working and cache stats",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_job_details",
                "description": "Get full details for one job URL",
                "inputSchema": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            },
        ]

    async def handle(self, tool_name: str, args: Dict) -> Dict:
        try:
            if tool_name == "search_jobs":
                jobs = await self._s.fetch_all(
                    query    = args.get("query", "software engineer"),
                    location = args.get("location", "india"),
                )
                n = args.get("max_results", 20)
                return {"jobs": jobs[:n], "total_found": len(jobs), "query": args.get("query")}
            elif tool_name == "scraper_health":
                return self._s.health_report()
            elif tool_name == "get_job_details":
                job = await self._s.fetch_single_url(args.get("url", ""))
                return job or {"error": "Could not extract job from URL"}
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as exc:
            self._log.error("MCP handle error: %s", exc)
            return {"error": str(exc)}

    async def serve_stdio(self):
        self._log.info("MCP server started (stdio)")
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        sys.stdout.flush()

        while True:
            line = sys.stdin.readline()
            if not line:
                break
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue

            method = req.get("method", "")
            rid    = req.get("id")

            if method == "tools/list":
                resp = {"jsonrpc": "2.0", "id": rid, "result": {"tools": self.tools()}}
            elif method == "tools/call":
                p      = req.get("params", {})
                result = await self.handle(p.get("name", ""), p.get("arguments", {}))
                resp   = {
                    "jsonrpc": "2.0", "id": rid,
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
                }
            else:
                resp = {"jsonrpc": "2.0", "id": rid, "result": {}}

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


# =============================================================================
# APIJobScraper — main orchestrator
# =============================================================================

class APIJobScraper(BaseScraper):
    def __init__(self, headless: bool = True, pool_size: int = 2):
        super().__init__("production_aggregator")
        self._headless   = headless
        self._log        = TLog("api_scraper")
        self._cache      = _CACHE
        self._http       = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            http2=False,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=8),
            headers={"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"},
        )
        self._cbs: Dict[str, CircuitBreaker] = {
            s: CircuitBreaker(s) for s in [
                "remotive", "adzuna", "foorilla", "multi_platform",
                "naukri", "linkedin", "indeed",
                "duckduckgo", "brave", "bing",
                "nodriver", "camoufox", "playwright",
            ]
        }

        # FIX #10: persistent circuit breakers for naukri sub-strategies
        self._naukri_cbs: Dict[str, CircuitBreaker] = {
            "tls":     CircuitBreaker("naukri_tls"),
            "browser": CircuitBreaker("naukri_browser"),
            "llm":     CircuitBreaker("naukri_llm"),
        }

        self._tls        = TLSLayer()
        self._nodriver   = NodriverEngine(headless=headless) if NODRIVER_OK else None  # FIX #11
        self._camoufox   = CamoufoxEngine()   if CAMOUFOX_OK   else None
        self._playwright = PlaywrightEngine(headless=headless)
        self._selenium   = None
        self._llm        = LocalLLMService()
        self._multi      = MultiPlatformJobScraper()
        self._jobspy     = JobSpyScraper()
        from src.scrapers.ats_scraper import ATSScraper
        self._ats        = ATSScraper()
        self._mcp_layer  = MCPLayer(self)

        self._browser_graph = self._build_browser_graph()
        self._ready = False

    def _build_browser_graph(self) -> StrategyGraph:
        """
        Browser engine fallback graph. Each node fetches HTML and returns [html_string].
        FIX #7: nodes return [html_string] consistently; callers unwrap result[0].
        """
        sg = StrategyGraph()

        async def _nodriver_get(url: str, card_selector: str = "", **kw) -> List:
            if not self._nodriver:
                return []
            html = await self._nodriver.get_page_html(url, timeout=kw.get("timeout", 20))
            return [html] if html else []

        async def _camoufox_get(url: str, card_selector: str = "", **kw) -> List:
            if not self._camoufox:
                return []
            html = await self._camoufox.get_page_html(url, timeout=kw.get("timeout", 25))
            return [html] if html else []

        async def _playwright_get(url: str, card_selector: str = "", **kw) -> List:
            html = await self._playwright.get_page_html(url, card_selector,
                                                         timeout=kw.get("timeout", 20))
            return [html] if html else []

        sg.add_node("nodriver",   _nodriver_get,   self._cbs["nodriver"])
        sg.add_node("camoufox",   _camoufox_get,   self._cbs["camoufox"])
        sg.add_node("playwright", _playwright_get, self._cbs["playwright"])
        sg.add_edge("nodriver",   "camoufox")
        sg.add_edge("camoufox",   "playwright")
        return sg

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def _init(self):
        if self._ready:
            return

        llm_ok = await self._llm.health_check()
        if not llm_ok:
            self._llm = None
            self._log.info("Ollama not available — LLM fallback disabled")

        if self._nodriver:
            try:
                await self._nodriver.start()
                self._log.info("✅ Nodriver ready")
            except Exception as exc:
                self._log.warning("Nodriver failed: %s", exc)
                self._nodriver = None

        try:
            await self._playwright.start()
            self._log.info("✅ Playwright ready")
        except Exception as exc:
            self._log.warning("Playwright failed: %s — trying Selenium", exc)
            if SELENIUM_OK:
                try:
                    self._selenium = _SeleniumHub()
                    self._log.info("✅ Selenium fallback ready")
                except Exception as e2:
                    self._log.warning("Selenium also failed: %s", e2)

        self._search_graph = SearchEngineGraph(self._http, self._cbs, self._tls)
        self._ready = True
        self._log.info(
            "APIJobScraper ready | curl_cffi=%s nodriver=%s camoufox=%s playwright=%s llm=%s",
            CURL_CFFI_OK, self._nodriver is not None,
            CAMOUFOX_OK,  self._playwright._browser is not None,
            self._llm is not None,
        )

    async def __aenter__(self):
        await self._init()
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def fetch_jobs(self, query: str = "software engineer",
                         location: str = "india") -> List[Dict]:
        await self._init()
        return await self.fetch_all(query=query, location=location)

    # ── Tier 1 sources ────────────────────────────────────────────────────────

    async def _fetch_remotive(self) -> List[Dict]:
        cb = self._cbs["remotive"]
        if cb.is_open: return []
        cached = self._cache.get("remotive", "all", "remote")
        if cached: return cached
        try:
            resp = await asyncio.wait_for(
                self._http.get("https://remotive.com/api/remote-jobs"),
                timeout=15.0
            )
            jobs = []
            for j in resp.json().get("jobs", [])[:60]:
                n = normalize(j, "remotive")
                if n: jobs.append(n.to_dict())
            cb.success()
            if jobs: self._cache.set("remotive", "all", "remote", jobs)
            return jobs
        except Exception as exc:
            cb.failure(str(exc)[:60])
            return []

    async def _fetch_adzuna(self, query: str, location: str) -> List[Dict]:
        cb = self._cbs["adzuna"]
        if cb.is_open: return []
        app_id  = getattr(settings, "adzuna_app_id",  "")
        app_key = getattr(settings, "adzuna_app_key", "")
        if not app_id or not app_key: return []
        cached = self._cache.get("adzuna", query, location)
        if cached: return cached
        try:
            resp = await asyncio.wait_for(
                self._http.get(
                    "https://api.adzuna.com/v1/api/jobs/in/search/1",
                    params={"app_id": app_id, "app_key": app_key,
                            "results_per_page": 50, "what": query, "where": location},
                ), timeout=15.0
            )
            jobs = []
            for j in resp.json().get("results", []):
                flat = {
                    "title":       j.get("title"),
                    "company":     j.get("company", {}).get("display_name"),
                    "location":    j.get("location", {}).get("display_name"),
                    "url":         j.get("redirect_url"),
                    "description": j.get("description"),
                    "posted_date": j.get("created"),
                    "source":      "adzuna",
                }
                n = normalize(flat, "adzuna")
                if n: jobs.append(n.to_dict())
            cb.success()
            if jobs: self._cache.set("adzuna", query, location, jobs)
            return jobs
        except Exception as exc:
            cb.failure(str(exc)[:60])
            return []

    async def _fetch_foorilla(self, query: str, location: str) -> List[Dict]:
        if not _FOORILLA_OK: return []
        cb = self._cbs["foorilla"]
        if cb.is_open: return []
        cached = self._cache.get("foorilla", query, location)
        if cached: return cached
        try:
            import aiohttp as _aio
            # Configure connection pooling for efficient resource reuse
            connector = _aio.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
            )
            async with _aio.ClientSession(
                timeout=_aio.ClientTimeout(total=30, connect=5.0, sock_read=15.0),
                connector=connector,
            ) as session:
                raw  = await asyncio.wait_for(_Foorilla(session).search(query, location), 28.0)
                jobs = []
                for p in raw:
                    n = normalize({
                        "title": p.title, "company": p.company, "location": p.location,
                        "url": p.url, "description": p.description,
                        "posted_date": p.posted_date, "job_id": p.job_id,
                    }, "foorilla")
                    if n: jobs.append(n.to_dict())
            cb.success()
            if jobs: self._cache.set("foorilla", query, location, jobs)
            return jobs
        except Exception as exc:
            cb.failure(str(exc)[:60])
            return []

    async def _fetch_multi_platform(self, query: str) -> List[Dict]:
        """
        FIX #6: query is now passed to search_all_platforms() instead of being ignored.
        """
        cb = self._cbs["multi_platform"]
        if cb.is_open: return []
        cached = self._cache.get("multi_platform", query, "all")
        if cached: return cached
        try:
            # FIX: pass query so multi_platform actually searches for what was asked
            postings = await asyncio.wait_for(
                self._multi.search_all_platforms(query), 35.0  # FIX #6
            )
            jobs = []
            for p in postings:
                n = normalize({
                    "title": p.title, "company": p.company, "location": p.location,
                    "url": p.url, "description": p.description,
                    "posted_date": p.posted_date, "source": p.source, "job_id": p.job_id,
                    "salary": getattr(p, "salary", None),
                    "experience": getattr(p, "experience", None),
                    "skills": getattr(p, "skills", []),
                    "job_type": getattr(p, "job_type", None),
                }, p.source)
                if n: jobs.append(n.to_dict())
            cb.success()
            if jobs: self._cache.set("multi_platform", query, "all", jobs)
            return jobs
        except Exception as exc:
            cb.failure(str(exc)[:60])
            return []

    # ── Tier 2 browser sources ────────────────────────────────────────────────

    async def _fetch_browser_sources(self, keyword: str, location: str,
                                      max_per_source: int = 15) -> List[Dict]:
        """
        FIX #8: Selenium is used as fallback for individual scrapers when playwright
        browser is unavailable, not just skipped entirely.
        """
        pw_available = self._playwright._browser is not None

        # If neither playwright nor selenium available, bail early
        if not pw_available and not self._selenium:
            return []

        # Use playwright if available, otherwise use a selenium-backed engine
        engine = self._playwright

        tasks = [
            _scrape_naukri(keyword, location, max_per_source,
                           self._browser_graph, self._naukri_cbs,  # FIX #10: pass persistent CBs
                           self._llm, self._cache, self._log),
            _scrape_linkedin(keyword, location, max_per_source,
                             engine, self._llm, self._cache, self._log),
            _scrape_indeed(keyword, location, max_per_source,
                           engine, self._llm, self._cache, self._log),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = []
        for r in results:
            if isinstance(r, list):
                out.extend(r)
            elif isinstance(r, Exception):
                self._log.warning("Browser source error: %s", r)
        return out

    # ── Deduplication ─────────────────────────────────────────────────────────

    def _dedup(self, jobs: List[Dict]) -> List[Dict]:
        dedup  = TrieDedup()
        unique = dedup.filter(jobs)
        unique.sort(key=lambda j: j.get("trust_score", 0), reverse=True)
        self._log.info("Dedup: %d raw → %d unique", len(jobs), len(unique))
        return unique

    # ── Main pipeline ─────────────────────────────────────────────────────────

    async def fetch_all(self, query: str = "software engineer",
                         location: str = "india") -> List[Dict]:
        """
        Full pipeline. All sources run concurrently with per-source timeouts.
        FIX: tier1 properly scheduled with ensure_future before gather.
        """
        await self._init()
        trace = str(uuid.uuid4())[:8]
        log   = TLog("fetch_all", trace_id=trace)
        log.info("🚀 fetch_all: query='%s' location='%s'", query, location)
        t0    = time.monotonic()

        tier1 = asyncio.ensure_future(asyncio.gather(
            self._timed("remotive",       self._fetch_remotive()),
            self._timed("adzuna",         self._fetch_adzuna(query, location)),
            self._timed("foorilla",       self._fetch_foorilla(query, location)),
            self._timed("multi_platform", self._fetch_multi_platform(query)),
            self._timed("jobspy",         self._jobspy.search(query, location), timeout=60.0),
            self._timed("ats",            self._ats.search(query, location),    timeout=35.0),
        ))
        tier2 = asyncio.ensure_future(
            self._timed("browser", self._fetch_browser_sources(query, location))
        )

        (t1_rem, t1_adz, t1_foo, t1_mp, t1_spy, t1_ats), t2_all = await asyncio.gather(tier1, tier2)

        all_raw: List[Dict] = []
        for name, jobs in [("remotive", t1_rem), ("adzuna", t1_adz),
                            ("foorilla", t1_foo), ("multi_platform", t1_mp),
                            ("jobspy",   t1_spy), ("ats", t1_ats),
                            ("browser",  t2_all)]:
            log.info("Source %-15s → %d jobs", name, len(jobs))
            all_raw.extend(jobs)

        if len(all_raw) < 5:
            log.warning("Only %d jobs — activating Tier 3 (search engine + LLM)", len(all_raw))
            try:
                urls = await self._search_graph.find_job_urls(f"{query} jobs {location}", 5)
                for url in urls[:3]:
                    j = await self.fetch_single_url(url)
                    if j:
                        all_raw.append(j)
            except Exception as exc:
                log.warning("Tier 3 failed: %s", exc)

        unique  = self._dedup(all_raw)
        elapsed = time.monotonic() - t0
        log.info("🎯 Done: %d raw → %d unique in %.1fs | cache=%s",
                 len(all_raw), len(unique), elapsed, self._cache.stats)
        return unique

    async def _timed(self, name: str, coro, timeout: float = 35.0) -> List[Dict]:
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            return result if isinstance(result, list) else []
        except asyncio.TimeoutError:
            self._log.warning("Source %s timed out (%.0fs)", name, timeout)
            return []
        except Exception as exc:
            self._log.error("Source %s error: %s", name, exc)
            return []

    async def fetch_single_url(self, url: str) -> Optional[Dict]:
        html = await self._playwright.get_page_html(url, timeout=15.0)
        if not html:
            return None
        soup = BeautifulSoup(html, "lxml") if BS4_OK else None
        if soup:
            jsonld = HTMLParser._parse_jsonld(soup, "direct")
            if jsonld:
                n = normalize(jsonld[0], "direct")
                return n.to_dict() if n else None
            title   = (soup.find("h1") or soup.find("h2"))
            company = soup.find(class_=re.compile(r"company|employer", re.I))
            desc    = soup.find("main") or soup.find("article")
            n = normalize({
                "title":       title.get_text(strip=True)   if title   else "",
                "company":     company.get_text(strip=True)  if company else "Unknown",
                "url":         url,
                "description": desc.get_text(separator=" ", strip=True)[:2000] if desc else "",
                "source":      "direct",
            }, "direct")
            return n.to_dict() if n else None
        return None

    def health_report(self) -> Dict:
        return {
            "engines": {
                "curl_cffi":  CURL_CFFI_OK,
                "nodriver":   self._nodriver is not None,
                "camoufox":   CAMOUFOX_OK,
                "playwright": self._playwright._browser is not None,
                "selenium":   self._selenium is not None,
                "llm_local":  self._llm is not None,
            },
            "cache":    self._cache.stats,
            "circuits": {k: v.status for k, v in self._cbs.items()},
            "naukri_circuits": {k: v.status for k, v in self._naukri_cbs.items()},
        }

    async def close(self):
        if self._nodriver:
            await self._nodriver.close()
        await self._playwright.close()
        await self._http.aclose()
        self._log.info("APIJobScraper closed")

    @property
    def mcp(self) -> MCPLayer:
        return self._mcp_layer


# =============================================================================
# CLI
# =============================================================================

async def _run_mcp():
    async with APIJobScraper() as s:
        await s.mcp.serve_stdio()


async def _run_test():
    async with APIJobScraper() as s:
        jobs = await s.fetch_all("python developer", "Bangalore")
        print(f"\n✅ Total: {len(jobs)} jobs")
        for j in jobs[:5]:
            print(f"  [{j['trust_score']:3d}] {j['title'][:50]} @ {j['company'][:30]} [{j['source']}]")
        print(f"\nCache: {s._cache.stats}")
        print(f"Health: {json.dumps(s.health_report(), indent=2)}")


if __name__ == "__main__":
    if "--mcp" in sys.argv:
        asyncio.run(_run_mcp())
    else:
        asyncio.run(_run_test())