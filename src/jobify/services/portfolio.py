"""
jobify_portfolio.py — Jobify Phase 5: per-user portfolio draft, publish, and regenerate.

Contract (jobify/docs/INTEGRATION.md, jobify/src/services/portfolioService.js):
  Portfolio = { status: draft|published, username, identity{fullName, firstName, jobTitle, tagline, bio,
                introLabels, skills[]}, contact{email, website, calendar, resume},
                projects|experience|education|hacks|research: [{id, title, subtitle, description}],
                socials{github, linkedin, x}, custom: [{id, title, body}], sources{resume, github, snapshot},
                updatedAt, publishedAt }

Rules:
  - Drafts are lenient (length/count limits only) so autosave never drops edits while the user is
    mid-typing a URL. Publishing is strict: full name required, every link must be http(s).
  - Publishing snapshots the draft into `published_content`; the public endpoint serves only that
    snapshot, so draft autosaves never leak to the public page.
  - Usernames: ^[a-z0-9-]{3,24}$, no leading/trailing hyphen (it becomes a subdomain), not reserved,
    not held by another user. Unpublishing keeps the username claimed.
  - Regenerate is deterministic: it fills EMPTY fields and appends missing items from the user's
    CandidateProfile (+ its experiences/projects). It never overwrites manual edits and never
    invents content; nothing on file means nothing is added. (LLM polishing waits on the provider decision.)
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.contract import iso_utc
from src.jobify.services import jobs as jj
from src.models import CandidateExperience, CandidateProject, Portfolio, User

USERNAME_RE = re.compile(r"^[a-z0-9-]{3,24}$")
RESERVED = {
    "admin", "administrator", "root", "jobify", "demo", "test", "api", "app", "www", "mail", "email", "inbox",
    "support", "help", "about", "blog", "docs", "status", "billing", "pricing", "plans", "checkout", "signin",
    "signup", "login", "logout", "account", "settings", "me", "static", "assets", "cdn", "dev", "staging",
    "portfolio", "publish", "regenerate", "username-available", "null", "undefined",
}
LIST_SECTIONS = ("projects", "experience", "education", "hacks", "research")
_URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*\.[^\s]+$", re.I)
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# --- schema (draft = lenient) ---------------------------------------------------------

class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


def _s(n: int):
    return Field(default="", max_length=n)


class Identity(_Base):
    fullName: str = _s(120)
    firstName: str = _s(60)
    jobTitle: str = _s(120)
    tagline: str = _s(200)
    bio: str = _s(3000)
    introLabels: str = _s(500)
    skills: list[str] = Field(default_factory=list, max_length=60)

    @field_validator("skills")
    @classmethod
    def _skills(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for raw in v:
            s = " ".join(str(raw).split())[:40].lower()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out


class Contact(_Base):
    email: str = _s(254)
    website: str = _s(500)
    calendar: str = _s(500)
    resume: str = _s(500)


class Socials(_Base):
    github: str = _s(500)
    linkedin: str = _s(500)
    x: str = _s(500)


class Item(_Base):
    id: str = Field(default="", max_length=64)
    title: str = _s(200)
    subtitle: str = _s(300)
    description: str = _s(3000)


class CustomSection(_Base):
    id: str = Field(default="", max_length=64)
    title: str = _s(120)
    body: str = _s(8000)


class PortfolioContent(_Base):
    identity: Identity = Field(default_factory=Identity)
    contact: Contact = Field(default_factory=Contact)
    projects: list[Item] = Field(default_factory=list, max_length=50)
    experience: list[Item] = Field(default_factory=list, max_length=50)
    education: list[Item] = Field(default_factory=list, max_length=50)
    hacks: list[Item] = Field(default_factory=list, max_length=50)
    research: list[Item] = Field(default_factory=list, max_length=50)
    socials: Socials = Field(default_factory=Socials)
    custom: list[CustomSection] = Field(default_factory=list, max_length=20)

    def with_ids(self) -> PortfolioContent:
        for key in (*LIST_SECTIONS, "custom"):
            seen = set()
            for item in getattr(self, key):
                if not item.id or item.id in seen:
                    item.id = f"{key[:2]}_{uuid.uuid4().hex[:10]}"
                seen.add(item.id)
        return self


# --- persistence ------------------------------------------------------------------------

def _real_name(user: User, name: str | None) -> str:
    """Auto-provisioning stores the Clerk id as the name when the session token has none
    ("User_3Lhdz..."); that's a placeholder, not something to publish."""
    name = (name or "").strip()
    if not name:
        return ""
    return "" if user.clerk_user_id and name.lower() == user.clerk_user_id.lower() else name


