"""
suniel_shetty_startups.py — Registry of Startups from Suniel Shetty's Shows & Direct Portfolio.

Contains startups featured on:
1. "Bharat Ke Super Founders" (Amazon MX Player / Prime Video - Hosted by Suniel Shetty with ₹100 Cr fund)
2. "Horses Stable: Jo Jeeta Wahi Sikandar" (NITI Aayog & MeitY supported reality show mentored/hosted by Suniel Shetty)
3. Suniel Shetty's Direct High-Growth Startup Investments (Waayu, Fittr, Aquatein, Regrip, The Biohacker, etc.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SunielShettyStartup:
    id: str
    name: str
    show_or_source: str  # "Bharat Ke Super Founders", "Horses Stable", "Suniel Shetty Portfolio"
    category: str        # "Gig Economy & B2B", "CleanTech & Circular", "HealthTech & Fitness", "D2C & Consumer", "FoodTech & Delivery", "AgriTech & WasteTech"
    pitch_description: str
    funding_or_backing: str
    domain: Optional[str] = None
    careers_url: Optional[str] = None
    ats_platform: str = "custom"
    key_roles: List[str] = field(default_factory=lambda: ["Software Engineer", "Backend Developer", "Full Stack Engineer", "Founding Engineer"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "show_or_source": self.show_or_source,
            "category": self.category,
            "pitch_description": self.pitch_description,
            "funding_or_backing": self.funding_or_backing,
            "domain": self.domain,
            "careers_url": self.careers_url,
            "ats_platform": self.ats_platform,
            "key_roles": self.key_roles,
        }


SUNIEL_SHETTY_STARTUPS_REGISTRY: List[SunielShettyStartup] = [
    # ── 1. BHARAT KE SUPER FOUNDERS (Amazon MX Player - Hosted by Suniel Shetty) ──
    SunielShettyStartup("digitallabourchowk", "Digital Labour Chowk", "Bharat Ke Super Founders", "Gig Economy & B2B", "Digital marketplace connecting daily-wage construction laborers with contractors", "Funded on Bharat Ke Super Founders", "digitallabourchowk.com", "https://digitallabourchowk.com/careers"),
    SunielShettyStartup("regrip", "Regrip", "Bharat Ke Super Founders", "CleanTech & Circular", "Re-engineered tyre technology & circular economy recycling tech", "Backed by Suniel Shetty & Bharat Ke Super Founders", "regrip.in", "https://regrip.in/careers"),
    SunielShettyStartup("craste", "CRASTE", "Bharat Ke Super Founders", "CleanTech & Circular", "Converting crop stubble waste into circular green packaging & pulp", "Funded on Bharat Ke Super Founders", "craste.co", "https://craste.co/contact"),
    SunielShettyStartup("zozocards", "Zozo Cards", "Bharat Ke Super Founders", "D2C & Consumer", "Smart NFC business cards & digital identity networking platform", "Funded on Bharat Ke Super Founders", "zozocards.com", "https://zozocards.com/careers"),
    SunielShettyStartup("fionadiamonds", "Fiona Diamonds", "Bharat Ke Super Founders", "D2C & Consumer", "Pioneering lab-grown sustainable diamonds & fine jewelry brand", "Funded on Bharat Ke Super Founders", "fionadiamonds.com", "https://fionadiamonds.com/pages/careers"),
    SunielShettyStartup("avniwellness", "Avni Wellness", "Bharat Ke Super Founders", "HealthTech & Fitness", "Organic toxin-free menstrual health & holistic feminine hygiene care", "Funded on Bharat Ke Super Founders", "myavni.com", "https://myavni.com/pages/careers"),
    SunielShettyStartup("naario", "Naario", "Bharat Ke Super Founders", "D2C & Consumer", "India's 1st women-led organic breakfast & packaged food brand", "Funded on Bharat Ke Super Founders", "naario.com", "https://naario.com/pages/about-us"),
    SunielShettyStartup("wevois", "WeVOIS Labs", "Bharat Ke Super Founders", "AgriTech & WasteTech", "AI & IoT-driven automated municipal solid waste collection platform", "Funded on Bharat Ke Super Founders", "wevois.com", "https://wevois.com/careers"),
    SunielShettyStartup("onyc", "ONYC Footwear", "Bharat Ke Super Founders", "D2C & Consumer", "Ergonomic barefoot & orthotic footwear designed for children", "Funded on Bharat Ke Super Founders", "onyc.in", "https://onyc.in/pages/contact"),

    # ── 2. HORSES STABLE (NITI Aayog & MeitY Supported - Mentored by Suniel Shetty) ──
    SunielShettyStartup("medyseva", "Medyseva", "Horses Stable", "HealthTech & Fitness", "Rural telemedicine & e-clinic diagnostic health centers network", "Funded on Horses Stable (ah! Ventures)", "medyseva.com", "https://medyseva.com/careers"),
    SunielShettyStartup("rupyz", "Rupyz", "Horses Stable", "Gig Economy & B2B", "B2B omni-channel e-commerce & distributor management SaaS for SMEs", "Funded on Horses Stable", "rupyz.com", "https://rupyz.com/careers"),
    SunielShettyStartup("lifeofgirl", "LifeOfGirl", "Horses Stable", "HealthTech & Fitness", "AI-driven emergency personal safety tech for women", "Funded on Horses Stable", "lifeofgirl.com", "https://lifeofgirl.com"),
    SunielShettyStartup("pataa", "Pataa Navigation", "Horses Stable", "Gig Economy & B2B", "Digital square-meter address geocoding & navigation infrastructure", "Mentored on Horses Stable", "pataa.com", "https://pataa.com/careers"),
    SunielShettyStartup("strawfit", "Strawfit", "Horses Stable", "D2C & Consumer", "Flavor-infused nutrient-rich milk flavoring drinking straws", "Funded on Horses Stable", "strawfit.com", "https://strawfit.com"),

    # ── 3. SUNIEL SHETTY'S DIRECT HIGH-GROWTH STARTUP INVESTMENTS ─────────────
    SunielShettyStartup("waayu", "Waayu", "Suniel Shetty Portfolio", "FoodTech & Delivery", "Zero-commission restaurant food delivery app backed by AHAR", "Co-founded & Backed by Suniel Shetty", "waayu.app", "https://waayu.app/careers"),
    SunielShettyStartup("fittr", "Fittr", "Suniel Shetty Portfolio", "HealthTech & Fitness", "Global community-driven fitness tech & wellness platform (Series A)", "Backed by Suniel Shetty & Peak XV", "fittr.com", "https://www.fittr.com/careers"),
    SunielShettyStartup("aquatein", "Aquatein", "Suniel Shetty Portfolio", "HealthTech & Fitness", "India's first ready-to-drink protein water innovation brand", "Equity Backed by Suniel Shetty", "aquatein.com", "https://aquatein.com/pages/careers"),
    SunielShettyStartup("thebiohacker", "The Biohacker", "Suniel Shetty Portfolio", "HealthTech & Fitness", "India's first integrative health & cellular longevity recovery clinic", "Backed by Suniel Shetty", "thebiohacker.com", "https://thebiohacker.com"),
    SunielShettyStartup("menoveda", "Menoveda", "Suniel Shetty Portfolio", "HealthTech & Fitness", "Ayurvedic menopause health & women wellness supplement brand", "Backed by Suniel Shetty", "menoveda.com", "https://menoveda.com/pages/careers"),
    SunielShettyStartup("klub", "Klub", "Suniel Shetty Portfolio", "Gig Economy & B2B", "Leading revenue-based financing platform for digital & D2C brands", "Backed by Suniel Shetty & Peak XV", "klubworks.com", "https://klubworks.com/careers"),
]


def get_all_suniel_shetty_startups() -> List[SunielShettyStartup]:
    """Return all startups associated with Suniel Shetty shows and portfolio."""
    return SUNIEL_SHETTY_STARTUPS_REGISTRY


def filter_by_show(show_name: str) -> List[SunielShettyStartup]:
    """Filter startups by show name (e.g. 'Bharat Ke Super Founders', 'Horses Stable')."""
    s_lower = show_name.strip().lower()
    return [s for s in SUNIEL_SHETTY_STARTUPS_REGISTRY if s_lower in s.show_or_source.lower()]


def filter_by_shetty_category(category_name: str) -> List[SunielShettyStartup]:
    """Filter startups by category."""
    cat_lower = category_name.strip().lower()
    return [s for s in SUNIEL_SHETTY_STARTUPS_REGISTRY if cat_lower in s.category.lower()]
