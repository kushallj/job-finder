# Career-Ops: How It's Built Into Your Job-Finder Repo

## Overview

Your job-finder repository is fully integrated with **career-ops**, an AI-powered job search pipeline powered by Claude. This document explains the architecture, features, and how each component works together.

---

## 🎯 System Purpose

Career-ops automates the entire job search workflow:

```
Paste a Job URL or Description
        ↓
    Evaluation (A-F scoring)
        ↓
    Generate Report & PDF
        ↓
    Track Application
        ↓
    Monitor Progress
```

Instead of manually tracking applications in a spreadsheet, you get an AI-powered pipeline that evaluates fit, generates tailored CVs, and maintains an audit-ready tracker.

---

## 📁 Repository Structure & How It's Organized

### Core Configuration Files

```
repo-root/
├── CLAUDE.md                 # Agent instructions (defines how Claude behaves)
├── cv.md                     # Your CV in markdown (source of truth for CV data)
├── config/
│   └── profile.yml           # Your profile, target roles, identity, proof points
├── portals.yml               # Job portal configuration (45+ companies)
└── package.json              # Node.js dependencies (Playwright, etc.)
```

**Key Principle:** These are your **configuration sources of truth**. Everything else is derived from them.

---

## 🔄 How Each Feature Works

### 1️⃣ **Auto-Pipeline: Paste → Evaluate → PDF → Track**

This is the primary workflow. When you paste a job URL or description:

```
User Action: /career-ops {paste URL or JD text}
                    ↓
        ┌───────────────────────────┐
        │  CLAUDE.md Router         │
        │  Routes to auto-pipeline  │
        └───────┬───────────────────┘
                ↓
    ┌────────────────────────────────────┐
    │  modes/auto-pipeline.md            │
    │  (executes full evaluation)        │
    └───────┬────────────────────────────┘
            ├──→ modes/_shared.md         (evaluation framework)
            ├──→ cv.md                    (reads your CV)
            ├──→ config/profile.yml       (reads your profile)
            │
            ├──────────────────────┬──────────────────────┐
            ↓                      ↓                      ↓
        Save Report           Generate PDF           Create Tracker Entry
      (reports/*.md)       (output/*.pdf)        (tracker-additions/*.tsv)
            │                    │                      │
            └────────────────────┴──────────────────────┘
                        ↓
            data/applications.md  (merged tracker)
```

**What happens:**
1. Claude reads the JD (from URL or text)
2. Classifies it into one of 6 archetypes (Senior SE, AI Manager, etc.)
3. Evaluates across 10 dimensions → A-F score (1-5 scale)
4. Generates a detailed report with recommendations
5. Creates an ATS-optimized PDF from your CV
6. Writes a TSV entry to `batch/tracker-additions/`
7. `merge-tracker.mjs` automatically merges it into `data/applications.md`

**Files involved:**
- **Input:** URL from pipeline or pasted text
- **Output:** 
  - `reports/{###}-{company}-{YYYY-MM-DD}.md` - Evaluation report
  - `output/cv-{company}-{date}.pdf` - Generated PDF
  - `batch/tracker-additions/{num}-{slug}.tsv` - Tracker entry (pending merge)

---

### 2️⃣ **Portal Scanner: Auto-Discover New Offers**

The scanner runs against 45+ pre-configured companies:

```
/career-ops scan
        ↓
    modes/scan.md
        ↓
    ┌─────────────────────────────────────────┐
    │ For each company in portals.yml:        │
    │  • Query Ashby, Greenhouse, Lever       │
    │  • Check company career pages           │
    │  • Filter by role_filter.positive       │
    └─────────────────────────────────────────┘
        ↓
    New URLs added to data/pipeline.md (inbox)
        ↓
    /career-ops pipeline  (process inbox)
```

**Pre-configured companies include:**
- **AI Labs:** Anthropic, OpenAI, Mistral, Cohere, LangChain, Pinecone
- **Voice AI:** ElevenLabs, PolyAI, Parloa, Hume AI, Deepgram, Vapi
- **AI Platforms:** Retool, Airtable, Vercel, Temporal, Glean, Arize AI
- **Contact Center:** Ada, LivePerson, Sierra, Decagon, Talkdesk, Genesys
- **Enterprise:** Salesforce, Twilio, Gong, Dialpad
- **LLMOps:** Langfuse, Weights & Biases, Lindy, Cognigy, Speechmatics
- **Automation:** n8n, Zapier, Make.com
- **European:** Factorial, Attio, Tinybird, Clarity AI, Travelperk

