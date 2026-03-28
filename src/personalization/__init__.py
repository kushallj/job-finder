"""
src/personalization — Personalization Engine (Task 5)

Converts generic outreach into hyper-personalized messages by researching:
  - The company  (GitHub org, blog, HN mentions, tech signals)
  - The contact  (GitHub profile, public repos, technical interests)
  - The role fit (resume achievements ↔ JD requirements alignment)

Pipeline:
  company + contact + job
      ↓
  CompanyResearcher  →  CompanyProfile
  ContactResearcher  →  ContactProfile
      ↓
  HookGenerator      →  List[Hook]   (genuine connection points)
      ↓
  EmailComposer      →  PersonalizedEmail  (subject + body ≤ 150 words)
      ↓
  PersonalizationEngine → PersonalizedOutreach  (email + cover_letter + score)
"""

from .models import (
    CompanyProfile,
    ContactProfile,
    Hook,
    HookType,
    PersonalizedEmail,
    PersonalizedOutreach,
)
from .company_researcher import CompanyResearcher
from .contact_researcher import ContactResearcher
from .hook_generator import HookGenerator
from .email_composer import EmailComposer
from .personalization_engine import PersonalizationEngine, get_engine

__all__ = [
    "CompanyProfile",
    "ContactProfile",
    "Hook",
    "HookType",
    "PersonalizedEmail",
    "PersonalizedOutreach",
    "CompanyResearcher",
    "ContactResearcher",
    "HookGenerator",
    "EmailComposer",
    "PersonalizationEngine",
    "get_engine",
]
