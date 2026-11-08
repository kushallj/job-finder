"""
jobify_founders.py — VC portfolio companies -> the Jobify Founders shape, plus credit unlocks.

Contract (jobify/docs/INTEGRATION.md, jobify/src/services/founderService.js):
  Company = { id, name, website, location, country, industry, description, hiring,
              founders[{ id, name, initials, role, linkedin, x, email? }] }

Rules:
  - Founder emails are returned ONLY for companies the current user has unlocked.
  - Unlocking costs CREDIT_COSTS["founder_unlock"], is charged once per user+company,
    and is atomic (credit_service.deduct_credits uses SELECT ... FOR UPDATE).
  - Country comes from the stored location (startups.gallery), else the domain's ccTLD or the
    VC firm's country focus, else "Unknown" (never guessed).
  - Scraped founder emails are pattern guesses: they're returned with emailVerified=false so the
    UI can label them; companies with no founders on file can't be unlocked (nothing to sell).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import (
    CompanyFounder,
    FounderUnlock,
    Job,
    PortfolioCompany,
    SavedFounderCompany,
    User,
    VCFirm,
)
from src.services.credit_service import CREDIT_COSTS, add_credits, deduct_credits

UNLOCK_ACTION = "founder_unlock"
MAX_SCAN = 5000  # companies filtered in Python (country/hiring are derived, not columns)

_COUNTRY_ALIASES = {"united states": "USA", "us": "USA", "usa": "USA", "united kingdom": "UK", "uk": "UK",
                    "england": "UK", "united arab emirates": "UAE"}
_CCTLD = {"in": "India", "uk": "UK", "de": "Germany", "fr": "France", "sg": "Singapore", "ca": "Canada",
          "au": "Australia", "ng": "Nigeria", "ke": "Kenya", "br": "Brazil", "jp": "Japan", "nl": "Netherlands",
          "ie": "Ireland", "es": "Spain", "se": "Sweden", "il": "Israel", "id": "Indonesia", "ae": "UAE", "us": "USA"}


def unlock_cost() -> int:
    return int(CREDIT_COSTS.get(UNLOCK_ACTION, 5))


def _tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [str(t).strip() for t in val if str(t).strip()]
    except (ValueError, TypeError):
        pass
    return [t.strip() for t in re.split(r"[,;|]", raw) if t.strip()]


_NOT_A_COUNTRY = {"", "remote", "global", "worldwide", "international", "anywhere"}


# Accepted filter values. Scraped locations contain prose ("New Zealand and growing fast!"),
# so anything not in this list is searched for a known name, else dropped.
_KNOWN_PLACES = [
    "USA", "UK", "UAE", "India", "China", "Japan", "Singapore", "Indonesia", "Vietnam", "Thailand", "Malaysia",
    "Philippines", "South Korea", "Taiwan", "Hong Kong", "Australia", "New Zealand", "Canada", "Mexico", "Brazil",
    "Argentina", "Chile", "Colombia", "Peru", "Germany", "France", "Spain", "Italy", "Portugal", "Netherlands",
    "Belgium", "Switzerland", "Austria", "Ireland", "Sweden", "Norway", "Denmark", "Finland", "Poland", "Estonia",
    "Lithuania", "Latvia", "Czech Republic", "Hungary", "Romania", "Greece", "Turkey", "Israel", "Saudi Arabia",
    "Qatar", "Egypt", "Nigeria", "Kenya", "South Africa", "Ghana", "Rwanda", "Pakistan", "Bangladesh", "Sri Lanka",
    "Nepal", "Armenia", "Ukraine", "Luxembourg", "Iceland",
    # regions used by VC firms
    "Europe", "Africa", "LatAm", "Southeast Asia", "Middle East",
]
_KNOWN_LOWER = {p.lower(): p for p in _KNOWN_PLACES}
_ALL_NAMES = sorted(list(_KNOWN_LOWER) + list(_COUNTRY_ALIASES), key=len, reverse=True)


def normalize_country(value: str | None) -> str | None:
    """'San Francisco, United States' -> 'USA'; 'X, Y · Oct 15, 2026' -> 'Y'; 'Singapore / Asia' -> 'Singapore'."""
    text = (value or "").split("·")[0].strip()
    if not text:
        return None
    v = text.split(",")[-1].split("/")[0].strip().rstrip(".!")
    if v.lower() in _NOT_A_COUNTRY:
        return None
    if v.lower() in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[v.lower()]
    if v.lower() in _KNOWN_LOWER:
        return _KNOWN_LOWER[v.lower()]
    # Free text: take the last known place mentioned anywhere in the location.
    low = f" {text.lower()} "
    best = None
    for name in _ALL_NAMES:
        idx = low.rfind(f" {name}")
        boundary = low[idx + len(name) + 1:idx + len(name) + 2] in (" ", ",", ".", "!", "/", ")")
        if idx >= 0 and boundary and (best is None or idx > best[0]):
            best = (idx, name)
    if best is None:
        return None
    return _COUNTRY_ALIASES.get(best[1]) or _KNOWN_LOWER[best[1]]


def country_of(company: PortfolioCompany, firm: VCFirm | None) -> str:
    from_location = normalize_country(company.location)
    if from_location:
        return from_location
    host = (company.domain or re.sub(r"^https?://", "", company.website or "")).split("/")[0].lower()
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    if tld in _CCTLD:
        return _CCTLD[tld]
    return normalize_country(firm.country_focus if firm else None) or "Unknown"


def _initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", name or "") if p]
    return ("".join(p[0] for p in parts[:2]) or "?").upper()


def founder_ui(f: CompanyFounder, unlocked: bool) -> dict[str, Any]:
    out = {
        "id": str(f.id),
        "name": f.full_name or "",
        "initials": _initials(f.full_name or ""),
        "role": f.title or "Founder",
        "linkedin": f.linkedin_url or None,
        "x": f"https://x.com/{f.twitter_handle.lstrip('@')}" if f.twitter_handle else None,
    }
    if unlocked:
        out["email"] = f.email or None
        out["emailVerified"] = bool(f.email_verified)
    return out


def company_ui(company: PortfolioCompany, founders: list[CompanyFounder], firm: VCFirm | None,
               hiring: bool, unlocked: bool) -> dict[str, Any]:
    country = country_of(company, firm)
    website = company.website or (f"https://{company.domain}" if company.domain else "")
    tags = _tags(company.industry_tags)
    return {
        "id": str(company.id),
        "name": company.name,
        "website": website,
        "location": (company.location or "").split("·")[0].strip() or (country if country != "Unknown" else ""),
        "country": country,
        "industry": tags[0] if tags else "Other",
        "description": company.description or "",
        "hiring": hiring or bool(company.jobs_count),
        "founders": [founder_ui(f, unlocked) for f in founders],
    }


def hiring_names(db: Session, names: Iterable[str]) -> set[str]:
    """Lower-cased company names with at least one open (non-expired) job in our catalog."""
    lowered = {n.lower() for n in names if n}
    if not lowered:
        return set()
    rows = (db.query(func.lower(Job.company)).filter(Job.expired_at.is_(None), func.lower(Job.company).in_(lowered))
            .distinct().all())
    return {r[0] for r in rows}


def user_state(db: Session, user: User) -> dict[str, list[str]]:
    saved = [str(r.company_id) for r in db.query(SavedFounderCompany).filter(SavedFounderCompany.user_id == user.id)]
    unlocked = [str(r.company_id) for r in db.query(FounderUnlock).filter(FounderUnlock.user_id == user.id)]
    return {"saved": saved, "unlocked": unlocked}


def load_companies(db: Session, user: User, ids: list[int] | None = None) -> list[dict[str, Any]]:
    query = db.query(PortfolioCompany)
    if ids is not None:
        query = query.filter(PortfolioCompany.id.in_(ids))
    companies = query.order_by(PortfolioCompany.name).limit(MAX_SCAN).all()
    if not companies:
        return []
    cids = [c.id for c in companies]
    founders: dict[int, list[CompanyFounder]] = {}
    for f in db.query(CompanyFounder).filter(CompanyFounder.company_id.in_(cids)).order_by(CompanyFounder.id):
        founders.setdefault(f.company_id, []).append(f)
    firm_ids = {c.vc_firm_id for c in companies if c.vc_firm_id}
    firms = {f.id: f for f in db.query(VCFirm).filter(VCFirm.id.in_(firm_ids))} if firm_ids else {}
    hiring = hiring_names(db, [c.name for c in companies])
    unlocked = {r.company_id for r in db.query(FounderUnlock).filter(FounderUnlock.user_id == user.id,
                                                                      FounderUnlock.company_id.in_(cids))}
    out = [company_ui(c, founders.get(c.id, []), firms.get(c.vc_firm_id), c.name.lower() in hiring, c.id in unlocked)
           for c in companies]
    out.sort(key=lambda c: (not c["founders"], c["name"].lower()))  # companies with founders first
    return out


def search(items: list[dict[str, Any]], q: str, country: str, industry: str, hiring_only: bool) -> list[dict[str, Any]]:
    needle = q.strip().lower()
    out = []
    for c in items:
        if country and c["country"] != country:
            continue
        if industry and c["industry"] != industry:
            continue
        if hiring_only and not c["hiring"]:
            continue
        if needle:
            hay = f"{c['name']} {c['industry']} {c['location']} {c['description']} {' '.join(f['name'] for f in c['founders'])}"
            if needle not in hay.lower():
                continue
        out.append(c)
    return out


def unlock(db: Session, user: User, company_id: int) -> dict[str, Any]:
    """Charge once and record the unlock. Returns {cost, already}. Raises HTTP 402 via credit_service."""
    if db.query(FounderUnlock.id).filter(FounderUnlock.user_id == user.id, FounderUnlock.company_id == company_id).first():
        return {"cost": 0, "already": True}
    if not db.query(CompanyFounder.id).filter(CompanyFounder.company_id == company_id).first():
        raise HTTPException(409, {"code": "NO_FOUNDERS", "message": "No founders on file for this company yet"})
    cost = unlock_cost()
    deduct_credits(db, user.id, cost, UNLOCK_ACTION, reference_id=f"company:{company_id}",
                   notes="Unlocked founder contacts")  # commits; 402 if not enough credits
    try:
        db.add(FounderUnlock(user_id=user.id, company_id=company_id, credits_spent=cost))
        db.commit()
    except IntegrityError:
        # A concurrent request unlocked it first: give these credits back.
        db.rollback()
        add_credits(db, user.id, cost, action="founder_unlock_refund", notes="Duplicate unlock refunded")
        return {"cost": 0, "already": True}
    return {"cost": cost, "already": False}