def _default_content(user: User) -> PortfolioContent:
    name = _real_name(user, user.full_name)
    email = user.email or ""
    return PortfolioContent(identity=Identity(fullName=name[:120], firstName=name.split(" ")[0][:60] if name else ""),
                            contact=Contact(email="" if email.endswith("@clerk.user") else email[:254]))


def get_or_create(db: Session, user: User) -> Portfolio:
    row = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
    if row is not None:
        return row
    row = Portfolio(user_id=user.id, status="draft", content=_default_content(user).model_dump_json())
    db.add(row)
    try:
        db.commit()
    except IntegrityError:  # concurrent first load
        db.rollback()
        return db.query(Portfolio).filter(Portfolio.user_id == user.id).one()
    db.refresh(row)
    return row


def load_content(raw: str | None) -> PortfolioContent:
    try:
        return PortfolioContent.model_validate(json.loads(raw or "{}"))
    except (ValueError, TypeError):
        return PortfolioContent()


def _sources(db: Session, user: User, row: Portfolio) -> dict[str, Any]:
    profile = jj.profile_for(db, user)
    return {
        "resume": iso_utc(profile.updated_at) if profile is not None and profile.updated_at else None,
        "github": None,  # GitHub analysis isn't implemented; links are saved only
        "snapshot": iso_utc(row.snapshot_at),
    }


def to_api(db: Session, user: User, row: Portfolio) -> dict[str, Any]:
    out = load_content(row.content).model_dump()
    out.update({"status": row.status, "username": row.username or "", "sources": _sources(db, user, row),
                "updatedAt": iso_utc(row.updated_at), "publishedAt": iso_utc(row.published_at)})
    return out


def save_draft(db: Session, row: Portfolio, content: PortfolioContent) -> Portfolio:
    row.content = content.with_ids().model_dump_json()
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


# --- usernames ----------------------------------------------------------------------------

def username_problem(db: Session, name: str, user: User | None = None) -> str | None:
    """None if `name` can be claimed by `user`, else a human-readable reason."""
    if not USERNAME_RE.match(name or ""):
        return "Use 3 to 24 lowercase letters, numbers or hyphens"
    if name.startswith("-") or name.endswith("-"):
        return "Usernames can't start or end with a hyphen"
    if name in RESERVED:
        return "That username is reserved"
    q = db.query(Portfolio.id).filter(Portfolio.username == name)
    if user is not None:
        q = q.filter(Portfolio.user_id != user.id)
    if q.first() is not None:
        return "That username is taken"
    return None


# --- publish ------------------------------------------------------------------------------

def publish_errors(content: PortfolioContent) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not content.identity.fullName.strip():
        errors["fullName"] = "Add your full name before publishing"
    if content.contact.email and not _EMAIL_RE.match(content.contact.email):
        errors["email"] = "Enter a valid email"
    for group, keys in (("contact", ("website", "calendar", "resume")), ("socials", ("github", "linkedin", "x"))):
        for key in keys:
            value = getattr(getattr(content, group), key).strip()
            if value and not _URL_RE.match(value):
                errors[key] = "Enter a URL starting with https://"
    return errors


