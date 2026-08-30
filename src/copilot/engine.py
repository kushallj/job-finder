from __future__ import annotations

import re
import urllib.parse
from typing import List, Dict, Any, Optional

from src.ai.unified_ai_service import UnifiedAIService
from .models import BooleanDorkResult



class OSINTBooleanEngine:
    """
    Precision Google Boolean Dork & Career Intelligence Generation Engine.
    Synthesizes multi-operator search strings to find unindexed JDs, hiring manager inboxes,
    salary sheets, candidate take-homes, and engineering debriefs.
    """

    def __init__(self, ai_service: Optional[UnifiedAIService] = None):
        self.ai = ai_service or UnifiedAIService()


    def generate_dorks(
        self,
        role: str,
        company: Optional[str] = None,
        intent: str = "all",
    ) -> List[BooleanDorkResult]:
        company_clean = (company or "").strip()
        role_clean = role.strip()
        comp_filter = f'"{company_clean}"' if company_clean else ""

        results: List[BooleanDorkResult] = []

        # 1. Unindexed JDs & Cloud Docs
        if intent in ("all", "unindexed_jds"):
            q1 = f'site:lever.co OR site:greenhouse.io OR site:ashbyhq.com "{role_clean}" {comp_filter}'.strip()
            results.append(BooleanDorkResult(
                title="Unindexed ATS Openings (Lever / Greenhouse / Ashby)",
                query=q1,
                explanation="Directly targets ATS hosts bypassing search aggregators to find live or recently created job postings.",
                search_url=f"https://www.google.com/search?q={urllib.parse.quote(q1)}",
                category="unindexed_jds",
            ))

            q2 = f'site:notion.site OR site:notion.so "Job Description" OR "We are hiring" "{role_clean}" {comp_filter}'.strip()
            results.append(BooleanDorkResult(
                title="Hidden Notion Job Specs & Team Roadmaps",
                query=q2,
                explanation="Uncovers unindexed Notion workspace pages containing candid team descriptions and direct founder notes.",
                search_url=f"https://www.google.com/search?q={urllib.parse.quote(q2)}",
                category="unindexed_jds",
            ))

            q3 = f'site:docs.google.com/document/d "Job Description" "{role_clean}" {comp_filter}'.strip()
            results.append(BooleanDorkResult(
                title="Public Google Docs Job Descriptions",
                query=q3,
                explanation="Finds shared Google Docs job specs often circulated internally by startup founders and hiring managers.",
                search_url=f"https://www.google.com/search?q={urllib.parse.quote(q3)}",
                category="unindexed_jds",
            ))

        # 2. Hiring Manager & Executive Direct Inboxes
        if intent in ("all", "hiring_managers"):
            q4 = f'site:linkedin.com/in ("hiring" OR "we\'re hiring") ("Engineering Manager" OR "Director of Engineering" OR "VP of Engineering") {comp_filter}'.strip()
            results.append(BooleanDorkResult(
                title="Hiring Managers & Engineering Directors on LinkedIn",
                query=q4,
                explanation="Extracts decision-makers whose current headline explicitly states they are hiring for their engineering teams.",
                search_url=f"https://www.google.com/search?q={urllib.parse.quote(q4)}",
                category="hiring_managers",
            ))

            q5 = f'site:x.com OR site:twitter.com "hiring" "{role_clean}" {comp_filter} "@"'.strip()
            results.append(BooleanDorkResult(
                title="X / Twitter Hiring Announcements with Direct Handles",
                query=q5,
                explanation="Finds fast-moving tweets by engineers and founders asking candidates to DM them directly for open roles.",
                search_url=f"https://www.google.com/search?q={urllib.parse.quote(q5)}",
                category="hiring_managers",
            ))

        # 3. Leaked Salary & Compensation Spreadsheets
        if intent in ("all", "salary_sheets"):
            q6 = f'site:docs.google.com/spreadsheets "compensation" OR "salary" OR "equity" {comp_filter}'.strip()
            results.append(BooleanDorkResult(
                title="Crowdsourced Google Sheets Compensation & Levels Data",
                query=q6,
                explanation="Discovers public community spreadsheets tracking salary, equity vesting, and leveling transparency.",
                search_url=f"https://www.google.com/search?q={urllib.parse.quote(q6)}",
                category="salary_sheets",
            ))

        # 4. Hidden Candidate Take-Home Challenges & Repos
        if intent in ("all", "hidden_repos"):
            q7 = f'site:github.com {comp_filter} ("take-home" OR "interview-challenge" OR "coding-assignment" OR "assessment")'.strip()
            results.append(BooleanDorkResult(
                title="GitHub Leaked Take-Home Challenges & Solutions",
                query=q7,
                explanation="Searches public GitHub repositories containing actual candidate submissions for the company's take-home rounds.",
                search_url=f"https://www.google.com/search?q={urllib.parse.quote(q7)}",
                category="hidden_repos",
            ))

        # 5. Engineering Blog Architecture & Outage Debriefs
        if intent in ("all", "engineering_blogs"):
            q8 = f'site:medium.com OR site:substack.com {comp_filter} ("architecture" OR "how we scaled" OR "postmortem" OR "infrastructure")'.strip()
            results.append(BooleanDorkResult(
                title="Engineering Architecture & Scaling Retrospectives",
                query=q8,
                explanation="Finds deep-dive articles authored by company engineers explaining database scaling, event queues, and outages.",
                search_url=f"https://www.google.com/search?q={urllib.parse.quote(q8)}",
                category="engineering_blogs",
            ))

        return results

    async def answer_chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        company: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes an intelligent, actionable response with contextual Boolean Dorks.
        """
        # Auto-detect role or company mentions if not passed explicitly
        detected_role = role or "Software Engineer"
        detected_company = company or ""

        # Extract company from message if present e.g. "for Stripe" or "at OpenAI"
        comp_match = re.search(r'\b(?:at|for|about|with)\s+([A-Z][a-zA-Z0-9_\-\.]+)', message)
        if comp_match and not detected_company:
            detected_company = comp_match.group(1)

        # Generate targeted Boolean Dorks matching the user's intent
        lower_msg = message.lower()
        if "salary" in lower_msg or "comp" in lower_msg or "pay" in lower_msg or "sheet" in lower_msg:
            intent = "salary_sheets"
        elif "manager" in lower_msg or "email" in lower_msg or "who is hiring" in lower_msg or "lead" in lower_msg:
            intent = "hiring_managers"
        elif "repo" in lower_msg or "take home" in lower_msg or "github" in lower_msg or "assignment" in lower_msg:
            intent = "hidden_repos"
        elif "blog" in lower_msg or "postmortem" in lower_msg or "architecture" in lower_msg:
            intent = "engineering_blogs"
        else:
            intent = "all"

        dorks = self.generate_dorks(role=detected_role, company=detected_company, intent=intent)

        # Generate AI-powered conversational explanation
        prompt = (
            f"You are the JobFinder OSINT & Career Intelligence Copilot. The user is asking:\n\n"
            f"\"{message}\"\n\n"
            f"Target Context: Role='{detected_role}', Company='{detected_company or 'General Tech'}'.\n"
            f"Generated Google Boolean Dorks: {len(dorks)} queries available.\n\n"
            f"Provide a concise, expert answer detailing the exact search strategy, which search operators are used, "
            f"and tactical advice for reaching decision-makers or discovering unlisted openings."
        )

        try:
            ai_reply = await self.ai.generate_text(prompt, max_tokens=350)
        except Exception:
            ai_reply = ""


        if not ai_reply or len(ai_reply.strip()) < 20:
            target_str = f" for **{detected_company}**" if detected_company else ""
            ai_reply = (
                f"Here are the targeted OSINT Google Boolean Dorks{target_str} tailored to find hidden opportunities, "
                f"unindexed job specs, and decision-maker contact points. Click any query below to launch directly in Google, "
                f"or copy the search string into your custom sourcing pipeline."
            )

        followups = [
            f"Find unindexed Notion job descriptions for {detected_company or 'Startups'}",
            f"Generate LinkedIn Boolean Dork for Engineering Managers hiring {detected_role}",
            f"Discover public compensation spreadsheets and levels for {detected_company or 'FAANG/Tier-1'}",
            f"Search GitHub for take-home challenges and interview assignments",
        ]

        return {
            "reply": ai_reply,
            "dorks": dorks,
            "suggested_followups": followups[:3],
        }


osint_boolean_engine = OSINTBooleanEngine()
