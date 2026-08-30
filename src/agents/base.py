"""
base.py — Shared foundation for the nine target-company agents.

Every agent in src/agents/ follows the same DAG node contract already used
by src/contact_intelligence and src/personalization:

    Input:  AgentContext (+ agent-specific kwargs)
    Output: AgentResult   (typed, JSON-serialisable, .ok / .error)

Design goals:
  - Zero hard crashes without API keys / network — every agent degrades to
    a clearly-labelled fallback rather than raising.
  - Config (config/profile.yml, config/target_companies.yml) is the single
    source of truth. Agents NEVER invent company facts or candidate metrics.
  - Every agent is runnable standalone (`python -m src.agents.agent_0X_...`)
    for debugging, and composable via orchestrator.py for the full pipeline.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

log = logging.getLogger("nexus.agents")

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"
PROFILE_PATH = CONFIG_DIR / "profile.yml"
TARGET_COMPANIES_PATH = CONFIG_DIR / "target_companies.yml"
AGENT_STATE_DB = DATA_DIR / "agent_state.db"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required: pip install pyyaml")
    if not path.exists():
        raise FileNotFoundError(
            f"Missing config file: {path}. See config/profile.yml and "
            f"config/target_companies.yml in the repo for the expected shape."
        )
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _classify_theme(text: str) -> str:
    """Keyword heuristic used to bucket a proof point under the theme keys
    agents look up (security/performance/ownership/scale). Pure keyword
    matching on the person's own text — never invents new claims."""
    text_l = text.lower()
    if any(k in text_l for k in ("security", "auth", "access", "rbac", "compliance", "audit")):
        return "security"
    if any(k in text_l for k in ("ms", "query", "sql", "latency", "performance", "optimi")):
        return "performance"
    if any(k in text_l for k in ("transaction", "uptime", "dau", "scal", "volume")):
        return "scale"
    return "ownership"