def publish(db: Session, user: User, row: Portfolio, username: str) -> Portfolio:
    username = (username or "").strip().lower()
    reason = username_problem(db, username, user)
    if reason:
        raise HTTPException(409 if reason.endswith("taken") else 422,
                            detail={"code": "USERNAME_UNAVAILABLE", "message": reason})
    content = load_content(row.content)
    errors = publish_errors(content)
    if errors:
        raise HTTPException(422, detail={"code": "PORTFOLIO_INVALID", "message": next(iter(errors.values())),
                                         "fields": errors})
    now = datetime.utcnow()
    row.username = username
    row.status = "published"
    row.published_content = content.model_dump_json()
    row.published_at = now
    row.updated_at = now
    try:
        db.commit()
    except IntegrityError:  # another user claimed it between the check and the write
        db.rollback()
        raise HTTPException(409, detail={"code": "USERNAME_UNAVAILABLE", "message": "That username is taken"}) from None
    db.refresh(row)
    return row


def unpublish(db: Session, row: Portfolio) -> Portfolio:
    row.status = "draft"
    row.published_content = None
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def public_view(db: Session, username: str) -> dict[str, Any] | None:
    row = (db.query(Portfolio)
           .filter(Portfolio.username == (username or "").lower(), Portfolio.status == "published").first())
    if row is None or not row.published_content:
        return None
    out = load_content(row.published_content).model_dump()
    out.update({"username": row.username, "publishedAt": iso_utc(row.published_at)})
    return out


# --- regenerate -------------------------------------------------------------------------------

def _period(start: str | None, end: str | None) -> str:
    start, end = (start or "").strip(), (end or "").strip()
    return f"{start} – {end}" if start and end else start or end


def _append_missing(items: list[Item], new: list[Item]) -> None:
    have = {(i.title.strip().lower(), i.subtitle.strip().lower()) for i in items}
    for item in new:
        key = (item.title.strip().lower(), item.subtitle.strip().lower())
        if item.title.strip() and key not in have and len(items) < 50:
            items.append(item)
            have.add(key)


def regenerate(db: Session, user: User, row: Portfolio) -> Portfolio:
    content = load_content(row.content)
    profile = jj.profile_for(db, user)
    ident, contact, socials = content.identity, content.contact, content.socials

    def fill(obj, field: str, value: str | None, limit: int) -> None:
        if value and str(value).strip() and not getattr(obj, field).strip():
            setattr(obj, field, str(value).strip()[:limit])

    def real_email(value: str | None) -> str | None:
        return value if value and not value.endswith("@clerk.user") else None  # Clerk placeholder, not an address

    fill(ident, "fullName", _real_name(user, profile.full_name if profile else None) or _real_name(user, user.full_name), 120)
    fill(ident, "firstName", ident.fullName.split(" ")[0] if ident.fullName else None, 60)
    fill(contact, "email", real_email(profile.email if profile else None) or real_email(user.email), 254)

    if profile is not None:
        fill(ident, "jobTitle", profile.current_title or profile.headline, 120)
        fill(ident, "bio", profile.bio_summary, 3000)
        fill(contact, "website", profile.portfolio_url, 500)
        fill(socials, "github", profile.github_url, 500)
        fill(socials, "linkedin", profile.linkedin_url, 500)
        ident.skills = Identity(skills=ident.skills + jj._json_list(profile.skills)).skills

        exps = (db.query(CandidateExperience).filter(CandidateExperience.profile_id == profile.id)
                .order_by(CandidateExperience.display_order, CandidateExperience.id).all())
        _append_missing(content.experience, [
            Item(title=(e.title or "")[:200],
                 subtitle=" · ".join(p for p in (e.company, _period(e.start_date, e.end_date)) if p)[:300],
                 description=(e.description or "")[:3000]) for e in exps])
        projs = (db.query(CandidateProject).filter(CandidateProject.profile_id == profile.id)
                 .order_by(CandidateProject.display_order, CandidateProject.id).all())
        _append_missing(content.projects, [
            Item(title=(p.title or "")[:200], subtitle=(p.demo_url or p.github_repo_url or "")[:300],
                 description=(p.description or p.tagline or "")[:3000]) for p in projs])

    row.content = content.with_ids().model_dump_json()
    row.snapshot_at = datetime.utcnow()
    row.updated_at = row.snapshot_at
    db.commit()
    db.refresh(row)
    return row
