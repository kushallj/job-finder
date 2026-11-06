"""
jobify_founders.py — VC portfolio companies -> the Jobify Founders shape, plus credit unlocks.

Contract (jobify/docs/INTEGRATION.md, jobify/src/services/founderService.js):
  Company = { id, name, website, location, country, industry, description, hiring,
              founders[{ id, name, initials, role, linkedin, x, email? }] }

Rules:
  - Founder emails are returned ONLY for companies the current user has unlocked.
  - Unlocking costs CREDIT_COSTS["founder_unlock"], is charged once per user+company,
    and is atomic (credit_service.deduct_credits uses SELECT ... FOR UPDATE).
  - PortfolioCompany has no location column: country comes from the domain's ccTLD or the
    VC firm's country focus, else "Unknown" (never guessed).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Set

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import CompanyFounder, FounderUnlock, Job, PortfolioCompany, SavedFounderCompany, User, VCFirm
from src.services.credit_service import CREDIT_COSTS, add_credits, deduct_credits

UNLOCK_ACTION = "founder_unlock"
MAX_SCAN = 5000  # companies filtered in Python (country/hiring are derived, not columns)

_CCTLD = {"in": "India", "uk": "UK", "de": "Germany", "fr": "France", "sg": "Singapore", "ca": "Canada",
          "au": "Australia", "ng": "Nigeria", "ke": "Kenya", "br": "Brazil", "jp": "Japan", "nl": "Netherlands",
          "ie": "Ireland", "es": "Spain", "se": "Sweden", "il": "Israel", "id": "Indonesia", "ae": "UAE", "us": "USA"}


def unlock_cost() -> int:
    return int(CREDIT_COSTS.get(UNLOCK_ACTION, 5))


def _tags(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [str(t).strip() for t in val if str(t).strip()]
    except (ValueError, TypeError):
        pass
    return [t.strip() for t in re.split(r"[,;|]", raw) if t.strip()]


def country_of(company: PortfolioCompany, firm: Optional[VCFirm]) -> str:
    host = (company.domain or re.sub(r"^https?://", "", company.website or "")).split("/")[0].lower()
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    if tld in _CCTLD:
        return _CCTLD[tld]
    focus = (firm.country_focus or "").strip() if firm else ""
    if focus and focus.lower() not in ("global", "worldwide", "international"):
        return focus
    return "Unknown"


def _initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", name or "") if p]
    return ("".join(p[0] for p in parts[:2]) or "?").upper()


def founder_ui(f: CompanyFounder, unlocked: bool) -> Dict[str, Any]:
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
    return out


def company_ui(company: PortfolioCompany, founders: List[CompanyFounder], firm: Optional[VCFirm],
               hiring: bool, unlocked: bool) -> Dict[str, Any]:
    country = country_of(company, firm)
    website = company.website or (f"https://{company.domain}" if company.domain else "")
    tags = _tags(company.industry_tags)
    return {
        "id": str(company.id),
        "name": company.name,
        "website": website,
        "location": country if country != "Unknown" else "",
        "country": country,
        "industry": tags[0] if tags else "Other",
        "description": company.description or "",
        "hiring": hiring,
        "founders": [founder_ui(f, unlocked) for f in founders],
    }


def hiring_names(db: Session, names: Iterable[str]) -> Set[str]:
    """Lower-cased company names with at least one open (non-expired) job in our catalog."""
    lowered = {n.lower() for n in names if n}
    if not lowered:
        return set()
    rows = (db.query(func.lower(Job.company)).filter(Job.expired_at.is_(None), func.lower(Job.company).in_(lowered))
            .distinct().all())
    return {r[0] for r in rows}


def user_state(db: Session, user: User) -> Dict[str, List[str]]:
    saved = [str(r.company_id) for r in db.query(SavedFounderCompany).filter(SavedFounderCompany.user_id == user.id)]
    unlocked = [str(r.company_id) for r in db.query(FounderUnlock).filter(FounderUnlock.user_id == user.id)]
    return {"saved": saved, "unlocked": unlocked}


def load_companies(db: Session, user: User, ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    query = db.query(PortfolioCompany)
    if ids is not None:
        query = query.filter(PortfolioCompany.id.in_(ids))
    companies = query.order_by(PortfolioCompany.name).limit(MAX_SCAN).all()
    if not companies:
        return []
    cids = [c.id for c in companies]
    founders: Dict[int, List[CompanyFounder]] = {}
    for f in db.query(CompanyFounder).filter(CompanyFounder.company_id.in_(cids)).order_by(CompanyFounder.id):
        founders.setdefault(f.company_id, []).append(f)
    firm_ids = {c.vc_firm_id for c in companies if c.vc_firm_id}
    firms = {f.id: f for f in db.query(VCFirm).filter(VCFirm.id.in_(firm_ids))} if firm_ids else {}
    hiring = hiring_names(db, [c.name for c in companies])
    unlocked = {r.company_id for r in db.query(FounderUnlock).filter(FounderUnlock.user_id == user.id,
                                                                      FounderUnlock.company_id.in_(cids))}
    return [company_ui(c, founders.get(c.id, []), firms.get(c.vc_firm_id), c.name.lower() in hiring, c.id in unlocked)
            for c in companies]


def search(items: List[Dict[str, Any]], q: str, country: str, industry: str, hiring_only: bool) -> List[Dict[str, Any]]:
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


def unlock(db: Session, user: User, company_id: int) -> Dict[str, Any]:
    """Charge once and record the unlock. Returns {cost, already}. Raises HTTP 402 via credit_service."""
    if db.query(FounderUnlock.id).filter(FounderUnlock.user_id == user.id, FounderUnlock.company_id == company_id).first():
        return {"cost": 0, "already": True}
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