def _normalize_profile(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Adapts config/profile.yml (whichever schema is currently on disk)
    into the shape src/agents/*.py expects, by computing compatibility keys
    from whatever real fields are present. Never fabricates content —
    every derived value is a direct transform/aggregation of something
    already in the file. Existing keys are never overwritten, so a future
    profile.yml written in the "old" flat schema keeps working unchanged.
    """
    profile = dict(raw)  # shallow copy — don't mutate the loaded YAML in place

    candidate = dict(profile.get("candidate", {}))
    if "name" not in candidate and "full_name" in candidate:
        candidate["name"] = candidate["full_name"]
    profile["candidate"] = candidate

    narrative_raw = profile.get("narrative", {})
    proof_points_raw = narrative_raw.get("proof_points", [])
    # New schema: list of {name, metric, stack?, url?} dicts.
    # Old schema: proof_points_by_theme dict already — leave untouched if present.
    differentiators = narrative_raw.get("differentiators")
    if differentiators is None and proof_points_raw:
        differentiators = [
            f"{p.get('name', '')}: {p.get('metric', '')}".strip(": ").strip()
            for p in proof_points_raw if p.get("name") or p.get("metric")
        ]

    proof_points_by_theme = narrative_raw.get("proof_points_by_theme")
    if proof_points_by_theme is None and proof_points_raw:
        proof_points_by_theme = {}
        for p in proof_points_raw:
            sentence = f"{p.get('name', '')}: {p.get('metric', '')}".strip(": ").strip()
            if not sentence:
                continue
            theme = _classify_theme(f"{p.get('name', '')} {p.get('metric', '')}")
            proof_points_by_theme.setdefault(theme, sentence)

    one_liner = narrative_raw.get("one_liner")
    if one_liner is None:
        summary = narrative_raw.get("summary", "")
        one_liner = summary.strip().split(". ")[0].strip()
        if one_liner and not one_liner.endswith("."):
            one_liner += "."

    profile["narrative"] = {
        **narrative_raw,
        "one_liner": one_liner or "",
        "proof_points_by_theme": proof_points_by_theme or {},
    }

    positioning_raw = profile.get("positioning", {})
    headline = positioning_raw.get("headline") or narrative_raw.get("headline", "")
    lead_with = positioning_raw.get("lead_with")
    if lead_with is None:
        lead_with = profile.get("tech_stack", {}).get("strong", [])
    seniority = positioning_raw.get("seniority")
    if seniority is None:
        primary_roles = " ".join(profile.get("target_roles", {}).get("primary", []))
        seniority = ("Senior/Staff (per config/profile.yml target_roles)"
                     if any(w in primary_roles for w in ("Senior", "Staff", "Lead"))
                     else "Mid-level")
    profile["positioning"] = {
        **positioning_raw,
        "headline": headline,
        "lead_with": lead_with,
        "differentiators": differentiators or positioning_raw.get("differentiators", []),
        "seniority": seniority,
    }

    target_raw = profile.get("target", {})
    roles = target_raw.get("roles")
    if roles is None:
        target_roles_cfg = profile.get("target_roles", {})
        roles = list(dict.fromkeys(
            target_roles_cfg.get("primary", []) + target_roles_cfg.get("secondary", [])
        ))
    locations = target_raw.get("locations")
    if locations is None:
        loc_prefs = profile.get("location_preferences", {})
        locations = list(loc_prefs.get("on_site_cities", []))
        if loc_prefs.get("remote"):
            locations.append("Remote")
    profile["target"] = {**target_raw, "roles": roles or [], "locations": locations or []}

    comp_raw = profile.get("compensation", {})
    target_min = comp_raw.get("target_ctc_lakhs_min")
    target_max = comp_raw.get("target_ctc_lakhs_max")
    if target_min is None:
        target_min = comp_raw.get("minimum_inr_lpa")
    if target_max is None:
        target_max = comp_raw.get("target_inr_lpa")
    profile["compensation"] = {**comp_raw, "target_ctc_lakhs_min": target_min, "target_ctc_lakhs_max": target_max}

    return profile


@dataclass
class AgentContext:
    """Loaded once per run, passed to every agent.

    Holds the candidate profile and the target-company list so no agent
    ever needs to re-read/re-parse config on its own.
    """

    profile: Dict[str, Any] = field(default_factory=dict)
    companies: List[Dict[str, Any]] = field(default_factory=list)
    sector_context: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, profile_path: Path = PROFILE_PATH,
              companies_path: Path = TARGET_COMPANIES_PATH) -> "AgentContext":
        profile = _normalize_profile(_load_yaml(profile_path))
        target_cfg = _load_yaml(companies_path)
        return cls(
            profile=profile,
            companies=target_cfg.get("companies", []),
            sector_context=target_cfg.get("sector_context", {}),
        )

    def company(self, name: str) -> Optional[Dict[str, Any]]:
        """Case-insensitive lookup by name or alias."""
        name_l = name.lower().strip()
        for c in self.companies:
            if c.get("name", "").lower() == name_l:
                return c
            if any(a.lower() == name_l for a in c.get("aka", [])):
                return c
        return None

    def companies_by_tier(self, tier: Optional[int] = None) -> List[Dict[str, Any]]:
        if tier is None:
            return sorted(self.companies, key=lambda c: c.get("tier", 99))
        return [c for c in self.companies if c.get("tier") == tier]


# ---------------------------------------------------------------------------
# Result envelope
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    agent: str
    ok: bool
    summary: str
    data: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)


class BaseAgent:
    """Subclass and implement `run()`. Use `self.log` for structured logging."""

    name: str = "base_agent"

    def __init__(self, context: AgentContext):
        self.context = context
        self.log = logging.getLogger(f"nexus.agents.{self.name}")

    def run(self, **kwargs) -> AgentResult:  # pragma: no cover - overridden
        raise NotImplementedError

    def _timed(self, fn, *args, **kwargs) -> AgentResult:
        """Wrap `fn` (returns AgentResult) with duration tracking + error capture."""
        start = time.monotonic()
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - agents must never crash the pipeline
            self.log.exception("Agent %s failed", self.name)
            result = AgentResult(agent=self.name, ok=False, summary=f"Error: {exc}")
        result.duration_ms = round((time.monotonic() - start) * 1000, 1)
        return result


# ---------------------------------------------------------------------------
# Lightweight local state store (sqlite) — used by agents that need to
# remember things between runs (signals seen, priority scores, learned
# weights) without requiring the full Postgres/production DB setup.
# ---------------------------------------------------------------------------

def get_state_conn():
    import sqlite3
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AGENT_STATE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS company_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            detail TEXT,
            source TEXT,
            signal_date TEXT,
            discovered_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS open_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            location TEXT,
            ats_source TEXT,
            fit_score REAL,
            discovered_at REAL NOT NULL,
            UNIQUE(company, title, url)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS priority_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role_title TEXT,
            priority_score REAL NOT NULL,
            reason TEXT,
            queued_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS strategy_weights (
            key TEXT PRIMARY KEY,
            weight REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    conn.commit()
    return conn
