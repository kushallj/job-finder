"""
jd_analyzer.py — LLM-powered Job Description analyzer.

Extracts structured intelligence from a raw JD text.

Output (JDAnalysis):
  required_skills   — must-have (in Requirements/Qualifications section)
  nice_to_have      — preferred (in "bonus", "plus if you have" sections)
  tech_stack        — specific technologies/versions mentioned
  pain_points       — what problem is this role solving?
  culture_keywords  — "fast-paced", "ownership", "autonomous", "collaborative"
  exact_phrases     — literal phrases to mirror in the resume
  seniority_level   — junior / mid / senior / lead / staff / principal
  role_focus        — backend / frontend / fullstack / data / devops / ml
  tone              — startup_casual / enterprise_formal / technical
  company_name      — extracted company name

Why exact_phrases matters:
  ATS systems often do exact string matching. If the JD says
  "REST API development" and the resume says "RESTful API design",
  some ATS systems won't match them. We extract the exact phrases
  so SectionOptimizer can mirror the JD's language precisely.

LLM prompt design:
  - Constrained JSON output (no free-form prose)
  - Single prompt for all fields (efficient, one LLM call)
  - Fallback: regex-based extraction when LLM is unavailable
  - Validates output schema before returning

Tier 1: LLM (Ollama local → Gemini)
Tier 2: Regex heuristics (always works, lower quality)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class JDAnalysis:
    """Structured analysis of a job description."""
    required_skills:   List[str]   = field(default_factory=list)
    nice_to_have:      List[str]   = field(default_factory=list)
    tech_stack:        List[str]   = field(default_factory=list)
    pain_points:       List[str]   = field(default_factory=list)   # problems this role solves
    culture_keywords:  List[str]   = field(default_factory=list)   # e.g. "ownership", "fast-paced"
    exact_phrases:     List[str]   = field(default_factory=list)   # mirror these verbatim
    seniority_level:   str         = "mid"                         # junior/mid/senior/lead/staff
    role_focus:        str         = "backend"                     # backend/frontend/fullstack/data/devops/ml
    tone:              str         = "technical"                   # startup_casual/enterprise_formal/technical
    company_name:      str         = ""
    jd_word_count:     int         = 0
    keywords_frequency: dict       = field(default_factory=dict)   # word → count

    @property
    def all_keywords(self) -> List[str]:
        """Combined deduped keyword list for ATS optimization."""
        seen = set()
        out  = []
        for kw in self.required_skills + self.tech_stack + self.nice_to_have:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                out.append(kw)
        return out

    @property
    def critical_keywords(self) -> List[str]:
        """High-frequency + required skills — must appear in resume."""
        freq_threshold = max(2, self.jd_word_count // 200)
        freq_keywords  = [k for k, v in self.keywords_frequency.items() if v >= freq_threshold]
        return list(dict.fromkeys(self.required_skills + freq_keywords))


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

_LLM_PROMPT = """Analyze this job description and return a JSON object with exactly these fields.
Be precise and concise. Return ONLY valid JSON, no markdown, no explanation.

Job Description:
---
{jd}
---

Return JSON:
{{
  "required_skills": ["skill1", "skill2"],
  "nice_to_have": ["skill1"],
  "tech_stack": ["Python", "PostgreSQL"],
  "pain_points": ["scaling microservices", "improving API reliability"],
  "culture_keywords": ["ownership", "fast-paced"],
  "exact_phrases": ["REST API", "distributed systems", "production experience"],
  "seniority_level": "senior",
  "role_focus": "backend",
  "tone": "technical",
  "company_name": "CompanyName"
}}

