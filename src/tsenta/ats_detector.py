"""
src/tsenta/ats_detector.py — Multi-Pattern ATS Classifier (18+ Systems Supported).

Accurately identifies the Applicant Tracking System (ATS) powering a job application URL
or career page markup to configure optimal form mapping, DOM selectors, and API endpoints.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ATSInfo:
    code: str
    name: str
    category: str
    supports_direct_api: bool
    supports_dom_autofill: bool
    typical_url_pattern: str
    color_token: str  # Color code for Web3 UI badges


SUPPORTED_ATS_LIST: List[ATSInfo] = [
    ATSInfo(
        code="greenhouse",
        name="Greenhouse",
        category="Modern ATS",
        supports_direct_api=True,
        supports_dom_autofill=True,
        typical_url_pattern=r"(boards\.greenhouse\.io|gh_jid=|greenhouse)",
        color_token="#00FFA3",  # Electric Lime
    ),
    ATSInfo(
        code="lever",
        name="Lever",
        category="Modern ATS",
        supports_direct_api=True,
        supports_dom_autofill=True,
        typical_url_pattern=r"(jobs\.lever\.co|lever\.co)",
        color_token="#00F0FF",  # Neon Cyan
    ),
    ATSInfo(
        code="workday",
        name="Workday",
        category="Enterprise ATS",
        supports_direct_api=False,
        supports_dom_autofill=True,
        typical_url_pattern=r"(myworkdayjobs\.com|myworkdaysite\.com|workday)",
        color_token="#FFE600",  # Solar Gold
    ),
    ATSInfo(
        code="ashby",
        name="Ashby",
        category="High-Growth ATS",
        supports_direct_api=True,
        supports_dom_autofill=True,
        typical_url_pattern=r"(jobs\.ashbyhq\.com|ashbyhq\.com|ashby)",
        color_token="#FF007A",  # Laser Pink
    ),
    ATSInfo(
        code="smartrecruiters",
        name="SmartRecruiters",
        category="Enterprise ATS",
        supports_direct_api=True,
        supports_dom_autofill=True,
        typical_url_pattern=r"(smartrecruiters\.com|sr-job)",
        color_token="#7928CA",  # Hyper Violet
    ),
    ATSInfo(
        code="bamboohr",
        name="BambooHR",
        category="Mid-Market ATS",
        supports_direct_api=True,
        supports_dom_autofill=True,
        typical_url_pattern=r"(bamboohr\.com)",
        color_token="#10B981",  # Emerald
    ),
    ATSInfo(
        code="jobvite",
        name="Jobvite",
        category="Enterprise ATS",
        supports_direct_api=False,
        supports_dom_autofill=True,
        typical_url_pattern=r"(jobs\.jobvite\.com|jobvite\.com)",
        color_token="#3B82F6",  # Blue
    ),
    ATSInfo(
        code="taleo",
        name="Oracle Taleo",
        category="Legacy Enterprise",
        supports_direct_api=False,
        supports_dom_autofill=True,
        typical_url_pattern=r"(taleo\.net|oraclecloud\.com\/ords\/custom_careers)",
        color_token="#F59E0B",  # Amber
    ),
    ATSInfo(
        code="icims",
        name="iCIMS",
        category="Enterprise ATS",
        supports_direct_api=False,
        supports_dom_autofill=True,
        typical_url_pattern=r"(icims\.com|careers-.*\.icims\.com)",
        color_token="#EC4899",  # Pink
    ),
    ATSInfo(
        code="successfactors",
        name="SAP SuccessFactors",
        category="Enterprise ATS",
        supports_direct_api=False,
        supports_dom_autofill=True,
        typical_url_pattern=r"(successfactors\.com|sap\.com\/careers)",
        color_token="#6366F1",  # Indigo
    ),
    ATSInfo(
        code="breezyhr",
        name="Breezy HR",
        category="Startup ATS",
        supports_direct_api=True,
        supports_dom_autofill=True,
        typical_url_pattern=r"(breezy\.hr)",
        color_token="#14B8A6",  # Teal
    ),
    ATSInfo(
        code="recruitee",
        name="Recruitee",
        category="Modern ATS",
        supports_direct_api=True,
        supports_dom_autofill=True,
        typical_url_pattern=r"(recruitee\.com)",
        color_token="#8B5CF6",  # Purple
    ),
    ATSInfo(
        code="workable",
        name="Workable",
        category="Modern ATS",
        supports_direct_api=True,
        supports_dom_autofill=True,
        typical_url_pattern=r"(apply\.workable\.com|workable\.com)",
        color_token="#06B6D4",  # Cyan
    ),
    ATSInfo(
        code="jazzhr",
        name="JazzHR",
        category="Mid-Market ATS",
        supports_direct_api=False,
        supports_dom_autofill=True,
        typical_url_pattern=r"(applytojob\.com|theresumator\.com)",
        color_token="#F97316",  # Orange
    ),
    ATSInfo(
        code="ripplematch",
        name="RippleMatch",
        category="Early Career",
        supports_direct_api=True,
        supports_dom_autofill=True,
        typical_url_pattern=r"(ripplematch\.com)",
        color_token="#A855F7",
    ),
    ATSInfo(
        code="handshake",
        name="Handshake",
        category="University/Campus",
        supports_direct_api=False,
        supports_dom_autofill=True,
        typical_url_pattern=r"(joinhandshake\.com)",
        color_token="#EF4444",
    ),
    ATSInfo(
        code="ziprecruiter",
        name="ZipRecruiter",
        category="Job Board ATS",
        supports_direct_api=True,
        supports_dom_autofill=True,
        typical_url_pattern=r"(ziprecruiter\.com)",
        color_token="#84CC16",
    ),
    ATSInfo(
        code="custom_ats",
        name="Enterprise Portal",
        category="Custom Direct",
        supports_direct_api=False,
        supports_dom_autofill=True,
        typical_url_pattern=r".*",
        color_token="#94A3B8",  # Slate Gray
    ),
]

_ATS_MAP: Dict[str, ATSInfo] = {ats.code: ats for ats in SUPPORTED_ATS_LIST}


def detect_ats(url: Optional[str], page_source: Optional[str] = None) -> ATSInfo:
    """Classify the ATS from URL pattern, URL query parameters, and page source heuristics."""
    url_str = (url or "").lower().strip()
    source_str = (page_source or "").lower()

    # 1. Check specific high-signal URL regex patterns
    if re.search(r"boards\.greenhouse\.io|gh_jid|greenhouse\.io", url_str):
        return _ATS_MAP["greenhouse"]
    if re.search(r"jobs\.lever\.co|lever\.co", url_str):
        return _ATS_MAP["lever"]
    if re.search(r"myworkdayjobs\.com|myworkdaysite\.com|workday", url_str):
        return _ATS_MAP["workday"]
    if re.search(r"jobs\.ashbyhq\.com|ashbyhq\.com", url_str):
        return _ATS_MAP["ashby"]
    if re.search(r"smartrecruiters\.com|sr-job", url_str):
        return _ATS_MAP["smartrecruiters"]
    if re.search(r"bamboohr\.com", url_str):
        return _ATS_MAP["bamboohr"]
    if re.search(r"jobs\.jobvite\.com|jobvite\.com", url_str):
        return _ATS_MAP["jobvite"]
    if re.search(r"taleo\.net", url_str):
        return _ATS_MAP["taleo"]
    if re.search(r"icims\.com", url_str):
        return _ATS_MAP["icims"]
    if re.search(r"successfactors\.com", url_str):
        return _ATS_MAP["successfactors"]
    if re.search(r"breezy\.hr", url_str):
        return _ATS_MAP["breezyhr"]
    if re.search(r"recruitee\.com", url_str):
        return _ATS_MAP["recruitee"]
    if re.search(r"apply\.workable\.com|workable\.com", url_str):
        return _ATS_MAP["workable"]
    if re.search(r"applytojob\.com|theresumator\.com", url_str):
        return _ATS_MAP["jazzhr"]
    if re.search(r"ripplematch\.com", url_str):
        return _ATS_MAP["ripplematch"]
    if re.search(r"joinhandshake\.com", url_str):
        return _ATS_MAP["handshake"]
    if re.search(r"ziprecruiter\.com", url_str):
        return _ATS_MAP["ziprecruiter"]

    # 2. Check page source clues if provided
    if source_str:
        if "greenhouse" in source_str or "gh_jid" in source_str:
            return _ATS_MAP["greenhouse"]
        if "lever-form" in source_str or "jobs.lever.co" in source_str:
            return _ATS_MAP["lever"]
        if "workday" in source_str or "wd-form" in source_str:
            return _ATS_MAP["workday"]
        if "ashby" in source_str or "ashbyhq" in source_str:
            return _ATS_MAP["ashby"]
        if "smartrecruiters" in source_str:
            return _ATS_MAP["smartrecruiters"]

    # Default fallback
    return _ATS_MAP["custom_ats"]
