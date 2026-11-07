"""
chat_context.py — the facts the chat model may use about the current user.

Built per request from data the user entered themselves: the matching profile (Jobs page),
the portfolio draft (identity, experience, projects, education, links) and their application
board (company / role / stage only; private notes are not included). The block is appended
to the system prompt with an instruction to use only these facts plus what the user says.

Bounded to MAX_CHARS so prompts stay small for free-tier models with short context windows.
This text is sent to the configured LLM provider: it is personal data (CLAUDE.md §1).
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from src.models import Application, Portfolio, User
from src.jobify.services import jobs as jj
from src.jobify.services import portfolio as jp

MAX_CHARS = 4000
MAX_ITEMS = 6
MAX_APPS = 15


def _clip(text: Optional[str], n: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def build_user_context(db: Session, user: User) -> str:
    lines: List[str] = []
    profile = jj.profile_for(db, user)
    row = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
    content = jp.load_content(row.content) if row is not None else None
    ident = content.identity if content else None

    # Sign-up derives a name from the email when Clerk sends none ("kushall.jain07" -> "Kushall Jain07");
    # that's a guess, not a fact the user entered.
    derived = (user.email or "").split("@")[0].replace(".", " ").title()
    account_name = jp._real_name(user, user.full_name)
    name = jp._real_name(user, ident.fullName if ident else None) or (account_name if account_name != derived else "")
    if name:
        lines.append(f"Name: {_clip(name, 80)}")
    title = (ident.jobTitle if ident else "") or (profile.current_title if profile else "") or ""
    if title:
        lines.append(f"Current title: {_clip(title, 120)}")
    if profile is not None and profile.years_of_experience is not None and jj._json_list(profile.skills):
        lines.append(f"Years of experience: {profile.years_of_experience:g}")
    skills = list(dict.fromkeys((ident.skills if ident else []) + [s.lower() for s in jj._json_list(profile.skills if profile else None)]))
    if skills:
        lines.append(f"Skills: {', '.join(skills[:40])}")
    if profile is not None:
        if jj._json_list(profile.target_roles):
            lines.append(f"Target roles: {', '.join(jj._json_list(profile.target_roles)[:10])}")
        if jj._json_list(profile.target_locations):
            lines.append(f"Preferred locations: {', '.join(jj._json_list(profile.target_locations)[:10])}")
    if ident and ident.tagline:
        lines.append(f"Tagline: {_clip(ident.tagline, 200)}")
    bio = (ident.bio if ident else "") or (profile.bio_summary if profile else "") or ""
    if bio:
        lines.append(f"Bio: {_clip(bio, 600)}")

    if content:
        for key, label in (("experience", "Experience"), ("projects", "Projects"), ("education", "Education"),
                           ("hacks", "Hackathons"), ("research", "Research")):
            items = getattr(content, key)[:MAX_ITEMS]
            if items:
                lines.append(f"{label}:")
                for it in items:
                    head = " — ".join(p for p in (_clip(it.title, 120), _clip(it.subtitle, 120)) if p)
                    desc = _clip(it.description, 300)
                    lines.append(f"- {head}" + (f": {desc}" if desc else ""))
        links = [f"{k}: {v}" for k, v in (("website", content.contact.website), ("github", content.socials.github),
                                          ("linkedin", content.socials.linkedin)) if v]
        if links:
            lines.append("Links: " + "; ".join(links))

    apps = (db.query(Application).filter(Application.user_id == user.id)
            .order_by(Application.id.desc()).limit(MAX_APPS).all())
    if apps:
        lines.append(f"Job applications on their board (latest {len(apps)}):")
        for a in apps:
            lines.append(f"- {_clip(a.company, 60) or 'Unknown company'} — {_clip(a.position, 80) or 'role not set'} "
                         f"({(a.kanban_stage or 'applied').lower()})")

    if not lines:
        return ("USER PROFILE: none saved yet. If a request needs their background, ask for it or use "
                "bracketed placeholders. Suggest saving a profile on the Jobs page and Portfolio page.")
    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[: MAX_CHARS - 1].rstrip() + "…"
    return ("USER PROFILE (facts the user entered in Jobify; you may use these and what they say in chat, "
            "nothing else):\n" + text)
