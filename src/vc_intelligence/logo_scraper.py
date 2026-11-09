"""Scrape a logo URL for every company in the founder datasets -> data/company_logos.json.

    python -m src.vc_intelligence.logo_scraper            # new domains only (resumable)
    python -m src.vc_intelligence.logo_scraper --refresh  # re-check every domain
    python -m src.vc_intelligence.logo_scraper --limit 50

The company list is exactly what `founders-import` loads: the importer is run against a
throwaway in-memory database and its domains are read back, so every imported company is
covered. For each domain the homepage is fetched and the best logo candidate is picked:

  1. JSON-LD Organization/Corporation "logo"
  2. <link rel="apple-touch-icon"> (largest declared size)
  3. <link rel="icon"> (SVG, else largest declared size)
  4. <meta property="og:image">  (often a social banner, so last)

Each candidate must answer 200 with an image content type before it is accepted. Domains
with no usable candidate fall back to Google's favicon service (source "google_favicon").
Results are keyed by domain and saved after every batch, so an interrupted run resumes.
The importer copies them into portfolio_companies.logo_url; the API returns them as `logo`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parents[2]
LOGOS_FILE = REPO / "data" / "company_logos.json"
USER_AGENT = "JobifyBot/1.0 (+https://github.com/devnoid1/Jobify)"
CONCURRENCY = 16
TIMEOUT = 12.0
BATCH = 100


@dataclass(frozen=True, slots=True)
class Candidate:
    url: str
    source: str
    rank: int      # lower is better
    size: int = 0  # declared pixel size, larger is better within a rank


def google_favicon(domain: str) -> str:
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"


def _largest(sizes: str | None) -> int:
    if not sizes:
        return 0
    if sizes.strip().lower() == "any":
        return 10_000  # scalable (SVG)
    nums = [int(n) for n in re.findall(r"(\d+)x\d+", sizes)]
    return max(nums, default=0)


def _jsonld_logos(soup: BeautifulSoup) -> list[str]:
    out: list[str] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        stack: list[Any] = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                logo = node.get("logo")
                if isinstance(logo, str):
                    out.append(logo)
                elif isinstance(logo, dict) and isinstance(logo.get("url"), str):
                    out.append(logo["url"])
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
    return out


def extract_candidates(html: str, base_url: str) -> list[Candidate]:
    """All logo candidates found in a homepage, best first."""
    soup = BeautifulSoup(html, "lxml")
    found: list[Candidate] = [Candidate(urljoin(base_url, u), "jsonld", 1) for u in _jsonld_logos(soup)]
    for link in soup.find_all("link", href=True):
        rels = {r.lower() for r in (link.get("rel") or [])}
        href = urljoin(base_url, link["href"])
        size = _largest(link.get("sizes"))
        if rels & {"apple-touch-icon", "apple-touch-icon-precomposed"}:
            found.append(Candidate(href, "apple_touch_icon", 2, size or 180))
        elif "icon" in rels:
            is_svg = href.lower().split("?")[0].endswith(".svg") or "svg" in (link.get("type") or "")
            found.append(Candidate(href, "icon", 3, 10_000 if is_svg else size))
    for meta in soup.find_all("meta", content=True):
        if (meta.get("property") or meta.get("name") or "").lower() in ("og:image", "og:image:url"):
            found.append(Candidate(urljoin(base_url, meta["content"]), "og_image", 4))
    seen: set[str] = set()
    unique = [c for c in found if c.url.startswith(("http://", "https://")) and not (c.url in seen or seen.add(c.url))]
    return sorted(unique, key=lambda c: (c.rank, -c.size))


async def _is_image(client: httpx.AsyncClient, url: str) -> bool:
    try:
        async with client.stream("GET", url) as res:
            if res.status_code != 200:
                return False
            kind = res.headers.get("content-type", "").lower()
            if kind.startswith("image/"):
                return True
            # Some servers mislabel icons; sniff the first bytes.
            head = b""
            async for chunk in res.aiter_bytes():
                head += chunk
                if len(head) >= 64:
                    break
            return head.startswith((b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"\x00\x00\x01\x00", b"RIFF")) \
                or b"<svg" in head[:64].lower()
    except (httpx.HTTPError, ValueError):
        return False


async def find_logo(client: httpx.AsyncClient, domain: str) -> dict[str, str]:
    """Best verified logo for one domain (falls back to Google's favicon service)."""
    for scheme_host in (f"https://{domain}", f"https://www.{domain}"):
        try:
            res = await client.get(scheme_host)
        except (httpx.HTTPError, ValueError):
            continue
        if res.status_code >= 400 or "html" not in res.headers.get("content-type", "").lower():
            continue
        for cand in extract_candidates(res.text, str(res.url)):
            if await _is_image(client, cand.url):
                return {"logo_url": cand.url, "source": cand.source}
        # Conventional location when the page declares nothing usable.
        fallback = urljoin(str(res.url), "/apple-touch-icon.png")
        if await _is_image(client, fallback):
            return {"logo_url": fallback, "source": "apple_touch_icon"}
        break
    return {"logo_url": google_favicon(domain), "source": "google_favicon"}


def collect_domains() -> list[str]:
    """Every company domain the founder importer loads, read from a throwaway database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from src.model_registry import load_all_models
    from src.models import Base, PortfolioCompany
    from src.vc_intelligence.import_founder_data import run_import

    load_all_models()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        run_import(db)
        domains = {d.lower() for (d,) in db.query(PortfolioCompany.domain) if d}
    engine.dispose()
    return sorted(domains)


def load_logos(path: Path = LOGOS_FILE) -> dict[str, dict[str, str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_logos(logos: dict[str, dict[str, str]], path: Path = LOGOS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(logos.items())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)  # atomic: an interrupted run never leaves a half-written file


async def scrape(domains: list[str], logos: dict[str, dict[str, str]], path: Path = LOGOS_FILE) -> dict[str, int]:
    sem = asyncio.Semaphore(CONCURRENCY)
    stats: dict[str, int] = {}
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True,
                                 headers={"User-Agent": USER_AGENT, "Accept": "text/html,image/*;q=0.9,*/*;q=0.8"}) as client:

        async def one(domain: str) -> None:
            async with sem:
                result = await find_logo(client, domain)
            result["checked_at"] = datetime.now(tz=UTC).date().isoformat()
            logos[domain] = result
            stats[result["source"]] = stats.get(result["source"], 0) + 1

        for start in range(0, len(domains), BATCH):
            await asyncio.gather(*(one(d) for d in domains[start:start + BATCH]))
            save_logos(logos, path)
            log.info("logos: %d/%d domains done %s", min(start + BATCH, len(domains)), len(domains), stats)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m src.vc_intelligence.logo_scraper")
    ap.add_argument("--refresh", action="store_true", help="re-check domains already in the file")
    ap.add_argument("--limit", type=int, default=0, help="only the first N pending domains")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logos = load_logos()
    domains = collect_domains()
    pending = domains if args.refresh else [d for d in domains if d not in logos]
    if args.limit:
        pending = pending[: args.limit]
    print(f"{len(domains)} company domains; {len(pending)} to scrape; {len(logos)} already in {LOGOS_FILE.name}")
    stats = asyncio.run(scrape(pending, logos))
    print(f"done: {stats}; {len(logos)} logos in {LOGOS_FILE}")


if __name__ == "__main__":
    main()