**Customization:**
```yaml
# portals.yml example
companies:
  Anthropic:
    board: "ashby"  # Greenhouse, Lever, or direct URL
    title_filter:
      positive: ["Senior", "Staff", "Python", "Backend"]
      negative: ["Intern", "Support"]
```

---

### 3️⃣ **Pipeline Processor: Handle Inbox**

`data/pipeline.md` is your job inbox.

```
data/pipeline.md
┌────────────────────────────┐
│ | Company | URL | Note |   │
│ | Acme    | ... | ...  |   │
│ | Beta    | ... | ...  |   │
└────────────────────────────┘
        ↓
    /career-ops pipeline
        ↓
    Process each URL through auto-pipeline
        ↓
    Updates moved from pipeline.md
    Reports created, PDFs generated
```

---

### 4️⃣ **Batch Processing: Evaluate 10+ Offers in Parallel**

For processing multiple offers at once:

```
/career-ops batch
        ↓
    modes/batch.md
        ↓
    batch/batch-runner.sh (orchestrator)
        ↓
    ┌──────────────────────────┐
    │ N parallel workers       │
    │ (claude -p instances)    │
    │ Each runs batch-prompt.md│
    └──────────────────────────┘
        ↓
    All produce reports, PDFs, tracker TSVs in parallel
        ↓
    merge-tracker.mjs consolidates results
```

**Efficiency:** Process 10 offers in ~90 seconds instead of 10+ minutes.

---

### 5️⃣ **Tracker: Your Single Source of Truth**

`data/applications.md` is a Markdown table:

```markdown
| # | Date | Company | Role | Score | Status | PDF | Report | Notes |
|---|------|---------|------|-------|--------|-----|--------|-------|
| 1 | 2026-04-06 | Anovium | Senior Full Stack Eng | 4.5/5 | Evaluada | ❌ | [1](reports/001...) | Exact match |
```

**Canonical Statuses** (defined in `templates/states.yml`):
- `Evaluated` - Report done, pending your decision
- `Applied` - Application sent
- `Responded` - Company replied
- `Interview` - In interview process
- `Offer` - Offer received
- `Rejected` - Company rejected
- `Discarded` - You declined or offer closed
- `SKIP` - Doesn't fit, don't apply

**Pipeline Integrity Scripts:**
```bash
node merge-tracker.mjs        # Merge batch TSV additions
node verify-pipeline.mjs      # Health check
node dedup-tracker.mjs        # Remove duplicates
node normalize-statuses.mjs   # Standardize status values
```

---

## 📋 Evaluation Framework (A-F Blocks)

When Claude evaluates an offer, it analyzes 6 blocks:

### Block A: Role Summary
- What is this role actually about?
- How rare / how many competitors?
- Company scale, funding, trajectory
- Remote policy and location requirement

### Block B: CV Match
- How well does your CV align?
- Specific gaps and how to address them
- Which keywords from the JD to emphasize

### Block C: Level Strategy
- Is this the right career level for you?
- Growth potential? Downleveling risk?
- Compensation vs. market rate
- Title inflation/deflation assessment

### Block D: Compensation Research
- Base salary market range
- Equity/stock options typical
- Bonus structure
- Total comp benchmarks

### Block E: CV Personalization Plan
- Which projects to highlight
- Which metrics to emphasize
- Which skills to prioritize
- ATS keyword injection strategy

### Block F: Interview Prep (STAR+R Stories)
- What stories from interview-prep/story-bank.md apply?
- New stories to develop for this company
- Red flags and how to handle them

### Scoring: 10 Weighted Dimensions

The system scores you on:
1. **Role Match** - How well your skills fit
2. **Career Level** - Is this the right level?
3. **Compensation** - Is the range acceptable?
4. **Location/Remote** - Does it fit your preferences?
5. **Tech Stack** - How much do you like the tech?
6. **Company Stage** - (Startup vs. Scale-up vs. Enterprise) alignment
7. **Growth Potential** - Will this role grow your career?
8. **Culture Fit** - Based on company research
9. **Application Effort** - How hard to get the job?
10. **Negotiation Headroom** - Can you improve the offer?

