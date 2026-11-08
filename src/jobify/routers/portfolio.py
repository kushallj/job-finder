"""
jobify_portfolio_router.py — Phase 5 of the Jobify MVP: Portfolio.

  GET    /api/portfolio                          the caller's draft (created on first read)
  PUT    /api/portfolio                          save draft -> portfolio
  POST   /api/portfolio/publish {username}       snapshot draft + claim username -> portfolio
  DELETE /api/portfolio/publish                  unpublish (username stays claimed) -> portfolio
  GET    /api/portfolio/username-available?name= { available, reason? }
  POST   /api/portfolio/regenerate               fill empty fields from the matching profile -> portfolio
  GET    /api/portfolio/{username}               PUBLIC: published snapshot only, else 404

Static paths are declared before `/{username}`, and those names are reserved usernames.
Logic: src/jobify/services/portfolio.py.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import CURRENT_USER, DB_SESSION
from src.jobify.services import portfolio as jp
from src.models import User

router = APIRouter(prefix="/api/portfolio", tags=["Jobify"])


class PublishBody(BaseModel):
    username: str = Field(max_length=64)


@router.get("")
def get_portfolio(user: User = CURRENT_USER, db: Session = DB_SESSION) -> dict[str, Any]:
    return jp.to_api(db, user, jp.get_or_create(db, user))


@router.put("")
def save_portfolio(body: jp.PortfolioContent, user: User = CURRENT_USER, db: Session = DB_SESSION) -> dict[str, Any]:
    row = jp.save_draft(db, jp.get_or_create(db, user), body)
    return jp.to_api(db, user, row)


@router.get("/username-available")
def username_available(user: User = CURRENT_USER, db: Session = DB_SESSION, name: str = Query(default="", max_length=64)) -> dict[str, Any]:
    reason = jp.username_problem(db, name.strip().lower(), user)
    return {"available": True} if reason is None else {"available": False, "reason": reason}


@router.post("/publish")
def publish(body: PublishBody, user: User = CURRENT_USER, db: Session = DB_SESSION) -> dict[str, Any]:
    row = jp.publish(db, user, jp.get_or_create(db, user), body.username)
    return jp.to_api(db, user, row)


@router.delete("/publish")
def unpublish(user: User = CURRENT_USER, db: Session = DB_SESSION) -> dict[str, Any]:
    return jp.to_api(db, user, jp.unpublish(db, jp.get_or_create(db, user)))


@router.post("/regenerate")
def regenerate(user: User = CURRENT_USER, db: Session = DB_SESSION) -> dict[str, Any]:
    return jp.to_api(db, user, jp.regenerate(db, user, jp.get_or_create(db, user)))


@router.get("/{username}")
def public_portfolio(username: str, db: Session = DB_SESSION) -> dict[str, Any]:
    view = jp.public_view(db, username)
    if view is None:
        raise HTTPException(404, "Portfolio not found")
    return view
