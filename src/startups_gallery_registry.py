"""
startups_gallery_registry.py — Curated Registry of 1,369 Early-Stage & High-Growth Startups
from startups.gallery (backed by YC, Sequoia, a16z, Accel, and leading venture funds).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "startups_gallery_companies.json",
)


@dataclass
class StartupsGalleryCompany:
    slug: str
    name: str
    domain: str
    category: str
    funding: str
    location: str
    founded_year: str
    description: str
    investors: List[str] = field(default_factory=list)
    jobs: List[str] = field(default_factory=list)
    jobs_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "domain": self.domain,
            "category": self.category,
            "funding": self.funding,
            "location": self.location,
            "founded_year": self.founded_year,
            "description": self.description,
            "investors": self.investors,
            "jobs": self.jobs,
            "jobs_count": self.jobs_count,
        }


def _load_registry() -> List[StartupsGalleryCompany]:
    """Loads all startups.gallery companies from cached JSON dataset."""
    if not os.path.exists(DATA_PATH):
        return []

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            items = json.load(f)
        return [
            StartupsGalleryCompany(
                slug=item.get("slug", ""),
                name=item.get("name", ""),
                domain=item.get("domain", f"{item.get('slug', '')}.com"),
                category=item.get("category", "AI"),
                funding=item.get("funding", ""),
                location=item.get("location", "Remote / Global"),
                founded_year=item.get("founded_year", ""),
                description=item.get("description", ""),
                investors=item.get("investors", []),
                jobs=item.get("jobs", []),
                jobs_count=item.get("jobs_count", len(item.get("jobs", []))),
            )
            for item in items
        ]
    except Exception:
        return []


STARTUPS_GALLERY_REGISTRY: List[StartupsGalleryCompany] = _load_registry()


def get_all_startups_gallery_companies() -> List[StartupsGalleryCompany]:
    """Return all 1,369 startups in the registry."""
    return STARTUPS_GALLERY_REGISTRY


def get_company_by_slug(slug: str) -> Optional[StartupsGalleryCompany]:
    """Find company by its URL slug."""
    clean = slug.strip().lower()
    for c in STARTUPS_GALLERY_REGISTRY:
        if c.slug.lower() == clean:
            return c
    return None


def filter_by_category(category: str) -> List[StartupsGalleryCompany]:
    """Filter companies by sector (e.g. AI, Fintech, Cybersecurity, DevTools)."""
    target = category.strip().lower()
    return [c for c in STARTUPS_GALLERY_REGISTRY if target in c.category.lower()]


def filter_by_location(location: str) -> List[StartupsGalleryCompany]:
    """Filter companies by location substring (e.g. San Francisco, New York, London, India)."""
    target = location.strip().lower()
    return [c for c in STARTUPS_GALLERY_REGISTRY if target in c.location.lower()]


def search_startups(keyword: str) -> List[StartupsGalleryCompany]:
    """Search companies by name or description."""
    q = keyword.strip().lower()
    return [
        c
        for c in STARTUPS_GALLERY_REGISTRY
        if q in c.name.lower() or q in c.description.lower() or q in c.category.lower()
    ]


def get_category_breakdown() -> Dict[str, int]:
    """Calculate company counts grouped by industry category."""
    counts: Dict[str, int] = {}
    for c in STARTUPS_GALLERY_REGISTRY:
        counts[c.category] = counts.get(c.category, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