**Final Score:** Weighted average = A-F (1-5 scale)

---

## 🎓 Interview Story Bank

`interview-prep/story-bank.md` accumulates **STAR+Reflection** stories:

```markdown
# Story Bank

## Story 1: Scale Python Backend to 10K Users
**Situation:** Monolithic Django app, 100ms p99 latency
**Task:** Reduce latency and support growth
**Action:** Async FastAPI migration, Redis caching, query optimization
**Result:** 75% query improvement, 50ms p99, handled 10x traffic spike
**Reflection:** Learned importance of profiling before premature optimization
```

Each evaluation can reference relevant stories. By the end of your search, you'll have 5-10 master stories that answer most behavioral questions.

---

## 📄 PDF Generation

Your CV gets **personalized per job**:

```
cv.md (master CV)
    ↓
cv.md + JD keywords analysis
    ↓
templates/cv-template.html (design template)
    ↓
generate-pdf.mjs (Playwright)
    ↓
output/cv-{company}-{date}.pdf (ATS-optimized)
```

**Key Features:**
- Space Grotesk + DM Sans typography
- Keyword injection from JD analysis
- Maintains ATS compatibility
- Two-column resume format
- Proof points with metrics highlighted

---

## 🔧 Configuration & Customization

### Your Profile (`config/profile.yml`)

```yaml
candidate:
  full_name: "Kushall Jain"
  email: "Kushall.jain07@gmail.com"
  location: "Delhi, India"
  linkedin: "https://www.linkedin.com/in/..."
  portfolio_url: "https://kushall.in"

target_roles:
  primary:
    - "Senior Software Engineer"
    - "Staff Python Engineer"
  archetypes:
    - name: "Software Engineer"
      level: "Senior/Staff"
      fit: "primary"

narrative:
  headline: "Full Stack Python Developer — Django, FastAPI, React.js"
  exit_story: "3+ years building..."
  superpowers:
    - "Python backend systems"
    - "Database optimization"
    - "Full-stack delivery"
  proof_points:
    - name: "job finder"
      url: "https://github.com/kushallj/job-finder"
      hero_metric: "job fetching using python script"
```

This is read by **every** evaluation. All metrics come from here and `cv.md`.

### Portal Configuration (`portals.yml`)

```yaml
companies:
  Anthropic:
    board: "ashby"
    title_filter:
      positive: ["Senior", "Staff", "Python"]
      negative: ["Intern"]
    
  "Company Name":
    board: "greenhouse"  # or "lever", "direct_url", "workable", etc.
```

---

## 🚀 All Available Commands

| Command | What it does |
|---------|------------|
| `/career-ops` | Show all commands (discovery mode) |
| `/career-ops {paste JD}` | Full auto-pipeline |
| `/career-ops scan` | Scan portals for new offers |
| `/career-ops pdf` | Generate ATS-optimized CV only |
| `/career-ops batch` | Batch evaluate 10+ offers |
| `/career-ops tracker` | View application status |
| `/career-ops apply` | Fill application forms with AI |
| `/career-ops pipeline` | Process pending URLs from inbox |
| `/career-ops contacto` | LinkedIn outreach message |
| `/career-ops deep` | Deep company research |
| `/career-ops training` | Evaluate a course/cert |
| `/career-ops project` | Evaluate a portfolio project |
| `/career-ops oferta` | Single offer evaluation (A-F only) |
| `/career-ops ofertas` | Compare and rank multiple offers |

---

## 📊 Modes Directory

Each mode is a self-contained prompt:

```
modes/
├── _shared.md          # Shared context (evaluation framework, archetypes, rules)
├── auto-pipeline.md    # Full pipeline: report + PDF + tracker
├── batch.md            # Batch processing orchestrator
├── oferta.md           # Single evaluation only
├── ofertas.md          # Compare multiple offers
├── pdf.md              # PDF generation only
├── pipeline.md         # Process pipeline.md inbox
├── scan.md             # Portal scanner
├── apply.md            # Application form filler
├── contacto.md         # LinkedIn outreach
├── deep.md             # Company deep research
├── training.md         # Course/cert evaluation
├── project.md          # Portfolio project evaluation
├── tracker.md          # Tracker viewer
```

Each mode loads `_shared.md` for context (evaluation framework, archetypes, scoring).

---

## 🔐 Data Flow & Privacy

