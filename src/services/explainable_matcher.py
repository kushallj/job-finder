"""
src/services/explainable_matcher.py
Explainable Match Scoring Engine.
Computes matched skills, missing skills, match score (0-100), and 3-bullet validation reasons
based on an expansive modern engineering taxonomy (LLMs, MCP, RAG, Web, Cloud, Infra).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple, Any

# Canonical skill taxonomy with normalized representations and aliases
TECH_TAXONOMY: Dict[str, List[str]] = {
    # ── AI, LLMs & Modern Autonomous Agents ──
    "LLM Integration": ["llm", "large language model", "llms", "gpt-4", "gpt-4o", "claude", "gemini", "openai api", "llm integration"],
    "Model Context Protocol (MCP)": ["mcp", "model context protocol", "modelcontextprotocol"],
    "Retrieval-Augmented Generation (RAG)": ["rag", "retrieval augmented generation", "retrieval-augmented generation", "semantic search"],
    "Vector Databases": ["vector database", "vector db", "pinecone", "weaviate", "qdrant", "chromadb", "chroma", "milvus", "pgvector"],
    "AI Agents": ["ai agent", "ai agents", "autonomous agents", "multi-agent", "agentic", "crewai", "autogen"],
    "LangChain": ["langchain", "langgraph"],
    "LlamaIndex": ["llamaindex", "llama-index"],
    "PyTorch": ["pytorch", "torch"],
    "TensorFlow": ["tensorflow", "keras"],
    "Hugging Face": ["huggingface", "hugging face", "transformers", "diffusers"],
    "Prompt Engineering": ["prompt engineering", "few-shot", "chain-of-thought", "prompting"],
    "Fine-Tuning": ["fine-tuning", "fine tuning", "lora", "qlora", "peft", "sft"],
    "Embeddings": ["embeddings", "text-embedding", "sentence-transformers"],

    # ── Modern Frontend & Mobile ──
    "React": ["react", "react.js", "reactjs"],
    "TypeScript": ["typescript", "ts"],
    "Next.js": ["next.js", "nextjs", "next"],
    "Vite": ["vite", "vitejs"],
    "Tailwind CSS": ["tailwind", "tailwindcss"],
    "Vue.js": ["vue", "vue.js", "vuejs"],
    "Redux": ["redux", "redux toolkit", "rtk"],
    "Zustand": ["zustand"],
    "HTML5": ["html", "html5"],
    "CSS3": ["css", "css3", "sass", "scss"],
    "Figma": ["figma", "ui/ux", "ui design", "ux design"],
    "GraphQL": ["graphql", "apollo"],

    # ── Backend & Systems & Languages ──
    "Python": ["python", "python3"],
    "FastAPI": ["fastapi"],
    "Django": ["django", "django rest framework", "drf"],
    "Flask": ["flask"],
    "Go": ["go", "golang"],
    "Rust": ["rust"],
    "Node.js": ["node", "node.js", "nodejs"],
    "Express": ["express", "express.js"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp", ".net", "dotnet", ".net core", "asp.net"],
    "Java": ["java", "spring boot", "spring"],

    # ── Databases & Streaming ──
    "PostgreSQL": ["postgresql", "postgres", "psql"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "Kafka": ["kafka", "apache kafka"],
    "Elasticsearch": ["elasticsearch", "elastic search", "opensearch"],
    "Cassandra": ["cassandra"],

    # ── Cloud, DevOps & Infrastructure ──
    "AWS": ["aws", "amazon web services", "s3", "ec2", "ecs", "lambda"],
    "GCP": ["gcp", "google cloud", "google cloud platform"],
    "Azure": ["azure", "microsoft azure"],
    "Docker": ["docker", "containerization", "containers"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Terraform": ["terraform", "iac"],
    "CI/CD": ["ci/cd", "github actions", "gitlab ci", "jenkins"],
    "Microservices": ["microservices", "microservice"],
    "RESTful APIs": ["rest", "restful", "rest api", "apis"],
    "gRPC": ["grpc", "protobuf"],
    "Distributed Systems": ["distributed systems", "high availability", "concurrency"],
}

class ExplainableMatcherService:
    """Service to compute matched skills, missing skills, and natural-language validation reasons."""

    def __init__(self, candidate_profile: Optional[Dict[str, Any]] = None):
        self.candidate = candidate_profile or {}
        self._candidate_skills_set = {
            skill.lower() for skill in (self.candidate.get("skills") or [])
        }

    def _extract_skills(self, text: str, tags: Optional[List[str]] = None) -> List[str]:
        """Extract canonical skills present in the text or tags."""
        found: List[str] = []
        lowered_text = f" {(text or '').lower()} "
        lowered_tags = {t.lower() for t in (tags or [])}

        for canonical_name, aliases in TECH_TAXONOMY.items():
            # Check tags first
            tag_match = any(alias in lowered_tags or canonical_name.lower() in lowered_tags for alias in aliases)
            if tag_match:
                found.append(canonical_name)
                continue

            # Check text with word boundary matching
            for alias in aliases:
                # Use regex with word boundaries to avoid false positives (e.g., 'go' in 'good')
                pattern = r"(?:\b|_)" + re.escape(alias) + r"(?:\b|_)"
                if re.search(pattern, lowered_text):
                    found.append(canonical_name)
                    break

        return found

    def compute_match(
        self,
        title: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        location: Optional[str] = None,
        work_mode: Optional[str] = None,
        has_remote: Optional[bool] = None,
        experience_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute explainable match details.
        
        Returns:
            {
                "score": int (0-100),
                "matched_skills": List[str],
                "missing_skills": List[str],
                "reasons": List[str] (3 bullets)
            }
        """
        combined_text = f"{title} {description or ''}"
        extracted_job_skills = self._extract_skills(combined_text, tags)

        # Fallback if JD does not mention explicit keywords
        if not extracted_job_skills:
            if "frontend" in title.lower() or "ui" in title.lower():
                extracted_job_skills = ["React", "TypeScript", "HTML5", "CSS3"]
            elif "ai" in title.lower() or "ml" in title.lower():
                extracted_job_skills = ["Python", "LLM Integration", "PyTorch", "RAG"]
            else:
                extracted_job_skills = ["Python", "PostgreSQL", "Docker", "RESTful APIs"]

        if not self.candidate:
            return {
                "score": 0,
                "matched_skills": [],
                "missing_skills": extracted_job_skills,
                "reasons": [
                    "Candidate profile is not configured",
                    "Seniority match is unavailable without candidate experience",
                    "Location preferences are not configured",
                ],
            }

        matched_skills: List[str] = []
        missing_skills: List[str] = []

        for skill in extracted_job_skills:
            if skill.lower() in self._candidate_skills_set or any(alias in self._candidate_skills_set for alias in TECH_TAXONOMY.get(skill, [])):
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)

        # Calculate score (base skill overlap + seniority + location)
        total_skills = len(extracted_job_skills)
        overlap_ratio = len(matched_skills) / max(1, total_skills)

        # Base skill score: up to 70 points
        skill_score = int(overlap_ratio * 70)

        # Seniority match: up to 15 points
        cand_yoe = self.candidate.get("years_of_experience")
        exp_score = 0 if cand_yoe is None else 15
        seniority_reason = (
            "Seniority: Candidate experience not provided"
            if cand_yoe is None else f"Seniority: Matches your {cand_yoe:.0f}+ years experience"
        )

        lowered_title = title.lower()
        lowered_exp = (experience_level or "").lower()

        if cand_yoe is None:
            pass
        elif "lead" in lowered_title or "principal" in lowered_title or "staff" in lowered_title or "lead" in lowered_exp:
            if cand_yoe >= 5:
                seniority_reason = f"Seniority: Well-positioned for Staff/Lead tier with your {cand_yoe:.0f}+ years background"
                exp_score = 15
            else:
                seniority_reason = f"Seniority: High-stretch Staff role; leverages your strong {cand_yoe:.0f}+ years core foundations"
                exp_score = 8
        elif "senior" in lowered_title or "senior" in lowered_exp:
            seniority_reason = f"Seniority: Strong match for your {cand_yoe:.0f}+ years engineering experience"
            exp_score = 15
        elif "entry" in lowered_title or "junior" in lowered_title:
            seniority_reason = f"Seniority: Exceeds entry requirements with your {cand_yoe:.0f}+ years hands-on track record"
            exp_score = 12
        else:
            seniority_reason = f"Seniority: Matches your {cand_yoe:.0f}+ years engineering background"
            exp_score = 15

        # Location / Work mode match: up to 15 points
        loc_score = 0
        location_str = (location or "Remote").strip()
        is_remote = bool(has_remote) or "remote" in (work_mode or "").lower() or "remote" in location_str.lower()
        preferred_modes = {
            mode.lower() for mode in (self.candidate.get("preferred_work_modes") or [])
        }
        target_locations = [
            loc.lower() for loc in (self.candidate.get("target_locations") or [])
        ]

        if is_remote and "remote" in preferred_modes:
            loc_score = 15
            location_reason = "Location: 100% Global Remote match as preferred"
        elif target_locations and any(loc in location_str.lower() for loc in target_locations):
            loc_score = 15
            location_reason = f"Location: Matches a configured preference ({location_str})"
        else:
            location_reason = "Location preferences are not configured"

        raw_score = skill_score + exp_score + loc_score
        # Ensure realistic bounded match score (between 40 and 98)
        final_score = max(45, min(98, raw_score))

        # 3 Natural Language Validation Reasons
        if matched_skills:
            top_matched = ", ".join(matched_skills[:3])
            more_cnt = len(matched_skills) - 3
            if more_cnt > 0:
                skills_reason = f"Matches {len(matched_skills)} of your verified skills including {top_matched} +{more_cnt} more"
            else:
                skills_reason = f"Matches {len(matched_skills)} of your verified skills ({top_matched})"
        else:
            skills_reason = "Strong transferable engineering fundamentals for this tech stack"

        reasons = [
            skills_reason,
            seniority_reason,
            location_reason,
        ]

        return {
            "score": final_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "reasons": reasons,
        }


# Singleton instance for quick reuse
_matcher_singleton: Optional[ExplainableMatcherService] = None

def get_explainable_matcher(candidate_profile: Optional[Dict[str, Any]] = None) -> ExplainableMatcherService:
    global _matcher_singleton
    if candidate_profile is not None:
        return ExplainableMatcherService(candidate_profile)
    if _matcher_singleton is None:
        _matcher_singleton = ExplainableMatcherService()
    return _matcher_singleton
