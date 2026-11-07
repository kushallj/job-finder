"""
jobify_founders_router.py — Phase 4 of the Jobify MVP: Founders + credit unlocks.

  GET  /api/founders?q&country&industry&hiringOnly&page&pageSize   list shape
  GET  /api/founders/facets                                        { countries, industries }
  POST /api/founders/{id}/unlock    charges credits once -> { ok, cost, state, company }
  GET  /api/me/founders/state       { saved: [], unlocked: [] }
  PUT  /api/me/founders/{id}/saved  { saved?: bool } (no body toggles) -> state

Emails are only ever present on companies the caller has unlocked.
Logic: src/jobify/services/founders.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.auth.dependencies import get_current_user
from src.database import get_db
from src.models import PortfolioCompany, SavedFounderCompany, User
from src.jobify.services import founders as jf

router = APIRouter(tags=["Jobify"])


def _company_or_404(db: Session, company_id: int) -> PortfolioCompany:
    company = db.query(PortfolioCompany).filter(PortfolioCompany.id == company_id).first()
    if company is None:
        raise HTTPException(404, "Company not found")
    return company


@router.get("/api/founders")
def list_founders(q: str = "", country: str = "", industry: str = "", hiringOnly: bool = False,
                  page: int = Query(default=1, ge=1), pageSize: int = Query(default=10, ge=1, le=100),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    items = jf.search(jf.load_companies(db, user), q, country, industry, hiringOnly)
    start = (page - 1) * pageSize
    return {"items": items[start:start + pageSize], "total": len(items), "page": page, "pageSize": pageSize}


@router.get("/api/founders/facets")
def facets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    items = jf.load_companies(db, user)
    return {"countries": sorted({c["country"] for c in items}), "industries": sorted({c["industry"] for c in items}),
            "unlockCost": jf.unlock_cost()}


@router.post("/api/founders/{company_id:int}/unlock")
def unlock(company_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    _company_or_404(db, company_id)
    result = jf.unlock(db, user, company_id)
    company = jf.load_companies(db, user, ids=[company_id])[0]
    return {"ok": True, "cost": result["cost"], "state": jf.user_state(db, user), "company": company}


@router.get("/api/me/founders/state")
def founders_state(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, List[str]]:
    return jf.user_state(db, user)


@router.put("/api/me/founders/{company_id:int}/saved")
def set_saved(company_id: int, body: Optional[Dict[str, Any]] = Body(default=None),
              user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, List[str]]:
    _company_or_404(db, company_id)
    row = (db.query(SavedFounderCompany)
           .filter(SavedFounderCompany.user_id == user.id, SavedFounderCompany.company_id == company_id).first())
    want = (row is None) if not body or "saved" not in body else bool(body["saved"])
    if want and row is None:
        db.add(SavedFounderCompany(user_id=user.id, company_id=company_id, created_at=datetime.utcnow()))
    elif not want and row is not None:
        db.delete(row)
    db.commit()
    return jf.user_state(db, user)