```
Your Data (cv.md, profile.yml, story-bank.md)
        ↓
    Modes (modes/*.md) + Claude
        ↓
    Reports (reports/*.md)  — Plain markdown, YOUR disk
    PDFs (output/*.pdf)     — Encrypted PDFs, YOUR disk
    Tracker (data/*.md)     — Markdown table, YOUR disk
```

**All data stays on your machine.** Reports, PDFs, and trackers are gitignored and never leave your environment.

---

## 🛠️ Scripts for Pipeline Maintenance

```bash
# After evaluations, merge tracker additions
node merge-tracker.mjs

# Health check: verify all reports, links, statuses
node verify-pipeline.mjs

# Remove duplicate company+role entries
node dedup-tracker.mjs

# Normalize status aliases → canonical values
node normalize-statuses.mjs

# Check CV and profile consistency
node cv-sync-check.mjs
```

---

## 📈 Dashboard TUI (Optional)

For visual browsing of your pipeline:

```bash
cd dashboard
go build -o career-dashboard .
./career-dashboard
```

Features:
- 6 filter tabs (by status, archetype, score, etc.)
- 4 sort modes (date, score, company, etc.)
- Grouped/flat view
- Lazy-loaded report previews
- Inline status changes

---

## 🎯 Intended Workflow

1. **Setup once:**
   - Fill `config/profile.yml`
   - Create/paste your `cv.md`
   - Customize `portals.yml` with your target companies

2. **Daily/Weekly:**
   - `/career-ops scan` → discover new offers
   - Or paste individual job URLs
   - Review evaluations in `reports/`
   - Decide: Apply or Skip

3. **When applying:**
   - Use `/career-ops apply` to fill forms
   - Reference interview stories from `interview-prep/story-bank.md`
   - Track status in `data/applications.md`

4. **Weekly maintenance:**
   - Run `node verify-pipeline.mjs` to check integrity
   - Update tracker status as you hear back
   - Accumulate interview stories

---

## 🧠 Key Principles

1. **Quality over Quantity** — This system helps you apply to 5-10 great fits instead of 50 weak fits.

2. **Single Source of Truth** — `cv.md` and `profile.yml` are read by every evaluation. No hardcoded metrics.

3. **Audit Trail** — Every evaluation creates a report. You can review why you rated a company a 4.5/5.

4. **Customizable** — The archetypes, scoring weights, modes, and commands are all designed to be edited. Just ask Claude to change them.

5. **Ethical** — Never auto-submit applications. Always review and approve before sending.

---

## 📚 Further Reading

- [README.md](README.md) — Feature overview
- [docs/SETUP.md](docs/SETUP.md) — Full setup guide
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Detailed system architecture
- [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md) — How to personalize the system
- [CONTRIBUTING.md](CONTRIBUTING.md) — How to contribute improvements

---

## 🎓 Example: Full Auto-Pipeline Walkthrough

You paste this URL: `https://jobs.ashby.com/anthropic/open/xxx`

```
Step 1: Claude reads modes/auto-pipeline.md + modes/_shared.md
Step 2: Playwright fetches the JD from that URL
Step 3: Claude classifies → "AI Platform Engineer" (archetype)
Step 4: Claude reads cv.md + profile.yml + article-digest.md
Step 5: Evaluates across 10 dimensions → 4.2/5 score
Step 6: Writes report to reports/005-anthropic-2026-04-07.md
Step 7: generate-pdf.mjs creates output/cv-anthropic-2026-04-07.pdf
        → Keywords injected based on JD analysis
Step 8: Writes TSV to batch/tracker-additions/005-anthropic.tsv
Step 9: Next time you run anything, merge-tracker.mjs auto-merges it
        → data/applications.md now has the entry
Step 10: You review the report and decide:
         → Apply? Update status to "Applied"
         → Skip? Update status to "SKIP"
         → Follow up? Status becomes "Interview", etc.
```

Total time: ~30 seconds for Claude, ~10 seconds for PDF generation.

---

## 🔗 Related Projects

- **[cv-santiago](https://github.com/santifer/cv-santiago)** — Open-source portfolio website (fork and make it yours)
- **[claude](https://claude.ai)** — Claude Code (the AI agent powering this system)

---

Created by **Kushall Jain** | Built with Claude Code | Forked from [santifer/career-ops](https://github.com/santifer/career-ops)
