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
| `data/applications.md` | Application tracker — current pipeline state |
| `data/pipeline.md` | Pending job URLs to process |

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
