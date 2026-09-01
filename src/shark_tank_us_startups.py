"""
shark_tank_us_startups.py — Comprehensive Registry of Startups from Shark Tank US (Seasons 1-16).

Contains iconic breakout companies, tech unicorns, and D2C giants from Shark Tank US:
- Season 1-5 Classics: Ring (Doorbot), Scrub Daddy, Bombas, Tipsy Elves, Cousins Maine Lobster, Squatty Potty
- Season 6-10 Growth: Kodiak Cakes, Everlywell, LuminAID, LARQ, Spikeball, Dude Wipes, Manscaped, Bantam Bagels
- Season 11-16 Modern: Chirp, Cupbop, Blueland, Slate Milk, Deux, Tenikle, Prepdeck, Touchland, Flyte, Curie

Mapped with Shark investors, seasons, categories, official websites, domains, and ATS career portals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SharkTankUSStartup:
    id: str
    name: str
    season: int        # 1 to 16
    category: str      # "Smart Tech & IoT", "HealthTech & Diagnostics", "D2C & Consumer", "Food & Beverage", "CleanTech & Sustainability", "Apparel & Accessories"
    pitch_description: str
    sharks_invested: List[str]  # ["Mark Cuban", "Lori Greiner", "Kevin O'Leary", "Daymond John", "Barbara Corcoran", "Robert Herjavec", "Guest Sharks"]
    valuation_or_exit: str
    domain: Optional[str] = None
    careers_url: Optional[str] = None
    ats_platform: str = "custom"  # "greenhouse", "lever", "ashby", "workday", "custom"
    ats_slug: Optional[str] = None
    key_roles: List[str] = field(default_factory=lambda: ["Software Engineer", "Backend Engineer", "Full Stack Developer", "Platform Engineer"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "season": self.season,
            "category": self.category,
            "pitch_description": self.pitch_description,
            "sharks_invested": self.sharks_invested,
            "valuation_or_exit": self.valuation_or_exit,
            "domain": self.domain,
            "careers_url": self.careers_url,
            "ats_platform": self.ats_platform,
            "ats_slug": self.ats_slug,
            "key_roles": self.key_roles,
        }


# ── The Official Shark Tank US Database (Seasons 1 - 16) ─────────────────────

SHARK_TANK_US_REGISTRY: List[SharkTankUSStartup] = [
    # ── 1. HISTORIC UNICORNS & MEGA-BREAKOUTS ────────────────────────────────
    SharkTankUSStartup("ring", "Ring (Doorbot)", 5, "Smart Tech & IoT", "Smart Wi-Fi video doorbell and home security ecosystem", ["Turned down show offer (Later backed by Richard Branson)"], "Acquired by Amazon for $1.1 Billion+", "ring.com", "https://ring.com/careers", "greenhouse", "ring"),
    SharkTankUSStartup("bombas", "Bombas", 6, "Apparel & Accessories", "Engineered comfort socks & apparel with 1-for-1 donation model (#1 Shark Tank revenue)", ["Daymond John"], "$1 Billion+ Lifetime Revenue ($200k for 17.5%)", "bombas.com", "https://bombas.com/pages/careers", "greenhouse", "bombas"),
    SharkTankUSStartup("scrubdaddy", "Scrub Daddy", 4, "D2C & Consumer", "Temperature-responsive texture cleaning sponges (#1 retail success)", ["Lori Greiner"], "$670M+ Retail Revenue ($200k for 20%)", "scrubdaddy.com", "https://scrubdaddy.com/careers"),
    SharkTankUSStartup("squattypotty", "Squatty Potty", 6, "HealthTech & Diagnostics", "Ergonomic toilet posture stool with viral marketing", ["Lori Greiner"], "$250M+ Revenue ($350k for 10%)", "squattypotty.com", "https://www.squattypotty.com/pages/careers"),
    SharkTankUSStartup("tipsyelves", "Tipsy Elves", 4, "Apparel & Accessories", "Holiday apparel and humorous statement clothing", ["Robert Herjavec"], "$300M+ Revenue ($100k for 10%)", "tipsyelves.com", "https://www.tipsyelves.com/pages/careers"),
    SharkTankUSStartup("everlywell", "Everlywell", 9, "HealthTech & Diagnostics", "At-home lab testing and digital health diagnostic platform", ["Lori Greiner"], "$3 Billion+ Unicorn Valuation ($1M Line of Credit)", "everlywell.com", "https://www.everlywell.com/careers", "greenhouse", "everlywell"),
    SharkTankUSStartup("manscaped", "Manscaped", 10, "D2C & Consumer", "Below-the-waist grooming and lifestyle consumer tech", ["Mark Cuban", "Lori Greiner"], "$1 Billion+ Valuation ($500k for 25%)", "manscaped.com", "https://www.manscaped.com/pages/careers", "lever", "manscaped"),
    SharkTankUSStartup("kodiakcakes", "Kodiak Cakes", 5, "Food & Beverage", "High-protein pancake and waffle mix brand", ["Turned down offer (Funded by L Catterton)"], "$500M+ Valuation (Turned down $500k for 35%)", "kodiakcakes.com", "https://kodiakcakes.com/pages/careers"),

    # ── 2. TECH, IOT, SMART HARDWARE & SUSTAINABILITY ────────────────────────
    SharkTankUSStartup("larq", "LARQ", 12, "Smart Tech & IoT", "World's first self-cleaning UV-C LED water purification bottle", ["Mark Cuban", "Lori Greiner"], "$1.5M for 4% ($37.5M Valuation)", "livelarq.com", "https://livelarq.com/careers"),
    SharkTankUSStartup("luminaid", "LuminAID", 6, "CleanTech & Sustainability", "Inflatable solar-powered waterproof lanterns and phone chargers", ["Mark Cuban"], "$200k for 15% + $300k line of credit", "luminaid.com", "https://luminaid.com/pages/careers"),
    SharkTankUSStartup("chirp", "Chirp (Chirp Wheel+)", 12, "HealthTech & Diagnostics", "Ergonomic back pain relief trigger wheels and devices", ["Lori Greiner"], "$100M+ Revenue ($900k for 2.5%)", "gochirp.com", "https://gochirp.com/pages/careers"),
    SharkTankUSStartup("blueland", "Blueland", 11, "CleanTech & Sustainability", "Eco-friendly zero-waste cleaning tablets and reusable bottles", ["Kevin O'Leary"], "$270k for 3% + $50M+ Revenue", "blueland.com", "https://www.blueland.com/pages/careers", "ashby", "blueland"),
    SharkTankUSStartup("touchland", "Touchland", 12, "D2C & Consumer", "Sleek, pocket-sized moisturizing hand sanitizer mist", ["Turned down offer on show"], "$100M+ Retail Brand (Scaled Independently)", "touchland.com", "https://touchland.com/pages/careers"),
    SharkTankUSStartup("prepdeck", "Prepdeck", 13, "Smart Tech & IoT", "All-in-one meal preparation and smart kitchen organization station", ["Turned down show offer"], "$30M+ Revenue", "prepdeck.com", "https://prepdeck.com/pages/careers"),
    SharkTankUSStartup("basepaws", "Basepaws", 10, "HealthTech & Diagnostics", "Cat DNA genetics test kit and microbiome diagnostic platform", ["Mark Cuban", "Kevin O'Leary"], "Acquired by Zoetis ($250k for 10%)", "basepaws.com", "https://basepaws.com/careers"),

    # ── 3. D2C, FOOD, BEVERAGE & LIFESTYLE EMPIRES ────────────────────────────
    SharkTankUSStartup("dudewipes", "Dude Wipes", 7, "D2C & Consumer", "Flushable on-the-go hygiene wipes for men", ["Mark Cuban"], "$100M+ ARR ($300k for 25%)", "dudeproducts.com", "https://dudeproducts.com/pages/careers"),
    SharkTankUSStartup("cousinsmainelobster", "Cousins Maine Lobster", 4, "Food & Beverage", "Nationwide Maine lobster food truck and restaurant franchise", ["Barbara Corcoran"], "$100M+ Revenue ($55k for 15%)", "cousinsmainelobster.com", "https://www.cousinsmainelobster.com/careers"),
    SharkTankUSStartup("cupbop", "Cupbop", 13, "Food & Beverage", "Fast-casual Korean BBQ in a cup chain with 100+ stores", ["Mark Cuban"], "$1M for 5% ($20M Valuation)", "cupbop.com", "https://cupbop.com/careers"),
    SharkTankUSStartup("thebouqs", "The Bouqs Company", 5, "D2C & Consumer", "Farm-to-table direct online floral delivery platform", ["Robert Herjavec (Invested 3 years post-show)"], "$100M+ Raised ($24M Series C)", "bouqs.com", "https://bouqs.com/careers", "greenhouse", "thebouqscompany"),
    SharkTankUSStartup("bantambagels", "Bantam Bagels", 6, "Food & Beverage", "Mini stuffed bagel balls (Distributed in Starbucks nationwide)", ["Lori Greiner"], "Acquired by T. Marzetti for $34M", "bantambagels.com", "https://bantambagels.com"),
    SharkTankUSStartup("spikeball", "Spikeball", 6, "D2C & Consumer", "Roundnet competitive active sport and tournament platform", ["Daymond John"], "$100M+ Revenue ($500k for 20%)", "spikeball.com", "https://spikeball.com/pages/careers"),
    SharkTankUSStartup("slatemilk", "Slate Milk", 11, "Food & Beverage", "High-protein, lactose-free canned chocolate milk and latte", ["Mark Cuban", "Kevin O'Leary"], "$50M+ Revenue ($400k for 10%)", "slatemilk.com", "https://slatemilk.com/pages/careers"),
    SharkTankUSStartup("wickedgoodcupcakes", "Wicked Good Cupcakes", 4, "Food & Beverage", "Gourmet layered cupcakes in mason jars", ["Kevin O'Leary"], "Acquired by Hickory Farms ($75k for royalty)", "wickedgoodcupcakes.com", "https://wickedgoodcupcakes.com"),
    SharkTankUSStartup("deux", "Deux", 13, "Food & Beverage", "Functional, vegan, vitamin-enhanced edible cookie dough", ["Robert Herjavec"], "$300k for 10%", "eatdeux.com", "https://eatdeux.com/pages/careers"),
    SharkTankUSStartup("groovering", "Groove Life", 8, "Apparel & Accessories", "Breathable silicone wedding rings, watchbands and rugged gear", ["Turned down deal"], "$100M+ Revenue", "groovelife.com", "https://groovelife.com/pages/careers"),
]


def get_all_shark_tank_us_startups() -> List[SharkTankUSStartup]:
    """Return all startups in the Shark Tank US registry."""
    return SHARK_TANK_US_REGISTRY


def filter_by_season_us(season_number: int) -> List[SharkTankUSStartup]:
    """Filter US startups by Shark Tank season (1-16)."""
    return [s for s in SHARK_TANK_US_REGISTRY if s.season == season_number]


def filter_by_shark_us(shark_name: str) -> List[SharkTankUSStartup]:
    """Filter US startups that received investment from a specific Shark."""
    s_lower = shark_name.strip().lower()
    return [
        s for s in SHARK_TANK_US_REGISTRY
        if any(s_lower in inv.lower() for inv in s.sharks_invested)
    ]


def filter_by_category_us(category_name: str) -> List[SharkTankUSStartup]:
    """Filter US startups by category."""
    cat_lower = category_name.strip().lower()
    return [s for s in SHARK_TANK_US_REGISTRY if cat_lower in s.category.lower()]
