"""
intent_analyzer.py — Natural Language Intent Parser for The Godfather Bot.
Infers user intent from free-form chat messages and maps them to sovereign agent commands.
"""
from __future__ import annotations

import re
from typing import List, Tuple


class GodfatherIntentAnalyzer:
    """Parses natural language phrases to extract intent and arguments."""

    @staticmethod
    def _extract_company(text: str, default: str = "Target Corp") -> str:
        stopwords = {"the", "an", "a", "my", "our", "me", "his", "her", "staff", "senior", "lpa", "usd", "inr", "days", "day", "onsite"}
        matches = re.findall(r"(?:at|for|with|from|to)\s+([a-zA-Z][a-zA-Z0-9_\-\.]*)", text, re.IGNORECASE)
        for m in matches:
            if m.lower() not in stopwords and not m.isdigit():
                return m
        return default

    def parse_intent(self, text: str) -> Tuple[str, List[str]]:
        """
        Returns (command, args) tuple.
        If already starts with '/', returns the command and split args.
        """
        text_clean = text.strip()
        if not text_clean:
            return ("/menu", [])

        if text_clean.startswith("/"):
            parts = text_clean.split()
            cmd = parts[0]
            args = parts[1:]
            return (cmd, args)

        lower = text_clean.lower()

        # 1. Autopilot / Status check
        if any(k in lower for k in ["autopilot", "auto pilot", "auto-pilot", "status", "daemon"]):
            if "off" in lower or "stop" in lower or "disable" in lower:
                return ("/autopilot", ["off"])
            return ("/autopilot", ["on"])

        # 2. Executive Decision Memo / ROI Justification (Higher priority than general numbers)
        if any(k in lower for k in ["memo", "roi", "justification", "justif", "business case", "cost of vacancy", "debrief"]):
            company = self._extract_company(text_clean, default="Unicorn Inc")
            numbers = re.findall(r"\b\d+\b", lower)
            target = numbers[0] if numbers else "50"
            return ("/memo", [company, target])

        # 3. Counter / Offer / Negotiation
        if any(k in lower for k in ["counter", "negotiat", "salary offer", "base offer", "npv", "competing offer", "arbitrage"]):
            numbers = re.findall(r"\b\d+(?:\.\d+)?\b", lower)
            company = self._extract_company(text_clean, default="Target Corp")
            if len(numbers) >= 2:
                return ("/counter", [numbers[0], numbers[1], company])
            elif len(numbers) == 1:
                return ("/counter", [numbers[0], str(float(numbers[0]) * 0.8), company])
            return ("/counter", ["45", "35", company])

        # 4. System Design Whiteboard
        if any(k in lower for k in ["whiteboard", "system design", "architecture", "capacity math", "mermaid", "scale", "latency"]):
            if "trade" in lower or "trading" in lower or "exchange" in lower or "orderbook" in lower:
                return ("/whiteboard", ["trading"])
            elif "ride" in lower or "uber" in lower or "dispatch" in lower or "geo" in lower:
                return ("/whiteboard", ["ridehailing"])
            elif "video" in lower or "stream" in lower or "netflix" in lower or "youtube" in lower:
                return ("/whiteboard", ["video"])
            elif "rate" in lower or "limit" in lower or "throttle" in lower or "token" in lower:
                return ("/whiteboard", ["ratelimiter"])
            return ("/whiteboard", ["trading"])

        # 5. Proof of Work Fabricator
        if any(k in lower for k in ["fabricat", "proof of work", "pow", "repo", "demo project", "artifact", "prototype"]):
            company = self._extract_company(text_clean, default="Stripe")
            return ("/fabricate", [company, "Senior Distributed Systems Engineer"])

        # 6. Anti-Ghosting Escalation
        if any(k in lower for k in ["ghost", "escalat", "no reply", "no response", "follow up", "recruiter", "sla"]):
            company = self._extract_company(text_clean, default="Tech Corp")
            days_match = re.search(r"\b(\d+)\s*(?:days|d)\b", lower)
            days = days_match.group(1) if days_match else "5"
            return ("/escalate", [company, "onsite", days])

        # 7. Frontier AI Radar
        if any(k in lower for k in ["frontier", "rlhf", "outlier", "scale ai", "mercor", "alignerr", "usd gig", "$/hr", "dollar gig"]):
            return ("/frontier", [])

        # 8. Web3 Bounties & Grants
        if any(k in lower for k in ["bounty", "bounties", "web3", "solana", "ethereum", "base", "gitcoin", "grant", "crypto"]):
            return ("/bounty", [])

        # 9. Geo-Arbitrage / Relocation Math
        if any(k in lower for k in ["geo", "relocat", "tokyo", "singapore", "amsterdam", "berlin", "london", "dubai", "japan", "europe", "visa"]):
            for city in ["tokyo", "singapore", "amsterdam", "berlin", "london", "dubai"]:
                if city in lower:
                    return ("/geo", [city])
            if "japan" in lower:
                return ("/geo", ["tokyo"])
            if "germany" in lower:
                return ("/geo", ["berlin"])
            if "netherlands" in lower:
                return ("/geo", ["amsterdam"])
            if "uk" in lower:
                return ("/geo", ["london"])
            return ("/geo", ["tokyo"])

        # 10. Executive Bypass / Outreach Pitch
        if any(k in lower for k in ["pitch", "outreach", "vp", "cto", "engineering leader", "bypass", "drip"]):
            company = self._extract_company(text_clean, default="Databricks")
            return ("/pitch", [company, "Alex Chen"])

        # 11. Distributed Sandbox Simulation
        if any(k in lower for k in ["simulat", "chaos", "lru", "cache", "raft", "consensus", "token bucket"]):
            if "raft" in lower or "consensus" in lower:
                return ("/simulate", ["raft"])
            elif "token" in lower or "bucket" in lower or "rate" in lower:
                return ("/simulate", ["tokenbucket"])
            return ("/simulate", ["cache"])

        # 12. Interviewer Profiler / Interview Prep
        if any(k in lower for k in ["interview", "profil", "interviewer", "hiring manager", "evaluat", "questions"]):
            company = self._extract_company(text_clean, default="Google")
            return ("/profile", [company, "Staff Engineering Lead"])

        # Default: Show Godfather Menu
        return ("/menu", [])
