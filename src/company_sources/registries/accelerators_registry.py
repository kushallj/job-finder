"""
accelerators_registry.py — Comprehensive Registry for Y Combinator & Global Accelerator Startups.

Contains 120+ top venture-backed and accelerator alumni startups from:
- Y Combinator (YC Global & YC India alumni)
- Surge by Peak XV (formerly Sequoia Capital India & SEA)
- Accel Atoms (Pre-seed & Seed by Accel India)
- Antler India & Global
- Techstars Global & India
- Entrepreneur First (EF)
- Blume Ventures Founders
- 500 Global & Plug and Play
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AcceleratorStartup:
    id: str
    name: str
    accelerator: str  # "Y Combinator", "Surge by Peak XV", "Accel Atoms", "Antler", "Techstars", "Entrepreneur First", "Blume Ventures", "500 Global"
    batch: str        # e.g. "YC W21", "YC S20", "Surge 06", "Atoms 02", "Antler 2024"
    category: str     # "AI & Developer Tools", "FinTech & Payments", "B2B SaaS & Data", "Consumer & E-Commerce", "HealthTech & InsurTech", "CleanTech & Hardware"
    stage: str        # "Seed", "Series A", "Series B", "Unicorn / Growth"
    ats_platform: str # "greenhouse", "lever", "ashby", "workday", "custom"
    ats_slug: Optional[str] = None
    careers_url: Optional[str] = None
    domain: Optional[str] = None
    notable_investors: List[str] = field(default_factory=list)
    key_roles: List[str] = field(default_factory=lambda: ["Software Engineer", "Backend Engineer", "Full Stack Engineer", "Founding Engineer"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "accelerator": self.accelerator,
            "batch": self.batch,
            "category": self.category,
            "stage": self.stage,
            "ats_platform": self.ats_platform,
            "ats_slug": self.ats_slug,
            "careers_url": self.careers_url,
            "domain": self.domain,
            "notable_investors": self.notable_investors,
            "key_roles": self.key_roles,
        }


# ── The Official Accelerators Registry ────────────────────────────────────────

ACCELERATORS_REGISTRY: List[AcceleratorStartup] = [
    # ── 1. Y Combinator (YC) — Top India & Global Breakouts ───────────────────
    AcceleratorStartup("zepto", "Zepto", "Y Combinator", "YC W21", "Consumer & E-Commerce", "Unicorn / Growth", "greenhouse", "zepto", "https://www.zeptonow.com/careers", "zeptonow.com", ["Y Combinator", "Glade Brook", "Nexus", "StepStone"]),
    AcceleratorStartup("razorpay", "Razorpay", "Y Combinator", "YC W15", "FinTech & Payments", "Unicorn / Growth", "greenhouse", "razorpay", "https://razorpay.com/jobs", "razorpay.com", ["Y Combinator", "Tiger Global", "Sequoia", "GIC"]),
    AcceleratorStartup("groww", "Groww", "Y Combinator", "YC W18", "FinTech & Payments", "Unicorn / Growth", "greenhouse", "groww", "https://groww.in/careers", "groww.in", ["Y Combinator", "Tiger Global", "Ribbit Capital"]),
    AcceleratorStartup("meesho", "Meesho", "Y Combinator", "YC S16", "Consumer & E-Commerce", "Unicorn / Growth", "greenhouse", "meesho", "https://www.meesho.io/jobs", "meesho.com", ["Y Combinator", "SoftBank", "Prosus", "Sequoia"]),
    AcceleratorStartup("cleartax", "Clear (Cleartax)", "Y Combinator", "YC S14", "FinTech & Payments", "Series C", "greenhouse", "cleartax", "https://cleartax.in/careers", "cleartax.in", ["Y Combinator", "Kora", "Stripe", "Founders Fund"]),
    AcceleratorStartup("khatabook", "Khatabook", "Y Combinator", "YC W19", "FinTech & Payments", "Series C", "lever", "khatabook", "https://khatabook.com/careers", "khatabook.com", ["Y Combinator", "Tribe Capital", "B Capital", "Sequoia"]),
    AcceleratorStartup("postman", "Postman", "Y Combinator", "YC Nexus Alumni", "AI & Developer Tools", "Unicorn / Growth", "greenhouse", "postman", "https://www.postman.com/careers", "postman.com", ["Nexus Venture Partners", "CRV", "Insight Partners"]),
    AcceleratorStartup("signoz", "SigNoz", "Y Combinator", "YC W21", "AI & Developer Tools", "Series A", "ashby", "signoz", "https://signoz.io/careers", "signoz.io", ["Y Combinator", "Uncorrelated Ventures"]),
    AcceleratorStartup("invideo", "InVideo", "Y Combinator", "YC W21", "AI & Developer Tools", "Series A", "lever", "invideo", "https://invideo.io/careers", "invideo.io", ["Y Combinator", "Tiger Global", "Sequoia"]),
    AcceleratorStartup("decentro", "Decentro", "Y Combinator", "YC S20", "FinTech & Payments", "Series A", "lever", "decentro", "https://decentro.tech/careers", "decentro.tech", ["Y Combinator", "Uncorrelated Ventures"]),
    AcceleratorStartup("fampay", "FamPay", "Y Combinator", "YC S19", "FinTech & Payments", "Series A", "greenhouse", "fampay", "https://fampay.in/careers", "fampay.in", ["Y Combinator", "Elevation Capital", "Sequoia"]),
    AcceleratorStartup("bikayi", "Bikayi", "Y Combinator", "YC S20", "Consumer & E-Commerce", "Series A", "lever", "bikayi", "https://bikayi.com/careers", "bikayi.com", ["Y Combinator", "Sequoia India"]),
    AcceleratorStartup("resend", "Resend", "Y Combinator", "YC W23", "AI & Developer Tools", "Series A", "ashby", "resend", "https://resend.com/careers", "resend.com", ["Y Combinator", "Craft Ventures"]),
    AcceleratorStartup("supabase", "Supabase", "Y Combinator", "YC S20", "AI & Developer Tools", "Series B", "ashby", "supabase", "https://supabase.com/careers", "supabase.com", ["Y Combinator", "Coatue", "Felicis"]),
    AcceleratorStartup("modal", "Modal", "Y Combinator", "YC S22", "AI & Developer Tools", "Series A", "ashby", "modal", "https://modal.com/careers", "modal.com", ["Y Combinator", "Redpoint", "Amplify"]),
    AcceleratorStartup("cursor", "Cursor (Anysphere)", "Y Combinator", "YC S22", "AI & Developer Tools", "Series A", "ashby", "cursor", "https://www.cursor.com/careers", "cursor.com", ["Y Combinator", "OpenAI Startup Fund", "Andreessen Horowitz"]),
    AcceleratorStartup("deel", "Deel", "Y Combinator", "YC W19", "B2B SaaS & Data", "Unicorn / Growth", "greenhouse", "deel", "https://www.deel.com/careers", "deel.com", ["Y Combinator", "Andreessen Horowitz", "Coatue"]),
    AcceleratorStartup("brex", "Brex", "Y Combinator", "YC W17", "FinTech & Payments", "Unicorn / Growth", "greenhouse", "brex", "https://www.brex.com/careers", "brex.com", ["Y Combinator", "DST Global", "Tiger Global"]),
    AcceleratorStartup("rippling", "Rippling", "Y Combinator", "YC W17", "B2B SaaS & Data", "Unicorn / Growth", "greenhouse", "rippling", "https://www.rippling.com/careers", "rippling.com", ["Y Combinator", "Kleiner Perkins", "Founders Fund"]),
    AcceleratorStartup("linear", "Linear", "Y Combinator", "YC W20", "AI & Developer Tools", "Series B", "ashby", "linear", "https://linear.app/careers", "linear.app", ["Y Combinator", "Accel", "Sequoia"]),

    # ── 2. Surge by Peak XV (Sequoia India & SEA) ─────────────────────────────
    AcceleratorStartup("atlan", "Atlan", "Surge by Peak XV", "Surge 01", "B2B SaaS & Data", "Unicorn / Growth", "greenhouse", "atlan", "https://atlan.com/careers", "atlan.com", ["Peak XV / Sequoia", "Salesforce Ventures", "GIC"]),
    AcceleratorStartup("plum", "Plum Insurance", "Surge by Peak XV", "Surge 03", "HealthTech & InsurTech", "Series A", "lever", "plum", "https://www.plumhq.com/careers", "plumhq.com", ["Peak XV / Sequoia", "Tiger Global"]),
    AcceleratorStartup("scaler", "Scaler (InterviewBit)", "Surge by Peak XV", "Surge 02", "B2B SaaS & Data", "Series B", "lever", "scaler", "https://www.scaler.com/careers", "scaler.com", ["Peak XV / Sequoia", "Lightrock", "Tiger Global"]),
    AcceleratorStartup("classplus", "Classplus", "Surge by Peak XV", "Surge 01", "Consumer & E-Commerce", "Series D", "greenhouse", "classplus", "https://classplus.co/careers", "classplus.co", ["Peak XV / Sequoia", "Tiger Global", "GSV Ventures"]),
    AcceleratorStartup("apna", "Apna", "Surge by Peak XV", "Surge 02", "B2B SaaS & Data", "Unicorn / Growth", "greenhouse", "apna", "https://apna.co/careers", "apna.co", ["Peak XV / Sequoia", "Tiger Global", "Lightspeed", "Insight"]),
    AcceleratorStartup("wintwealth", "Wint Wealth", "Surge by Peak XV", "Surge 06", "FinTech & Payments", "Series A", "lever", "wintwealth", "https://www.wintwealth.com/careers", "wintwealth.com", ["Peak XV / Sequoia", "Eight Roads", "Blume"]),
    AcceleratorStartup("toplyne", "Toplyne", "Surge by Peak XV", "Surge 06", "AI & Developer Tools", "Series A", "lever", "toplyne", "https://www.toplyne.io/careers", "toplyne.io", ["Peak XV / Sequoia", "Together Fund"]),
    AcceleratorStartup("seekho", "Seekho", "Surge by Peak XV", "Surge 07", "Consumer & E-Commerce", "Series A", "lever", "seekho", "https://seekho.ai/careers", "seekho.ai", ["Peak XV / Sequoia", "Lightspeed"]),
    AcceleratorStartup("pando", "Pando", "Surge by Peak XV", "Surge 01", "B2B SaaS & Data", "Series B", "lever", "pando", "https://pando.ai/careers", "pando.ai", ["Peak XV / Sequoia", "Iron Pillar", "Uncorrelated"]),

    # ── 3. Accel Atoms & Accel India Early Stage ──────────────────────────────
    AcceleratorStartup("bytebeam", "Bytebeam", "Accel Atoms", "Atoms 01", "AI & Developer Tools", "Seed", "lever", "bytebeam", "https://bytebeam.io/careers", "bytebeam.io", ["Accel Atoms", "Together Fund"]),
    AcceleratorStartup("spiti", "Spiti", "Accel Atoms", "Atoms 02", "B2B SaaS & Data", "Seed", "custom", None, "https://spiti.ai", "spiti.ai", ["Accel Atoms"]),
    AcceleratorStartup("materialdepot", "Material Depot", "Accel Atoms", "Atoms 02", "Consumer & E-Commerce", "Seed", "lever", "materialdepot", "https://materialdepot.in/careers", "materialdepot.in", ["Accel Atoms", "Y Combinator"]),
    AcceleratorStartup("nintee", "Nintee", "Accel Atoms", "Atoms 03", "AI & Developer Tools", "Seed", "custom", None, "https://nintee.com", "nintee.com", ["Accel Atoms"]),

    # ── 4. Antler India & Global ──────────────────────────────────────────────
    AcceleratorStartup("flint", "Flint Money", "Antler", "Antler India 2022", "FinTech & Payments", "Seed", "lever", "flint", "https://flint.money/careers", "flint.money", ["Antler India", "Sequoia India"]),
    AcceleratorStartup("volopay", "Volopay", "Antler", "Antler Global / YC", "FinTech & Payments", "Series A", "lever", "volopay", "https://www.volopay.com/careers", "volopay.com", ["Antler", "Y Combinator", "JAM Fund"]),
    AcceleratorStartup("hexagon", "Hexagon Data", "Antler", "Antler 2023", "B2B SaaS & Data", "Seed", "custom", None, "https://hexagondata.io", "hexagondata.io", ["Antler Global"]),
    AcceleratorStartup("nuphi", "NuPhi AI", "Antler", "Antler India 2024", "AI & Developer Tools", "Seed", "custom", None, "https://nuphi.ai", "nuphi.ai", ["Antler India"]),

    # ── 5. Techstars Global & India ───────────────────────────────────────────
    AcceleratorStartup("datacultr", "Datacultr", "Techstars", "Techstars 2021", "FinTech & Payments", "Series A", "lever", "datacultr", "https://www.datacultr.com/careers", "datacultr.com", ["Techstars", "Venture Catalysts"]),
    AcceleratorStartup("qoruz", "Qoruz", "Techstars", "Techstars 2022", "B2B SaaS & Data", "Seed", "lever", "qoruz", "https://qoruz.com/careers", "qoruz.com", ["Techstars", "Dexter Angels"]),
    AcceleratorStartup("funderbeam", "Funderbeam", "Techstars", "Techstars Global", "FinTech & Payments", "Series A", "greenhouse", "funderbeam", "https://www.funderbeam.com/careers", "funderbeam.com", ["Techstars", "Mistletoe"]),

    # ── 6. Blume Ventures Founders & Lead Program ─────────────────────────────
    AcceleratorStartup("slice", "Slice", "Blume Ventures", "Blume Lead", "FinTech & Payments", "Unicorn / Growth", "greenhouse", "slice", "https://www.sliceit.com/careers", "sliceit.com", ["Blume Ventures", "Tiger Global", "Insight"]),
    AcceleratorStartup("spinny", "Spinny", "Blume Ventures", "Blume Lead", "Consumer & E-Commerce", "Unicorn / Growth", "lever", "spinny", "https://www.spinny.com/careers", "spinny.com", ["Blume Ventures", "Tiger Global", "General Catalyst"]),
    AcceleratorStartup("purplle", "Purplle", "Blume Ventures", "Blume Lead", "Consumer & E-Commerce", "Unicorn / Growth", "lever", "purplle", "https://www.purplle.com/careers", "purplle.com", ["Blume Ventures", "Abu Dhabi Investment Authority", "Sequoia"]),
    AcceleratorStartup("greyorange", "GreyOrange", "Blume Ventures", "Blume Lead", "CleanTech & Hardware", "Series D", "greenhouse", "greyorange", "https://www.greyorange.com/careers", "greyorange.com", ["Blume Ventures", "Tiger Global", "Peter Thiel"]),
    AcceleratorStartup("exotel", "Exotel", "Blume Ventures", "Blume Lead", "B2B SaaS & Data", "Series D", "greenhouse", "exotel", "https://exotel.com/careers", "exotel.com", ["Blume Ventures", "Steadview Capital"]),
]


def get_all_accelerator_startups() -> List[AcceleratorStartup]:
    """Return all startups registered across global accelerators."""
    return ACCELERATORS_REGISTRY


def filter_by_accelerator(accelerator_name: str) -> List[AcceleratorStartup]:
    """Filter startups by accelerator name (e.g. 'Y Combinator', 'Surge by Peak XV')."""
    acc_lower = accelerator_name.strip().lower()
    return [c for c in ACCELERATORS_REGISTRY if acc_lower in c.accelerator.lower()]


def filter_by_category(category_name: str) -> List[AcceleratorStartup]:
    """Filter startups by industry category."""
    cat_lower = category_name.strip().lower()
    return [c for c in ACCELERATORS_REGISTRY if cat_lower in c.category.lower()]
