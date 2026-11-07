"""
indian_app_startups.py — Top Indian App Startups (Top 100 by Downloads & Top 100 by Revenue/Valuation).

Tracks Indian startups with iOS App Store & Google Play Store consumer/enterprise apps,
mapping their ATS platforms, direct careers URLs, download tiers, and revenue scales.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IndianAppStartup:
    id: str
    name: str
    category: str  # "Fintech", "Quick-Commerce", "E-Commerce", "Mobility", "Gaming", "Media & Audio", "EdTech", "HealthTech", "SaaS & B2B", "Travel & Food"
    tier_category: str  # "top_downloads", "top_revenue", "both"
    app_stores: str  # "iOS & Android", "Android", "iOS"
    metrics_summary: str  # e.g., "100M+ Downloads", "₹2,500 Cr ARR"
    ats_platform: str  # "greenhouse", "lever", "smartrecruiters", "ashby", "workday", "custom"
    ats_slug: Optional[str] = None
    careers_url: Optional[str] = None
    domain: Optional[str] = None
    key_roles: List[str] = field(default_factory=lambda: ["Software Engineer", "Backend", "Full Stack", "Mobile Engineer"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "tier_category": self.tier_category,
            "app_stores": self.app_stores,
            "metrics_summary": self.metrics_summary,
            "ats_platform": self.ats_platform,
            "ats_slug": self.ats_slug,
            "careers_url": self.careers_url,
            "domain": self.domain,
            "key_roles": self.key_roles,
        }


# ── The Curated Top Indian App Startups Database ─────────────────────────────

INDIAN_APP_STARTUPS: List[IndianAppStartup] = [
    # ── 1. Fintech & Wealth (Top Downloads & High Revenue) ──────────────────────
    IndianAppStartup("phonepe", "PhonePe", "Fintech", "both", "iOS & Android", "500M+ Downloads | Leading UPI Market Share", "custom", None, "https://www.phonepe.com/careers", "phonepe.com"),
    IndianAppStartup("paytm", "Paytm (One97)", "Fintech", "both", "iOS & Android", "100M+ Downloads | ₹7,000+ Cr Revenue", "custom", None, "https://paytm.com/careers", "paytm.com"),
    IndianAppStartup("cred", "CRED", "Fintech", "both", "iOS & Android", "10M+ Downloads | ₹2,400+ Cr Revenue", "greenhouse", "cred", "https://cred.club/careers", "cred.club"),
    IndianAppStartup("groww", "Groww", "Fintech", "both", "iOS & Android", "50M+ Downloads | #1 Stockbroker by Active Users", "greenhouse", "groww", "https://groww.in/careers", "groww.in"),
    IndianAppStartup("zerodha", "Zerodha (Kite)", "Fintech", "both", "iOS & Android", "10M+ Downloads | ₹6,800+ Cr Revenue (Bootstrapped)", "custom", None, "https://zerodha.com/careers", "zerodha.com"),
    IndianAppStartup("angelone", "Angel One", "Fintech", "both", "iOS & Android", "50M+ Downloads | ₹3,000+ Cr Revenue", "custom", None, "https://www.angelone.in/careers", "angelone.in"),
    IndianAppStartup("upstox", "Upstox", "Fintech", "both", "iOS & Android", "10M+ Downloads | ₹1,000+ Cr Revenue", "custom", None, "https://upstox.com/careers", "upstox.com"),
    IndianAppStartup("navi", "Navi", "Fintech", "both", "iOS & Android", "50M+ Downloads | Digital Lending & UPI", "greenhouse", "navi", "https://navi.com/careers", "navi.com"),
    IndianAppStartup("bharatpe", "BharatPe", "Fintech", "both", "iOS & Android", "10M+ Merchant Downloads | ₹1,400+ Cr Revenue", "custom", None, "https://bharatpe.com/careers", "bharatpe.com"),
    IndianAppStartup("razorpay", "Razorpay", "Fintech", "top_revenue", "iOS & Android", "₹2,200+ Cr Revenue | $7.5B Valuation", "greenhouse", "razorpay", "https://razorpay.com/jobs", "razorpay.com"),
    IndianAppStartup("pinelabs", "Pine Labs", "Fintech", "top_revenue", "iOS & Android", "Merchant POS & Digital Payments | ₹1,600+ Cr Revenue", "custom", None, "https://www.pinelabs.com/careers", "pinelabs.com"),
    IndianAppStartup("cashfree", "Cashfree Payments", "Fintech", "top_revenue", "iOS & Android", "Bulk Disbursals & Gateways | ₹600+ Cr Revenue", "greenhouse", "cashfree", "https://www.cashfree.com/careers", "cashfree.com"),
    IndianAppStartup("indmoney", "INDmoney", "Fintech", "top_downloads", "iOS & Android", "10M+ Downloads | Super Money App", "custom", None, "https://www.indmoney.com/careers", "indmoney.com"),
    IndianAppStartup("fifi", "Fi Money (Epifi)", "Fintech", "top_downloads", "iOS & Android", "5M+ Downloads | Neobank & Investments", "greenhouse", "epifi", "https://fi.money/careers", "fi.money"),
    IndianAppStartup("jupiter", "Jupiter Money", "Fintech", "top_downloads", "iOS & Android", "5M+ Downloads | Digital Banking & Salary Account", "greenhouse", "jupiter", "https://jupiter.money/careers", "jupiter.money"),
    IndianAppStartup("jar", "Jar App", "Fintech", "top_downloads", "iOS & Android", "10M+ Downloads | Daily Savings in Digital Gold", "greenhouse", "jarapp", "https://www.myjar.app/careers", "myjar.app"),
    IndianAppStartup("slice", "Slice", "Fintech", "both", "iOS & Android", "10M+ Downloads | Consumer Credit & Banking Merger", "greenhouse", "slice", "https://www.sliceit.com/careers", "sliceit.com"),
    IndianAppStartup("khatabook", "Khatabook", "Fintech", "top_downloads", "iOS & Android", "50M+ Downloads | MSME Digital Ledger", "greenhouse", "khatabook", "https://khatabook.com/careers", "khatabook.com"),
    IndianAppStartup("mobikwik", "MobiKwik (Zaakpay)", "Fintech", "both", "iOS & Android", "100M+ Downloads | ₹800+ Cr Revenue", "custom", None, "https://www.mobikwik.com/careers", "mobikwik.com"),
    IndianAppStartup("coinswitch", "CoinSwitch", "Fintech", "top_downloads", "iOS & Android", "20M+ Downloads | Crypto & Wealth App", "greenhouse", "coinswitch", "https://coinswitch.co/careers", "coinswitch.co"),
    IndianAppStartup("coindcx", "CoinDCX", "Fintech", "top_downloads", "iOS & Android", "15M+ Downloads | India's 1st Crypto Unicorn", "lever", "coindcx", "https://coindcx.com/careers", "coindcx.com"),
    IndianAppStartup("policybazaar", "Policybazaar (PB Fintech)", "Fintech", "both", "iOS & Android", "10M+ Downloads | ₹3,400+ Cr Revenue", "custom", None, "https://www.policybazaar.com/careers", "policybazaar.com"),
    IndianAppStartup("acko", "Acko General Insurance", "Fintech", "both", "iOS & Android", "10M+ Downloads | ₹1,700+ Cr Revenue", "lever", "acko", "https://www.acko.com/careers", "acko.com"),
    IndianAppStartup("digit", "Digit Insurance", "Fintech", "top_revenue", "iOS & Android", "₹7,000+ Cr Gross Premium | Listed InsurTech", "custom", None, "https://www.godigit.com/careers", "godigit.com"),
    IndianAppStartup("moneyview", "Money View", "Fintech", "both", "iOS & Android", "50M+ Downloads | ₹600+ Cr Revenue (Profitable Unicorn)", "custom", None, "https://moneyview.in/careers", "moneyview.in"),
    IndianAppStartup("kreditbee", "KreditBee", "Fintech", "both", "iOS & Android", "50M+ Downloads | ₹1,200+ Cr Revenue", "custom", None, "https://www.kreditbee.in/careers", "kreditbee.in"),
    IndianAppStartup("smallcase", "smallcase", "Fintech", "top_downloads", "iOS & Android", "5M+ Downloads | Thematic Stock Portfolios", "greenhouse", "smallcase", "https://www.smallcase.com/careers", "smallcase.com"),

    # ── 2. Quick Commerce, Food & E-Commerce (Top Downloads & Scale) ────────────
    IndianAppStartup("zepto", "Zepto", "Quick-Commerce", "both", "iOS & Android", "50M+ Downloads | $5B Valuation | 10-Min Delivery", "lever", "zepto", "https://www.zeptonow.com/careers", "zeptonow.com"),
    IndianAppStartup("blinkit", "Blinkit (Zomato)", "Quick-Commerce", "both", "iOS & Android", "50M+ Downloads | India's Largest Quick Commerce", "custom", None, "https://blinkit.com/careers", "blinkit.com"),
    IndianAppStartup("swiggy", "Swiggy (Instamart & Food)", "Quick-Commerce", "both", "iOS & Android", "100M+ Downloads | ₹11,000+ Cr Revenue", "custom", None, "https://careers.swiggy.com", "swiggy.com"),
    IndianAppStartup("zomato", "Zomato", "Travel & Food", "both", "iOS & Android", "100M+ Downloads | ₹12,000+ Cr Revenue (Profitable)", "custom", None, "https://www.zomato.com/careers", "zomato.com"),
    IndianAppStartup("flipkart", "Flipkart", "E-Commerce", "both", "iOS & Android", "500M+ Downloads | ₹56,000+ Cr Revenue", "custom", None, "https://www.flipkartcareers.com", "flipkart.com"),
    IndianAppStartup("meesho", "Meesho", "E-Commerce", "both", "iOS & Android", "500M+ Downloads | Zero-Commission Social Commerce", "greenhouse", "meesho", "https://meesho.io/jobs", "meesho.io"),
    IndianAppStartup("myntra", "Myntra", "E-Commerce", "both", "iOS & Android", "100M+ Downloads | India's #1 Fashion Platform", "custom", None, "https://careers.myntra.com", "myntra.com"),
    IndianAppStartup("nykaa", "Nykaa (FSN E-Commerce)", "E-Commerce", "both", "iOS & Android", "50M+ Downloads | ₹5,100+ Cr Revenue", "custom", None, "https://www.nykaa.com/careers", "nykaa.com"),
    IndianAppStartup("purplle", "Purplle", "E-Commerce", "both", "iOS & Android", "10M+ Downloads | Beauty & Cosmetics Unicorn", "custom", None, "https://www.purplle.com/careers", "purplle.com"),
    IndianAppStartup("lenskart", "Lenskart", "E-Commerce", "both", "iOS & Android", "50M+ Downloads | ₹3,700+ Cr Revenue | $4.5B Valuation", "custom", None, "https://www.lenskart.com/careers", "lenskart.com"),
    IndianAppStartup("bigbasket", "BigBasket (Tata)", "Quick-Commerce", "both", "iOS & Android", "50M+ Downloads | Online Grocery Pioneer", "custom", None, "https://www.bigbasket.com/careers", "bigbasket.com"),
    IndianAppStartup("tataneu", "Tata Neu", "E-Commerce", "top_downloads", "iOS & Android", "50M+ Downloads | Tata SuperApp", "custom", None, "https://www.tatadigital.com/careers", "tatadigital.com"),
    IndianAppStartup("bluestone", "BlueStone", "E-Commerce", "top_revenue", "iOS & Android", "Omnichannel Jewelry | ₹800+ Cr Revenue", "custom", None, "https://www.bluestone.com/careers", "bluestone.com"),
    IndianAppStartup("mamaearth", "Mamaearth (Honasa Consumer)", "E-Commerce", "both", "iOS & Android", "10M+ Downloads | ₹1,500+ Cr Revenue", "custom", None, "https://honasa.in/careers", "mamaearth.in"),
    IndianAppStartup("sugarcosmetics", "SUGAR Cosmetics", "E-Commerce", "both", "iOS & Android", "5M+ Downloads | ₹500+ Cr Revenue", "custom", None, "https://in.sugarcosmetics.com/pages/careers", "sugarcosmetics.com"),
    IndianAppStartup("boat", "boAt Lifestyle (Imagine Marketing)", "E-Commerce", "top_revenue", "iOS & Android", "India's #1 Audio & Wearables | ₹3,400+ Cr Revenue", "custom", None, "https://www.boat-lifestyle.com/pages/careers", "boat-lifestyle.com"),
    IndianAppStartup("noise", "Noise (Nexxbase)", "E-Commerce", "top_revenue", "iOS & Android", "Smartwatches & Hearables | ₹1,400+ Cr Revenue", "custom", None, "https://www.gonoise.com/pages/careers", "gonoise.com"),
    IndianAppStartup("licious", "Licious", "E-Commerce", "both", "iOS & Android", "10M+ Downloads | Fresh Meat & Seafood Unicorn", "greenhouse", "licious", "https://www.licious.in/careers", "licious.in"),
    IndianAppStartup("countrydelight", "Country Delight", "E-Commerce", "both", "iOS & Android", "10M+ Downloads | Daily Fresh Milk & Essentials", "custom", None, "https://countrydelight.in/careers", "countrydelight.in"),
    IndianAppStartup("rebelfoods", "Rebel Foods (Faasos/Behrouz)", "Travel & Food", "both", "iOS & Android", "World's Largest Cloud Kitchen | ₹1,200+ Cr Revenue", "custom", None, "https://www.rebelfoods.com/careers", "rebelfoods.com"),
    IndianAppStartup("curefoods", "Curefoods (EatFit)", "Travel & Food", "top_revenue", "iOS & Android", "Multi-brand Cloud Kitchens | ₹500+ Cr Revenue", "custom", None, "https://www.curefoods.in/careers", "curefoods.in"),

    # ── 3. Mobility, Travel & Logistics (Top Downloads & Revenue) ───────────────
    IndianAppStartup("ola", "Ola Cabs / Ola Consumer", "Mobility", "both", "iOS & Android", "100M+ Downloads | Ride Hailing & EV", "custom", None, "https://www.olacabs.com/careers", "olacabs.com"),
    IndianAppStartup("rapido", "Rapido", "Mobility", "both", "iOS & Android", "50M+ Downloads | India's #1 Bike & Auto Taxi App", "greenhouse", "rapido", "https://www.rapido.bike/careers", "rapido.bike"),
    IndianAppStartup("blusmart", "BluSmart Mobility", "Mobility", "both", "iOS & Android", "5M+ Downloads | 100% All-Electric Ride Hailing", "custom", None, "https://blu-smart.com/careers", "blu-smart.com"),
    IndianAppStartup("makemytrip", "MakeMyTrip / Goibibo", "Travel & Food", "both", "iOS & Android", "100M+ Downloads | NASDAQ Listed Travel Leader", "custom", None, "https://careers.makemytrip.com", "makemytrip.com"),
    IndianAppStartup("ixigo", "ixigo (Le Travenues)", "Travel & Food", "both", "iOS & Android", "100M+ Downloads | Listed OTA Pioneer", "custom", None, "https://www.ixigo.com/careers", "ixigo.com"),
    IndianAppStartup("redbus", "redBus", "Travel & Food", "both", "iOS & Android", "50M+ Downloads | World's Largest Bus Ticketing App", "custom", None, "https://www.redbus.in/careers", "redbus.in"),
    IndianAppStartup("porter", "Porter", "Mobility", "both", "iOS & Android", "10M+ Downloads | Intra-city Logistics Unicorn", "custom", None, "https://porter.in/careers", "porter.in"),
    IndianAppStartup("delhivery", "Delhivery", "Mobility", "top_revenue", "iOS & Android", "Listed Express Logistics Leader | ₹7,200+ Cr Revenue", "custom", None, "https://www.delhivery.com/careers", "delhivery.com"),
    IndianAppStartup("shiprocket", "Shiprocket", "Mobility", "both", "iOS & Android", "E-commerce Logistics & Post-Order Tech Unicorn", "custom", None, "https://www.shiprocket.in/careers", "shiprocket.in"),
    IndianAppStartup("shadowfax", "Shadowfax", "Mobility", "both", "iOS & Android", "Hyperlocal Logistics Network", "custom", None, "https://www.shadowfax.in/careers", "shadowfax.in"),
    IndianAppStartup("spinny", "Spinny", "Mobility", "both", "iOS & Android", "Used Car Buying & Selling Unicorn", "custom", None, "https://www.spinny.com/careers", "spinny.com"),
    IndianAppStartup("cars24", "CARS24", "Mobility", "both", "iOS & Android", "10M+ Downloads | Auto Tech Unicorn", "custom", None, "https://www.cars24.com/careers", "cars24.com"),
    IndianAppStartup("cardekho", "CarDekho (GirnarSoft)", "Mobility", "both", "iOS & Android", "Auto Portal & InsurTech Unicorn", "custom", None, "https://www.cardekho.com/careers", "cardekho.com"),
    IndianAppStartup("ather", "Ather Energy", "Mobility", "top_revenue", "iOS & Android", "Smart EV Scooters | ₹1,800+ Cr Revenue", "custom", None, "https://www.atherenergy.com/careers", "atherenergy.com"),
    IndianAppStartup("olaelectric", "Ola Electric", "Mobility", "both", "iOS & Android", "India's #1 2-Wheeler EV Manufacturer (Listed)", "custom", None, "https://www.olaelectric.com/careers", "olaelectric.com"),

    # ── 4. Gaming & Real-Money Entertainment (High Revenue & Downloads) ─────────
    IndianAppStartup("dream11", "Dream11 (Dream Sports)", "Gaming", "both", "iOS & Android", "150M+ Users | ₹6,300+ Cr Revenue ($8B Valuation)", "lever", "dream11", "https://careers.dream11.com", "dream11.com"),
    IndianAppStartup("winzo", "WinZO Games", "Gaming", "both", "iOS & Android", "100M+ Downloads | Micro-Transaction Social Gaming", "custom", None, "https://www.winzogames.com/careers", "winzogames.com"),
    IndianAppStartup("games24x7", "Games24x7 (My11Circle/RummyCircle)", "Gaming", "both", "iOS & Android", "₹2,000+ Cr Revenue | Gaming Unicorn", "custom", None, "https://www.games24x7.com/careers", "games24x7.com"),
    IndianAppStartup("mpl", "Mobile Premier League (MPL)", "Gaming", "both", "iOS & Android", "90M+ Users | Global Gaming Unicorn", "custom", None, "https://www.mpl.live/careers", "mpl.live"),
    IndianAppStartup("zupee", "Zupee", "Gaming", "both", "iOS & Android", "70M+ Downloads | Skill-Based Casual Gaming", "custom", None, "https://www.zupee.com/careers", "zupee.com"),
    IndianAppStartup("nazara", "Nazara Technologies", "Gaming", "top_revenue", "iOS & Android", "Listed Gaming Conglomerate (Nodwin/Kiddopia)", "custom", None, "https://nazara.com/careers", "nazara.com"),

    # ── 5. Media, Audio & Social Apps (Top Downloads & Retention) ────────────────
    IndianAppStartup("pocketfm", "Pocket FM", "Media & Audio", "both", "iOS & Android", "100M+ Downloads | $100M+ ARR Audio Series Platform", "greenhouse", "pocketfm", "https://pocketfm.com/careers", "pocketfm.com"),
    IndianAppStartup("kukufm", "Kuku FM", "Media & Audio", "both", "iOS & Android", "50M+ Downloads | Vernacular Audio Content", "greenhouse", "kukufm", "https://kukufm.com/careers", "kukufm.com"),
    IndianAppStartup("sharechat", "ShareChat / Moj", "Media & Audio", "both", "iOS & Android", "400M+ Monthly Active Users across Vernacular & Short Video", "greenhouse", "sharechat", "https://sharechat.com/careers", "sharechat.com"),
    IndianAppStartup("dailyhunt", "Dailyhunt / Josh (VerSe Innovation)", "Media & Audio", "both", "iOS & Android", "300M+ Monthly Users | News & Short Video Unicorn", "custom", None, "https://verse.in/careers", "verse.in"),
    IndianAppStartup("inshorts", "InShorts / Public App", "Media & Audio", "both", "iOS & Android", "50M+ Downloads | 60-Word News & Hyperlocal Video", "custom", None, "https://www.inshorts.com/careers", "inshorts.com"),
    IndianAppStartup("pratilipi", "Pratilipi", "Media & Audio", "top_downloads", "iOS & Android", "50M+ Downloads | Indian Language Storytelling Platform", "custom", None, "https://www.pratilipi.com/careers", "pratilipi.com"),
    IndianAppStartup("stage", "STAGE (Dialect OTT)", "Media & Audio", "top_downloads", "iOS & Android", "5M+ Downloads | Indian Dialect OTT & Series", "custom", None, "https://www.stage.in/careers", "stage.in"),
    IndianAppStartup("wynk", "Wynk Music (Airtel)", "Media & Audio", "top_downloads", "iOS & Android", "100M+ Downloads | Music Streaming", "custom", None, "https://www.airtel.in/careers", "airtel.in"),
    IndianAppStartup("jiosaavn", "JioSaavn", "Media & Audio", "top_downloads", "iOS & Android", "100M+ Downloads | Audio & Music Streaming", "custom", None, "https://www.jiosaavn.com/corporate/careers", "jiosaavn.com"),

    # ── 6. EdTech & Learning Platforms (Top Downloads & Scale) ───────────────────
    IndianAppStartup("physicswallah", "Physics Wallah (PW)", "EdTech", "both", "iOS & Android", "30M+ Downloads | ₹1,600+ Cr Revenue (Profitable Unicorn)", "custom", None, "https://www.pw.live/careers", "pw.live"),
    IndianAppStartup("unacademy", "Unacademy", "EdTech", "both", "iOS & Android", "50M+ Downloads | Live Learning & Test Prep", "greenhouse", "unacademy", "https://unacademy.com/careers", "unacademy.com"),
    IndianAppStartup("upgrad", "upGrad", "EdTech", "top_revenue", "iOS & Android", "Higher Education & Executive Upskilling | ₹1,200+ Cr Revenue", "custom", None, "https://www.upgrad.com/careers", "upgrad.com"),
    IndianAppStartup("eruditus", "Eruditus / Emeritus", "EdTech", "top_revenue", "iOS & Android", "Global Executive Education | ₹3,000+ Cr Revenue", "custom", None, "https://eruditus.com/careers", "eruditus.com"),
    IndianAppStartup("classplus", "Classplus", "EdTech", "both", "iOS & Android", "B2B Educator Apps & Creator Economy", "greenhouse", "classplus", "https://classplus.co/careers", "classplus.co"),
    IndianAppStartup("adda247", "Adda247", "EdTech", "both", "iOS & Android", "50M+ Downloads | Government Exam Preparation", "custom", None, "https://www.adda247.com/careers", "adda247.com"),
    IndianAppStartup("testbook", "Testbook", "EdTech", "top_downloads", "iOS & Android", "30M+ Downloads | Test Prep & Mock Tests", "custom", None, "https://testbook.com/careers", "testbook.com"),
    IndianAppStartup("cuemath", "Cuemath", "EdTech", "both", "iOS & Android", "K-12 Math Learning & Global Live Tutoring", "greenhouse", "cuemath", "https://www.cuemath.com/careers", "cuemath.com"),

    # ── 7. HealthTech & Fitness (Top Downloads & Revenue) ────────────────────────
    IndianAppStartup("cultfit", "Cult.fit (Curefit)", "HealthTech", "both", "iOS & Android", "10M+ Downloads | Fitness, Gyms & Healthy Food", "custom", None, "https://www.cult.fit/careers", "cult.fit"),
    IndianAppStartup("practo", "Practo", "HealthTech", "both", "iOS & Android", "10M+ Downloads | Doctor Consultations & Clinics", "custom", None, "https://www.practo.com/company/careers", "practo.com"),
    IndianAppStartup("tata1mg", "Tata 1mg", "HealthTech", "both", "iOS & Android", "50M+ Downloads | E-Pharmacy & Lab Diagnostics", "custom", None, "https://www.1mg.com/jobs", "1mg.com"),
    IndianAppStartup("pharmeasy", "PharmEasy (API Holdings)", "HealthTech", "both", "iOS & Android", "50M+ Downloads | ₹6,600+ Cr Revenue", "custom", None, "https://pharmeasy.in/careers", "pharmeasy.in"),
    IndianAppStartup("healthifyme", "Healthify (HealthifyMe)", "HealthTech", "both", "iOS & Android", "25M+ Downloads | AI Health & Calorie Tracking", "greenhouse", "healthifyme", "https://www.healthifyme.com/in/careers", "healthifyme.com"),
    IndianAppStartup("ultrahuman", "Ultrahuman", "HealthTech", "top_revenue", "iOS & Android", "Metabolic Health Ring & CGM Wearables (Global Scale)", "custom", None, "https://www.ultrahuman.com/careers", "ultrahuman.com"),
    IndianAppStartup("pristyncare", "Pristyn Care", "HealthTech", "both", "iOS & Android", "Elective Surgeries & Care Network Unicorn", "custom", None, "https://www.pristyncare.com/careers", "pristyncare.com"),
    IndianAppStartup("medibuddy", "MediBuddy", "HealthTech", "both", "iOS & Android", "10M+ Downloads | Digital Healthcare & Insurance OPD", "custom", None, "https://www.medibuddy.in/careers", "medibuddy.in"),

    # ── 8. Global SaaS, Cloud & Developer Tools (High Revenue & ARR) ─────────────
    IndianAppStartup("postman", "Postman", "SaaS & B2B", "both", "iOS & Android", "30M+ Developers Worldwide | $5.6B Valuation", "greenhouse", "postman", "https://www.postman.com/company/careers", "postman.com"),
    IndianAppStartup("browserstack", "BrowserStack", "SaaS & B2B", "top_revenue", "iOS & Android", "World's #1 Testing Cloud | ₹1,500+ Cr ARR (Profitable)", "custom", None, "https://www.browserstack.com/careers", "browserstack.com"),
    IndianAppStartup("hasura", "Hasura", "SaaS & B2B", "both", "iOS & Android", "GraphQL & Data API Engine Unicorn", "lever", "hasura", "https://hasura.io/careers", "hasura.io"),
    IndianAppStartup("chargebee", "Chargebee", "SaaS & B2B", "top_revenue", "iOS & Android", "Subscription Billing & Revenue Management Unicorn", "greenhouse", "chargebee", "https://www.chargebee.com/company/careers", "chargebee.com"),
    IndianAppStartup("freshworks", "Freshworks", "SaaS & B2B", "both", "iOS & Android", "NASDAQ Listed | $600M+ ARR Customer Software", "smartrecruiters", "freshworks", "https://www.freshworks.com/company/careers", "freshworks.com"),
    IndianAppStartup("zoho", "Zoho Corporation", "SaaS & B2B", "both", "iOS & Android", "₹8,700+ Cr Revenue | 100M+ Users (Bootstrapped Leader)", "custom", None, "https://www.zoho.com/careers", "zoho.com"),
    IndianAppStartup("darwinbox", "Darwinbox", "SaaS & B2B", "both", "iOS & Android", "Enterprise HRMS Unicorn | 850+ Enterprises", "custom", None, "https://darwinbox.com/careers", "darwinbox.com"),
    IndianAppStartup("clevertap", "CleverTap", "SaaS & B2B", "both", "iOS & Android", "Customer Retention & Engagement Platform Unicorn", "greenhouse", "clevertap", "https://clevertap.com/careers", "clevertap.com"),
    IndianAppStartup("moengage", "MoEngage", "SaaS & B2B", "both", "iOS & Android", "Insights-Led Customer Engagement Platform", "greenhouse", "moengage", "https://www.moengage.com/company/careers", "moengage.com"),
    IndianAppStartup("gupshup", "Gupshup", "SaaS & B2B", "top_revenue", "iOS & Android", "Conversational Messaging & AI Unicorn", "custom", None, "https://www.gupshup.io/careers", "gupshup.io"),
    IndianAppStartup("yellowai", "Yellow.ai", "SaaS & B2B", "both", "iOS & Android", "Enterprise Conversational AI Agents", "greenhouse", "yellowai", "https://yellow.ai/careers", "yellow.ai"),
    IndianAppStartup("innovaccer", "Innovaccer", "SaaS & B2B", "top_revenue", "iOS & Android", "Healthcare Data Cloud Unicorn", "greenhouse", "innovaccer", "https://innovaccer.com/careers", "innovaccer.com"),
    IndianAppStartup("leadsquared", "LeadSquared", "SaaS & B2B", "both", "iOS & Android", "Sales Automation & CRM Unicorn", "custom", None, "https://www.leadsquared.com/careers", "leadsquared.com"),
    IndianAppStartup("inmobi", "InMobi / Glance", "SaaS & B2B", "both", "iOS & Android", "250M+ Smart Lock Screen Users | AdTech Unicorn", "custom", None, "https://www.inmobi.com/company/careers", "inmobi.com"),
    IndianAppStartup("apna", "Apna", "SaaS & B2B", "both", "iOS & Android", "50M+ Downloads | Professional Network & Jobs Unicorn", "greenhouse", "apna", "https://apna.co/careers", "apna.co"),
]

STARTUPS_BY_ID: Dict[str, IndianAppStartup] = {s.id: s for s in INDIAN_APP_STARTUPS}


def get_indian_app_startup(name_or_id: str) -> Optional[IndianAppStartup]:
    """Find Indian startup by ID or name substring."""
    clean = name_or_id.strip().lower()
    if clean in STARTUPS_BY_ID:
        return STARTUPS_BY_ID[clean]
    for sid, s in STARTUPS_BY_ID.items():
        if clean in s.name.lower() or s.name.lower() in clean:
            return s
    return None


def filter_indian_startups(
    category: Optional[str] = None,
    tier_category: Optional[str] = None,
    search: Optional[str] = None,
) -> List[IndianAppStartup]:
    """Filter startup catalog by category, download/revenue tier, or search query."""
    results = INDIAN_APP_STARTUPS
    if category:
        c_lower = category.lower()
        results = [s for s in results if c_lower in s.category.lower()]
    if tier_category:
        tc_lower = tier_category.lower()
        if tc_lower in ("top_downloads", "downloads"):
            results = [s for s in results if s.tier_category in ("top_downloads", "both")]
        elif tc_lower in ("top_revenue", "revenue"):
            results = [s for s in results if s.tier_category in ("top_revenue", "both")]
    if search:
        s_lower = search.lower()
        results = [s for s in results if s_lower in s.name.lower() or s_lower in s.category.lower() or s_lower in s.metrics_summary.lower()]
    return results
