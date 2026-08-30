# NEXUS — Neural Execution for eXpert Unified Search
## Claude Code Agent Instructions

This is a job acquisition system. When operating in this repo, follow the routing below.

---

## Slash Command Routing

When the user types `/nexus <subcommand>`, route to the appropriate action:

| Command | Action |
|---------|--------|
| `/nexus` | Show all available commands (this table) |
| `/nexus tracker` | Run `python -m src.tracker` then display `data/applications.md` |
| `/nexus status <id> <Status>` | Run `python -m src.tracker --update <id> <Status>` then regenerate |
| `/nexus pipeline` | Read `data/pipeline.md`, process pending URLs (see Pipeline section) |
| `/nexus scan <query>` | Run job scraper: `python -m src.cli scan "<query>"` |
| `/nexus verify` | Run `python -m src.cli verify` — DB health check |
| `/nexus dedup` | Run `python -m src.cli dedup` — remove duplicate job entries |
| `/nexus normalize` | Run `python -m src.cli normalize` — fix non-canonical status values |
| `/nexus digest` | Run `python -m src.cli digest` — print weekly outreach digest |
| `/nexus deep <company>` | WebSearch company AI/engineering strategy + open roles + culture |
| `/nexus agents` | Run the 15-agent target-company pipeline: `python -m src.agents.orchestrator --stage daily`, then display `data/agent_run_report.md` |
| `/nexus agents tier1` | Same, restricted to Tier 1 companies: `python -m src.agents.orchestrator --stage daily --tiers 1` |
| `/nexus leads` | Run boolean/X-ray lead sourcing: `python -m src.agents.orchestrator --stage leads` |
| `/nexus networker <company>` | Find a real evidenced challenge + draft LinkedIn/X content: `python -m src.agents.orchestrator --stage networker --company "<company>"` |
| `/nexus prep <company>` | Run `python -m src.agents.orchestrator --stage interview-prep --company "<company>"` |
| `/nexus pitch <company>` | Build the WIN one-pager: `python -m src.agents.orchestrator --stage pitch --company "<company>"` |
| `/nexus mock <company>` | Generate mock-interview questions: `python -m src.agents.orchestrator --stage interview-questions --company "<company>"` |
| `/nexus negotiate <company> <offer_lpa>` | Comp benchmark + counter script: `python -m src.agents.orchestrator --stage negotiate-counter --company "<company>" --offer <offer_lpa>` |
| `/nexus learn` | Run `python -m src.agents.orchestrator --stage weekly-learning` — recalibrate tier weights from real reply data |
| `/nexus help` | Show this file |

### Status Values (canonical)
`Ready` · `Outreach` · `Applied` · `Replied` · `Interview` · `Offer` · `Rejected` · `Skip`

---

## Sources of Truth

ALWAYS read these before evaluating or generating content:

| File | Purpose |
|------|---------|
| `data/resume.txt` | Full resume — skills, experience, proof points |
| `config/profile.yml` | Candidate identity, target roles, compensation, narrative |
| `config/target_companies.yml` | Ranked target-company list with funding/hiring signals (labor-market research) |
| `config/boolean_queries.yml` | 30-query X-ray/boolean sourcing bank (ATS, YC, funding press, GitHub, YouTube, content) |
| `data/applications.md` | Application tracker — current pipeline state |
| `data/pipeline.md` | Pending job URLs to process |
| `docs/AGENT_STRATEGIES.md` | Rationale for each of the 15 target-company agents in `src/agents/` |

---

## Pipeline Processing (`/nexus pipeline`)

When processing `data/pipeline.md`:
1. Read the table — extract all rows where Status is empty or `pending`
2. For each URL:
   a. Fetch the job description (use WebFetch or Bash playwright if needed)
   b. Evaluate fit against `data/resume.txt` + `config/profile.yml`
   c. Report: company, role, match score (%), key matched skills, gaps, recommendation
3. After evaluating all, summarise: how many processed, top 3 by fit
4. Do NOT auto-apply or auto-send outreach — always surface results for user review

---

## Evaluation Framework

When evaluating a job description, score across these dimensions:

| # | Dimension | Weight |
|---|-----------|--------|
| 1 | Role match (skills vs JD) | 25% |
| 2 | Career level fit | 15% |
| 3 | Tech stack overlap | 20% |
| 4 | Remote / location | 10% |
| 5 | Company stage fit | 10% |
| 6 | Growth potential | 10% |
| 7 | Compensation vs target | 10% |

Score: 0–100%. Threshold for "worth applying": ≥65%.

---

## Global Rules

**NEVER:**
- Invent experience or metrics not in `data/resume.txt`
- Auto-submit applications or send emails without explicit approval
- Hardcode candidate metrics — always read from profile.yml / resume.txt
- Recommend applying to roles scoring below 50%

**ALWAYS:**
- Read `config/profile.yml` before evaluating compensation fit
- Cite specific lines from the resume when justifying match scores
- Regenerate `data/applications.md` after any status update
- Respect the canonical status list — no free-form status values

---

## Architecture Reference

```
NEXUS Pipeline
──────────────
Job Sources (JobSpy, Adzuna, ATS boards)
    ↓
src/scrapers/          — fetch raw job listings
    ↓
src/job_processor.py   — AI match scoring, content generation
    ↓
src/email_engine/      — email discovery (Hunter.io-style)
    ↓
src/contact_intelligence/ — decision-maker graph ranking
    ↓
src/personalization/   — company research + hook generation
    ↓
src/outreach/          — smart timing, A/B, follow-up scheduler
    ↓
src/feedback/          — self-improving feedback loop
    ↓
data/applications.md   — human-readable tracker
```

## Target-Company Agent Layer (`src/agents/`)

Fifteen strategy agents, purpose-built around `config/target_companies.yml`
(the ranked, research-backed company list) rather than the generic job-board
firehose above. They wrap the modules in the diagram above instead of
replacing them. Exposed over HTTP via `src/api/routers/agents_router.py`
(`/api/agents/*`, delegating to `src/services/agents_service.py`) for the
React dashboard. Full rationale in `docs/AGENT_STRATEGIES.md`.

```
1 SignalScoutAgent        — freshness-track funding/hiring signals per company
2 ATSHunterAgent          — probe Greenhouse/Lever/Ashby boards directly
3 FitScorerAgent          — CLAUDE.md rubric, deterministic, ≥65% = worth applying
4 ResumeTailorAgent       — Python/Django-first bullet reordering per JD
5 ContactMapperAgent      — wraps src/contact_intelligence, tier-gated + cached
6 OutreachComposerAgent   — wraps src/personalization, signal-seeded hooks
7 PriorityScheduleAgent   — fit + signal-freshness decay -> daily send queue (cap 8)
8 InterviewPrepAgent      — per-company dossier, triggered on Interview status
9 FeedbackStrategistAgent — learns whether Tier 1 really out-converts Tier 2/3
10 ChallengeSolverAgent   — finds a real, evidenced challenge (never invented)
11 QueryHunterAgent       — 30-query X-ray/boolean sourcing -> lead CRM table
12 InfluencerAgent        — drafts LinkedIn/X content, never auto-posts
13 PitcherAgent           — WIN (problem/solution/narrative) one-pager
14 InterviewerAgent       — mock Q&A + deterministic STAR-format feedback
15 NegotiatorAgent        — comp benchmarking + counter-offer script
```

Run: `python -m src.agents.orchestrator --stage daily`. Never auto-sends,
never scrapes LinkedIn/X/Google directly, never automates any social
platform — same hard rule as `/nexus pipeline` above, extended.
