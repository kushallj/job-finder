"""
referral_engine.py — People Discovery & Referral Network Engine for Tier-1 Tech Companies.

Implements Strategy 2:
  1. Generates targeted Boolean & X-Ray search queries to locate Senior Engineers, Tech Leads,
     Engineering Managers, and Alumni at top-tier companies.
  2. Executes live searches via SerpAPI / Google CSE / Serper.
  3. Generates high-conversion referral outreach messages tailored to 4-YOE candidate background.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx

from src.config import settings
from src.tier1_companies import get_tier1_company

logger = logging.getLogger(__name__)


def generate_referral_xray_queries(
    company_name: str,
    locations: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """Generate high-yield LinkedIn X-Ray query strings for a target company."""
    loc_str = ' OR '.join(f'"{loc}"' for loc in (locations or ["Bengaluru", "Bangalore", "Hyderabad", "Delhi NCR", "Remote"]))
    comp = get_tier1_company(company_name)
    display_name = comp.name if comp else company_name

    queries = [
        {
            "category": "Senior Engineers & Tech Leads (Direct Peers)",
            "query": f'site:linkedin.com/in ("Senior Software Engineer" OR "Staff Engineer" OR "Tech Lead" OR "SDE II" OR "SDE 3") "{display_name}" ({loc_str})',
            "purpose": "Find engineers at same/higher level who can vouch for backend/full-stack technical depth."
        },
        {
            "category": "Engineering Managers & Hiring Leaders",
            "query": f'site:linkedin.com/in ("Engineering Manager" OR "Software Engineering Manager" OR "Director of Engineering") "{display_name}" ({loc_str})',
            "purpose": "Direct outreach to decision makers managing engineering pods."
        },
        {
            "category": "Technical Recruiters & Talent Partners",
            "query": f'site:linkedin.com/in ("Technical Recruiter" OR "Talent Acquisition" OR "Engineering Recruiter") "{display_name}" ({loc_str})',
            "purpose": "Reach the recruiter handling tech pipelines for this company."
        }
    ]
    return queries


async def search_company_referral_contacts(
    company_name: str,
    max_leads: int = 10,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> List[Dict[str, Any]]:
    """Execute live X-Ray search using configured SerpAPI / Serper / Google CSE."""
    api_key = (
        getattr(settings, "serpapi_api_key", None)
        or getattr(settings, "serp_api_key", None)
    )
    if not api_key:
        logger.warning("No SerpAPI key found. Generating query templates only.")
        return []

    queries = generate_referral_xray_queries(company_name)
    primary_query = queries[0]["query"]

    leads: List[Dict[str, Any]] = []
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": primary_query,
        "api_key": api_key,
        "num": max_leads,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, transport=transport) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        organic_results = data.get("organic_results", [])
        for item in organic_results:
            title_text = item.get("title", "")
            snippet_text = item.get("snippet", "")
            link = item.get("link", "")
            if "linkedin.com/in/" not in link:
                continue

            # Heuristic name extraction from LinkedIn title: "Name - Title - Company | LinkedIn"
            name_part = title_text.split(" - ")[0].split(" | ")[0].strip()
            role_part = title_text.split(" - ")[1] if " - " in title_text else "Engineer"

            leads.append({
                "name": name_part,
                "role": role_part,
                "company": company_name,
                "linkedin_url": link,
                "snippet": snippet_text,
                "source": "serpapi_xray",
            })
    except Exception as exc:
        logger.error("SerpAPI X-Ray search failed for %s: %s", company_name, exc)

    return leads[:max_leads]


def compose_referral_request(
    contact_name: str,
    company_name: str,
    role_title: Optional[str] = "Software Engineer",
    job_id_or_url: Optional[str] = None,
    candidate_name: str = "Kushall Jain",
    candidate_yoe: str = "3+",
    tech_stack: str = "Python, FastAPI, distributed backend systems & PostgreSQL",
) -> Dict[str, str]:
    """Compose crisp, high-conversion referral outreach message & LinkedIn note."""
    first_name = contact_name.split()[0] if contact_name else "there"
    comp = get_tier1_company(company_name)
    display_comp = comp.name if comp else company_name
    level_str = f" ({comp.likely_level})" if comp else ""

    # Short LinkedIn Connection Request Note (<300 chars)
    connection_note = (
        f"Hi {first_name}, I follow {display_comp}'s engineering work. I'm a SWE with {candidate_yoe} YOE ({tech_stack}). "
        f"I'm exploring {role_title} openings at {display_comp} and would love to connect!"
    )[:298]

    # Full InMail / Email Referral Request Message
    full_message = f"""Hi {first_name},

Hope you are doing well!

I noticed you're working as {comp.likely_level if comp else 'an Engineer'} at {display_comp}. I've been following {display_comp}'s engineering initiatives and product growth closely.

I am a Software Engineer with {candidate_yoe} years of experience building high-throughput REST APIs, asynchronous microservices, and distributed backend architectures ({tech_stack}).

I came across the {role_title}{level_str} opening at {display_comp}{f' (Ref: {job_id_or_url})' if job_id_or_url else ''} and believe my technical background in scalable backend design is a direct fit for the team.

Would you be open to submitting a quick internal referral for my profile?

I've attached a 2-line summary and links below to make it effortless for you:
• Role: {role_title}
• Experience: {candidate_yoe} YOE in backend engineering, database optimization, and cloud services
• Profile / Portfolio: https://github.com/kushallj | https://linkedin.com/in/kushall-jain-263009261

Thank you so much for your time and help!

Best regards,
{candidate_name}
"""

    return {
        "connection_note_300chars": connection_note,
        "full_referral_message": full_message,
        "target_company": display_comp,
        "target_role": role_title,
    }
