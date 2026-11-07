"""
tier1_companies.py — Comprehensive Registry & Intelligence for 60 Tier-1 Tech Companies.

Contains:
  1. Compensation & Leveling Matrix (4-YOE Base, Bonus, RSU, Typical TC, Negotiation Targets).
  2. Official Career Pages & Direct ATS Endpoints (Greenhouse, Lever, SmartRecruiters, Ashby).
  3. Boolean & X-Ray Sourcing Queries for Engineering Managers, Senior Engineers, and Alumni.
  4. Specialized Referral Outreach Templates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Tier1Company:
    rank: int
    name: str
    likely_level: str
    base_range_lakhs: str
    bonus_range_lakhs: str
    rsu_range_lakhs: str
    typical_tc_lakhs: str
    negotiation_target_lakhs: str
    evidence_grade: str  # "V" (Verified), "M" (Market Estimate), "V/M"
    ats_platform: str   # "greenhouse", "lever", "smartrecruiters", "ashby", "workday", "custom"
    ats_slug: Optional[str] = None
    careers_url: Optional[str] = None
    domain: Optional[str] = None
    xray_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "name": self.name,
            "likely_level": self.likely_level,
            "base_range_lakhs": self.base_range_lakhs,
            "bonus_range_lakhs": self.bonus_range_lakhs,
            "rsu_range_lakhs": self.rsu_range_lakhs,
            "typical_tc_lakhs": self.typical_tc_lakhs,
            "negotiation_target_lakhs": self.negotiation_target_lakhs,
            "evidence_grade": self.evidence_grade,
            "ats_platform": self.ats_platform,
            "ats_slug": self.ats_slug,
            "careers_url": self.careers_url,
            "domain": self.domain,
            "xray_keywords": self.xray_keywords,
        }


# ── The 60 Tier-1 Target Companies ───────────────────────────────────────────

TIER1_REGISTRY: List[Tier1Company] = [
    Tier1Company(1, "Rubrik", "L4 / SWE II", "₹50–55", "₹4–5", "₹40–45", "₹94–103", "₹105–115L", "V", "greenhouse", "rubrik", "https://www.rubrik.com/company/careers", "rubrik.com", ["Software Engineer", "Engineering Manager", "Backend"]),
    Tier1Company(2, "Stripe", "L2/L3", "₹50–60", "₹5–8", "₹30–45", "₹90–105", "₹105–120L", "V", "greenhouse", "stripe", "https://stripe.com/jobs", "stripe.com", ["Software Engineer", "Staff Engineer", "Engineering Lead"]),
    Tier1Company(3, "Databricks", "L4", "₹45–50", "₹3–5", "₹40–45", "₹90–100", "₹100–115L", "V", "greenhouse", "databricks", "https://www.databricks.com/company/careers", "databricks.com", ["Software Engineer", "Engineering Manager"]),
    Tier1Company(4, "Meta", "E4", "₹43–47", "₹3–4", "₹30–36", "₹77–85", "₹90–100L", "V", "custom", None, "https://www.metacareers.com", "meta.com", ["Software Engineer", "Engineering Manager"]),
    Tier1Company(5, "Airbnb", "G8", "₹43–48", "₹4–6", "₹32–38", "₹80–90", "₹90–100L", "V", "greenhouse", "airbnb", "https://careers.airbnb.com", "airbnb.com", ["Software Engineer", "Engineering Manager"]),
    Tier1Company(6, "Atlassian", "P40", "₹48–51", "₹6–8", "₹15–18", "₹70–78", "₹80–90L", "V", "custom", None, "https://www.atlassian.com/company/careers", "atlassian.com", ["Software Engineer", "Engineering Manager"]),
    Tier1Company(7, "Broadcom", "ICB2/ICB3", "₹26–35", "₹2–4", "₹40–50", "₹68–80", "₹80–90L", "V", "custom", None, "https://careers.broadcom.com", "broadcom.com", ["Software Engineer", "R&D Manager"]),
    Tier1Company(8, "Uber", "SWE II", "₹47–51", "₹6–7", "₹15–18", "₹68–76", "₹78–88L", "V", "greenhouse", "uber", "https://www.uber.com/careers", "uber.com", ["Software Engineer", "Engineering Manager", "Tech Lead"]),
    Tier1Company(9, "Google", "L4", "₹40–44", "₹2–3", "₹18–22", "₹58–67", "₹68–75L", "V", "custom", None, "https://www.google.com/about/careers", "google.com", ["Software Engineer", "Engineering Manager"]),
    Tier1Company(10, "Coinbase", "IC4", "₹43–47", "₹2–3", "₹23–27", "₹68–77", "₹78–88L", "V", "greenhouse", "coinbase", "https://www.coinbase.com/careers", "coinbase.com", ["Software Engineer", "Engineering Manager"]),
    Tier1Company(11, "LinkedIn", "IC2/IC3", "₹40–48", "₹2–4", "₹18–27", "₹65–78", "₹75–85L", "M", "custom", None, "https://careers.linkedin.com", "linkedin.com", ["Software Engineer", "Engineering Manager"]),
    Tier1Company(12, "Apple", "ICT3 / strong ICT3", "₹34–40", "₹1–2", "₹25–32", "₹60–72", "₹70–80L", "V/M", "custom", None, "https://jobs.apple.com", "apple.com", ["Software Engineer", "Engineering Manager"]),
    Tier1Company(13, "Adobe", "SWE 4", "₹49–53", "₹3–4", "₹18–22", "₹70–80", "₹78–88L", "V", "custom", None, "https://www.adobe.com/careers.html", "adobe.com", ["Software Engineer", "Engineering Manager"]),
    Tier1Company(14, "Salesforce", "MTS / Senior MTS", "₹38–50", "₹2–7", "₹8–15", "₹48–68", "₹60–72L", "V", "custom", None, "https://www.salesforce.com/company/careers", "salesforce.com", ["Member of Technical Staff", "Senior MTS"]),
    Tier1Company(15, "ServiceNow", "IC2 / IC3", "₹40–45", "₹2–3", "₹17–21", "₹58–67", "₹68–78L", "V", "smartrecruiters", "servicenow", "https://careers.servicenow.com", "servicenow.com", ["Software Engineer", "Senior Software Engineer"]),
    Tier1Company(16, "Booking.com", "F", "₹50–58", "₹5–7", "₹15–22", "₹75–87", "₹85–95L", "V/M", "greenhouse", "bookingcom", "https://jobs.booking.com", "booking.com", ["Software Engineer", "Tech Lead"]),
    Tier1Company(17, "GitLab", "Intermediate", "₹58–65", "₹2–3", "₹7–10", "₹67–76", "₹78–88L", "V", "greenhouse", "gitlab", "https://about.gitlab.com/jobs", "gitlab.com", ["Backend Engineer", "Senior Engineer"]),
    Tier1Company(18, "Intuit", "SWE II", "₹31–34", "₹2–3", "₹10–13", "₹44–50", "₹52–58L", "V", "custom", None, "https://www.intuit.com/careers", "intuit.com", ["Software Engineer 2", "Senior Software Engineer"]),
    Tier1Company(19, "GitHub", "E3", "₹35–39", "₹3–4", "₹13–15", "₹51–58", "₹60–68L", "V", "greenhouse", "github", "https://github.com/about/careers", "github.com", ["Software Engineer", "Senior Engineer"]),
    Tier1Company(20, "NVIDIA", "IC2", "₹22–25", "~₹0", "₹9–11", "₹30–36", "₹38–45L", "V", "custom", None, "https://www.nvidia.com/en-us/about-nvidia/careers", "nvidia.com", ["System Software Engineer", "Deep Learning Engineer"]),
    Tier1Company(21, "Snowflake", "IC2", "₹18–21", "₹1–2", "₹7–9", "₹26–31", "₹33–40L", "V/M", "greenhouse", "snowflake", "https://careers.snowflake.com", "snowflake.com", ["Software Engineer", "Senior Software Engineer"]),
    Tier1Company(22, "Twilio", "IC2", "₹25–28", "₹1–2", "₹11–14", "₹36–42", "₹44–50L", "V", "greenhouse", "twilio", "https://www.twilio.com/company/jobs", "twilio.com", ["Software Engineer", "Senior Software Engineer"]),
    Tier1Company(23, "Walmart Global Tech", "P3", "₹23–26", "₹4–5", "₹6–7", "₹32–38", "₹40–45L", "V", "custom", None, "https://careers.walmart.com", "walmart.com", ["Software Engineer III", "Staff Software Engineer"]),
    Tier1Company(24, "PayPal", "CL5", "₹23–25", "₹2–3", "₹6–7", "₹30–35", "₹37–43L", "V", "custom", None, "https://careers.pypl.com", "paypal.com", ["Software Engineer", "Senior Software Engineer"]),
    Tier1Company(25, "Okta", "SWE II", "₹24–27", "₹1–2", "₹7–8", "₹31–36", "₹38–43L", "V", "greenhouse", "okta", "https://www.okta.com/company/careers", "okta.com", ["Software Engineer", "Senior Software Engineer"]),
    Tier1Company(26, "Microsoft", "61 / SDE II", "₹29–31", "₹2", "₹10–12", "₹41–47", "₹48–55L", "V", "custom", None, "https://careers.microsoft.com", "microsoft.com", ["Software Engineer II", "Senior Software Engineer"]),
    Tier1Company(27, "Amazon", "L5 / SDE II", "₹44–48", "<₹1", "₹12–15", "₹56–63", "₹65–72L", "V", "custom", None, "https://www.amazon.jobs", "amazon.com", ["Software Development Engineer II", "SDE II"]),
    Tier1Company(28, "Qualcomm", "Engineer / Senior Engineer", "₹28–34", "₹2–3", "₹8–11", "₹38–48", "₹45–52L", "V/M", "custom", None, "https://www.qualcomm.com/company/careers", "qualcomm.com", ["Senior Software Engineer", "Staff Engineer"]),
    Tier1Company(29, "Cisco", "Grade 8-ish", "₹31–35", "₹1–2", "₹4–6", "₹37–43", "₹45–50L", "V/M", "custom", None, "https://jobs.cisco.com", "cisco.com", ["Software Engineer", "Senior Software Engineer"]),
    Tier1Company(30, "VMware/Broadcom VMware", "MTS 2/3", "₹25–32", "₹2", "₹5–7", "₹32–40", "₹42–48L", "V/M", "custom", None, "https://careers.vmware.com", "vmware.com", ["Member of Technical Staff", "Senior MTS"]),
    Tier1Company(31, "Oracle", "IC2", "₹18–21", "~₹0", "₹8–10", "₹26–30", "₹32–38L", "V", "custom", None, "https://www.oracle.com/careers", "oracle.com", ["Software Developer 2", "Senior Developer"]),
    Tier1Company(32, "Intel", "Grade 5/6", "₹22–28", "₹1–2", "₹1–3", "₹25–32", "₹33–38L", "V/M", "custom", None, "https://jobs.intel.com", "intel.com", ["Software Engineer", "Senior Software Engineer"]),
    Tier1Company(33, "Bloomberg", "SWE", "₹37–40", "₹4–5", "₹0", "₹41–46", "₹48–54L", "V", "custom", None, "https://www.bloomberg.com/careers", "bloomberg.com", ["Software Engineer", "Senior Software Engineer"]),
    Tier1Company(34, "JPMorgan Chase", "Associate", "₹24–27", "₹2–3", "₹0", "₹26–31", "₹32–38L", "V", "custom", None, "https://careers.jpmorgan.com", "jpmorgan.com", ["Software Engineer", "Associate Software Engineer"]),
    Tier1Company(35, "Goldman Sachs", "Associate", "₹30–33", "₹6–8", "₹0", "₹36–41", "₹42–48L", "V", "custom", None, "https://www.goldmansachs.com/careers", "goldmansachs.com", ["Associate", "Software Engineering Associate"]),
    Tier1Company(36, "Morgan Stanley", "Associate", "₹25–30", "₹3–5", "₹0–2", "₹30–37", "₹38–44L", "M", "custom", None, "https://www.morganstanley.com/about-us/careers", "morganstanley.com", ["Associate", "Manager Software Engineering"]),
    Tier1Company(37, "Visa", "L4", "₹17–20", "₹1", "₹4–5", "₹22–27", "₹28–33L", "V", "smartrecruiters", "visa", "https://www.visa.com/careers", "visa.com", ["Senior Software Engineer", "Lead Software Engineer"]),
    Tier1Company(38, "Mastercard", "L8", "₹21–24", "₹1", "<₹1", "₹28–32", "₹33–38L", "V", "custom", None, "https://careers.mastercard.com", "mastercard.com", ["Senior Software Engineer", "Lead Engineer"]),
    Tier1Company(39, "PhonePe", "SWE 2", "₹36–39", "~₹0.5", "₹9–10", "₹44–50", "₹52–58L", "V", "custom", None, "https://www.phonepe.com/careers", "phonepe.com", ["Software Engineer 2", "Engineering Manager"]),
    Tier1Company(40, "Flipkart", "SDE 2", "₹29–32", "₹2", "₹3–4", "₹33–38", "₹40–46L", "V", "custom", None, "https://www.flipkartcareers.com", "flipkart.com", ["SDE 2", "SDE 3", "Engineering Manager"]),
    Tier1Company(41, "Razorpay", "Senior SWE", "₹34–37", "~₹0", "₹5–6", "₹38–43", "₹45–50L", "V", "greenhouse", "razorpay", "https://razorpay.com/jobs", "razorpay.com", ["Senior Software Engineer", "Tech Lead"]),
    Tier1Company(42, "CRED", "L3 / early L4", "₹30–38", "~₹0", "₹4–11", "₹34–48", "₹42–52L", "V/M", "greenhouse", "cred", "https://cred.club/careers", "cred.club", ["Backend Engineer", "Senior Backend Engineer"]),
    Tier1Company(43, "Meesho", "SWE II", "₹33–36", "<₹1", "₹7–8", "₹40–44", "₹46–52L", "V", "greenhouse", "meesho", "https://meesho.io/jobs", "meesho.io", ["SDE 2", "SDE 3", "Tech Lead"]),
    Tier1Company(44, "Zepto", "SWE II", "₹39–42", "~₹1", "₹6–7", "₹43–48", "₹50–55L", "V", "lever", "zepto", "https://www.zeptonow.com/careers", "zeptonow.com", ["SDE 2", "SDE 3", "Engineering Manager"]),
    Tier1Company(45, "Groww", "SWE II", "₹31–33", "₹1–2", "₹2–3", "₹34–39", "₹42–48L", "V", "greenhouse", "groww", "https://groww.in/careers", "groww.in", ["Software Development Engineer 2", "Tech Lead"]),
    Tier1Company(46, "Zomato / Eternal", "SWE II/III", "₹30–38", "₹1–3", "₹4–8", "₹36–46", "₹45–52L", "M", "custom", None, "https://www.zomato.com/careers", "zomato.com", ["Senior Software Development Engineer", "Tech Lead"]),
    Tier1Company(47, "Swiggy", "L7/L8", "₹30–35", "~₹0–1", "₹6–8", "₹37–42", "₹44–50L", "V/M", "custom", None, "https://careers.swiggy.com", "swiggy.com", ["Software Development Engineer II", "SDE 3"]),
    Tier1Company(48, "Dream11", "SDE II", "₹46–50", "₹2", "₹4–5", "₹50–57", "₹58–65L", "V", "lever", "dream11", "https://careers.dream11.com", "dream11.com", ["SDE 2", "SDE 3", "Engineering Manager"]),
    Tier1Company(49, "Ola", "SWE II", "₹36–39", "₹1–2", "~₹0", "₹38–42", "₹44–50L", "V", "custom", None, "https://www.olacabs.com/careers", "olacabs.com", ["Software Development Engineer 2", "Tech Lead"]),
    Tier1Company(50, "Freshworks", "SWE / Senior transition", "₹20–26", "₹0–1", "₹0–2", "₹20–29", "₹25–32L", "V", "smartrecruiters", "freshworks", "https://www.freshworks.com/company/careers", "freshworks.com", ["Senior Software Engineer", "Lead Engineer"]),
    Tier1Company(51, "Zoho", "L2/L3", "₹15–19", "₹1–3", "₹0", "₹17–22", "₹23–26L", "V", "custom", None, "https://www.zoho.com/careers", "zoho.com", ["Software Developer", "Member Technical Staff"]),
    Tier1Company(52, "Paytm", "SWE / Senior SWE", "₹15–25", "<₹1", "~₹0.5", "₹16–27", "₹25–30L", "V", "custom", None, "https://paytm.com/careers", "paytm.com", ["Senior Software Engineer", "Tech Lead"]),
    Tier1Company(53, "Pine Labs", "SWE / Senior", "₹15–22", "₹1–2", "~₹0", "₹16–25", "₹25–30L", "V/M", "custom", None, "https://www.pinelabs.com/careers", "pinelabs.com", ["Senior Software Engineer", "Tech Lead"]),
    Tier1Company(54, "OYO", "SDE II", "₹27–30", "~₹1", "₹3–4", "₹30–35", "₹36–40L", "V", "custom", None, "https://www.oyorooms.com/careers", "oyorooms.com", ["Software Development Engineer II", "Tech Lead"]),
    Tier1Company(55, "Navi", "SWE II", "₹25–32", "₹1–3", "₹2–5", "₹30–40", "₹40–45L", "M", "greenhouse", "navi", "https://navi.com/careers", "navi.com", ["Software Engineer", "Senior Software Engineer"]),
    Tier1Company(56, "Policybazaar", "SWE II/III", "₹23–30", "₹1–3", "₹1–3", "₹28–36", "₹35–40L", "M", "custom", None, "https://www.policybazaar.com/careers", "policybazaar.com", ["Software Engineer", "Technical Lead"]),
    Tier1Company(57, "Ather Energy", "SWE II", "₹22–30", "₹1–3", "₹2–5", "₹26–37", "₹36–42L", "M", "custom", None, "https://www.atherenergy.com/careers", "atherenergy.com", ["Software Engineer", "Senior Software Engineer"]),
    Tier1Company(58, "InMobi", "SWE II", "₹27–34", "₹2–4", "₹3–7", "₹32–43", "₹42–48L", "M", "custom", None, "https://www.inmobi.com/company/careers", "inmobi.com", ["Software Development Engineer 2", "Tech Lead"]),
    Tier1Company(59, "Myntra", "SWE II/III", "₹29–35", "₹2–3", "₹3–6", "₹34–42", "₹42–48L", "M", "custom", None, "https://careers.myntra.com", "myntra.com", ["Software Development Engineer II", "Tech Lead"]),
    Tier1Company(60, "MakeMyTrip", "SWE II", "₹27–34", "₹2–3", "₹2–5", "₹31–40", "₹40–45L", "M", "custom", None, "https://careers.makemytrip.com", "makemytrip.com", ["Senior Software Engineer", "Tech Lead"]),
]


COMPANY_BY_NAME: Dict[str, Tier1Company] = {c.name.lower(): c for c in TIER1_REGISTRY}


def get_tier1_company(name: str) -> Optional[Tier1Company]:
    """Retrieve company benchmarking and sourcing config by name (case-insensitive substring match)."""
    name_clean = name.strip().lower()
    if name_clean in COMPANY_BY_NAME:
        return COMPANY_BY_NAME[name_clean]
    for key, comp in COMPANY_BY_NAME.items():
        if key in name_clean or name_clean in key:
            return comp
    return None
