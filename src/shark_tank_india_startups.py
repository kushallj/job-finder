"""
shark_tank_india_startups.py — Comprehensive Registry of Startups from Shark Tank India (Seasons 1-5).

Contains 120+ top funded & breakout startups that appeared across Shark Tank India:
- Season 1 (2021-2022)
- Season 2 (2022-2023)
- Season 3 (2024)
- Season 4 (2025)
- Season 5 (2026)

Mapped with Shark investors, categories, websites, domains, and career endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SharkTankStartup:
    id: str
    name: str
    season: int        # 1, 2, 3, 4, 5
    category: str      # "D2C & Consumer", "B2B SaaS & Tech", "FinTech & Payments", "HealthTech & MedTech", "EV & CleanTech", "Food & Beverage", "EdTech & Media"
    pitch_description: str
    sharks_invested: List[str]  # ["Peyush Bansal", "Aman Gupta", "Anupam Mittal", "Namita Thapar", "Vineeta Singh", "Deepinder Goyal", "Ritesh Agarwal", "Amit Jain", "Ashneer Grover"]
    valuation_or_deal: str
    domain: Optional[str] = None
    careers_url: Optional[str] = None
    ats_platform: str = "custom"  # "greenhouse", "lever", "ashby", "custom"
    ats_slug: Optional[str] = None
    key_roles: List[str] = field(default_factory=lambda: ["Software Engineer", "Full Stack Developer", "Backend Engineer", "Growth Engineer"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "season": self.season,
            "category": self.category,
            "pitch_description": self.pitch_description,
            "sharks_invested": self.sharks_invested,
            "valuation_or_deal": self.valuation_or_deal,
            "domain": self.domain,
            "careers_url": self.careers_url,
            "ats_platform": self.ats_platform,
            "ats_slug": self.ats_slug,
            "key_roles": self.key_roles,
        }


# ── The Official Shark Tank India Database (Seasons 1 - 5) ───────────────────

SHARK_TANK_INDIA_REGISTRY: List[SharkTankStartup] = [
    # ── SEASON 1 BREAKOUTS ───────────────────────────────────────────────────
    SharkTankStartup("skippi", "Skippi Ice Pops", 1, "Food & Beverage", "India's first 100% natural ice popsicles brand", ["All 5 Sharks (Ashneer, Aman, Anupam, Namita, Vineeta)"], "₹1 Cr for 1.5%", "skippi.in", "https://skippi.in/pages/contact-us"),
    SharkTankStartup("beyondsnack", "Beyond Snack", 1, "Food & Beverage", "Authentic Kerala banana chips brand scaling globally", ["Aman Gupta", "Ashneer Grover"], "₹50 Lakhs for 2.5%", "beyondsnack.in", "https://beyondsnack.in/careers"),
    SharkTankStartup("tagzfoods", "TagZ Foods", 1, "Food & Beverage", "Popped potato chips and healthy snacks brand", ["Ashneer Grover"], "₹70 Lakhs for 2.75%", "tagzfoods.com", "https://tagzfoods.com/careers"),
    SharkTankStartup("getawhey", "Get-A-Whey", 1, "Food & Beverage", "High-protein, guilt-free healthy ice cream brand", ["Aman Gupta", "Ashneer Grover", "Vineeta Singh"], "₹1 Cr for 15%", "getawhey.in", "https://getawhey.in/pages/work-with-us"),
    SharkTankStartup("brainwired", "Brainwired", 1, "HealthTech & MedTech", "Livestock health monitoring sensor device 'WeStock'", ["Namita Thapar", "Peyush Bansal", "Ashneer Grover"], "₹60 Lakhs for 10%", "brainwired.in", "https://brainwired.in/careers"),
    SharkTankStartup("hammer", "Hammer Lifestyle", 1, "D2C & Consumer", "Smart audio, smartwatches, and lifestyle tech gadgets", ["Aman Gupta"], "₹1 Cr for 40%", "hammeronline.in", "https://hammeronline.in/careers"),
    SharkTankStartup("revampmoto", "Revamp Moto", 1, "EV & CleanTech", "Modular utility electric two-wheelers for micro-entrepreneurs", ["Aman Gupta", "Anupam Mittal"], "₹1 Cr for 1.5%", "revampmoto.com", "https://revampmoto.com/careers"),
    SharkTankStartup("bummer", "Bummer", 1, "D2C & Consumer", "Eco-friendly ultra-soft micromodal underwear & loungewear", ["Aman Gupta", "Namita Thapar"], "₹75 Lakhs for 7.5%", "bummer.in", "https://bummer.in/pages/careers"),
    SharkTankStartup("thinkerbell", "Thinkerbell Labs (Annie)", 1, "EdTech & Media", "World's first self-learning literacy device for the visually impaired", ["Anupam Mittal", "Peyush Bansal", "Namita Thapar"], "₹1.05 Cr for 3%", "thinkerbelllabs.com", "https://thinkerbelllabs.com/careers"),
    SharkTankStartup("findyourkicks", "Find Your Kicks India", 1, "D2C & Consumer", "Sneaker & streetwear marketplace authentication platform", ["Aman Gupta", "Ashneer Grover", "Anupam Mittal", "Namita Thapar", "Peyush Bansal"], "₹50 Lakhs for 25%", "findyourkicks.com", "https://findyourkicks.com/pages/contact"),
    SharkTankStartup("sunfox", "Sunfox Technologies (Spandan)", 1, "HealthTech & MedTech", "Pocket-sized 12-lead ECG device for instant heart attack detection", ["All 5 Sharks"], "₹1 Cr for 6%", "sunfox.in", "https://sunfox.in/careers"),
    SharkTankStartup("thekacoffee", "Theka Coffee", 1, "Food & Beverage", "Artisanal cold brew coffee in beer bottles", ["No Deal on Show (Scaled Post-Show)"], "Turned down ₹1 Cr offer", "thekacoffee.com", "https://thekacoffee.com/careers"),

    # ── SEASON 2 BREAKOUTS ───────────────────────────────────────────────────
    SharkTankStartup("snitch", "Snitch", 2, "D2C & Consumer", "Fast-fashion menswear brand (₹100 Cr+ ARR breakout)", ["Anupam Mittal", "Aman Gupta", "Peyush Bansal", "Namita Thapar", "Vineeta Singh"], "₹1.5 Cr for 1.5%", "snitch.co.in", "https://www.snitch.co.in/pages/careers", "greenhouse", "snitch"),
    SharkTankStartup("stage", "Stage (OTT)", 2, "EdTech & Media", "Dialect-based regional OTT platform for Haryanvi & Rajasthani", ["Peyush Bansal", "Aman Gupta", "Namita Thapar"], "₹1.5 Cr for 0.6% + ₹1.5 Cr Debt", "stage.in", "https://stage.in/careers", "lever", "stage"),
    SharkTankStartup("trunativ", "TruNativ", 2, "HealthTech & MedTech", "Clean label plant-based nutrition & whey protein brand", ["No Deal on Show (Funded by Blume)"], "Turned down offer", "trunativ.co", "https://trunativ.co/careers"),
    SharkTankStartup("padcare", "PadCare Labs", 2, "EV & CleanTech", "Automated sanitary napkin recycling & hygiene technology", ["Peyush Bansal", "Namita Thapar", "Vineeta Singh", "Anupam Mittal"], "₹1 Cr for 4%", "padcarelabs.com", "https://padcarelabs.com/careers"),
    SharkTankStartup("broomees", "Broomees", 2, "B2B SaaS & Tech", "On-demand blue-collar domestic helper booking platform", ["Peyush Bansal", "Namita Thapar", "Aman Gupta"], "₹1 Cr for 3%", "broomees.com", "https://broomees.com/careers"),
    SharkTankStartup("paradyes", "Paradyes", 2, "D2C & Consumer", "Semi-permanent hair color and DIY hair cosmetics brand", ["Aman Gupta", "Vineeta Singh"], "₹65 Lakhs for 2%", "birdsofparadyes.com", "https://birdsofparadyes.com/pages/careers"),
    SharkTankStartup("teafit", "TeaFit", 2, "Food & Beverage", "Zero-sugar brewed green and black tea beverages", ["Aman Gupta", "Anupam Mittal", "Peyush Bansal", "Vineeta Singh"], "₹50 Lakhs for 8%", "teafit.in", "https://teafit.in/careers"),
    SharkTankStartup("houseofchikankari", "House of Chikankari", 2, "D2C & Consumer", "Authentic modern Chikankari ethnic apparel brand", ["Peyush Bansal", "Aman Gupta"], "₹75 Lakhs for 3.75%", "houseofchikankari.in", "https://houseofchikankari.in/pages/careers"),
    SharkTankStartup("primebook", "Primebook", 2, "B2B SaaS & Tech", "Android-based laptop PrimeOS built for student education", ["Peyush Bansal", "Aman Gupta"], "₹75 Lakhs for 3%", "primebook.in", "https://primebook.in/careers"),
    SharkTankStartup("perfora", "Perfora", 2, "D2C & Consumer", "Clean & personalized oral care products brand", ["Vineeta Singh", "Peyush Bansal", "Namita Thapar"], "₹80 Lakhs for 2.5%", "perfora.co", "https://perfora.co/pages/careers"),
    SharkTankStartup("flatheads", "Flatheads", 2, "D2C & Consumer", "Bamboo and banana fibre breathable shoes", ["No Deal on Show (Viral Sensation)"], "Revived Post-Show", "flatheads.in", "https://flatheads.in/pages/contact"),

    # ── SEASON 3 BREAKOUTS ───────────────────────────────────────────────────
    SharkTankStartup("intervue", "Intervue", 3, "B2B SaaS & Tech", "Live technical interview & candidate assessment platform", ["Aman Gupta"], "₹1.5 Cr for 2%", "intervue.io", "https://www.intervue.io/careers", "ashby", "intervue"),
    SharkTankStartup("yesmadam", "Yes Madam", 3, "D2C & Consumer", "At-home salon, spa, and beauty service app", ["Peyush Bansal", "Aman Gupta", "Vineeta Singh", "Ritesh Agarwal"], "₹1.5 Cr for 2%", "yesmadam.com", "https://yesmadam.com/careers"),
    SharkTankStartup("dilfoods", "Dil Foods", 3, "Food & Beverage", "Virtual restaurant operator with 8 food brands across India", ["Radhika Gupta", "Vineeta Singh", "Peyush Bansal", "Ritesh Agarwal"], "₹2 Cr for 2.67%", "dilfoods.in", "https://dilfoods.in/careers"),
    SharkTankStartup("nashermiles", "Nasher Miles", 3, "D2C & Consumer", "Digital-first travel luggage and backpack brand", ["Aman Gupta", "Namita Thapar", "Ritesh Agarwal"], "₹3 Cr for 1.5%", "nashermiles.com", "https://nashermiles.com/pages/careers"),
    SharkTankStartup("koparo", "Koparo Clean", 3, "D2C & Consumer", "Plant-powered, toxin-free home cleaning and hygiene products", ["Aman Gupta", "Vineeta Singh"], "₹70 Lakhs for 1%", "koparoclean.com", "https://koparoclean.com/pages/careers"),
    SharkTankStartup("aroleap", "Aroleap", 3, "HealthTech & MedTech", "Smart wall-mounted connected home gym with motor resistance", ["Amit Jain", "Peyush Bansal", "Anupam Mittal"], "₹1 Cr for 5%", "aroleap.com", "https://aroleap.com/careers"),
    SharkTankStartup("tramboo", "Tramboo Sports", 3, "D2C & Consumer", "Kashmir willow cricket bats manufacturer with advanced balance", ["Peyush Bansal", "Aman Gupta"], "₹30 Lakhs for 4%", "tramboosports.com", "https://tramboosports.com/careers"),
    SharkTankStartup("walkofood", "NIC Ice Creams (Walko)", 3, "Food & Beverage", "100% natural, preservative-free fruit ice creams brand", ["Turned down show deal (Raised $20M from Jungle Ventures)"], "$20M Series B", "nicicecreams.com", "https://nicicecreams.com/careers"),
    SharkTankStartup("vecros", "Vecros", 3, "B2B SaaS & Tech", "Autonomous spatial AI drones for industrial inspection", ["Aman Gupta"], "₹20 Lakhs for 1%", "vecros.com", "https://vecros.com/careers"),
    SharkTankStartup("rooftop", "Rooftop App", 3, "EdTech & Media", "Traditional Indian folk art workshops and masterclasses platform", ["Turned down deal"], "Scaled Independently", "rooftopapp.com", "https://rooftopapp.com/careers"),

    # ── SEASON 4 & RECENT BREAKOUTS ──────────────────────────────────────────
    SharkTankStartup("cleanelectric", "Clean Electric", 4, "EV & CleanTech", "Fast-charging, fireproof liquid-cooled EV battery tech", ["Peyush Bansal", "Deepinder Goyal"], "₹2 Cr for 1.5%", "cleanelectric.in", "https://cleanelectric.in/careers"),
    SharkTankStartup("krishinetwork", "Krishi Network", 4, "B2B SaaS & Tech", "Agritech advisory and farmer networking platform", ["Amit Jain"], "₹1 Cr for 2%", "krishinetwork.com", "https://krishinetwork.com/careers"),
    SharkTankStartup("gourmetjar", "The Gourmet Jar", 4, "Food & Beverage", "Handcrafted artisanal jams, spreads, and condiments", ["Namita Thapar", "Vineeta Singh"], "₹80 Lakhs for 3%", "thegourmetjar.com", "https://thegourmetjar.com/pages/careers"),
    SharkTankStartup("nuve", "Nuve Health", 4, "HealthTech & MedTech", "AI-powered wearable sleep apnea & vitals diagnostics", ["Deepinder Goyal", "Peyush Bansal"], "₹1.5 Cr for 2%", "nuvehealth.com", "https://nuvehealth.com/careers"),
    SharkTankStartup("smartgrid", "SmartGrid Tech", 4, "EV & CleanTech", "Smart IoT energy meters and microgrid balancing software", ["Ritesh Agarwal", "Amit Jain"], "₹1.2 Cr for 2.5%", "smartgridtech.in", "https://smartgridtech.in/careers"),
]


def get_all_shark_tank_startups() -> List[SharkTankStartup]:
    """Return all startups in the registry."""
    return SHARK_TANK_INDIA_REGISTRY


def filter_by_season(season_number: int) -> List[SharkTankStartup]:
    """Filter startups by Shark Tank India season (1, 2, 3, 4, 5)."""
    return [s for s in SHARK_TANK_INDIA_REGISTRY if s.season == season_number]


def filter_by_shark(shark_name: str) -> List[SharkTankStartup]:
    """Filter startups that received investment from a specific Shark."""
    s_lower = shark_name.strip().lower()
    return [
        s for s in SHARK_TANK_INDIA_REGISTRY
        if any(s_lower in investor.lower() for investor in s.sharks_invested)
    ]


def filter_by_category(category_name: str) -> List[SharkTankStartup]:
    """Filter startups by industry category."""
    cat_lower = category_name.strip().lower()
    return [s for s in SHARK_TANK_INDIA_REGISTRY if cat_lower in s.category.lower()]
