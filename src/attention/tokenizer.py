from __future__ import annotations

import re
import yaml
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional

from .models import QueryToken, KeyToken, ValuePayload

TECH_KEYWORDS = {
    "python", "fastapi", "django", "react", "typescript", "javascript", "node", "nodejs",
    "postgresql", "postgres", "redis", "docker", "kubernetes", "k8s", "aws", "gcp",
    "graphql", "rest", "grpc", "microservices", "sql", "nosql", "mongodb", "kafka",
    "celery", "rabbitmq", "ci/cd", "git", "linux", "html", "css", "tailwind", "next.js"
}

SCALE_KEYWORDS = {
    "scale", "latency", "throughput", "concurrency", "distributed", "performance",
    "optimization", "caching", "load", "high availability", "sharding", "replica",
    "p99", "p95", "million", "billion", "qps", "async", "event-driven", "fault-tolerant"
}

IMPACT_KEYWORDS = {
    "revenue", "growth", "users", "conversion", "cost", "delivered", "shipped",
    "launched", "increased", "reduced", "automated", "improved", "optimized", "kpi",
    "retention", "efficiency", "milestone", "roi", "savings", "scale"
}

SENIORITY_KEYWORDS = {
    "lead", "senior", "staff", "principal", "architect", "mentor", "mentored",
    "ownership", "autonomous", "design", "rfc", "strategy", "roadmap", "hiring",
    "cross-functional", "stakeholder", "code review", "best practices", "leadership"
}


class SemanticClauseTokenizer:
    """
    Tokenizes Job Descriptions into Queries (Q_i) and Candidate Profiles into Keys (K_j) and Values (V_j).
    """

    def __init__(self, profile_path: Optional[str] = None):
        self.profile_path = profile_path or "config/profile.yml"

    def classify_category(self, text: str) -> str:
        """Classifies a clause into one of the 4 attention head dimensions."""
        low = text.lower()
        scores = {
            "tech": sum(1 for k in TECH_KEYWORDS if re.search(rf"\b{re.escape(k)}\b", low)),
            "scale": sum(1 for k in SCALE_KEYWORDS if re.search(rf"\b{re.escape(k)}\b", low)),
            "impact": sum(1 for k in IMPACT_KEYWORDS if re.search(rf"\b{re.escape(k)}\b", low)),
            "seniority": sum(1 for k in SENIORITY_KEYWORDS if re.search(rf"\b{re.escape(k)}\b", low)),
        }
        best_cat = max(scores, key=scores.get)
        return best_cat if scores[best_cat] > 0 else "tech"

    def tokenize_job_description(self, jd_text: str, max_queries: int = 12) -> List[QueryToken]:
        """Splits job description into discrete semantic requirement clauses (Q_i)."""
        if not jd_text or not jd_text.strip():
            # Default fallback queries
            jd_text = (
                "Develop high-performance async microservices with Python and FastAPI.\n"
                "Build scalable distributed systems with low latency and high availability.\n"
                "Collaborate with cross-functional teams to design architecture and mentor engineers.\n"
                "Optimize PostgreSQL database queries and manage Redis caching."
            )

        # Split on bullet points, newlines, and sentence delimiters
        raw_lines = re.split(r"[\n\r•\-\*]+|(?<=[.!?])\s+(?=[A-Z])", jd_text)
        cleaned = [re.sub(r"^\W+", "", l).strip() for l in raw_lines if len(l.strip()) >= 15]

        # Deduplicate while preserving order
        unique_clauses: List[str] = []
        seen = set()
        for c in cleaned:
            c_low = c.lower()
            if c_low not in seen and not any(ign in c_low for ign in ("about us", "equal opportunity", "benefits", "apply now")):
                seen.add(c_low)
                unique_clauses.append(c)

        if not unique_clauses:
            unique_clauses = [jd_text.strip()]

        query_tokens: List[QueryToken] = []
        for idx, clause in enumerate(unique_clauses[:max_queries]):
            cat = self.classify_category(clause)
            # Assign weight: requirements containing 'must', 'required', 'years' get higher weight
            w = 1.3 if any(req in clause.lower() for req in ("must", "required", "years", "proven", "strong")) else 1.0
            query_tokens.append(QueryToken(
                id=f"q_{idx}",
                text=clause,
                category=cat,
                weight=w,
            ))

        return query_tokens

    def extract_keys_and_values(
        self,
        custom_bullets: Optional[List[str]] = None,
    ) -> Tuple[List[KeyToken], List[ValuePayload]]:
        """Extracts Key tokens (K_j) and Value payloads (V_j) from candidate profile/resume."""
        bullets: List[str] = []

        if custom_bullets:
            bullets = custom_bullets
        else:
            # Load from profile.yml if available
            p_file = Path(self.profile_path)
            if p_file.exists():
                try:
                    with open(p_file, "r") as f:
                        data = yaml.safe_load(f)
                    pos = data.get("positioning", {})
                    bullets.extend(pos.get("differentiators", []))
                    bullets.extend(pos.get("lead_with", []))
                except Exception:
                    pass

        if not bullets:
            # Canonical candidate experience bullets for Kushall Jain
            bullets = [
                "Architected and deployed high-throughput async microservices using Python, FastAPI, and PostgreSQL with <50ms p99 latency.",
                "Built DevFrnds: full-stack developer collaboration platform with real-time WebSockets, Redis pub/sub, and React/TypeScript frontend.",
                "Engineered robust distributed workflows, background task queues with Celery/Redis, and high-concurrency API gateways.",
                "Led database schema design, index optimization, and complex query tuning in PostgreSQL, reducing query latency by 45%.",
                "Spearheaded end-to-end full-stack feature development with React.js, TypeScript, Next.js, and automated CI/CD deployment pipelines.",
                "Authored comprehensive technical architecture RFCs, led sprint planning, and conducted rigorous peer code reviews.",
                "Collaborated with ByteDance engineers on frontend performance profiling and optimized web vitals to sub-second load times.",
                "Implemented secure authentication architectures including OAuth 2.0 PKCE, JWT stateless sessions, and role-based access control.",
            ]

        key_tokens: List[KeyToken] = []
        value_payloads: List[ValuePayload] = []

        for idx, b in enumerate(bullets):
            k_id = f"k_{idx}"
            v_id = f"v_{idx}"
            cat = self.classify_category(b)

            # Extract metric if present
            metric_match = re.search(r"(\d+%\s*|\d+x\s*|<\s*\d+ms\s*|\d+k\+?\s*|\d+M\+?\s*|\$\d+[kKmM]?|sub-second)", b)
            metric = metric_match.group(0).strip() if metric_match else None

            # Create headline key
            first_clause = b.split(":")[0] if ":" in b else b.split(",")[0]
            if len(first_clause) > 60:
                first_clause = first_clause[:57] + "..."

            key_tokens.append(KeyToken(
                id=k_id,
                text=first_clause.strip(),
                category=cat,
                source="profile",
            ))

            value_payloads.append(ValuePayload(
                id=v_id,
                proof_point=b.strip(),
                context="Production Experience",
                impact_metric=metric,
            ))

        return key_tokens, value_payloads


clause_tokenizer = SemanticClauseTokenizer()
