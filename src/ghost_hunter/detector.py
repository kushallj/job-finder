from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .models import GhostSignal, GhostAnalysisResult

GHOST_KEYWORDS = [
    (r"\b(talent pool|future opportunities|ongoing consideration|evergreen|general application)\b", 35, "Generic Talent Pool / Evergreen Phrasing"),
    (r"\b(we are always looking|continuous hiring|keep your resume on file|potential openings)\b", 30, "Continuous Resume Harvester Phrasing"),
    (r"\b(reposted (?:30\+|60\+|90\+) days ago|posted (?:60\+|90\+) days ago)\b", 40, "Extreme Stale Repost Age"),
    (r"\b(hiring freeze|restructuring|reorg)\b", 30, "Company Restructuring Indicator"),
]

URGENT_KEYWORDS = [
    (r"\b(urgent requirement|immediate joiner|immediate start|urgent hiring|asap)\b", -25, "Immediate Joiner / Urgency Flag"),
    (r"\b(newly opened|new team|expansion|newly funded|series [a-d])\b", -20, "Fresh Expansion / Funding Growth Signal"),
    (r"\b(direct replacement|backfill|growth hire)\b", -15, "Direct Backfill / Growth Role"),
    (r"\b(interview within \d+ days|fast-track|quick process)\b", -20, "Fast-Track Interview Process"),
]


class GhostJobDetector:
    """
    Evaluates job postings against multiple structural, textual, and temporal signals
    to calculate the probability that a posting is a stale 'Ghost Job'.
    """

    def analyze_job(
        self,
        title: str,
        company: str,
        description: str,
        posted_date: Optional[str] = None,
        fetched_at: Optional[datetime] = None,
        has_decision_maker: bool = False,
    ) -> GhostAnalysisResult:
        score = 25.0  # Baseline neutral
        signals: List[GhostSignal] = []
        low_desc = f"{title.lower()} {description.lower()}"

        # 1. Temporal Age Analysis
        age_days = None
        if posted_date:
            try:
                # Try parsing relative or standard dates
                match_days = re.search(r"(\d+)\s+days?\s+ago", posted_date.lower())
                if match_days:
                    age_days = int(match_days.group(1))
                elif "month" in posted_date.lower():
                    age_days = 45
                elif "yesterday" in posted_date.lower() or "today" in posted_date.lower() or "hour" in posted_date.lower():
                    age_days = 1
            except Exception:
                pass

        if age_days is not None:
            if age_days <= 3:
                score -= 30.0
                signals.append(GhostSignal(
                    name="fresh_posting",
                    description=f"Posted {age_days} day(s) ago (Top 5% Freshness)",
                    score_impact=-30.0,
                    severity="positive",
                ))
            elif age_days <= 14:
                score -= 15.0
                signals.append(GhostSignal(
                    name="active_recency",
                    description=f"Posted within past 2 weeks ({age_days} days ago)",
                    score_impact=-15.0,
                    severity="positive",
                ))
            elif age_days >= 45:
                score += 35.0
                signals.append(GhostSignal(
                    name="stale_age",
                    description=f"Listing has been active for {age_days}+ days without filling",
                    score_impact=35.0,
                    severity="critical",
                ))
            elif age_days >= 25:
                score += 15.0
                signals.append(GhostSignal(
                    name="aging_listing",
                    description=f"Listing is {age_days} days old",
                    score_impact=15.0,
                    severity="warning",
                ))
        else:
            # Fallback based on text
            if any(k in low_desc for k in ("30+ days ago", "posted 1 month ago", "posted 2 months ago")):
                score += 30.0
                signals.append(GhostSignal(
                    name="textual_stale_flag",
                    description="Text indicates posting is 30+ days old",
                    score_impact=30.0,
                    severity="critical",
                ))

        # 2. Evergreen & Ghost Keywords
        for pattern, impact, desc in GHOST_KEYWORDS:
            if re.search(pattern, low_desc):
                score += impact
                signals.append(GhostSignal(
                    name="ghost_phrase_matched",
                    description=f"Matched: '{desc}'",
                    score_impact=impact,
                    severity="critical" if impact >= 30 else "warning",
                ))

        # 3. Urgency & Real Backfill Keywords
        for pattern, impact, desc in URGENT_KEYWORDS:
            if re.search(pattern, low_desc):
                score += impact
                signals.append(GhostSignal(
                    name="urgency_phrase_matched",
                    description=f"Matched: '{desc}'",
                    score_impact=impact,
                    severity="positive",
                ))

        # 4. Description Specificity & Depth
        desc_length = len(description.strip())
        if desc_length < 250:
            score += 25.0
            signals.append(GhostSignal(
                name="low_effort_jd",
                description="Extremely short/generic job description (<250 characters)",
                score_impact=25.0,
                severity="warning",
            ))
        elif desc_length > 1500:
            score -= 10.0
            signals.append(GhostSignal(
                name="detailed_architecture_spec",
                description="Comprehensive, highly tailored technical specifications (>1500 chars)",
                score_impact=-10.0,
                severity="positive",
            ))

        # 5. Verified Decision Maker Presence
        if has_decision_maker:
            score -= 20.0
            signals.append(GhostSignal(
                name="decision_maker_identified",
                description="Verified Engineering Leader or Recruiter linked to company",
                score_impact=-20.0,
                severity="positive",
            ))

        # Clamp score 0.0 to 100.0
        final_score = round(max(0.0, min(100.0, score)), 1)
        is_ghost = final_score >= 58.0

        if final_score < 35.0:
            urgency_label = "Active Hiring ⚡"
            recommendation = "High priority: Freshly opened role with active hiring velocity. Apply immediately & message hiring manager."
        elif final_score < 58.0:
            urgency_label = "Moderate / Evergreen ⚠️"
            recommendation = "Standard priority: Role is active but may be filled soon or part of ongoing sourcing. Reach out directly to stand out."
        else:
            urgency_label = "High Ghost Risk 👻"
            recommendation = "Caution: High likelihood of stale evergreen req or resume collection. Avoid generic ATS portal; reach out only via warm referral."

        return GhostAnalysisResult(
            ghost_score=final_score,
            urgency_label=urgency_label,
            is_ghost_risk=is_ghost,
            confidence_score=85.0 if age_days is not None else 72.0,
            estimated_age_days=age_days,
            signals=signals,
            action_recommendation=recommendation,
            timestamp=datetime.utcnow().isoformat(),
        )


ghost_job_detector = GhostJobDetector()
