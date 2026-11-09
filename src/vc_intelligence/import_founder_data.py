"""
import_founder_data.py — load every founder/startup dataset in the repo into the Founders tables.

Sources (all already in the repo):
  1. src/vc_intelligence/data/vc_100_firms.json            100 VC firms
  2. src/vc_intelligence/batch_data_catalog.py             VC portfolio companies + founders (13 batches)
  3. src/vc_intelligence/enrich_50_founders.py             VC portfolio companies + founders
  4. data/startups_{100,200,100_more}_founders.json         startups.gallery founders (placeholders skipped)
  5. data/startups_gallery_companies.json                  startups.gallery companies (location, funding, jobs)
  6. src/*_startups.py, *_registry.py, *_companies.py       company registries (Shark Tank, Indian apps, ...)

Rules:
  - Companies are de-duplicated by domain across all sources; later sources only fill blanks.
  - Placeholder "founders" (e.g. "Acme Founder" / founder@acme.com / LinkedIn company pages) are skipped.
  - Every scraped email is a guess (first@ / first.last@domain), so email_verified=False and
    email_confidence reflects that; the UI labels them "Likely email (unverified)".
  - Idempotent: re-running updates rows instead of duplicating them.

Run: python -m src.cli founders-import
"""

from __future__ import annotations

import importlib
import io
import json
import logging
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from src.models import CompanyFounder, PortfolioCompany, VCFirm, fit_to_columns

log = logging.getLogger("vc_intelligence.import")
REPO = Path(__file__).resolve().parents[2]

GENERIC_LOCAL_PARTS = {"founder", "founders", "hello", "hi", "contact", "info", "team", "support", "admin",
                       "careers", "jobs", "press", "sales", "office"}
REGISTRIES = [  # (module, variable, source firm name)
    ("src.company_sources.registries.shark_tank_india_startups", "SHARK_TANK_INDIA_REGISTRY", "Shark Tank India"),
    ("src.company_sources.registries.shark_tank_us_startups", "SHARK_TANK_US_REGISTRY", "Shark Tank US"),
    ("src.company_sources.registries.suniel_shetty_startups", "SUNIEL_SHETTY_STARTUPS_REGISTRY", "Suniel Shetty Portfolio"),
    ("src.company_sources.registries.accelerators_registry", "ACCELERATORS_REGISTRY", "Accelerator Portfolios"),
    ("src.company_sources.registries.indian_app_startups", "INDIAN_APP_STARTUPS", "Indian App Startups"),
    ("src.company_sources.registries.fintech_festival_companies", "FINTECH_FESTIVAL_REGISTRY", "Global Fintech Fest"),
]


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:255] or "company"


def _domain(raw: Optional[str]) -> Optional[str]:
    d = re.sub(r"^https?://", "", (raw or "").strip().lower()).split("/")[0]
    d = d[4:] if d.startswith("www.") else d
    return d or None


def is_placeholder(name: Optional[str], email: Optional[str], linkedin: Optional[str]) -> bool:
    n = (name or "").strip().lower()
    local = (email or "").lower().split("@")[0] if email and "@" in email else ""
    return (not n or n.endswith(" founder") or n in {"founder", "co-founder", "unknown", "ceo"}
            or local in GENERIC_LOCAL_PARTS or "/company/" in (linkedin or ""))


def email_confidence(name: str, email: Optional[str]) -> Optional[float]:
    """Pattern-built addresses (first@, first.last@, firstlast@) get a low score: they are guesses."""
    if not email or "@" not in email:
        return None
    parts = [p for p in re.sub(r"[^a-z\s]", "", (name or "").lower()).split() if p]
    local = email.split("@")[0].lower()
    patterns = {parts[0], f"{parts[0]}.{parts[-1]}", f"{parts[0]}{parts[-1]}", f"{parts[0][0]}{parts[-1]}"} if parts else set()
    return 0.3 if local in patterns else 0.5


def _clean_description(name: str, text: Optional[str]) -> str:
    t = (text or "").strip()
    t = re.sub(rf"^{re.escape(name)}\s*:\s*", "", t, flags=re.I)
    t = re.sub(r"\s*See [^.]*funding rounds, investors and open jobs\.?\s*$", "", t, flags=re.I)
    return t.strip()


