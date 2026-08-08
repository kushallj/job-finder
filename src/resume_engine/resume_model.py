"""
resume_model.py — Structured resume data model.

Why a structured model instead of raw text?
  Raw text → LLM = one monolithic rewrite (poor control, inconsistent output)
  Structured model → per-section LLM rewrites = surgical precision

  Each bullet is independently addressable:
    - We can rewrite bullet #3 to inject "distributed systems" without
      touching the other bullets
    - We can track exactly which bullets changed (diff)
    - We can score each section independently vs the JD

Design:
  ResumeBullet  — one bullet point, with extracted metadata
  ResumeSection — a section (experience/skills/summary/projects)
  ResumeData    — full resume, parsed into sections
  ResumeVariant — a tailored version for one job application

Parsing strategy (resume.txt → ResumeData):
  Uses heuristic section detection (capitalized headers + line patterns)
  No LLM needed for parsing — keeps it fast and free
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from pathlib import Path


# ---------------------------------------------------------------------------
# Atoms
# ---------------------------------------------------------------------------

@dataclass
class ResumeBullet:
    """
    One bullet point in a resume section.

    Metadata is extracted lazily (only when section optimizer needs it).
    """
    text:                 str
    skills_mentioned:     List[str]  = field(default_factory=list)  # extracted tech terms
    has_metric:           bool       = False                        # contains a number/%
    relevance_score:      float      = 0.0                         # vs current JD (0-1)
    was_modified:         bool       = False                        # track if rewritten
    original_text:        str        = ""                          # pre-rewrite text

    def mark_modified(self, new_text: str) -> None:
        if not self.original_text:
            self.original_text = self.text
        self.text         = new_text
        self.was_modified = True

    def diff(self) -> Optional[str]:
        """Return a one-line diff if this bullet was modified."""
        if not self.was_modified:
            return None
        return f"- {self.original_text}\n+ {self.text}"


@dataclass
class ResumeSection:
    """One section in a resume (Experience, Skills, Summary, etc.)"""
    type:     str              # "summary" | "skills" | "experience" | "projects" | "education" | "certs"
    title:    str              # display title (e.g. "Professional Experience")
    header:   str = ""         # company/role header for experience sections
    bullets:  List[ResumeBullet] = field(default_factory=list)
    raw_text: str = ""         # original unparsed text for fallback

    @property
    def modified_count(self) -> int:
        return sum(1 for b in self.bullets if b.was_modified)

    def all_text(self) -> str:
        return " ".join(b.text for b in self.bullets)


@dataclass
class ResumeData:
    """Full structured resume."""
    name:              str
    tagline:           str
    email:             str
    phone:             str
    linkedin:          str
    github:            str
    website:           str
    sections:          List[ResumeSection] = field(default_factory=list)
    all_skills:        List[str]           = field(default_factory=list)  # flat skill list
    source_path:       str                 = "data/resume.txt"

    # --- Section accessors ---

    def get_section(self, section_type: str) -> Optional[ResumeSection]:
        for s in self.sections:
            if s.type == section_type:
                return s
        return None

    def get_sections(self, section_type: str) -> List[ResumeSection]:
        return [s for s in self.sections if s.type == section_type]

    def all_bullets(self) -> List[ResumeBullet]:
        bullets = []
        for sec in self.sections:
            bullets.extend(sec.bullets)
        return bullets

    def modified_bullets(self) -> List[ResumeBullet]:
        return [b for b in self.all_bullets() if b.was_modified]

    def diff_report(self) -> str:
        """Human-readable diff of all modified bullets."""
        lines = []
        for sec in self.sections:
            modified = [b for b in sec.bullets if b.was_modified]
            if modified:
                lines.append(f"\n## {sec.title}")
                for b in modified:
                    lines.append(b.diff() or "")
        return "\n".join(lines) if lines else "No changes made."

    def clone(self) -> "ResumeData":
        """Deep clone for creating variants without mutating base."""
        import copy
        return copy.deepcopy(self)


@dataclass
class ResumeVariant:
    """A tailored resume variant for one specific job application."""
    job_id:          int
    job_title:       str
    company:         str
    pdf_path:        str
    ats_score:       float           # 0-100
    keywords_added:  List[str]       = field(default_factory=list)
    bullets_changed: int             = 0
    diff_summary:    str             = ""
    created_at:      str             = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Parser: resume.txt → ResumeData
# ---------------------------------------------------------------------------

class ResumeParser:
    """
    Parses resume.txt into structured ResumeData.

    Strategy (heuristic, no LLM):
      1. Split on SECTION HEADERS (all-caps lines or known titles)
      2. Within each section, split on bullet indicators (•, -, ·, digit.)
      3. Extract metadata from header block (name, email, phone, etc.)

    This is intentionally simple and robust — the resume.txt format is stable.
    """

    SECTION_KEYWORDS = {
        "summary":    ["professional summary", "summary", "objective", "profile", "about"],
        "skills":     ["technical skills", "skills", "technologies", "competencies"],
        "experience": ["professional experience", "experience", "work experience",
                       "employment history", "career history"],
        "projects":   ["key projects", "projects", "portfolio", "personal projects"],
        "education":  ["education", "academic", "qualifications", "degree"],
        "certs":      ["certifications", "certificates", "awards", "achievements",
                       "additional", "certifications & additional"],
    }

    @classmethod
    def parse_file(cls, path: str = "data/resume.txt") -> ResumeData:
        text = Path(path).read_text(encoding="utf-8")
        return cls.parse_text(text)

    @classmethod
    def parse_text(cls, text: str) -> ResumeData:
        lines = [l.rstrip() for l in text.splitlines()]

        # --- Header block: first ~5 lines ---
        name    = lines[0].strip() if lines else "Unknown"
        tagline = lines[1].strip() if len(lines) > 1 else ""
        contact = lines[2].strip() if len(lines) > 2 else ""

        email    = cls._extract_email(contact)
        phone    = cls._extract_phone(contact)
        linkedin = cls._extract_link(contact, "linkedin")
        github   = cls._extract_link(contact, "github")
        website  = cls._extract_link(contact, "portfolio") or cls._extract_link(contact, ".in")

        # --- Detect sections ---
        sections = cls._split_sections(lines[3:], text)

        # --- Flat skill list from skills section ---
        skills_section = next((s for s in sections if s.type == "skills"), None)
        all_skills     = cls._extract_skills_from_section(skills_section) if skills_section else []

        return ResumeData(
            name        = name,
            tagline     = tagline,
            email       = email,
            phone       = phone,
            linkedin    = linkedin,
            github      = github,
            website     = website,
            sections    = sections,
            all_skills  = all_skills,
            source_path = "data/resume.txt",
        )

    # ── Section splitting ─────────────────────────────────────────────────────

    @classmethod
    def _split_sections(cls, lines: List[str], full_text: str) -> List[ResumeSection]:
        sections: List[ResumeSection] = []
        current_type  = None
        current_title = ""
        current_lines: List[str] = []

        for line in lines:
            detected = cls._detect_section_type(line)
            if detected:
                # Save previous section
                if current_type and current_lines:
                    sections.extend(
                        cls._build_sections(current_type, current_title, current_lines)
                    )
                current_type  = detected
                current_title = line.strip()
                current_lines = []
            else:
                if current_type:
                    current_lines.append(line)

        # Final section
        if current_type and current_lines:
            sections.extend(cls._build_sections(current_type, current_title, current_lines))

        return sections

    @classmethod
    def _build_sections(
        cls, sec_type: str, title: str, lines: List[str]
    ) -> List[ResumeSection]:
        """
        For experience sections: may contain multiple job entries.
        Split on job title lines (Helvetica-Bold pattern: short line, title-cased).
        """
        if sec_type not in ("experience", "projects"):
            bullets = cls._extract_bullets(lines)
            return [ResumeSection(type=sec_type, title=title, bullets=bullets,
                                  raw_text="\n".join(lines))]

        # Split experience into sub-sections per role
        sub_sections: List[ResumeSection] = []
        current_header = ""
        current_bullets_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Heuristic: a job title line is short, title-cased, no bullet char
            if cls._looks_like_header(stripped):
                if current_bullets_lines:
                    sub_sections.append(ResumeSection(
                        type=sec_type, title=title, header=current_header,
                        bullets=cls._extract_bullets(current_bullets_lines),
                        raw_text="\n".join(current_bullets_lines),
                    ))
                    current_bullets_lines = []
                current_header = stripped
            else:
                current_bullets_lines.append(line)

        if current_bullets_lines:
            sub_sections.append(ResumeSection(
                type=sec_type, title=title, header=current_header,
                bullets=cls._extract_bullets(current_bullets_lines),
                raw_text="\n".join(current_bullets_lines),
            ))

        return sub_sections if sub_sections else [
            ResumeSection(type=sec_type, title=title,
                          bullets=cls._extract_bullets(lines), raw_text="\n".join(lines))
        ]

    @staticmethod
    def _extract_bullets(lines: List[str]) -> List[ResumeBullet]:
        bullets = []
        current = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Detect bullet start: •, -, ·, or (cid:127) from PDF extraction artifacts
            if re.match(r"^[•\-·]|^\(cid:\d+\)", stripped):
                if current:
                    bullets.append(ResumeBullet(
                        text         = _clean_bullet(current),
                        has_metric   = _has_metric(current),
                        skills_mentioned = _extract_tech_terms(current),
                    ))
                current = re.sub(r"^[•\-·]\s*|\(cid:\d+\)\s*", "", stripped)
            else:
                current = (current + " " + stripped).strip() if current else stripped

        if current:
            bullets.append(ResumeBullet(
                text         = _clean_bullet(current),
                has_metric   = _has_metric(current),
                skills_mentioned = _extract_tech_terms(current),
            ))
        return bullets

    # ── Heuristics ────────────────────────────────────────────────────────────

    @classmethod
    def _detect_section_type(cls, line: str) -> Optional[str]:
        """Detect if a line is a section header. Returns section type or None."""
        clean = line.strip().lower()
        for sec_type, keywords in cls.SECTION_KEYWORDS.items():
            if any(clean == kw or clean.startswith(kw) for kw in keywords):
                return sec_type
        return None

    @staticmethod
    def _looks_like_header(line: str) -> bool:
        """
        Heuristic: a job title line is:
          - Short (< 80 chars)
          - Not starting with a bullet
          - Title-cased or ALL-CAPS
          - Does NOT end with a comma (mid-sentence) or contain long text
        """
        if len(line) > 80:
            return False
        if re.match(r"^[•\-·]|\(cid:", line):
            return False
        words = line.split()
        if len(words) < 2:
            return False
        capitalized = sum(1 for w in words if w and w[0].isupper())
        return capitalized / len(words) >= 0.5

    @staticmethod
    def _extract_email(text: str) -> str:
        m = re.search(r"[\w.+\-]+@[\w.\-]+\.\w+", text)
        return m.group(0) if m else ""

    @staticmethod
    def _extract_phone(text: str) -> str:
        m = re.search(r"\b[\d]{10,}\b", text)
        return m.group(0) if m else ""

    @staticmethod
    def _extract_link(text: str, keyword: str) -> str:
        for token in text.replace("|", " ").split():
            if keyword.lower() in token.lower():
                return token.strip(".,;")
        return ""

    @staticmethod
    def _extract_skills_from_section(section: ResumeSection) -> List[str]:
        skills = []
        for bullet in section.bullets:
            skills.extend(_extract_tech_terms(bullet.text))
        return list(dict.fromkeys(skills))  # dedup, preserve order


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TECH_TERMS = re.compile(
    r"\b("
    r"Python|FastAPI|Django|Flask|Node\.?js|Express|React|TypeScript|JavaScript"
    r"|Vue|Angular|HTML5?|CSS3?|Redux|Zustand|Next\.?js"
    r"|PostgreSQL|MySQL|MongoDB|Redis|SQLite|Elasticsearch|DynamoDB"
    r"|AWS|GCP|Azure|Docker|Kubernetes|Terraform|CI/CD|GitHub Actions"
    r"|Celery|RabbitMQ|Kafka|gRPC|GraphQL|REST|RESTful|WebSocket"
    r"|Pandas|NumPy|scikit.?learn|TensorFlow|PyTorch|Langchain|LangGraph"
    r"|Git|Linux|Nginx|JWT|OAuth|Pydantic|SQLAlchemy|Alembic"
    r"|SOLID|OOP|MVC|Microservices|API|ETL|ML|AI|LLM"
    r"|C#|\.NET|Java|Go|Rust|Ruby|PHP|Scala|Kotlin|Swift"
    r")\b",
    re.IGNORECASE,
)

_METRIC_RE = re.compile(r"\b\d+[\d,]*\s*(%|Cr|M\+?|K\+?|x|X|ms|s\b|hours?|days?|weeks?)")


def _extract_tech_terms(text: str) -> List[str]:
    return list(dict.fromkeys(m.group(0) for m in _TECH_TERMS.finditer(text)))


def _has_metric(text: str) -> bool:
    return bool(_METRIC_RE.search(text))


def _clean_bullet(text: str) -> str:
    """Remove artifacts and normalize whitespace."""
    text = re.sub(r"\(cid:\d+\)", "", text)
    text = re.sub(r"fi\b", "fi", text)         # ligature artifact
    text = re.sub(r"\s+", " ", text)
    return text.strip()