Rules:
- required_skills: only truly mandatory skills from Requirements/Qualifications
- nice_to_have: from "preferred", "bonus", "plus" sections
- tech_stack: exact technology names as written in the JD
- exact_phrases: 5-10 multi-word phrases from JD to use verbatim in resume
- seniority_level: one of [junior, mid, senior, lead, staff, principal]
- role_focus: one of [backend, frontend, fullstack, data, devops, ml, mobile]
- tone: one of [startup_casual, enterprise_formal, technical]"""


class JDAnalyzer:
    """
    Analyzes a job description and returns structured JDAnalysis.

    Usage:
        analyzer = JDAnalyzer()
        analysis = await analyzer.analyze(jd_text)
        print(analysis.required_skills)
        print(analysis.exact_phrases)
    """

    def __init__(self, ai_service=None):
        self._ai = ai_service
        if ai_service is None:
            try:
                from src.ai.unified_ai_service import UnifiedAIService
                self._ai = UnifiedAIService()
            except Exception as e:
                log.warning("AI service unavailable for JD analysis: %s", e)

    async def analyze(self, jd_text: str) -> JDAnalysis:
        """
        Analyze `jd_text` and return structured JDAnalysis.
        Falls back to regex if LLM is unavailable.
        """
        if not jd_text or not jd_text.strip():
            return JDAnalysis()

        # Tier 1: LLM
        if self._ai:
            try:
                result = await self._llm_analyze(jd_text)
                if result:
                    result.jd_word_count      = len(jd_text.split())
                    result.keywords_frequency = self._count_keywords(jd_text)
                    return result
            except Exception as e:
                log.warning("LLM JD analysis failed, falling back to regex: %s", e)

        # Tier 2: Regex heuristics
        result = self._regex_analyze(jd_text)
        result.jd_word_count      = len(jd_text.split())
        result.keywords_frequency = self._count_keywords(jd_text)
        return result

    # ── LLM analysis ─────────────────────────────────────────────────────────

    async def _llm_analyze(self, jd_text: str) -> Optional[JDAnalysis]:
        """Send prompt to LLM, parse JSON response."""
        # Truncate to 3000 chars to stay within context window
        snippet = jd_text[:3000]
        prompt  = _LLM_PROMPT.format(jd=snippet)

        raw = ""
        try:
            # Try direct generation methods across different AI backends
            if hasattr(self._ai, "backend") and self._ai.backend:
                backend = self._ai.backend
                if hasattr(backend, "generate"):
                    raw = await backend.generate(prompt)
                elif hasattr(backend, "_generate_with_ollama"):
                    raw = await backend._generate_with_ollama(prompt)
                elif hasattr(backend, "chat"):
                    raw = await backend.chat(prompt)
        except Exception as e:
            log.debug("LLM generation error: %s", e)
            return None

        if not raw:
            return None

        # Extract JSON from response (LLMs sometimes add prose around it)
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if not json_match:
            return None

        try:
            data = json.loads(json_match.group(0))
            return JDAnalysis(
                required_skills  = data.get("required_skills", []),
                nice_to_have     = data.get("nice_to_have", []),
                tech_stack       = data.get("tech_stack", []),
                pain_points      = data.get("pain_points", []),
                culture_keywords = data.get("culture_keywords", []),
                exact_phrases    = data.get("exact_phrases", []),
                seniority_level  = data.get("seniority_level", "mid"),
                role_focus       = data.get("role_focus", "backend"),
                tone             = data.get("tone", "technical"),
                company_name     = data.get("company_name", ""),
            )
        except (json.JSONDecodeError, KeyError) as e:
            log.debug("Failed to parse LLM JSON response: %s | raw=%s", e, raw[:200])
            return None

    # ── Regex heuristics ─────────────────────────────────────────────────────

    def _regex_analyze(self, jd_text: str) -> JDAnalysis:
        """
        Regex-based JD analysis — works without LLM.
        Lower quality than LLM but always available.
        """
        text_lower = jd_text.lower()

        required, preferred = self._split_required_preferred(jd_text)
        tech_stack          = self._extract_tech_terms(jd_text)
        culture             = self._extract_culture_keywords(text_lower)
        exact_phrases       = self._extract_exact_phrases(jd_text)
        seniority           = self._detect_seniority(text_lower)
        role_focus          = self._detect_role_focus(text_lower)
        tone                = self._detect_tone(text_lower)
        company             = self._extract_company_name(jd_text)
        pain_points         = self._extract_pain_points(jd_text)

        return JDAnalysis(
            required_skills  = required,
            nice_to_have     = preferred,
            tech_stack       = tech_stack,
            pain_points      = pain_points,
            culture_keywords = culture,
            exact_phrases    = exact_phrases,
            seniority_level  = seniority,
            role_focus       = role_focus,
            tone             = tone,
            company_name     = company,
        )

    # ── Section splitting ─────────────────────────────────────────────────────

    @staticmethod
    def _split_required_preferred(text: str) -> tuple[List[str], List[str]]:
        """
        Heuristically separate required vs preferred skills.
        Required: found in "Requirements", "Qualifications", "Must have"
        Preferred: found in "Preferred", "Bonus", "Nice to have", "Plus"
        """
        required_section_re  = re.compile(
            r"(requirements?|qualifications?|must.have|required|you have|you.ll bring)[:\s]*(.*?)(?=\n[A-Z]|\n\n|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        preferred_section_re = re.compile(
            r"(preferred|bonus|nice.to.have|plus if|great if|ideally)[:\s]*(.*?)(?=\n[A-Z]|\n\n|\Z)",
            re.IGNORECASE | re.DOTALL,
        )

        def extract_bullets(section_text: str) -> List[str]:
            items = re.findall(r"[•\-·✓*]\s*(.+?)(?:\n|$)", section_text)
            if not items:
                items = re.split(r"[,;]", section_text)
            return [i.strip() for i in items if 3 < len(i.strip()) < 120]

        required  = []
        preferred = []

        for m in required_section_re.finditer(text):
            required.extend(extract_bullets(m.group(2)))

        for m in preferred_section_re.finditer(text):
            preferred.extend(extract_bullets(m.group(2)))

        # Dedup
        return list(dict.fromkeys(required)), list(dict.fromkeys(preferred))

    @staticmethod
    def _extract_tech_terms(text: str) -> List[str]:
        """Extract technology names mentioned in the JD."""
        pattern = re.compile(
            r"\b("
            r"Python|FastAPI|Django|Flask|Node\.?js|Express|React|TypeScript|JavaScript"
            r"|Vue\.?js|Angular|Next\.?js|Svelte|HTML|CSS|GraphQL|REST|gRPC"
            r"|PostgreSQL|MySQL|MongoDB|Redis|Cassandra|DynamoDB|ElasticSearch"
            r"|AWS|GCP|Azure|Docker|Kubernetes|Terraform|Ansible|Helm"
            r"|Kafka|RabbitMQ|Celery|Airflow|Spark|Flink"
            r"|Git|Linux|CI/CD|GitHub Actions|Jenkins|CircleCI"
            r"|Pandas|NumPy|scikit.?learn|TensorFlow|PyTorch|Hugging.?Face"
            r"|LangChain|LangGraph|OpenAI|Gemini|Ollama|LLM"
            r"|C#|\.NET|Java|Go|Golang|Rust|Ruby on Rails|PHP|Scala|Kotlin"
            r"|microservices|distributed systems?|event.driven|serverless"
            r")\b",
            re.IGNORECASE,
        )
        found = [m.group(0) for m in pattern.finditer(text)]
        return list(dict.fromkeys(found))  # dedup, preserve order

    @staticmethod
    def _extract_culture_keywords(text_lower: str) -> List[str]:
        culture_terms = [
            "ownership", "fast-paced", "fast paced", "autonomous", "collaborative",
            "impact", "scale", "growth", "agile", "startup", "innovative",
            "data-driven", "cross-functional", "proactive", "self-starter",
            "high-performance", "mission-driven", "pragmatic",
        ]
        return [t for t in culture_terms if t in text_lower]

    @staticmethod
    def _extract_exact_phrases(text: str) -> List[str]:
        """
        Extract 2-4 word technical phrases that appear in the JD.
        These should be mirrored verbatim in the resume for ATS matching.
        """
        phrase_re = re.compile(
            r"\b("
            r"(?:REST|RESTful|REST API|REST APIs?)"
            r"|(?:distributed systems?)"
            r"|(?:microservices? architecture)"
            r"|(?:cloud.native)"
            r"|(?:production.grade|production experience)"
            r"|(?:high.availability|high availability)"
            r"|(?:fault.tolerant)"
            r"|(?:event.driven architecture)"
            r"|(?:CI/?CD pipelines?)"
            r"|(?:infrastructure as code)"
            r"|(?:test.driven development|TDD)"
            r"|(?:domain.driven design|DDD)"
            r"|(?:system design)"
            r"|(?:data pipeline)"
            r"|(?:machine learning|ML pipeline)"
            r"|(?:large language model|LLM)"
            r"|(?:backend engineering)"
            r"|(?:full.?stack development)"
            r"|(?:API design|API development)"
            r"|(?:database optimization|query optimization)"
            r")\b",
            re.IGNORECASE,
        )
        found = [m.group(0) for m in phrase_re.finditer(text)]
        return list(dict.fromkeys(found))

    @staticmethod
    def _detect_seniority(text_lower: str) -> str:
        if any(k in text_lower for k in ["staff engineer", "principal", "distinguished"]):
            return "staff"
        if any(k in text_lower for k in ["tech lead", "lead engineer", "engineering lead"]):
            return "lead"
        if any(k in text_lower for k in ["senior", "sr.", "sr ", "5+ years", "6+ years", "7+ years"]):
            return "senior"
        if any(k in text_lower for k in ["junior", "jr.", "entry level", "0-2 years", "1+ year"]):
            return "junior"
        return "mid"

    @staticmethod
    def _detect_role_focus(text_lower: str) -> str:
        if any(k in text_lower for k in ["machine learning", "ml engineer", "data scientist", "nlp", "llm"]):
            return "ml"
        if any(k in text_lower for k in ["devops", "sre", "infrastructure", "platform engineer", "kubernetes"]):
            return "devops"
        if any(k in text_lower for k in ["data engineer", "data pipeline", "etl", "spark", "airflow"]):
            return "data"
        if any(k in text_lower for k in ["frontend", "react", "vue", "angular", "ui/ux"]):
            return "frontend"
        if any(k in text_lower for k in ["full stack", "fullstack", "full-stack"]):
            return "fullstack"
        return "backend"

    @staticmethod
    def _detect_tone(text_lower: str) -> str:
        if any(k in text_lower for k in ["startup", "fast-paced", "we move fast", "move quickly"]):
            return "startup_casual"
        if any(k in text_lower for k in ["enterprise", "fortune 500", "corporate", "compliance"]):
            return "enterprise_formal"
        return "technical"

    @staticmethod
    def _extract_company_name(text: str) -> str:
        m = re.search(r"(?:at|join|about)\s+([A-Z][a-zA-Z\s]{2,30}?)(?:\s+is|\s+we|\s*[,\.\n])", text)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _extract_pain_points(text: str) -> List[str]:
        """Extract what problems the role is expected to solve."""
        patterns = [
            r"you.?ll\s+(?:be\s+responsible\s+for|help\s+(?:us\s+)?(?:build|scale|improve)|own)\s+(.+?)(?:\.|,|\n)",
            r"(?:build|scale|improve|design|architect|own)\s+(.+?)\s+(?:at scale|for|to|that|which)",
        ]
        found = []
        for p in patterns:
            for m in re.finditer(p, text, re.IGNORECASE):
                snippet = m.group(1).strip()[:100]
                if len(snippet) > 10:
                    found.append(snippet)
        return list(dict.fromkeys(found))[:5]

    @staticmethod
    def _count_keywords(text: str) -> dict:
        """Count frequency of each significant word in JD."""
        words = re.findall(r"\b[a-zA-Z][a-zA-Z\-\.]{3,}\b", text.lower())
        stop  = {"that", "this", "with", "from", "have", "will", "your", "their",
                 "they", "able", "well", "also", "team", "work", "role", "join",
                 "what", "into", "more", "some", "such", "than", "when", "were",
                 "been", "both", "about", "would", "which", "other", "these"}
        freq: dict = {}
        for w in words:
            if w not in stop:
                freq[w] = freq.get(w, 0) + 1
        return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True)[:50])