def _twitter_handle(url: Optional[str]) -> Optional[str]:
    m = re.search(r"(?:x|twitter)\.com/(@?[A-Za-z0-9_]{1,30})", url or "")
    return m.group(1).lstrip("@") if m else None


class Importer:
    def __init__(self, db: Session):
        self.db = db
        self.firms: Dict[str, VCFirm] = {f.slug: f for f in db.query(VCFirm)}
        self.by_domain: Dict[str, PortfolioCompany] = {}
        self.by_firm_slug: Dict[tuple, PortfolioCompany] = {}
        for c in db.query(PortfolioCompany):
            self._index(c)
        # In-memory founder index: the session doesn't autoflush, so a query can't see founders
        # added earlier in this run (the same person often appears in several batches).
        self.founders: Dict[tuple, CompanyFounder] = {
            (f.company_id, f.full_name.strip().lower()): f for f in db.query(CompanyFounder)}
        from src.vc_intelligence.logo_scraper import load_logos

        self.logos = load_logos()  # domain -> {logo_url, source}; empty until the scraper has run
        self.stats = {"firms": 0, "companies_created": 0, "companies_updated": 0, "founders_created": 0,
                      "founders_updated": 0, "placeholders_skipped": 0}

    def _index(self, c: PortfolioCompany) -> None:
        if c.domain:
            self.by_domain[c.domain] = c
        self.by_firm_slug[(c.vc_firm_id, c.slug)] = c

    def firm(self, slug: str, name: str, **fields) -> VCFirm:
        f = self.firms.get(slug)
        if f is None:
            f = VCFirm(slug=slug, name=name, **{k: v for k, v in fields.items() if v})
            self.db.add(f)
            self.db.flush()
            self.firms[slug] = f
            self.stats["firms"] += 1
        else:
            for k, v in fields.items():
                if v and not getattr(f, k, None):
                    setattr(f, k, v)
        return f

    def company(self, firm: VCFirm, name: str, domain: Optional[str], **fields) -> PortfolioCompany:
        domain = _domain(domain)
        slug = _slugify(fields.pop("slug", None) or name)
        c = (self.by_domain.get(domain) if domain else None) or self.by_firm_slug.get((firm.id, slug))
        if c is None:
            c = PortfolioCompany(vc_firm_id=firm.id, name=name, slug=slug, domain=domain)
            self.db.add(c)
            self.db.flush()
            self._index(c)
            self.stats["companies_created"] += 1
        else:
            self.stats["companies_updated"] += 1
            if domain and not c.domain:
                c.domain = domain
                self._index(c)
        # Clip to column lengths (Postgres rejects over-long values; the source data is unchanged).
        fields = fit_to_columns(PortfolioCompany, fields)
        for k, v in fields.items():  # fill blanks only; first good value wins
            current = getattr(c, k, None)
            if v not in (None, "", [], "[]") and current in (None, "", "[]", "{}"):  # "[]" is a column default
                setattr(c, k, v)
        if c.domain and not c.logo_url:  # scraped by src/vc_intelligence/logo_scraper.py
            c.logo_url = (self.logos.get(c.domain.lower()) or {}).get("logo_url")
        return c

    def founder(self, company: PortfolioCompany, name: str, title: Optional[str], email: Optional[str],
                linkedin: Optional[str], source: str, twitter: Optional[str] = None, bio: Optional[str] = None) -> None:
        if is_placeholder(name, email, linkedin):
            self.stats["placeholders_skipped"] += 1
            return
        name = name.strip()
        key = (company.id, name.lower())
        f = self.founders.get(key)
        if f is None:
            f = CompanyFounder(company_id=company.id, full_name=name)
            self.db.add(f)
            self.founders[key] = f
            self.stats["founders_created"] += 1
        else:
            self.stats["founders_updated"] += 1
        f.title = f.title or title
        f.linkedin_url = f.linkedin_url or (linkedin if "/in/" in (linkedin or "") else None)
        f.twitter_handle = f.twitter_handle or _twitter_handle(twitter)
        f.bio = f.bio or bio
        if email and not f.email_verified:
            f.email = email.strip().lower()
            f.email_confidence = email_confidence(name, email)
            f.email_verified = False
        f.source = f.source or source

    # --- sources -----------------------------------------------------------------------------

    def vc_firms(self) -> None:
        for r in json.load(io.open(REPO / "src/vc_intelligence/data/vc_100_firms.json", encoding="utf-8")):
            self.firm(r["slug"], r["name"], website=r.get("website"), portfolio_url=r.get("portfolio_url"),
                      country_focus=r.get("country_focus"), region=r.get("region"))

    def vc_catalog(self) -> None:
        from src.vc_intelligence.batch_data_catalog import ALL_AVAILABLE_BATCHES
        from src.vc_intelligence.enrich_50_founders import VERIFIED_VC_FOUNDERS_DATASET

        records: List[Dict[str, Any]] = [r for batch in ALL_AVAILABLE_BATCHES for r in batch] + list(VERIFIED_VC_FOUNDERS_DATASET)
        for r in records:
            firm = self.firm(r.get("vc_slug") or _slugify(r.get("vc_name", "unknown")), r.get("vc_name") or "Unknown VC")
            c = self.company(firm, r["company_name"], r.get("domain"), slug=r.get("slug"), website=r.get("website"),
                             description=r.get("description"), batch_or_year=str(r.get("batch") or "") or None,
                             funding_stage=r.get("stage"), industry_tags=json.dumps(r.get("industries") or []) if r.get("industries") else None)
            for f in r.get("founders") or []:
                self.founder(c, f.get("name"), f.get("title"), f.get("email"), f.get("linkedin"), "vc_catalog", bio=f.get("bio"))

    def startups_gallery_founders(self) -> None:
        firm = self.firm("startups-gallery", "startups.gallery", website="https://startups.gallery")
        for fname in ("startups_100_founders.json", "startups_200_founders.json", "startups_100_more_founders.json"):
            path = REPO / "data" / fname
            if not path.exists():
                continue
            for r in json.load(io.open(path, encoding="utf-8")):
                c = self.company(firm, r["company"], r.get("domain"), location=r.get("location"),
                                 funding_summary=r.get("funding"), jobs_count=r.get("jobs_count"),
                                 careers_url=r.get("ats_url"), batch_or_year=str(r.get("founded_year") or "") or None,
                                 investors=json.dumps(r["investors"]) if isinstance(r.get("investors"), list) and r["investors"] else None,
                                 industry_tags=json.dumps([r["category"]]) if r.get("category") else None)
                self.founder(c, r.get("name"), r.get("title"), r.get("email"), r.get("linkedin_url"),
                             "startups_gallery", twitter=r.get("twitter_url"))

    def startups_gallery_companies(self) -> None:
        firm = self.firm("startups-gallery", "startups.gallery", website="https://startups.gallery")
        path = REPO / "data" / "startups_gallery_companies.json"
        for r in json.load(io.open(path, encoding="utf-8")):
            self.company(firm, r["name"], r.get("domain"), slug=r.get("slug"), location=r.get("location"),
                         description=_clean_description(r["name"], r.get("description")),
                         funding_summary=r.get("funding") or None, jobs_count=r.get("jobs_count"),
                         batch_or_year=str(r.get("founded_year") or "") or None,
                         investors=json.dumps(r["investors"]) if isinstance(r.get("investors"), list) and r["investors"] else None,
                         industry_tags=json.dumps([r["category"]]) if r.get("category") else None)

    def registries(self) -> None:
        for module, var, source in REGISTRIES:
            try:
                rows: Iterable[Any] = getattr(importlib.import_module(module), var)
            except Exception as exc:  # noqa: BLE001  a broken registry must not stop the import
                log.warning("skipping %s.%s: %s", module, var, exc)
                continue
            firm = self.firm(_slugify(source), source)
            for row in rows:
                r = asdict(row) if is_dataclass(row) else dict(vars(row))
                desc = r.get("pitch_description") or r.get("metrics_summary") or r.get("description")
                self.company(firm, r["name"], r.get("domain"), description=desc, careers_url=r.get("careers_url"),
                             industry_tags=json.dumps([r["category"]]) if r.get("category") else None,
                             batch_or_year=str(r.get("batch") or r.get("season") or "") or None)

    def run(self) -> Dict[str, int]:
        # Order matters: richest sources first; later ones only fill blanks.
        for step in (self.vc_firms, self.vc_catalog, self.startups_gallery_founders,
                     self.startups_gallery_companies, self.registries):
            step()
            self.db.flush()
        self.db.commit()
        return self.stats


def run_import(db: Session) -> Dict[str, int]:
    return Importer(db).run()
