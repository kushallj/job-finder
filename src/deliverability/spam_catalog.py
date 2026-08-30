from __future__ import annotations

from typing import Dict, List, Tuple

# Comprehensive B2B Spam Trigger Dictionary with replacement suggestions
SPAM_CATALOG: Dict[str, Dict[str, any]] = {
    # Urgency Triggers
    "urgent": {"category": "urgency", "severity": "critical", "alts": ["timely", "priority", "relevant"]},
    "immediately": {"category": "urgency", "severity": "warning", "alts": ["soon", "at your earliest convenience", "when time permits"]},
    "act now": {"category": "urgency", "severity": "critical", "alts": ["happy to connect", "open to discussing"]},
    "limited time": {"category": "urgency", "severity": "critical", "alts": ["current", "this quarter"]},
    "don't miss": {"category": "urgency", "severity": "warning", "alts": ["worth noting", "sharing in case relevant"]},
    "asap": {"category": "urgency", "severity": "warning", "alts": ["when possible", "at your convenience"]},

    # Financial / Hype Triggers
    "guarantee": {"category": "financial_hype", "severity": "critical", "alts": ["demonstrated", "proven", "track record"]},
    "guaranteed": {"category": "financial_hype", "severity": "critical", "alts": ["validated", "consistently delivered"]},
    "100% free": {"category": "financial_hype", "severity": "critical", "alts": ["complimentary", "open-source", "no-obligation"]},
    "make money": {"category": "financial_hype", "severity": "critical", "alts": ["drive revenue", "increase EBITDA", "business impact"]},
    "risk free": {"category": "financial_hype", "severity": "critical", "alts": ["low-friction", "seamless", "straightforward"]},
    "once in a lifetime": {"category": "financial_hype", "severity": "critical", "alts": ["rare opportunity", "compelling role"]},
    "billion dollar": {"category": "financial_hype", "severity": "warning", "alts": ["enterprise-scale", "high-growth"]},

    # Aggressive / Pushy CTAs
    "call me now": {"category": "aggressive_cta", "severity": "critical", "alts": ["open to a brief intro chat?", "happy to find 10 mins"]},
    "reply immediately": {"category": "aggressive_cta", "severity": "critical", "alts": ["let me know your thoughts", "would love your feedback"]},
    "click here": {"category": "aggressive_cta", "severity": "critical", "alts": ["attached resume", "profile link below"]},
    "must read": {"category": "aggressive_cta", "severity": "warning", "alts": ["quick context", "summary"]},
    "reminder: final notice": {"category": "aggressive_cta", "severity": "critical", "alts": ["quick follow up", "circling back"]},

    # Generic Sourcing Buzzwords
    "rockstar": {"category": "spam_formatting", "severity": "warning", "alts": ["senior engineer", "high-impact builder"]},
    "ninja": {"category": "spam_formatting", "severity": "warning", "alts": ["specialist", "staff engineer"]},
    "guru": {"category": "spam_formatting", "severity": "warning", "alts": ["domain expert", "technical lead"]},
    "10x engineer": {"category": "spam_formatting", "severity": "warning", "alts": ["high-velocity contributor", "senior technical talent"]},
}
