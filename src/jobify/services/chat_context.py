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

from sqlalchemy.orm import Session

from src.jobify.services import jobs as jj
from src.jobify.services import portfolio as jp
from src.models import Application, CandidateProfile, Portfolio, User

MAX_CHARS = 4000
MAX_ITEMS = 6
MAX_APPS = 15


def _clip(text: str | None, n: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


PORTFOLIO_SECTIONS = (("experience", "Experience"), ("projects", "Projects"), ("education", "Education"),
                      ("hacks", "Hackathons"), ("research", "Research"))
EMPTY_CONTEXT = ("USER PROFILE: none saved yet. If a request needs their background, ask for it or use "
                 "bracketed placeholders. Suggest saving a profile on the Jobs page and Portfolio page.")
CONTEXT_HEADER = ("USER PROFILE (facts the user entered in Jobify; you may use these and what they say in chat, "
                  "nothing else):\n")


def build_user_context(db: Session, user: User) -> str:
    """Profile facts + portfolio sections + application board, rendered for the system prompt."""
    profile = jj.profile_for(db, user)
    row = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
    content = jp.load_content(row.content) if row is not None else None
    lines = [
        *_identity_lines(user, profile, content),
        *_portfolio_lines(content),
        *_application_lines(db, user),
    ]
    return _render(lines)


def _display_name(user: User, ident: jp.Identity | None) -> str:
    # Sign-up may derive a display name from the email when Clerk sends none;
    # that's a guess, not a fact the user entered.
    derived = (user.email or "").split("@")[0].replace(".", " ").title()
    account_name = jp._real_name(user, user.full_name)
    portfolio_name = jp._real_name(user, ident.fullName if ident else None)
    return portfolio_name or (account_name if account_name != derived else "")


def _identity_lines(user: User, profile: CandidateProfile | None, content: jp.PortfolioContent | None) -> list[str]:
    ident = content.identity if content else None
    profile_skills = jj._json_list(profile.skills) if profile else []
    roles = jj._json_list(profile.target_roles) if profile else []
    locations = jj._json_list(profile.target_locations) if profile else []
    years = profile.years_of_experience if profile else None
    skills = list(dict.fromkeys((ident.skills if ident else []) + [s.lower() for s in profile_skills]))
    title = (ident.jobTitle if ident else "") or (profile.current_title if profile else "") or ""
    bio = (ident.bio if ident else "") or (profile.bio_summary if profile else "") or ""
    fields = (
        ("Name", _clip(_display_name(user, ident), 80)),
        ("Current title", _clip(title, 120)),
        # Years alone (no skills) is the profile form's default, not something the user entered.
        ("Years of experience", f"{years:g}" if years is not None and profile_skills else ""),
        ("Skills", ", ".join(skills[:40])),
        ("Target roles", ", ".join(roles[:10])),
        ("Preferred locations", ", ".join(locations[:10])),
        ("Tagline", _clip(ident.tagline if ident else "", 200)),
        ("Bio", _clip(bio, 600)),
    )
    return [f"{label}: {value}" for label, value in fields if value]


def _portfolio_lines(content: jp.PortfolioContent | None) -> list[str]:
    if content is None:
        return []
    lines: list[str] = []
    for key, label in PORTFOLIO_SECTIONS:
        items = getattr(content, key)[:MAX_ITEMS]
        if items:
            lines.append(f"{label}:")
            lines.extend(_item_line(it) for it in items)
    links = [f"{k}: {v}" for k, v in (("website", content.contact.website), ("github", content.socials.github),
                                      ("linkedin", content.socials.linkedin)) if v]
    if links:
        lines.append("Links: " + "; ".join(links))
    return lines


def _item_line(item: jp.Item) -> str:
    head = " — ".join(p for p in (_clip(item.title, 120), _clip(item.subtitle, 120)) if p)
    desc = _clip(item.description, 300)
    return f"- {head}" + (f": {desc}" if desc else "")


def _application_lines(db: Session, user: User) -> list[str]:
    apps = (db.query(Application).filter(Application.user_id == user.id)
            .order_by(Application.id.desc()).limit(MAX_APPS).all())
    if not apps:
        return []
    return [
        f"Job applications on their board (latest {len(apps)}):",
        *(f"- {_clip(a.company, 60) or 'Unknown company'} — {_clip(a.position, 80) or 'role not set'} "
          f"({(a.kanban_stage or 'applied').lower()})" for a in apps),
    ]


def _render(lines: list[str]) -> str:
    if not lines:
        return EMPTY_CONTEXT
    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[: MAX_CHARS - 1].rstrip() + "…"
    return CONTEXT_HEADER + text
