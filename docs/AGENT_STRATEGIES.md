# The Nine Agent Strategies

This document explains the *why* behind each agent in `src/agents/`. It's the
companion to `config/target_companies.yml` (the researched company list,
compiled Aug 29, 2026) and `config/profile.yml` (your positioning).

Every agent follows the same contract: input `AgentContext`, output
`AgentResult` (`ok`, `summary`, `data`, `warnings`). No agent auto-sends
anything — that rule is inherited from `CLAUDE.md` and enforced by the
orchestrator, which only ever writes `data/agent_run_report.md` for you to
review.

---

## 1. Signal Scout — `agent_01_signal_scout.py`

**Problem it solves:** timing. Outreach sent 2-4 weeks after a funding round,
IPO filing, or leadership hire reads completely differently than a cold email
to a company that hasn't been in the news in a year.

**What it does:** loads the curated signals already baked into
`config/target_companies.yml`, tracks them in `data/agent_state.db`, and
classifies companies as "hot" (signal < 45 days old) or "stale" (> 180 days,
needs re-verification). Exposes `ingest_signal()` so a human or Claude Code
(`/nexus deep <company>`) can drop in a freshly-found signal without editing
YAML by hand.

**It deliberately does not scrape the web itself** — that's
`src/personalization/company_researcher.py`'s job, and duplicating it would
just be two things that can drift out of sync.

## 2. ATS Hunter — `agent_02_ats_hunter.py`

**Problem it solves:** LinkedIn/Naukri postings are noisy, reposted, and
often stale by the time you see them. A company's own ATS board is the
fastest, least-gamed source.

**What it does:** for every target company, generates plausible board slugs
from its name/domain/aliases and probes the free public JSON APIs of
Greenhouse, Lever, and Ashby (no auth needed). Matches titles against your
target-role keywords from `config/profile.yml`. 403/404s are expected and
silent — most companies won't be on a given ATS, that's fine.

## 3. Fit Scorer — `agent_03_fit_scorer.py`

**Problem it solves:** consistent, explainable scoring instead of gut-feel.

**What it does:** implements the exact weighted rubric already defined in
`CLAUDE.md` (role match 25%, career level 15%, tech stack 20%, location 10%,
company stage 10%, growth potential 10%, compensation 10%). Deterministic,
no LLM call — cheap enough to run against every ATS-Hunter result. Enforces
the hard rule: never recommend applying below 50%, "worth applying" is ≥65%.

## 4. Resume Tailor — `agent_04_resume_tailor.py`

**Problem it solves:** the positioning mismatch the labor-market analysis
found — your resume headline led with Node.js while every production
backend artifact is Django/FastAPI.

**What it does:** re-ranks the `differentiators` list in `config/profile.yml`
by keyword overlap with the specific job description, and reframes the
headline (e.g. foregrounds the security angle if the JD mentions auth/RBAC).
Tier 1 (deterministic) always runs; Tier 2 (LLM polish via
`UnifiedAIService`) only smooths phrasing — it is never allowed to add facts.

## 5. Contact Mapper — `agent_05_contact_mapper.py`

**Problem it solves:** generic `careers@` inboxes convert far worse than the
actual hiring manager or a referral path.

**What it does:** a thin, budget-aware wrapper around the existing
`src/contact_intelligence.IntelligenceEngine` (graph-based PageRank contact
ranking). Adds two things that engine doesn't have on its own: tier-gating
(skips Tier-3 "Low probability" companies by default, so you don't burn
contact-discovery API budget on the watch-list) and a 7-day cache so the
daily pipeline doesn't re-hit external APIs for the same company/role.

## 6. Outreach Composer — `agent_06_outreach_composer.py`

**Problem it solves:** the strongest hook type in
`src/personalization/hook_generator.py` is `COMPANY_SIGNAL` — but it's only
as good as what you feed it. Generic "I saw you're hiring" openers are weak.

**What it does:** feeds the *exact* funding/IPO/leadership signal from
`config/target_companies.yml` into a `CompanyProfile.growth_signals`, then
calls the existing `HookGenerator` + `EmailComposer` for real. Falls back to
a deterministic template (still signal-seeded) if the full personalization
stack isn't importable — never crashes the pipeline.

## 7. Priority Scheduler — `agent_07_priority_scheduler.py`

**Problem it solves:** fit score alone ignores timing, and you can't email
all 15+ target companies in one day without it reading as spam.

**What it does:** combines fit score + signal-freshness (exponential decay,
30-day half-life) + a tier floor boost + a *learned* multiplier from Agent 9
into one `priority_score`, then caps the day's send queue at 8. Writes the
queue to `data/agent_state.db` for auditability.

## 8. Interview Prep — `agent_08_interview_prepper.py`

**Problem it solves:** once a company actually replies, generic "tell me
about yourself" prep isn't good enough — you want to reference their real
situation and know what they're likely to probe for.

**What it does:** *not* part of the daily pipeline — triggered manually
once an application moves to `Interview` status. Combines the target-company
signal history, live GitHub/blog/HN research (via
`CompanyResearcher`, cached 7 days), and industry-informed heuristics (e.g.
`fintech-lending` → "credit-scoring/rules-engine design, auth & RBAC") into
one markdown dossier that also maps your own proof points to likely
interview focus areas.

## 9. Feedback Strategist — `agent_09_feedback_strategist.py`

**Problem it solves:** "Tier 1 = High hiring probability" is a one-time
research judgment. This agent turns it into a testable, self-correcting
assumption instead of a static label forever.

**What it does:** distinct from the existing `src/feedback/feedback_loop.py`
(which learns hook-type and send-hour weights) — this agent specifically
tests whether Tier 1 companies *actually* out-convert Tier 2/3 in practice,
using real `OutreachRecord` reply data joined against
`config/target_companies.yml` tiers. Requires ≥5 sends per tier before
touching weights (`MIN_SAMPLE_SIZE`), and dampens each update
(`DAMPENING = 0.5`) so a lucky/unlucky early batch can't wildly swing
priorities. Writes `tier:N` multipliers straight into the table Agent 7
reads.

---

## Running it

```bash
# Full daily pipeline (Signal Scout -> ATS Hunter -> Fit Scorer ->
# Priority Scheduler -> Resume Tailor -> Contact Mapper -> Outreach Composer)
python -m src.agents.orchestrator --stage daily

# Restrict to Tier 1 companies only (highest hiring probability)
python -m src.agents.orchestrator --stage daily --tiers 1

# Once a company replies and you have an interview
python -m src.agents.orchestrator --stage interview-prep --company Perfios --role "Backend Software Engineer"

# Run weekly (or via a cron alongside scripts/nexus_cron.sh) to recalibrate
# tier weights from real reply-rate data
python -m src.agents.orchestrator --stage weekly-learning
```

Every agent is also runnable standalone for debugging:
`python -m src.agents.agent_0N_whatever`.

## What this does NOT do

- Does not auto-apply or auto-send email (same hard rule as `/nexus pipeline`).
- Does not invent candidate metrics — everything traces back to
  `data/resume.txt` / `config/profile.yml`.
- Does not scrape company signals live by default — `config/target_companies.yml`
  is the source of truth until you refresh it (manually, or via
  `/nexus deep <company>` + `SignalScoutAgent.ingest_signal()`).
