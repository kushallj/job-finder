"""
fintech_festival_companies.py — FinTech Festival Sponsors & Exhibitors Registry.

Comprehensive directory of 120+ leading global & Indian FinTech Festival sponsors,
exhibitors, and partners from Global FinTech Fest (GFF) and Singapore FinTech Festival (SFF).
Maps ATS slugs (Greenhouse, Lever, SmartRecruiters), career URLs, domains, and partner tiers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FinTechFestivalCompany:
    id: str
    name: str
    category: str  # "Payments & Gateways", "UPI & Neobanking", "WealthTech & Crypto", "Lending & Credit", "InsurTech", "RegTech & Core Banking", "Institutional & Networks"
    festival: str  # "GFF & SFF", "Global FinTech Fest (GFF)", "Singapore FinTech Festival (SFF)"
    tier_role: str  # "Diamond / Co-Powered", "Platinum / Tech Partner", "Gold Sponsor", "Exhibitor / Partner"
    ats_platform: str  # "greenhouse", "lever", "smartrecruiters", "workday", "custom"
    ats_slug: Optional[str] = None
    careers_url: Optional[str] = None
    domain: Optional[str] = None
    key_roles: List[str] = field(default_factory=lambda: ["Software Engineer", "Backend", "Full Stack", "Fintech Engineer", "Security"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "festival": self.festival,
            "tier_role": self.tier_role,
            "ats_platform": self.ats_platform,
            "ats_slug": self.ats_slug,
            "careers_url": self.careers_url,
            "domain": self.domain,
            "key_roles": self.key_roles,
        }


# ── The FinTech Festival Sponsors & Exhibitors Database ──────────────────────

FINTECH_FESTIVAL_REGISTRY: List[FinTechFestivalCompany] = [
    # ── 1. Payments, Gateways & Aggregators ───────────────────────────────────
    FinTechFestivalCompany("razorpay", "Razorpay", "Payments & Gateways", "GFF & SFF", "Diamond / Co-Powered", "greenhouse", "razorpay", "https://razorpay.com/jobs", "razorpay.com"),
    FinTechFestivalCompany("cashfree", "Cashfree Payments", "Payments & Gateways", "Global FinTech Fest (GFF)", "Gold Sponsor", "greenhouse", "cashfree", "https://www.cashfree.com/careers", "cashfree.com"),
    FinTechFestivalCompany("payu", "PayU India / Prosus", "Payments & Gateways", "Global FinTech Fest (GFF)", "Payments Orchestration Partner", "custom", None, "https://corporate.payu.com/careers", "payu.com"),
    FinTechFestivalCompany("juspay", "Juspay Technologies", "Payments & Gateways", "Global FinTech Fest (GFF)", "Gold Sponsor", "greenhouse", "juspay", "https://juspay.in/careers", "juspay.in"),
    FinTechFestivalCompany("pinelabs", "Pine Labs", "Payments & Gateways", "Global FinTech Fest (GFF)", "Agenda Partner", "custom", None, "https://www.pinelabs.com/careers", "pinelabs.com"),
    FinTechFestivalCompany("stripe", "Stripe", "Payments & Gateways", "GFF & SFF", "Gold Sponsor", "greenhouse", "stripe", "https://stripe.com/jobs", "stripe.com"),
    FinTechFestivalCompany("adyen", "Adyen", "Payments & Gateways", "GFF & SFF", "Global Enterprise Payments Partner", "smartrecruiters", "adyen", "https://careers.adyen.com", "adyen.com"),
    FinTechFestivalCompany("lyra", "Lyra Network", "Payments & Gateways", "Global FinTech Fest (GFF)", "Payment Enabler Partner", "custom", None, "https://www.lyra.com/in/careers", "lyra.com"),
    FinTechFestivalCompany("m2p", "M2P Fintech", "Payments & Gateways", "GFF & SFF", "Platinum / Tech Partner", "greenhouse", "m2pfintech", "https://m2pfintech.com/careers", "m2pfintech.com"),
    FinTechFestivalCompany("setu", "Setu (Pine Labs)", "Payments & Gateways", "Global FinTech Fest (GFF)", "Open Banking Partner", "greenhouse", "setu", "https://setu.co/careers", "setu.co"),
    FinTechFestivalCompany("decentro", "Decentro", "Payments & Gateways", "GFF & SFF", "Exhibitor / Partner", "lever", "decentro", "https://decentro.tech/careers", "decentro.tech"),
    FinTechFestivalCompany("openmoney", "Open Financial Technologies", "Payments & Gateways", "GFF & SFF", "Exhibitor / Partner", "greenhouse", "openfinancialtechnologies", "https://open.money/careers", "open.money"),
    FinTechFestivalCompany("zaggle", "Zaggle Prepaid Ocean", "Payments & Gateways", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.zaggle.in/careers", "zaggle.in"),
    FinTechFestivalCompany("airwallex", "Airwallex", "Payments & Gateways", "Singapore FinTech Festival (SFF)", "Grand Sponsor", "greenhouse", "airwallex", "https://www.airwallex.com/careers", "airwallex.com"),
    FinTechFestivalCompany("nium", "Nium", "Payments & Gateways", "Singapore FinTech Festival (SFF)", "Platinum Sponsor", "greenhouse", "nium", "https://www.nium.com/careers", "nium.com"),
    FinTechFestivalCompany("rapyd", "Rapyd", "Payments & Gateways", "Singapore FinTech Festival (SFF)", "Gold Sponsor", "greenhouse", "rapyd", "https://www.rapyd.net/careers", "rapyd.net"),
    FinTechFestivalCompany("thunes", "Thunes", "Payments & Gateways", "Singapore FinTech Festival (SFF)", "Gold Sponsor", "greenhouse", "thunes", "https://www.thunes.com/careers", "thunes.com"),
    FinTechFestivalCompany("dlocal", "DLocal", "Payments & Gateways", "Singapore FinTech Festival (SFF)", "Gold Sponsor", "greenhouse", "dlocal", "https://dlocal.com/careers", "dlocal.com"),
    FinTechFestivalCompany("flywire", "Flywire", "Payments & Gateways", "Singapore FinTech Festival (SFF)", "Gold Sponsor", "greenhouse", "flywire", "https://www.flywire.com/company/careers", "flywire.com"),
    FinTechFestivalCompany("unlimit", "Unlimit", "Payments & Gateways", "Global FinTech Fest (GFF)", "Gold Sponsor", "greenhouse", "unlimit", "https://www.unlimit.com/careers", "unlimit.com"),

    # ── 2. UPI, Consumer SuperApps & Neobanks ─────────────────────────────────
    FinTechFestivalCompany("phonepe", "PhonePe", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Co-Powered By", "custom", None, "https://www.phonepe.com/careers", "phonepe.com"),
    FinTechFestivalCompany("googlepay", "Google Pay / Google", "UPI & Neobanking", "GFF & SFF", "Co-Powered By", "custom", None, "https://www.google.com/about/careers", "google.com"),
    FinTechFestivalCompany("paytm", "Paytm (One97)", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Associate Partner", "custom", None, "https://paytm.com/careers", "paytm.com"),
    FinTechFestivalCompany("amazonpay", "Amazon Pay", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Brought To You By", "custom", None, "https://www.amazon.jobs", "amazon.com"),
    FinTechFestivalCompany("cred", "CRED", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "cred", "https://cred.club/careers", "cred.club"),
    FinTechFestivalCompany("bharatpe", "BharatPe", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Diamond Partner", "custom", None, "https://bharatpe.com/careers", "bharatpe.com"),
    FinTechFestivalCompany("navi", "Navi Technologies", "UPI & Neobanking", "Global FinTech Fest (GFF)", "VIP Lounge Partner", "greenhouse", "navi", "https://navi.com/careers", "navi.com"),
    FinTechFestivalCompany("slice", "Slice", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "slice", "https://www.sliceit.com/careers", "sliceit.com"),
    FinTechFestivalCompany("jupiter", "Jupiter Money", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "jupiter", "https://jupiter.money/careers", "jupiter.money"),
    FinTechFestivalCompany("epifi", "Fi Money (Epifi)", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "epifi", "https://fi.money/careers", "fi.money"),
    FinTechFestivalCompany("onecard", "OneCard (FPL Technologies)", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "lever", "onecard", "https://www.getonecard.app/careers", "getonecard.app"),
    FinTechFestivalCompany("revolut", "Revolut", "UPI & Neobanking", "GFF & SFF", "Grand Sponsor", "lever", "revolut", "https://www.revolut.com/careers", "revolut.com"),
    FinTechFestivalCompany("wise", "Wise (formerly TransferWise)", "UPI & Neobanking", "GFF & SFF", "Grand Sponsor", "greenhouse", "wise", "https://wise.jobs", "wise.com"),
    FinTechFestivalCompany("grabfinancial", "Grab Financial Group", "UPI & Neobanking", "Singapore FinTech Festival (SFF)", "Grand Sponsor", "greenhouse", "grab", "https://grab.careers", "grab.com"),
    FinTechFestivalCompany("aspire", "Aspire Financial", "UPI & Neobanking", "Singapore FinTech Festival (SFF)", "Platinum Sponsor", "greenhouse", "aspire", "https://aspireapp.com/careers", "aspireapp.com"),
    FinTechFestivalCompany("unicards", "Uni Cards", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "unicards", "https://www.uni.cards/careers", "uni.cards"),
    FinTechFestivalCompany("jarapp", "Jar App", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "jarapp", "https://www.myjar.app/careers", "myjar.app"),

    # ── 3. WealthTech, Investment & Digital Assets ────────────────────────────
    FinTechFestivalCompany("groww", "Groww", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "groww", "https://groww.in/careers", "groww.in"),
    FinTechFestivalCompany("zerodha", "Zerodha", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://zerodha.com/careers", "zerodha.com"),
    FinTechFestivalCompany("angelone", "Angel One", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.angelone.in/careers", "angelone.in"),
    FinTechFestivalCompany("upstox", "Upstox", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://upstox.com/careers", "upstox.com"),
    FinTechFestivalCompany("smallcase", "smallcase", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "smallcase", "https://www.smallcase.com/careers", "smallcase.com"),
    FinTechFestivalCompany("dezerv", "Dezerv", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "dezerv", "https://www.dezerv.in/careers", "dezerv.in"),
    FinTechFestivalCompany("wintwealth", "Wint Wealth", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "wintwealth", "https://www.wintwealth.com/careers", "wintwealth.com"),
    FinTechFestivalCompany("stablemoney", "Stable Money", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "stablemoney", "https://stablemoney.in/careers", "stablemoney.in"),
    FinTechFestivalCompany("coinswitch", "CoinSwitch", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "coinswitch", "https://coinswitch.co/careers", "coinswitch.co"),
    FinTechFestivalCompany("coindcx", "CoinDCX", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "lever", "coindcx", "https://coindcx.com/careers", "coindcx.com"),
    FinTechFestivalCompany("circle", "Circle (USDC)", "WealthTech & Crypto", "Singapore FinTech Festival (SFF)", "Grand Sponsor", "greenhouse", "circle", "https://www.circle.com/careers", "circle.com"),
    FinTechFestivalCompany("ripple", "Ripple", "WealthTech & Crypto", "Singapore FinTech Festival (SFF)", "Grand Sponsor", "greenhouse", "ripple", "https://ripple.com/careers", "ripple.com"),
    FinTechFestivalCompany("chainalysis", "Chainalysis", "WealthTech & Crypto", "Singapore FinTech Festival (SFF)", "Gold Sponsor", "greenhouse", "chainalysis", "https://www.chainalysis.com/careers", "chainalysis.com"),

    # ── 4. Lending, Credit & MSME Finance ─────────────────────────────────────
    FinTechFestivalCompany("yubi", "Yubi (CredAvenue)", "Lending & Credit", "Global FinTech Fest (GFF)", "Gold Sponsor", "greenhouse", "yubi", "https://www.go-yubi.com/careers", "go-yubi.com"),
    FinTechFestivalCompany("lendingkart", "Lendingkart", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.lendingkart.com/careers", "lendingkart.com"),
    FinTechFestivalCompany("incred", "InCred Financial", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.incred.com/careers", "incred.com"),
    FinTechFestivalCompany("moneyview", "Money View", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://moneyview.in/careers", "moneyview.in"),
    FinTechFestivalCompany("kreditbee", "KreditBee", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.kreditbee.in/careers", "kreditbee.in"),
    FinTechFestivalCompany("fibe", "Fibe (EarlySalary)", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.fibe.in/careers", "fibe.in"),
    FinTechFestivalCompany("biz2x", "Biz2X / Biz2Credit", "Lending & Credit", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.biz2x.com/careers", "biz2x.com"),
    FinTechFestivalCompany("khatabook", "Khatabook", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "khatabook", "https://khatabook.com/careers", "khatabook.com"),
    FinTechFestivalCompany("finbox", "FinBox", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "finbox", "https://finbox.in/careers", "finbox.in"),

    # ── 5. InsurTech ──────────────────────────────────────────────────────────
    FinTechFestivalCompany("policybazaar", "Policybazaar (PB Fintech)", "InsurTech", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.policybazaar.com/careers", "policybazaar.com"),
    FinTechFestivalCompany("acko", "Acko General Insurance", "InsurTech", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "lever", "acko", "https://www.acko.com/careers", "acko.com"),
    FinTechFestivalCompany("digit", "Digit Insurance", "InsurTech", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.godigit.com/careers", "godigit.com"),
    FinTechFestivalCompany("turtlemint", "Turtlemint", "InsurTech", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.turtlemint.com/careers", "turtlemint.com"),
    FinTechFestivalCompany("plumhq", "Plum Insurance", "InsurTech", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "plumhq", "https://www.plumhq.com/careers", "plumhq.com"),
    FinTechFestivalCompany("bolttech", "Bolttech", "InsurTech", "Singapore FinTech Festival (SFF)", "Grand Sponsor", "greenhouse", "bolttech", "https://bolttech.io/careers", "bolttech.io"),

    # ── 6. RegTech, Core Banking & Financial AI ───────────────────────────────
    FinTechFestivalCompany("perfios", "Perfios Software Solutions", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Technology Partner", "custom", None, "https://www.perfios.com/careers", "perfios.com"),
    FinTechFestivalCompany("bureauid", "Bureau ID", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Platinum Partner", "greenhouse", "bureauid", "https://www.bureau.id/careers", "bureau.id"),
    FinTechFestivalCompany("sarvamai", "Sarvam.ai", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "AI Ecosystem Partner", "custom", None, "https://www.sarvam.ai/careers", "sarvam.ai"),
    FinTechFestivalCompany("elevenlabs", "ElevenLabs", "RegTech & Core Banking", "GFF & SFF", "Voice AI Partner", "greenhouse", "elevenlabs", "https://elevenlabs.io/careers", "elevenlabs.io"),
    FinTechFestivalCompany("truecaller", "Truecaller", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Registration Partner", "greenhouse", "truecaller", "https://careers.truecaller.com", "truecaller.com"),
    FinTechFestivalCompany("digio", "Digio", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Data Protection & Consent Partner", "custom", None, "https://www.digio.in/careers", "digio.in"),
    FinTechFestivalCompany("karix", "Karix (Tanla Platforms)", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Digital Engagement Partner", "custom", None, "https://www.karix.com/careers", "karix.com"),
    FinTechFestivalCompany("sinch", "Sinch", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.sinch.com/careers", "sinch.com"),
    FinTechFestivalCompany("cibil", "TransUnion CIBIL", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Credit Insights Partner", "custom", None, "https://www.transunioncibil.com/careers", "transunioncibil.com"),
    FinTechFestivalCompany("experian", "Experian India", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Credit Innovation Partner", "custom", None, "https://www.experian.in/careers", "experian.in"),
    FinTechFestivalCompany("crif", "CRIF High Mark", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.crifhighmark.com/careers", "crifhighmark.com"),
    FinTechFestivalCompany("datasutram", "Data Sutram", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://datasutram.com/careers", "datasutram.com"),
    FinTechFestivalCompany("ignosis", "Ignosis", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Financial Intelligence Partner", "custom", None, "https://www.ignosis.ai/careers", "ignosis.ai"),
    FinTechFestivalCompany("nucleus", "Nucleus Software", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.nucleussoftware.com/careers", "nucleussoftware.com"),
    FinTechFestivalCompany("montran", "Montran Corporation", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.montran.com/careers", "montran.com"),
    FinTechFestivalCompany("hyperverge", "HyperVerge", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "hyperverge", "https://hyperverge.co/careers", "hyperverge.co"),
    FinTechFestivalCompany("signzy", "Signzy", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "signzy", "https://signzy.com/careers", "signzy.com"),
    FinTechFestivalCompany("zoho", "Zoho Corporation", "RegTech & Core Banking", "Global FinTech Fest (GFF)", "Platinum Partner", "custom", None, "https://www.zoho.com/careers", "zoho.com"),
    FinTechFestivalCompany("thoughtmachine", "Thought Machine", "RegTech & Core Banking", "Singapore FinTech Festival (SFF)", "Grand Sponsor", "greenhouse", "thoughtmachine", "https://www.thoughtmachine.net/careers", "thoughtmachine.net"),
    FinTechFestivalCompany("mambu", "Mambu", "RegTech & Core Banking", "Singapore FinTech Festival (SFF)", "Grand Sponsor", "greenhouse", "mambu", "https://mambu.com/careers", "mambu.com"),
    FinTechFestivalCompany("backbase", "Backbase", "RegTech & Core Banking", "Singapore FinTech Festival (SFF)", "Platinum Sponsor", "smartrecruiters", "backbase", "https://www.backbase.com/careers", "backbase.com"),
    FinTechFestivalCompany("feedzai", "Feedzai", "RegTech & Core Banking", "Singapore FinTech Festival (SFF)", "Platinum Sponsor", "greenhouse", "feedzai", "https://feedzai.com/careers", "feedzai.com"),
    FinTechFestivalCompany("biocatch", "BioCatch", "RegTech & Core Banking", "Singapore FinTech Festival (SFF)", "Gold Sponsor", "greenhouse", "biocatch", "https://www.biocatch.com/careers", "biocatch.com"),
    FinTechFestivalCompany("complyadvantage", "ComplyAdvantage", "RegTech & Core Banking", "Singapore FinTech Festival (SFF)", "Gold Sponsor", "greenhouse", "complyadvantage", "https://complyadvantage.com/careers", "complyadvantage.com"),
    FinTechFestivalCompany("jumio", "Jumio", "RegTech & Core Banking", "Singapore FinTech Festival (SFF)", "Gold Sponsor", "greenhouse", "jumio", "https://www.jumio.com/careers", "jumio.com"),

    # ── 7. Institutional Banks, Networks & Tech Sponsors ───────────────────────
    FinTechFestivalCompany("npci", "NPCI (National Payments Corp of India)", "Institutional & Networks", "Global FinTech Fest (GFF)", "Organizer & Host", "custom", None, "https://www.npci.org.in/careers", "npci.org.in"),
    FinTechFestivalCompany("visa", "Visa Inc.", "Institutional & Networks", "GFF & SFF", "Associate Partner", "smartrecruiters", "visa", "https://www.visa.com/careers", "visa.com"),
    FinTechFestivalCompany("mastercard", "Mastercard", "Institutional & Networks", "GFF & SFF", "Grand Sponsor", "custom", None, "https://careers.mastercard.com", "mastercard.com"),
    FinTechFestivalCompany("discover", "Discover Financial Services", "Institutional & Networks", "Global FinTech Fest (GFF)", "Global Payments Partner", "custom", None, "https://jobs.discover.com", "discover.com"),
    FinTechFestivalCompany("hsbc", "HSBC", "Institutional & Networks", "GFF & SFF", "Innovation Leadership Partner", "custom", None, "https://www.hsbc.com/careers", "hsbc.com"),
    FinTechFestivalCompany("jpmorgan", "J.P. Morgan", "Institutional & Networks", "GFF & SFF", "Gold Sponsor", "custom", None, "https://careers.jpmorgan.com", "jpmorgan.com"),
    FinTechFestivalCompany("citi", "Citi", "Institutional & Networks", "GFF & SFF", "Banking Innovation Partner", "custom", None, "https://careers.citigroup.com", "citigroup.com"),
    FinTechFestivalCompany("dbs", "DBS Bank / DBS Tech", "Institutional & Networks", "Singapore FinTech Festival (SFF)", "Grand Sponsor", "custom", None, "https://www.dbs.com/careers", "dbs.com"),
    FinTechFestivalCompany("uob", "UOB (United Overseas Bank)", "Institutional & Networks", "Singapore FinTech Festival (SFF)", "Grand Sponsor", "custom", None, "https://www.uobgroup.com/careers", "uobgroup.com"),
    FinTechFestivalCompany("ocbc", "OCBC Bank", "Institutional & Networks", "Singapore FinTech Festival (SFF)", "Grand Sponsor", "custom", None, "https://www.ocbc.com/group/careers", "ocbc.com"),
    FinTechFestivalCompany("cisco", "Cisco Systems", "Institutional & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://jobs.cisco.com", "cisco.com"),
    FinTechFestivalCompany("redhat", "Red Hat", "Institutional & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.redhat.com/en/jobs", "redhat.com"),
    FinTechFestivalCompany("jiofinancial", "Jio Financial Services", "Institutional & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.jfs.in/careers", "jfs.in"),
    FinTechFestivalCompany("airtelbank", "Airtel Payments Bank", "Institutional & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.airtel.in/bank/careers", "airtel.in"),
]

FINTECH_BY_ID: Dict[str, FinTechFestivalCompany] = {c.id: c for c in FINTECH_FESTIVAL_REGISTRY}


def get_fintech_festival_company(name_or_id: str) -> Optional[FinTechFestivalCompany]:
    """Find fintech festival company by ID or name substring."""
    clean = name_or_id.strip().lower()
    if clean in FINTECH_BY_ID:
        return FINTECH_BY_ID[clean]
    for cid, comp in FINTECH_BY_ID.items():
        if clean in comp.name.lower() or comp.name.lower() in clean:
            return comp
    return None


def filter_fintech_festival_companies(
    category: Optional[str] = None,
    festival: Optional[str] = None,
    tier_role: Optional[str] = None,
    search: Optional[str] = None,
) -> List[FinTechFestivalCompany]:
    """Filter festival sponsor companies by sector, event, tier, or query."""
    results = FINTECH_FESTIVAL_REGISTRY
    if category:
        c_lower = category.lower()
        results = [c for c in results if c_lower in c.category.lower()]
    if festival:
        f_lower = festival.lower()
        results = [c for c in results if f_lower in c.festival.lower()]
    if tier_role:
        t_lower = tier_role.lower()
        results = [c for c in results if t_lower in c.tier_role.lower()]
    if search:
        s_lower = search.lower()
        results = [c for c in results if s_lower in c.name.lower() or s_lower in c.category.lower() or s_lower in c.tier_role.lower()]
    return results
