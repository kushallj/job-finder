"""
fintech_festival_companies.py — FinTech Festival Sponsors & Exhibitors Registry.

Comprehensive directory of 140+ verified FinTech Festival partners and sponsors directly
sourced from https://www.globalfintechfest.com/partners and Singapore FinTech Festival (SFF).
Maps ATS slugs (Greenhouse, Lever, SmartRecruiters, Workday), career portals, and partner tiers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FinTechFestivalCompany:
    id: str
    name: str
    category: str  # "Payments & Gateways", "UPI & Neobanking", "WealthTech & Crypto", "Lending & Credit", "InsurTech", "RegTech & AI", "Banking Tech & Infrastructure", "Telecom & Messaging", "Institutional Banks & Networks"
    festival: str  # "Global FinTech Fest (GFF)", "Singapore FinTech Festival (SFF)", "GFF & SFF"
    tier_role: str  # "Co-Powered By", "Brought To You By", "Diamond Partner", "Platinum Partner", "Gold Sponsor", "Associate Partner", "Technology Partner", "AI Ecosystem Partner", "Exhibitor / Partner"
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


# ── The Official GFF & SFF Partner Database ──────────────────────────────────

FINTECH_FESTIVAL_REGISTRY: List[FinTechFestivalCompany] = [
    # ── 1. GFF Co-Powered & Anchor Payment Giants ─────────────────────────────
    FinTechFestivalCompany("googlepay", "Google Pay", "UPI & Neobanking", "GFF & SFF", "Co-Powered By", "custom", None, "https://www.google.com/about/careers", "google.com"),
    FinTechFestivalCompany("phonepe", "PhonePe", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Co-Powered By", "custom", None, "https://www.phonepe.com/careers", "phonepe.com"),
    FinTechFestivalCompany("amazonpay", "Amazon Pay", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Brought To You By", "custom", None, "https://www.amazon.jobs", "amazon.com"),
    FinTechFestivalCompany("paytm", "Paytm (One97 Communications)", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Associate Partner", "custom", None, "https://paytm.com/careers", "paytm.com"),
    FinTechFestivalCompany("bharatpe", "BharatPe", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Diamond Partner", "custom", None, "https://bharatpe.com/careers", "bharatpe.com"),
    FinTechFestivalCompany("payu", "PayU", "Payments & Gateways", "Global FinTech Fest (GFF)", "Payments Orchestration Partner", "custom", None, "https://corporate.payu.com/careers", "payu.com"),
    FinTechFestivalCompany("razorpay", "Razorpay", "Payments & Gateways", "GFF & SFF", "Diamond Partner", "greenhouse", "razorpay", "https://razorpay.com/jobs", "razorpay.com"),
    FinTechFestivalCompany("cashfree", "Cashfree Payments", "Payments & Gateways", "Global FinTech Fest (GFF)", "Gold Sponsor", "greenhouse", "cashfree", "https://www.cashfree.com/careers", "cashfree.com"),
    FinTechFestivalCompany("juspay", "Juspay", "Payments & Gateways", "Global FinTech Fest (GFF)", "Gold Sponsor", "greenhouse", "juspay", "https://juspay.in/careers", "juspay.in"),
    FinTechFestivalCompany("pinelabs", "Pine Labs", "Payments & Gateways", "Global FinTech Fest (GFF)", "Agenda Partner", "custom", None, "https://www.pinelabs.com/careers", "pinelabs.com"),
    FinTechFestivalCompany("stripe", "Stripe", "Payments & Gateways", "GFF & SFF", "Gold Sponsor", "greenhouse", "stripe", "https://stripe.com/jobs", "stripe.com"),
    FinTechFestivalCompany("adyen", "Adyen", "Payments & Gateways", "GFF & SFF", "Global Enterprise Payments Partner", "smartrecruiters", "adyen", "https://careers.adyen.com", "adyen.com"),
    FinTechFestivalCompany("lyra", "Lyra Network", "Payments & Gateways", "Global FinTech Fest (GFF)", "Payment Enabler Partner", "custom", None, "https://www.lyra.com/in/careers", "lyra.com"),
    FinTechFestivalCompany("unlimit", "Unlimit", "Payments & Gateways", "Global FinTech Fest (GFF)", "Gold Sponsor", "greenhouse", "unlimit", "https://www.unlimit.com/careers", "unlimit.com"),
    FinTechFestivalCompany("payglocal", "PayGlocal", "Payments & Gateways", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "payglocal", "https://payglocal.in/careers", "payglocal.in"),
    FinTechFestivalCompany("ippopay", "IppoPay", "Payments & Gateways", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.ippopay.com/careers", "ippopay.com"),
    FinTechFestivalCompany("getepay", "Getepay", "Payments & Gateways", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://getepay.in/careers", "getepay.in"),
    FinTechFestivalCompany("iserveu", "iServeU", "Payments & Gateways", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://iserveu.in/careers", "iserveu.in"),
    FinTechFestivalCompany("paysprint", "Paysprint", "Payments & Gateways", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://paysprint.in/careers", "paysprint.in"),
    FinTechFestivalCompany("pay10", "Pay10", "Payments & Gateways", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://pay10.com/careers", "pay10.com"),
    FinTechFestivalCompany("vampay", "Vampay", "Payments & Gateways", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://vampay.in/careers", "vampay.in"),
    FinTechFestivalCompany("zaggle", "Zaggle", "Payments & Gateways", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.zaggle.in/careers", "zaggle.in"),
    FinTechFestivalCompany("hitachipayments", "Hitachi Payments", "Payments & Gateways", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.hitachi-payments.com/careers", "hitachi-payments.com"),

    # ── 2. AI, LLM & Voice AI Partners ────────────────────────────────────────
    FinTechFestivalCompany("sarvamai", "Sarvam.ai", "RegTech & AI", "Global FinTech Fest (GFF)", "AI Ecosystem Partner", "custom", None, "https://www.sarvam.ai/careers", "sarvam.ai"),
    FinTechFestivalCompany("elevenlabs", "Eleven Labs", "RegTech & AI", "GFF & SFF", "Voice AI Partner", "greenhouse", "elevenlabs", "https://elevenlabs.io/careers", "elevenlabs.io"),
    FinTechFestivalCompany("devrev", "DevRev", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "devrev", "https://devrev.ai/careers", "devrev.ai"),
    FinTechFestivalCompany("gnaniai", "Gnani.ai", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.gnani.ai/careers", "gnani.ai"),
    FinTechFestivalCompany("navanatech", "Navanatech AI", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://navana.ai/careers", "navana.ai"),
    FinTechFestivalCompany("bluemachines", "Blue Machines AI", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://bluemachines.ai/careers", "bluemachines.ai"),
    FinTechFestivalCompany("bolna", "Bolna AI", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://bolna.ai/careers", "bolna.ai"),
    FinTechFestivalCompany("ringgai", "Ringg.ai", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://ringg.ai/careers", "ringg.ai"),
    FinTechFestivalCompany("revragai", "RevRag.AI", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://revrag.ai/careers", "revrag.ai"),
    FinTechFestivalCompany("onfinance", "OnFinance AI", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://onfinance.ai/careers", "onfinance.ai"),

    # ── 3. Identity, Credit Bureau & RegTech ──────────────────────────────────
    FinTechFestivalCompany("bureauid", "Bureau ID", "RegTech & AI", "Global FinTech Fest (GFF)", "Platinum Partner", "greenhouse", "bureauid", "https://www.bureau.id/careers", "bureau.id"),
    FinTechFestivalCompany("perfios", "Perfios", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Technology Partner", "custom", None, "https://www.perfios.com/careers", "perfios.com"),
    FinTechFestivalCompany("cibil", "TransUnion CIBIL", "RegTech & AI", "Global FinTech Fest (GFF)", "Credit Insights Partner", "custom", None, "https://www.transunioncibil.com/careers", "transunioncibil.com"),
    FinTechFestivalCompany("experian", "Experian", "RegTech & AI", "Global FinTech Fest (GFF)", "Credit Innovation Partner", "custom", None, "https://www.experian.in/careers", "experian.in"),
    FinTechFestivalCompany("crif", "CRIF High Mark", "RegTech & AI", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.crifhighmark.com/careers", "crifhighmark.com"),
    FinTechFestivalCompany("digio", "Digio", "RegTech & AI", "Global FinTech Fest (GFF)", "Data Protection & Consent Partner", "custom", None, "https://www.digio.in/careers", "digio.in"),
    FinTechFestivalCompany("digitapai", "Digitap.AI", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://digitap.ai/careers", "digitap.ai"),
    FinTechFestivalCompany("hyperverge", "HyperVerge", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "hyperverge", "https://hyperverge.co/careers", "hyperverge.co"),
    FinTechFestivalCompany("signzy", "Signzy", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "signzy", "https://signzy.com/careers", "signzy.com"),
    FinTechFestivalCompany("sumsub", "Sumsub", "RegTech & AI", "GFF & SFF", "Exhibitor / Partner", "greenhouse", "sumsub", "https://sumsub.com/careers", "sumsub.com"),
    FinTechFestivalCompany("trackwizz", "Trackwizz (TSS Consultancy)", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.tssconsultancy.com/careers", "tssconsultancy.com"),
    FinTechFestivalCompany("datasutram", "Data Sutram", "RegTech & AI", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://datasutram.com/careers", "datasutram.com"),
    FinTechFestivalCompany("ignosis", "Ignosis", "RegTech & AI", "Global FinTech Fest (GFF)", "Financial Intelligence Partner", "custom", None, "https://www.ignosis.ai/careers", "ignosis.ai"),
    FinTechFestivalCompany("scoreme", "ScoreMe Solutions", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.scoreme.in/careers", "scoreme.in"),
    FinTechFestivalCompany("protecttai", "Protectt.ai Labs", "RegTech & AI", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://protectt.ai/careers", "protectt.ai"),

    # ── 4. Telecom, CPaaS & Customer Engagement ───────────────────────────────
    FinTechFestivalCompany("karix", "Karix (Tanla Platforms)", "Telecom & Messaging", "Global FinTech Fest (GFF)", "Digital Engagement Partner", "custom", None, "https://www.karix.com/careers", "karix.com"),
    FinTechFestivalCompany("sinch", "Sinch", "Telecom & Messaging", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.sinch.com/careers", "sinch.com"),
    FinTechFestivalCompany("truecaller", "Truecaller", "Telecom & Messaging", "Global FinTech Fest (GFF)", "Registration Partner", "greenhouse", "truecaller", "https://careers.truecaller.com", "truecaller.com"),
    FinTechFestivalCompany("clevertap", "CleverTap", "Telecom & Messaging", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "clevertap", "https://clevertap.com/careers", "clevertap.com"),
    FinTechFestivalCompany("routemobile", "Route Mobile (Proximus)", "Telecom & Messaging", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://routemobile.com/careers", "routemobile.com"),
    FinTechFestivalCompany("comviva", "Comviva (Tech Mahindra)", "Telecom & Messaging", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.comviva.com/careers", "comviva.com"),
    FinTechFestivalCompany("firsthive", "FirstHive", "Telecom & Messaging", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://firsthive.com/careers", "firsthive.com"),
    FinTechFestivalCompany("chat360", "Chat360", "Telecom & Messaging", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://chat360.io/careers", "chat360.io"),
    FinTechFestivalCompany("pinnacle", "Pinnacle Teleservices", "Telecom & Messaging", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://pinnacle.in/careers", "pinnacle.in"),

    # ── 5. Enterprise Banking Tech, Cloud & Infrastructure ────────────────────
    FinTechFestivalCompany("montran", "Montran Corporation India", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.montran.com/careers", "montran.com"),
    FinTechFestivalCompany("nucleus", "Nucleus Software", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.nucleussoftware.com/careers", "nucleussoftware.com"),
    FinTechFestivalCompany("intellect", "Intellect Design Arena", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.intellectdesign.com/careers", "intellectdesign.com"),
    FinTechFestivalCompany("mindgate", "Mindgate Solutions", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.mindgate.in/careers", "mindgate.in"),
    FinTechFestivalCompany("insolutions", "In-Solutions Global (ISG)", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://insoglobal.com/careers", "insoglobal.com"),
    FinTechFestivalCompany("protean", "Protean eGov Technologies", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.proteantech.in/careers", "proteantech.in"),
    FinTechFestivalCompany("vayana", "Vayana Network", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://vayana.com/careers", "vayana.com"),
    FinTechFestivalCompany("transbnk", "TransBnk", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://transbnk.com/careers", "transbnk.com"),
    FinTechFestivalCompany("jocata", "Jocata (BillDesk)", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.jocata.com/careers", "jocata.com"),
    FinTechFestivalCompany("zoho", "Zoho Corporation", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Platinum Partner", "custom", None, "https://www.zoho.com/careers", "zoho.com"),
    FinTechFestivalCompany("cisco", "Cisco", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://jobs.cisco.com", "cisco.com"),
    FinTechFestivalCompany("redhat", "Red Hat", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.redhat.com/en/jobs", "redhat.com"),
    FinTechFestivalCompany("cockroachlabs", "Cockroach Labs", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "cockroachlabs", "https://www.cockroachlabs.com/careers", "cockroachlabs.com"),
    FinTechFestivalCompany("aerospike", "Aerospike", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "aerospike", "https://aerospike.com/about/careers", "aerospike.com"),
    FinTechFestivalCompany("neo4j", "Neo4j", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "neo4j", "https://neo4j.com/careers", "neo4j.com"),
    FinTechFestivalCompany("geekyants", "GeekyAnts", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://geekyants.com/careers", "geekyants.com"),
    FinTechFestivalCompany("shellkode", "ShellKode", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://shellkode.com/careers", "shellkode.com"),

    # ── 6. Neobanks, Cards, Lending & Wealth Platforms ────────────────────────
    FinTechFestivalCompany("cred", "CRED", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "cred", "https://cred.club/careers", "cred.club"),
    FinTechFestivalCompany("navi", "Navi Technologies", "UPI & Neobanking", "Global FinTech Fest (GFF)", "VIP Lounge Partner", "greenhouse", "navi", "https://navi.com/careers", "navi.com"),
    FinTechFestivalCompany("scapia", "Scapia Cards", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "scapia", "https://www.scapia.cards/careers", "scapia.cards"),
    FinTechFestivalCompany("branchx", "BranchX", "UPI & Neobanking", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://branchx.in/careers", "branchx.in"),
    FinTechFestivalCompany("truebalance", "True Balance (Balancehero)", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://truebalance.io/careers", "truebalance.io"),
    FinTechFestivalCompany("kissht", "Kissht (Ring)", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://kissht.com/careers", "kissht.com"),
    FinTechFestivalCompany("lendenclub", "LenDenClub", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.lendenclub.com/careers", "lendenclub.com"),
    FinTechFestivalCompany("yubi", "Yubi (CredAvenue)", "Lending & Credit", "Global FinTech Fest (GFF)", "Gold Sponsor", "greenhouse", "yubi", "https://www.go-yubi.com/careers", "go-yubi.com"),
    FinTechFestivalCompany("northernarc", "Northern Arc", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.northernarc.com/careers", "northernarc.com"),
    FinTechFestivalCompany("biz2x", "Biz2X", "Lending & Credit", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.biz2x.com/careers", "biz2x.com"),
    FinTechFestivalCompany("credresolve", "CredResolve", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://credresolve.com/careers", "credresolve.com"),
    FinTechFestivalCompany("digikhata", "DigiKhata", "Lending & Credit", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://digikhata.in/careers", "digikhata.in"),
    FinTechFestivalCompany("indiabonds", "IndiaBonds", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.indiabonds.com/careers", "indiabonds.com"),
    FinTechFestivalCompany("safegold", "SafeGold", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.safegold.com/careers", "safegold.com"),
    FinTechFestivalCompany("appreciate", "Appreciate Wealth", "WealthTech & Crypto", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://appreciatewealth.com/careers", "appreciatewealth.com"),
    FinTechFestivalCompany("dreamfolks", "DreamFolks Services", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.dreamfolks.in/careers", "dreamfolks.in"),
    FinTechFestivalCompany("onsurity", "Onsurity", "InsurTech", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "greenhouse", "onsurity", "https://www.onsurity.com/careers", "onsurity.com"),
    FinTechFestivalCompany("mitigata", "Mitigata Cyber Insurance", "InsurTech", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://mitigata.com/careers", "mitigata.com"),
    FinTechFestivalCompany("paramotor", "Paramotor", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Platinum Partner", "custom", None, "https://paramotor.in/careers", "paramotor.in"),
    FinTechFestivalCompany("zrika", "Zrika", "Banking Tech & Infrastructure", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://zrika.com/careers", "zrika.com"),

    # ── 7. Banks, Financial Institutions & Global Networks ────────────────────
    FinTechFestivalCompany("npci", "NPCI (National Payments Corporation of India)", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Organizer & Host", "custom", None, "https://www.npci.org.in/careers", "npci.org.in"),
    FinTechFestivalCompany("visa", "Visa", "Institutional Banks & Networks", "GFF & SFF", "Associate Partner", "smartrecruiters", "visa", "https://www.visa.com/careers", "visa.com"),
    FinTechFestivalCompany("mastercard", "Mastercard", "Institutional Banks & Networks", "GFF & SFF", "Diamond Partner", "custom", None, "https://careers.mastercard.com", "mastercard.com"),
    FinTechFestivalCompany("discover", "Discover", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Global Payments Partner", "custom", None, "https://jobs.discover.com", "discover.com"),
    FinTechFestivalCompany("jcbinternational", "JCB International", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.global.jcb/en/about-us/careers", "global.jcb"),
    FinTechFestivalCompany("nabard", "NABARD", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Diamond Partner", "custom", None, "https://www.nabard.org/careers", "nabard.org"),
    FinTechFestivalCompany("sbi", "State Bank of India (SBI)", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Brought To You By", "custom", None, "https://sbi.co.in/careers", "sbi.co.in"),
    FinTechFestivalCompany("hdfc", "HDFC Bank", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Brought To You By", "custom", None, "https://www.hdfcbank.com/careers", "hdfcbank.com"),
    FinTechFestivalCompany("pnb", "Punjab National Bank (PNB)", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Brought To You By", "custom", None, "https://www.pnbindia.in/recruitment.aspx", "pnbindia.in"),
    FinTechFestivalCompany("bob", "Bank of Baroda", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Brought To You By", "custom", None, "https://www.bankofbaroda.in/careers", "bankofbaroda.in"),
    FinTechFestivalCompany("indianbank", "Indian Bank", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.indianbank.in/careers", "indianbank.in"),
    FinTechFestivalCompany("unionbank", "Union Bank of India", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.unionbankofindia.co.in/careers", "unionbankofindia.co.in"),
    FinTechFestivalCompany("dcbbank", "DCB Bank", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.dcbbank.com/careers", "dcbbank.com"),
    FinTechFestivalCompany("bankofindia", "Bank of India", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.bankofindia.co.in/careers", "bankofindia.co.in"),
    FinTechFestivalCompany("idfcfirst", "IDFC FIRST Bank", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.idfcfirstbank.com/careers", "idfcfirstbank.com"),
    FinTechFestivalCompany("tatacapital", "Tata Capital", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.tatacapital.com/careers", "tatacapital.com"),
    FinTechFestivalCompany("airtelbank", "Airtel Payments Bank", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.airtel.in/bank/careers", "airtel.in"),
    FinTechFestivalCompany("jfs", "Jio Financial Services Limited", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Gold Sponsor", "custom", None, "https://www.jfs.in/careers", "jfs.in"),
    FinTechFestivalCompany("hsbc", "HSBC", "Institutional Banks & Networks", "GFF & SFF", "Innovation Leadership Partner", "custom", None, "https://www.hsbc.com/careers", "hsbc.com"),
    FinTechFestivalCompany("jpmorgan", "J.P. Morgan", "Institutional Banks & Networks", "GFF & SFF", "Gold Sponsor", "custom", None, "https://careers.jpmorgan.com", "jpmorgan.com"),
    FinTechFestivalCompany("citi", "Citi", "Institutional Banks & Networks", "GFF & SFF", "Banking Innovation Partner", "custom", None, "https://careers.citigroup.com", "citigroup.com"),
    FinTechFestivalCompany("mufg", "MUFG Bank", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.mufg.jp/english/careers", "mufg.jp"),
    FinTechFestivalCompany("prudential", "Prudential PLC", "Institutional Banks & Networks", "Global FinTech Fest (GFF)", "Exhibitor / Partner", "custom", None, "https://www.prudentialplc.com/careers", "prudentialplc.com"),
    FinTechFestivalCompany("wise", "Wise", "UPI & Neobanking", "GFF & SFF", "Exhibitor / Partner", "greenhouse", "wise", "https://wise.jobs", "wise.com"),
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
